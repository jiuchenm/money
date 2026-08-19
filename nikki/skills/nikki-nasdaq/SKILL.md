---
name: nikki-nasdaq
description: Analyze Nikki daily US equity and Nasdaq snapshots, including drawdown speed, trend, breadth proxies, semiconductors, volatility, and credit confirmation.
---

# Nikki Nasdaq

Read one nikki/data/daily/YYYY-MM-DD.json snapshot. Use only nasdaq, risk, rotation, relevant rates_fx, and macro fields.

Distinguish intraday observations from confirmed closes. Treat historical drawdown rules as risk zones, not automatic orders: about 8% in 20 trading days or 10% in 30 days is a reduction watch; about 15% in 60 days plus broken trend is a short-term exit watch.

Return JSON with headline, stance, forces, divergences, triggers, invalidations, and confidence. Cite values in the text. Do not infer news causes from prices.
