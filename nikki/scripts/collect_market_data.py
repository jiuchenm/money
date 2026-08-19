from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import math
import statistics
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
USER_AGENT = "NikkiMarketDashboard/1.0 (+https://github.com/jiuchenm/money)"

GROUPS = {
    "nasdaq": {
        "title": "美股与纳指",
        "symbols": {"^NDX": "Nasdaq 100", "QQQ": "QQQ", "SOXX": "Semiconductors", "SPY": "S&P 500"},
    },
    "rates_fx": {
        "title": "利率与货币",
        "symbols": {"DX-Y.NYB": "Dollar Index", "CNY=X": "USD/CNY", "^TNX": "US 10Y yield", "TLT": "Long Treasury"},
    },
    "metals": {
        "title": "黄金与金属",
        "symbols": {"GC=F": "Gold", "SI=F": "Silver", "HG=F": "Copper", "GLD": "Gold ETF"},
    },
    "energy": {
        "title": "原油与能源",
        "symbols": {"CL=F": "WTI", "BZ=F": "Brent", "NG=F": "Natural Gas", "XLE": "US Energy"},
    },
    "risk": {
        "title": "风险与信用",
        "symbols": {"^VIX": "VIX", "HYG": "High Yield", "LQD": "Investment Grade", "RSP": "S&P Equal Weight"},
    },
    "hong_kong": {
        "title": "港股",
        "symbols": {"^HSI": "Hang Seng", "HSTECH.HK": "Hang Seng TECH", "2800.HK": "Tracker Fund", "3033.HK": "Hang Seng TECH ETF"},
    },
    "a_share": {
        "title": "A股",
        "symbols": {"000001.SS": "上证指数", "000300.SS": "沪深300", "399006.SZ": "创业板指", "000852.SS": "中证1000"},
    },
    "rotation": {
        "title": "市场风向",
        "symbols": {"IWM": "US Small Cap", "XLK": "US Technology", "XLP": "US Staples", "XLU": "US Utilities"},
    },
}

TENCENT_ALIASES = {
    "HSTECH.HK": "hkHSTECH",
    "399006.SZ": "sz399006",
    "000852.SS": "sh000852",
}


