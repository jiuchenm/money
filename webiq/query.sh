#!/usr/bin/env bash
# WebIQ 查询封装。用法：
#   export WEBIQ_KEY=<your key>        # key 只存在环境变量，不落盘、不进 KB
#   ./query.sh web  "查询词" [maxResults] [region] [contentFormat]
#   ./query.sh news "查询词" [maxResults] [region]
#
# 例：
#   ./query.sh news "SK Hynix Samsung stock July 2026" 10 US
#   ./query.sh web  "Alibaba 9988 forward PE 2026" 10 US passage

set -euo pipefail

MODE="${1:?用法: query.sh <web|news> <query> [maxResults] [region] [contentFormat]}"
QUERY="${2:?缺少查询词}"
MAXRESULTS="${3:-10}"
REGION="${4:-US}"
CONTENTFORMAT="${5:-passage}"   # passage=按查询抽取最相关段落，省 token

: "${WEBIQ_KEY:?请先 export WEBIQ_KEY=<your key>}"

case "$MODE" in
  web)  ENDPOINT="https://api.microsoft.ai/v3/search/web" ;;
  news) ENDPOINT="https://api.microsoft.ai/v3/search/news" ;;
  *) echo "MODE 必须是 web 或 news"; exit 1 ;;
esac

curl -sS -X POST "$ENDPOINT" \
  -H "host: api.microsoft.ai" \
  -H "x-apikey: ${WEBIQ_KEY}" \
  -H "content-type: application/json" \
  -d "{
    \"query\": $(printf '%s' "$QUERY" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
    \"maxResults\": ${MAXRESULTS},
    \"language\": \"en\",
    \"region\": \"${REGION}\",
    \"maxLength\": 6000,
    \"contentFormat\": \"${CONTENTFORMAT}\"
  }"
