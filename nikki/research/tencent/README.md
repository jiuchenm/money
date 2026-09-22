# Tencent research first edition

The first edition joins human-reviewed news, price/volume analysis and macro
context. It also benchmarks a small quantile LightGBM against empirical returns.
It does not claim predictive skill or place orders. All input data and generated
snapshots stay under the git-ignored research-private directory.

Tested on Windows with CPython 3.14.5 x64; the existing ARM Python could not build
LightGBM without a compiler. Use an x64 runtime and the pinned requirements.

Daily publication is configured through the current Codex task at 19:10
Asia/Shanghai. Follow DAILY-RUNBOOK.md. It publishes original research and source
links to the existing Nikki Pages site; raw market data remains local. The host
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
after a dated review receipt. Keep personal positions out of every public artifact.

Validation protocol: 5/10/20-day labels; future-dividend windows excluded; causal
cash-dividend momentum features; h-day gaps at train/calibration/test boundaries;
126-session calibration and 63-session rolling test blocks; raw quantile loss
separate from conformal interval coverage. Only two holdout blocks are available
in this bounded prototype. There is no transaction-cost strategy evaluation,
independence claim for overlapping labels, or neural model.

2026-09-22 outcome: all twelve LightGBM targets failed to beat the empirical
baseline. They remain visible as experimental diagnostics, not the report's
decision engine. Full prediction and actual labels are saved privately for audit.
