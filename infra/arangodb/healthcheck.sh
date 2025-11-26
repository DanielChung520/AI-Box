# 代碼功能說明: ArangoDB 健康檢查腳本
# 創建日期: 2025-11-25 22:25 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:25 (UTC+8)
#!/usr/bin/env bash

set -euo pipefail

HOST="${ARANGODB_HOST:-localhost}"
PORT="${ARANGODB_PORT:-8529}"
ROOT_USER="${ARANGODB_USERNAME:-root}"
ROOT_PASSWORD="${ARANGO_ROOT_PASSWORD:-ai_box_arangodb_password}"

echo "[ArangoDB] 目標 ${HOST}:${PORT}"

curl -sf -u "${ROOT_USER}:${ROOT_PASSWORD}" "http://${HOST}:${PORT}/_api/version" \
  | jq '.' || {
    echo "[ArangoDB] /_api/version 檢查失敗" >&2
    exit 1
  }

curl -sf -u "${ROOT_USER}:${ROOT_PASSWORD}" "http://${HOST}:${PORT}/_admin/server/role" \
  | jq '.result' || {
    echo "[ArangoDB] /_admin/server/role 檢查失敗" >&2
    exit 1
  }

echo "[ArangoDB] 健康檢查完成，可用於 CI/CD 或排程"
