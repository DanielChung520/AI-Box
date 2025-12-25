<!--
代碼功能說明: ArangoDB 知識圖譜 Schema 與資料說明
創建日期: 2025-11-25 22:58 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-11-25 22:58 (UTC+8)
-->

# ArangoDB 知識圖譜 Schema 與資料說明

根據《AI-Box-架構規劃.md》與 WBS 1.4 子計劃，AI-Box 的知識圖譜需要將 Agent、任務、資源與資料集串連，供記憶增強層（AAM）、Task Analyzer 與 Context Manager 使用。本文件記錄 Schema、索引策略、版本化規範與資料匯入流程。

## 1. 資料模型概覽

| 類別 | 說明 | 重要欄位 |
|------|------|----------|
| `agent` | 系統中的 Planning/Execution/Review 等 Agent | `capabilities`、`mcp_server` |
| `task` | WBS/里程碑/流程節點 | `wbs`、`milestone`、`status` |
| `dataset` | 長期記憶或資料包 | `format`、`ingestion_pipeline` |
| `resource` | 基礎設施/工具資源 | `capacity`、`region` |

所有節點均存於 `entities` 集合，使用 `type` 區分。關係存於 `relations` 集合，`type` 建議使用動詞（如 `handles`, `requires`）。

## 2. Schema 與索引

- `datasets/arangodb/schema.yml` 為單一真實來源，`scripts/arangodb_seed.py` 會依該檔建立集合/圖。
- `entities` 集合索引：
  - `type`：供 Task Analyzer 快速取得特定類別節點。
  - `owner`：支援依團隊/模組查詢。
  - `tags[*]`：供上下文字彙檢索。
- `relations` 集合索引：
  - `type`：快速定位 handles/requires/consumes 等不同語意的邊。
  - `weight`：供優先度與 traversal 排序使用。

版本欄位：

- `updated_at`（ISO 8601, UTC+8）為所有節點與邊的樂觀鎖欄位。
- 若 Schema 需要變更，請新增 `version` 欄位並在 `schema.yml` 中提升 `version` 數值，同時提供 migration 腳本或 AQL。

## 3. 種子資料與匯入

1. 修改 `.env` 中的 `ARANGODB_USERNAME/ARANGODB_PASSWORD`（敏感資訊仍在 `.env` 或 Vault）。
2. 於 `config/config.json` 的 `datastores.arangodb` 填寫 host/port/database。
3. 執行：

```bash
poetry run python scripts/arangodb_seed.py --reset
# 或 dry-run
poetry run python scripts/arangodb_seed.py --dry-run
```

`datasets/arangodb/seed_data.json` 內含：

- 3 個核心 Agent 節點。
- 任務、資料集與資源樣本。
- 4 條示範性關係（handles/requires/consumes/needs）。

## 4. 查詢範例

`databases/arangodb/queries.py` 提供三個封裝函式：

1. `fetch_neighbors`：查詢某個 Agent 直接相連的節點。
2. `fetch_subgraph`：取得指定深度的子圖（供 Context Manager 聚合）。
3. `filter_entities`：根據 `type`, `owner`, `tags` 等條件搜尋節點。

可透過示範腳本進行驗證：

```bash
poetry run python scripts/arangodb_query_demo.py \
  --vertex entities/agent_planning \
  --relation-types handles requires \
  --limit 5
```

## 5. Migration 指南

1. **Schema 更新**：修改 `schema.yml` 與本文，並在 PR 中描述 Breaking Change。
2. **資料變更**：新增 `scripts/migrations/arangodb_<timestamp>.py` 處理 AQL 遷移。
3. **驗證**：執行 `scripts/arangodb_seed.py --dry-run` 確認計畫插入內容，再執行查詢示範腳本確保結果符合預期。

## 6. 相關文件

- `docs/deployment/arangodb-deployment.md`：部署與驗證步驟。
- `docs/PROJECT_CONTROL_TABLE.md`：項目進度與 WBS 狀態。
- `AI-Box-架構規劃.md`：系統層級資料流與記憶增強層說明。
