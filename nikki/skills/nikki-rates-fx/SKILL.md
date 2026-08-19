---
name: nikki-rates-fx
description: Analyze Nikki daily dollar, renminbi, Treasury yield, real-rate, yield-curve, and liquidity signals with explicit data-lag handling.
---

# Nikki Rates And FX

Read one Nikki daily snapshot. Use rates_fx and macro; use other groups only for cross-validation.

Keep nominal yield, real yield, curve slope, dollar direction, and USD/CNY separate. Record each series market_date; FRED data often lags live markets. Do not count correlated rate indicators as independent votes.

Use plain Chinese names before any ticker or acronym. For each professional series explain what it measures, whether the latest level/change is supportive, neutral, or suppressive for Hong Kong/A shares, the transmission mechanism, and the data lag. Do not assume that a higher numerical reading is bullish.

Return JSON with headline, stance, forces, divergences, triggers, invalidations, and confidence.
