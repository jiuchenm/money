# Tencent research first edition

The first edition joins human-reviewed news, price/volume analysis and macro
context. It also benchmarks a small quantile LightGBM against empirical returns.
It does not claim predictive skill or place orders. Raw input responses and audit
snapshots stay under research-private. At the user's explicit request, the full
research page now includes chart facts and the three-lot position scenario.

Tested on Windows with CPython 3.14.5 x64; the existing ARM Python could not build
LightGBM without a compiler. Use an x64 runtime and the pinned requirements.

Daily publication is configured through the current Codex task at 19:10
Asia/Shanghai. Follow DAILY-RUNBOOK.md. It publishes original research and source
links plus daily/weekly/monthly and 30/120-minute charts to Nikki Pages. The host
and Codex must be running. GitHub Actions builds the committed public artifact.

Run from the repository root:

```powershell
research-private/.venv-x64/Scripts/python.exe nikki/research/tencent/collect.py --date 2026-09-22
research-private/.venv-x64/Scripts/python.exe nikki/research/tencent/analyze.py --date 2026-09-22
research-private/.venv-x64/Scripts/python.exe -m unittest discover -s nikki/research/tencent -p test_analysis.py
```

Analysis also reads the optional Tencent third-source snapshot, retained in the
private raw directory. If it is absent, unresolved cross-provider discrepancies
remain quarantined. Earlier than 2023-01-05 is deliberately excluded because of
unreconciled in-specie adjustment differences. Special 2023 HKEX closure dates
are explicit source-linked overrides; unexplained calendar gaps fail closed.

Eastmoney outages now fall back to fresh unadjusted Tencent daily OHLCV, with
recent Yahoo OHLC agreement and original date/freshness checks. Actual turnover
is taken only from a same-day validated Tencent closing quote or a matching
same-date historical record; missing amounts remain null, including period sums.
Same-timestamp Yahoo nulls can be repaired from previously captured completed
observations with snapshot hashes. No forward-filling of quote dates is allowed.
Minute collection archives stale failed responses and the UI handles missing
secondary-source values. Stock Connect execution holidays are separate from
Hong Kong price sessions; the official calendar must be refreshed each year.

News files must be independently reviewed before assembling:

- news-ai-compute.json
- news-tencent-china.json
- news-global-macro.json
- synthesis.json, topic-exclusions.json and optional macro-supplement.json

There is no fabricated automatic news interpretation. The assembler validates
required fields, deduplicates source URLs, applies recorded editorial exclusions,
distinguishes post-close information and requires at least 100 retained topics.
Semantic event deduplication remains a human/agent-reviewed step.

```powershell
python nikki/research/tencent/assemble.py --date 2026-09-22
npm --prefix nikki/site run build
python nikki/research/tencent/serve.py --date 2026-09-22 --port 4174
```

Open http://127.0.0.1:4174/money/#/tencent. The local server overlays the private
JSON at the public application's data path without copying it into site/public
or dist. It listens only on loopback. A future production publisher must use
explicitly cleared inputs and output fields. publish_public.py exports an allowlist
after a dated full-page review receipt. Credentials, account data and local paths
remain excluded. The user has authorized the 3-lot/428-HKD scenario on this page.

Validation protocol: 5/10/20-day labels; future-dividend windows excluded; causal
cash-dividend momentum features; h-day gaps at train/calibration/test boundaries;
126-session calibration and 63-session rolling test blocks; raw quantile loss
separate from conformal interval coverage. Only two holdout blocks are available
in this bounded prototype. There is no transaction-cost strategy evaluation,
independence claim for overlapping labels, or neural model.

2026-09-22 outcome: all twelve LightGBM targets failed to beat the empirical
baseline. They remain visible as experimental diagnostics, not the report's
decision engine. Full prediction and actual labels are saved privately for audit.
