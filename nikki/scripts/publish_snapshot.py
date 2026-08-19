from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "data" / "daily"
ANALYSIS = ROOT / "analysis"
PUBLIC_DATA = ROOT / "site" / "public" / "data"
SOURCE_DATA = ROOT / "site" / "src" / "data"


def merge_event_analysis(snapshot: dict[str, Any], analysis: dict[str, Any]) -> None:
    event_analysis = analysis.pop("world_events", None)
    if isinstance(event_analysis, dict):
        interpreted = event_analysis.get("events", [])
    elif isinstance(event_analysis, list):
        interpreted = event_analysis
    else:
        interpreted = []
    if not isinstance(interpreted, list):
        return

    by_url = {item.get("url"): item for item in interpreted if isinstance(item, dict) and item.get("url")}
    by_title = {
        item.get("original_title") or item.get("title"): item
        for item in interpreted
        if isinstance(item, dict) and (item.get("original_title") or item.get("title"))
    }
    for event in snapshot.get("world_events", []):
        interpretation = by_url.get(event.get("url")) or by_title.get(event.get("title"))
        if not interpretation:
            continue
        for key in ("chinese_summary", "hk_a_impact", "affected_assets", "mechanism", "priced_in"):
            if interpretation.get(key) is not None:
                event[key] = interpretation[key]


def load_snapshots() -> list[dict[str, Any]]:
    snapshots = []
    for path in sorted(DAILY.glob("*.json")):
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        analysis_path = ANALYSIS / f"{snapshot['report_date']}.json"
        if analysis_path.exists():
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            merge_event_analysis(snapshot, analysis)
            snapshot["agent_notes"] = analysis
        snapshots.append(snapshot)
    if not snapshots:
        raise SystemExit("No Nikki daily snapshots found")
    return snapshots


def build_history(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    tracked = {
        "^HSI": "恒生指数",
        "HSTECH.HK": "恒生科技指数",
        "000300.SS": "沪深300",
        "399006.SZ": "创业板指",
    }
    series = {symbol: {"symbol": symbol, "name": name, "points": []} for symbol, name in tracked.items()}
    for snapshot in snapshots:
        assets = {
            symbol: asset
            for group in snapshot.get("groups", {}).values()
            for symbol, asset in group.get("assets", {}).items()
        }
        for symbol in tracked:
            if symbol in assets:
                series[symbol]["points"].append({
                    "report_date": snapshot["report_date"],
                    "market_date": assets[symbol]["market_date"],
                    "value": assets[symbol]["value"],
                    "change_1d": assets[symbol]["change_1d"],
                })
    return {"generated_from": len(snapshots), "series": series}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest-only", action="store_true")
    parser.parse_args()
    snapshots = load_snapshots()
    latest = snapshots[-1]
    PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    SOURCE_DATA.mkdir(parents=True, exist_ok=True)
    (SOURCE_DATA / "daily").mkdir(parents=True, exist_ok=True)
    (PUBLIC_DATA / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (SOURCE_DATA / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive = [{
        "date": item["report_date"],
        "fetched_at": item["fetched_at"],
        "status": item.get("data_quality", {}).get("status", "unknown"),
        "signal_count": len(item.get("signals", [])),
    } for item in reversed(snapshots)]
    (PUBLIC_DATA / "archive.json").write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (SOURCE_DATA / "archive.json").write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    history = build_history(snapshots)
    (PUBLIC_DATA / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (SOURCE_DATA / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    daily_public = PUBLIC_DATA / "daily"
    daily_public.mkdir(parents=True, exist_ok=True)
    for snapshot in snapshots:
        rendered = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
        (daily_public / f"{snapshot['report_date']}.json").write_text(
            rendered, encoding="utf-8"
        )
        (SOURCE_DATA / "daily" / f"{snapshot['report_date']}.json").write_text(rendered, encoding="utf-8")
    print(f"published {len(snapshots)} Nikki snapshot(s)")


if __name__ == "__main__":
    main()