def fetch_json(url: str, timeout: int = 20) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def summarize_rows(symbol: str, rows: list[tuple[str, float]], source: str) -> dict[str, Any]:
    if len(rows) < 2:
        raise ValueError(f"insufficient data for {symbol}")
    values = [row[1] for row in rows]
    latest = values[-1]
    peak = max(values)

    def change(days: int) -> float | None:
        if len(values) <= days:
            return None
        return (latest / values[-days - 1] - 1) * 100

    def sma(days: int) -> float | None:
        if len(values) < days:
            return None
        return statistics.fmean(values[-days:])

    returns = [math.log(values[i] / values[i - 1]) for i in range(1, len(values)) if values[i - 1] > 0]
    volatility = statistics.stdev(returns[-20:]) * math.sqrt(252) * 100 if len(returns) >= 20 else None
    spark_rows = rows[-90:]
    step = max(1, len(spark_rows) // 30)
    sparkline = [{"date": date, "value": round(value, 4)} for date, value in spark_rows[::step]]
    if sparkline[-1]["date"] != spark_rows[-1][0]:
        sparkline.append({"date": spark_rows[-1][0], "value": round(spark_rows[-1][1], 4)})
    return {
        "symbol": symbol,
        "market_date": rows[-1][0],
        "value": round(latest, 4),
        "change_1d": round(change(1), 2),
        "change_5d": round(change(5), 2) if change(5) is not None else None,
        "change_20d": round(change(20), 2) if change(20) is not None else None,
        "drawdown_1y": round((latest / peak - 1) * 100, 2),
        "sma_50": round(sma(50), 4) if sma(50) is not None else None,
        "sma_200": round(sma(200), 4) if sma(200) is not None else None,
        "above_50d": latest >= sma(50) if sma(50) is not None else None,
        "above_200d": latest >= sma(200) if sma(200) is not None else None,
        "volatility_20d": round(volatility, 2) if volatility is not None else None,
        "sparkline": sparkline,
        "source": source,
    }


def fetch_tencent_chart(symbol: str) -> dict[str, Any]:
    alias = TENCENT_ALIASES[symbol]
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={alias},day,,,260,qfq"
    payload = fetch_json(url)
    series = payload["data"][alias]
    raw_rows = series.get("qfqday") or series.get("day") or []
    rows = []
    for raw in raw_rows:
        parts = raw.split() if isinstance(raw, str) else raw
        if len(parts) >= 3:
            rows.append((parts[0], float(parts[2])))
    return summarize_rows(symbol, rows, "Tencent ifzq kline API (unofficial)")


def fetch_chart(symbol: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=1y&interval=1d&events=div%2Csplits"
    payload = fetch_json(url)
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quotes = result["indicators"]["quote"][0]
    closes = result["indicators"].get("adjclose", [{"adjclose": quotes.get("close", [])}])[0]["adjclose"]
    rows = [
        (dt.datetime.fromtimestamp(ts, dt.timezone.utc).date().isoformat(), float(close))
        for ts, close in zip(timestamps, closes)
        if close is not None
    ]
    return summarize_rows(symbol, rows, "Yahoo Finance chart API (unofficial)")


def fetch_market_asset(symbol: str) -> dict[str, Any]:
    try:
        return fetch_chart(symbol)
    except Exception:
        if symbol in TENCENT_ALIASES:
            return fetch_tencent_chart(symbol)
        raise


def fetch_fred(series_id: str, label: str) -> dict[str, Any]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        lines = response.read().decode("utf-8").strip().splitlines()[1:]
    rows = []
    for line in lines:
        date, value = line.split(",", 1)
        if value not in {"", "."}:
            rows.append((date, float(value)))
    if not rows:
        raise ValueError(f"no FRED data for {series_id}")
    latest = rows[-1]
    previous = rows[-2] if len(rows) > 1 else latest
    return {
        "series": series_id,
        "label": label,
        "market_date": latest[0],
        "value": round(latest[1], 4),
        "change": round(latest[1] - previous[1], 4),
        "source": "Federal Reserve Bank of St. Louis FRED",
    }


def fetch_world_events() -> tuple[list[dict[str, Any]], str | None]:
    query = urllib.parse.quote('(central bank OR tariff OR sanctions OR war OR oil OR inflation) sourcecountry:US')
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=artlist&maxrecords=12&format=json&sort=hybridrel"
    try:
        payload = fetch_json(url, timeout=30)
        events = []
        for article in payload.get("articles", []):
            events.append({
                "title": article.get("title", "Untitled"),
                "url": article.get("url"),
                "domain": article.get("domain"),
                "published_at": article.get("seendate"),
                "language": article.get("language"),
                "source": "GDELT 2.1 DOC API",
            })
        return events[:8], None
    except Exception as gdelt_exc:
        rss_query = urllib.parse.quote('markets central bank oil gold tariffs geopolitics when:1d')
        rss_url = f"https://news.google.com/rss/search?q={rss_query}&hl=en-US&gl=US&ceid=US:en"
        try:
            request = urllib.request.Request(rss_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=30) as response:
                root = ET.fromstring(response.read())
            events = []
            for item in root.findall("./channel/item")[:8]:
                source_node = item.find("source")
                events.append({
                    "title": item.findtext("title", "Untitled"),
                    "url": item.findtext("link"),
                    "domain": source_node.text if source_node is not None else "Google News",
                    "published_at": item.findtext("pubDate"),
                    "language": "English",
                    "source": "Google News RSS fallback; headline lead only",
                })
            return events, f"GDELT unavailable: {gdelt_exc}; used RSS fallback"
        except Exception as rss_exc:  # Keep market data usable if both news sources fail.
            return [], f"GDELT: {gdelt_exc}; RSS: {rss_exc}"


def derive_signals(groups: dict[str, Any], fred: list[dict[str, Any]]) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    ndx = groups.get("nasdaq", {}).get("assets", {}).get("^NDX")
    if ndx:
        dd = ndx["drawdown_1y"]
        if dd <= -15:
            signals.append({"level": "risk", "label": "纳指进入深回撤", "detail": f"NDX 距一年高点 {dd:.1f}%，短线趋势需要重新确认。"})
        elif dd <= -8:
            signals.append({"level": "watch", "label": "纳指回撤达到减仓观察区", "detail": f"NDX 距一年高点 {dd:.1f}%，结合 50/200 日线判断。"})
        else:
            signals.append({"level": "calm", "label": "纳指未触发历史深回撤线", "detail": f"NDX 距一年高点 {dd:.1f}%。"})
    vix = groups.get("risk", {}).get("assets", {}).get("^VIX")
    if vix:
        level = "risk" if vix["value"] >= 30 else "watch" if vix["value"] >= 20 else "calm"
        signals.append({"level": level, "label": "波动率状态", "detail": f"VIX {vix['value']:.2f}，20 日变化 {vix['change_20d']:+.1f}%。"})
    hy = next((item for item in fred if item["series"] == "BAMLH0A0HYM2"), None)
    if hy:
        level = "risk" if hy["value"] >= 5 else "watch" if hy["value"] >= 4 else "calm"
        signals.append({"level": level, "label": "高收益信用利差", "detail": f"HY OAS {hy['value']:.2f}%，单日变化 {hy['change']:+.2f} 个百分点。"})
    return signals


def collect(as_of: dt.date) -> dict[str, Any]:
    fetched_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    symbol_names = {symbol: name for group in GROUPS.values() for symbol, name in group["symbols"].items()}
    assets: dict[str, Any] = {}
    failures: list[dict[str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_market_asset, symbol): symbol for symbol in symbol_names}
        for future in concurrent.futures.as_completed(futures):
            symbol = futures[future]
            try:
                asset = future.result()
                asset["name"] = symbol_names[symbol]
                assets[symbol] = asset
            except Exception as exc:
                failures.append({"source": symbol, "error": str(exc)})

    groups: dict[str, Any] = {}
    for group_id, config in GROUPS.items():
        groups[group_id] = {
            "id": group_id,
            "title": config["title"],
            "assets": {symbol: assets[symbol] for symbol in config["symbols"] if symbol in assets},
            "status": "ok" if all(symbol in assets for symbol in config["symbols"]) else "partial",
        }

    fred_specs = [
        ("BAMLH0A0HYM2", "US High Yield OAS"),
        ("DFF", "Federal Funds Effective Rate"),
        ("T10Y2Y", "US 10Y-2Y Treasury Spread"),
        ("DFII10", "US 10Y Real Yield"),
    ]
    fred: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_fred, series, label): series for series, label in fred_specs}
        for future in concurrent.futures.as_completed(futures):
            series = futures[future]
            try:
                fred.append(future.result())
            except Exception as exc:
                failures.append({"source": f"FRED:{series}", "error": str(exc)})

    events, event_error = fetch_world_events()
    if event_error:
        failures.append({"source": "world-events", "error": event_error})

    return {
        "schema_version": 1,
        "report_date": as_of.isoformat(),
        "fetched_at": fetched_at,
        "timezone": "Asia/Shanghai",
        "market_phase_note": "A/H 股为当日收盘数据；美股、外汇与商品在北京时间晚间运行时可能仍为盘中或盘前数据，请以各资产 market_date 和 fetched_at 为准。",
        "groups": groups,
        "macro": sorted(fred, key=lambda item: item["series"]),
        "world_events": events,
        "signals": derive_signals(groups, fred),
        "agent_notes": {},
        "data_quality": {
            "status": "ok" if not failures else "partial",
            "failures": failures,
            "disclaimer": "行情可能延迟。Yahoo Finance 为非官方接口；新闻标题只作事件线索，结论需回到原始来源。",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.datetime.now().astimezone().date().isoformat())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report_date = dt.date.fromisoformat(args.date)
    output = args.output or ROOT / "nikki" / "data" / "daily" / f"{report_date.isoformat()}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = collect(report_date)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
