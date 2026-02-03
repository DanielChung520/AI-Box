#!/usr/bin/env bash
# 啟動 RQ Dashboard（端口 9181，供系統監控使用）
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
PORT="${RQ_DASHBOARD_PORT:-9181}"
REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"

if [ -d "$ROOT/.venv" ]; then
  source "$ROOT/.venv/bin/activate"
elif [ -d "$ROOT/venv" ]; then
  source "$ROOT/venv/bin/activate"
fi

if ! python -c "import rq_dashboard" 2>/dev/null; then
  echo "rq-dashboard 未安裝，請執行: pip install rq-dashboard"
  exit 1
fi

echo "啟動 RQ Dashboard：端口 $PORT，Redis $REDIS_URL"
exec python -m rq_dashboard.cli run --port "$PORT" --redis-url "$REDIS_URL" "$@"
