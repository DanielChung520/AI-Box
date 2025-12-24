# 代碼功能說明: ArangoDB 初始化腳本
# 創建日期: 2025-11-25 22:25 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:25 (UTC+8)
#!/usr/bin/env bash

set -euo pipefail

HOST="${ARANGODB_HOST:-localhost}"
PORT="${ARANGODB_PORT:-8529}"
ROOT_USER="${ARANGODB_USERNAME:-root}"
ROOT_PASSWORD="${ARANGO_ROOT_PASSWORD:-ai_box_arangodb_password}"
DATABASE="${ARANGODB_DATABASE:-ai_box_kg}"
APP_USER="${ARANGODB_APP_USER:-ai_box_writer}"
APP_PASSWORD="${ARANGODB_APP_PASSWORD:-ai_box_writer_password}"

base_url="http://${HOST}:${PORT}"
auth_header="-u ${ROOT_USER}:${ROOT_PASSWORD}"

echo "[ArangoDB] 初始化開始：host=${HOST} port=${PORT} database=${DATABASE}"

create_database() {
  echo "[ArangoDB] 建立資料庫 ${DATABASE}（若不存在）"
  curl -sf ${auth_header} \
    -H "Content-Type: application/json" \
    -X POST "${base_url}/_api/database" \
    -d "{\"name\":\"${DATABASE}\",\"options\":{},\"users\":[{\"username\":\"${ROOT_USER}\",\"password\":\"${ROOT_PASSWORD}\"}]}" \
    >/dev/null || {
      echo "[ArangoDB] 資料庫可能已存在，忽略錯誤"
    }
}

create_app_user() {
  echo "[ArangoDB] 建立應用使用者 ${APP_USER}"
  curl -sf ${auth_header} \
    -H "Content-Type: application/json" \
    -X POST "${base_url}/_api/user" \
    -d "{\"user\":\"${APP_USER}\",\"passwd\":\"${APP_PASSWORD}\",\"active\":true}" \
    >/dev/null || echo "[ArangoDB] 使用者可能已存在，跳過"

  echo "[ArangoDB] 指派 ${APP_USER} 對 ${DATABASE} 的 RW 權限"
  curl -sf ${auth_header} \
    -H "Content-Type: application/json" \
    -X PUT "${base_url}/_api/user/${APP_USER}/database/${DATABASE}" \
    -d "{\"permission\":\"rw\"}" \
    >/dev/null
}

create_collections() {
  for collection in entities relations; do
    echo "[ArangoDB] 建立集合 ${collection}"
    curl -sf ${auth_header} \
      -H "Content-Type: application/json" \
      -X POST "${base_url}/_db/${DATABASE}/_api/collection" \
      -d "{\"name\":\"${collection}\",\"type\":2}" \
      >/dev/null || echo "[ArangoDB] 集合 ${collection} 已存在，跳過"
  done
}

create_edge_collection() {
  echo "[ArangoDB] 建立邊集合 relations_edges"
  curl -sf ${auth_header} \
    -H "Content-Type: application/json" \
    -X POST "${base_url}/_db/${DATABASE}/_api/collection" \
    -d "{\"name\":\"relations_edges\",\"type\":3}" \
    >/dev/null || echo "[ArangoDB] 邊集合已存在，跳過"
}

create_graph() {
  echo "[ArangoDB] 建立預設圖 knowledge_graph"
  curl -sf ${auth_header} \
    -H "Content-Type: application/json" \
    -X POST "${base_url}/_db/${DATABASE}/_api/gharial" \
    -d '{
      "name": "knowledge_graph",
      "edgeDefinitions": [
        {
          "collection": "relations_edges",
          "from": ["entities"],
          "to": ["entities"]
        }
      ]
    }' >/dev/null || echo "[ArangoDB] 圖已存在，跳過"
}

create_database
create_app_user
create_collections
create_edge_collection
create_graph

echo "[ArangoDB] 初始化完成"
