from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_json(path: Path):
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--parts", type=Path, default=ROOT / "analysis-parts")
    args = parser.parse_args()
    output = ROOT / "analysis" / f"{args.date}.json"
    current = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    if args.parts.exists():
        for path in sorted(args.parts.glob("*.json")):
            try:
                current[path.stem] = parse_json(path)
            except (json.JSONDecodeError, OSError) as exc:
                print(f"skip {path.name}: {exc}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
