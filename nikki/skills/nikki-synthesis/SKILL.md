---
name: nikki-synthesis
description: Synthesize independent Nikki market-agent JSON outputs into a daily cross-market force assessment, preserving divergences, evidence quality, triggers, and invalidations.
---

# Nikki Synthesis

Read the deterministic daily snapshot and all available specialist-agent outputs. Do not fill missing outputs with guesses.

Group correlated evidence into one causal force. Separate external drivers, internal market feedback, and forced trading. Judge the current force as up, down, or range with strength and horizon. Preserve disagreements across markets.

Return JSON with headline, force_direction, force_strength, timeline, independent_forces, divergences, duration_conditions, triggers, invalidations, missing_evidence, and confidence. This is analysis, not a trade instruction.
