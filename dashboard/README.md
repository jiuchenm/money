# Tide 每日复盘大屏

运行：

```bash
python3 dashboard/refresh.py
open dashboard/out/index.html
```

脚本保存市场原始快照到 `out/latest.json`，并生成 `out/index.html` 与当天 Markdown。建议交易日收盘后运行；用 cron 或 CI 定时执行。大屏中的“候选 Tide”是需要用独立数据核验的情景，不是确定预测或投资建议。
