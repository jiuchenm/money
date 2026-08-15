#!/usr/bin/env python3
"""Generate Tide's daily market dashboard. Run after the relevant market close."""
import csv, datetime as dt, html, io, json, os, pathlib, subprocess, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard" / "out"
OUT.mkdir(parents=True, exist_ok=True)
now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))

FRED = {
    "WTI 原油现货": "DCOILWTICO",
    "美国 10 年期国债收益率": "DGS10",
    "美元广义贸易加权指数": "DTWEXBGS",
    "标普 500": "SP500",
}
TICKERS = {"中国大盘 ETF (FXI)": "FXI", "半导体 ETF (SOXX)": "SOXX"}
STOOQ = {
    "GLD": "gld.us", "UUP": "uup.us", "IEF": "ief.us", "USO": "uso.us",
    "SPY": "spy.us", "FXI": "fxi.us", "SOXX": "soxx.us",
}

def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 TideDashboard/1.0"}), timeout=20)

def yahoo(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=5d&interval=1d"
    with fetch(url) as r:
        x = json.load(r)["chart"]["result"][0]
    closes = [v for v in x["indicators"]["quote"][0]["close"] if v is not None]
    if len(closes) < 2: raise ValueError("not enough prices")
    return {"symbol": symbol, "close": closes[-1], "change_pct": (closes[-1]/closes[-2]-1)*100, "source": "Yahoo Finance"}

def fred(series):
    # FRED's CSV endpoint intermittently rejects custom user agents; use its
    # standard public endpoint directly and retain the observation date.
    with urllib.request.urlopen(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={urllib.parse.quote(series)}", timeout=30) as r:
        rows = list(csv.DictReader(io.StringIO(r.read().decode())))
    values = [x for x in rows if x.get(series) not in (None, "", ".")]
    if len(values) < 2: raise ValueError("not enough FRED observations")
    last, prev = values[-1], values[-2]
    value, prior = float(last[series]), float(prev[series])
    return {"symbol": series, "close": value, "change_pct": (value/prior-1)*100, "source": "FRED", "market_date": last.get("observation_date", "")}

def stooq(symbol):
    start = (now.date() - dt.timedelta(days=14)).strftime("%Y%m%d")
    end = now.date().strftime("%Y%m%d")
    with fetch(f"https://stooq.com/q/d/l/?s={urllib.parse.quote(STOOQ[symbol])}&d1={start}&d2={end}&i=d") as r:
        rows = list(csv.DictReader(io.StringIO(r.read().decode())))
    rows = [x for x in rows if x.get("Close") not in (None, "", "N/D")]
    if len(rows) < 2: raise ValueError("not enough Stooq prices")
    last, prev = rows[-1], rows[-2]
    return {"symbol": symbol, "close": float(last["Close"]), "change_pct": (float(last["Close"])/float(prev["Close"])-1)*100, "source": "Stooq", "market_date": last.get("Date", "")}

def news(query):
    key_file = ROOT / "webiq" / "key"
    if not key_file.exists(): return []
    env = os.environ.copy(); env["WEBIQ_KEY"] = key_file.read_text().strip()
    try:
        raw = subprocess.check_output([str(ROOT/"webiq/query.sh"), "news", query, "5", "US"], env=env, text=True, timeout=40)
        data = json.loads(raw)
        return [{"title": i.get("title", ""), "url": i.get("url", ""), "source": i.get("source", ""), "time": i.get("lastUpdatedAt", "")} for i in data.get("newsResults", [])]
    except Exception: return []

prices, failures = {}, []
for label, series in FRED.items():
    try: prices[label] = fred(series)
    except Exception as e: failures.append(f"{label}: FRED={e}")
for label, ticker in TICKERS.items():
    try: prices[label] = yahoo(ticker)
    except Exception as yahoo_error:
        try: prices[label] = stooq(ticker)
        except Exception as stooq_error: failures.append(f"{label}: Yahoo={yahoo_error}; Stooq={stooq_error}")
events = news("global markets central banks oil China AI semiconductor")
snapshot = {"generated_at": now.isoformat(), "prices": prices, "events": events, "failures": failures}
(OUT / "latest.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))

def row(label, p):
    direction = "up" if p["change_pct"] >= 0 else "down"
    source = f"<small>{html.escape(p.get('source',''))} {html.escape(p.get('market_date',''))}</small>"
    return f"<tr><td>{html.escape(label)}{source}</td><td>{p['close']:.2f}</td><td class='{direction}'>{p['change_pct']:+.2f}%</td></tr>"
market = "".join(row(k,v) for k,v in prices.items()) or "<tr><td colspan='3'>数据源暂不可用</td></tr>"
event_html = "".join(f"<li><a href='{html.escape(e['url'])}'>{html.escape(e['title'])}</a><small>{html.escape(e['source'])} {html.escape(e['time'])}</small></li>" for e in events) or "<li>未抓到新闻；请检查 WebIQ 配置后重跑。</li>"
scenarios = [
 ("技术资本开支与制造链延续", "中", "SOXX/中国资产相对强势，订单与盈利预期继续上修", "订单、合约价或盈利指引转弱；价格对利好不再反应"),
 ("能源冲击抬升通胀，利率约束延长", "中", "油价走强、长端利率承压，估值资产波动加大", "油价和运费回落，核心通胀持续降温"),
 ("中国风险溢价修复但非普涨", "中低", "FXI 走强并伴随盈利/信用验证，而非只有汇率改善", "盈利与内需数据未改善，或美元流动性重新收紧"),
]
cards = "".join(f"<article><span>可能性：{a[1]}</span><h3>{a[0]}</h3><p><b>需要验证：</b>{a[2]}</p><p><b>失效条件：</b>{a[3]}</p><em>这是 Tide 推断，不是事实或投资建议。</em></article>" for a in scenarios)
page = f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Tide 每日复盘</title><style>body{{margin:0;background:#09131b;color:#dce9ef;font:16px system-ui;padding:32px;max-width:1200px;margin:auto}}h1{{font-size:36px}}.muted,small,em{{color:#94aab6}}section{{margin:28px 0}}table{{width:100%;border-collapse:collapse;background:#10212d}}td,th{{padding:13px;border-bottom:1px solid #24404e;text-align:left}}.up{{color:#48d597}}.down{{color:#ff7e7e}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}}article{{background:#10212d;border-left:3px solid #d7b45a;padding:18px}}a{{color:#78c7ff}}li{{margin:12px 0}}small{{display:block;margin-top:4px}}</style><h1>Tide · 每日复盘大屏</h1><p class='muted'>生成时间：{now:%Y-%m-%d %H:%M} 北京时间。行情为公开 ETF 代理，不等同于本地市场收盘；事件须打开来源复核。</p><section><h2>市场快照 · 事实</h2><table><tr><th>代理资产</th><th>最新价</th><th>相对前一交易日</th></tr>{market}</table></section><section><h2>世界事件雷达 · 待核实证据</h2><ul>{event_html}</ul></section><section><h2>候选 Tide · 推断与证伪</h2><div class='grid'>{cards}</div></section><section><h2>今日执行纪律</h2><p>先补全时间线，再判断合力。没有独立证据、传导链和失效条件，就只能列为观察，不给买点。</p></section></html>"""
(OUT / "index.html").write_text(page)
md = f"# Tide 每日快照｜{now:%Y-%m-%d}\n\n生成时间：{now:%Y-%m-%d %H:%M} 北京时间。行情与新闻来源见 dashboard/out/latest.json。\n\n## 候选 Tide\n\n" + "\n".join(f"- 📕 **{x[0]}**（可能性：{x[1]}）：验证 {x[2]}；失效 {x[3]}。" for x in scenarios) + "\n"
(OUT / f"{now:%Y-%m-%d}.md").write_text(md)
print(OUT / "index.html")
