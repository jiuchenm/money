---
name: nikki-synthesis
description: Synthesize independent Nikki market-agent JSON outputs into a daily cross-market force assessment, preserving divergences, evidence quality, triggers, and invalidations.
---

# Nikki Synthesis

Read the deterministic daily snapshot and all available specialist-agent outputs. Do not fill missing outputs with guesses.

Group correlated evidence into one causal force. Separate external drivers, internal market feedback, and forced trading. Judge the current force as up, down, or range with strength and horizon. Preserve disagreements across markets.

Write all user-facing fields in plain Chinese for a Hong Kong/A-share investor. Do not output unexplained tickers, English acronyms, foreign headlines, or professional series names. Introduce the Chinese meaning first, then place a necessary code in parentheses. Every overseas force must include its Hong Kong/A-share transmission path and whether the market has already priced it.

Return JSON with headline, force_direction, force_strength, timeline, independent_forces, divergences, duration_conditions, triggers, invalidations, missing_evidence, and confidence. This is analysis, not a trade instruction.
