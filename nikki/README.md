# Nikki market dashboard

Nikki separates deterministic market data from agent interpretation. Daily raw
snapshots are reproducible; model-written notes are optional and must cite the
evidence bundled with the snapshot.

Everything for Nikki lives under this directory. It does not import, edit, or
build the existing Tide site or dashboard.

Run locally:

```bash
python nikki/scripts/collect_market_data.py
python nikki/scripts/publish_snapshot.py
cd nikki/site
npm install
npm run dev
```

The generated latest snapshot lives in nikki/site/src/data/latest.json.
Historical snapshots live in nikki/data/daily. The static site provides latest,
trends, and dated archive views.
