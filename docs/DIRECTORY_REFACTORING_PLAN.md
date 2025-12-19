# AI-Box 目錄重構計劃

**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**狀態**: 規劃中

## 📋 概述

本文檔詳細說明 AI-Box 項目目錄結構重構計劃，按照組件服務分層的方式，逐步遷移現有代碼到新的目錄結構。

### 重構目標

1. **清晰的分層架構**: 按照 GenAI、Agent、Database、LLM、System 等大組件劃分
2. **職責明確**: 每個模組職責單一，易於理解和維護
3. **獨立部署**: 支持組件獨立部署和擴展
4. **易於測試**: 模組化後便於單元測試和集成測試

### 重構原則

1. **漸進式遷移**: 一個模組一個模組遷移，不一次性大改
2. **遷移即測試**: 每完成一個模組遷移，立即進行測試驗證
3. **備份測試代碼**: 現有測試代碼先備份，後續重新整合
4. **保持向後兼容**: 遷移過程中使用適配器保持接口兼容

---

## 📐 目標目錄結構

詳見文檔：[目錄結構文字稿](./DIRECTORY_STRUCTURE.md)（待創建）

主要組件：

- `genai/` - GenAI 相關組件（LangChain、RAG、NER/RE/RT、Context Record）
- `mcp/` - MCP Server 和 Client
- `database/` - 數據庫服務（ChromaDB、ArangoDB、Personnel Data）
- `llm/` - LLM 模型層（MoE、抽象層、客戶端、路由）
- `agents/` - Agent 服務層（註冊、協調、核心 Agent、工作流）
- `system/` - 系統管理（安全、配置、日誌、監控）
- `api/` - API 界面層（統一入口）
- `storage/` - 文件存儲
- `tests/` - 測試（重構後重新組織）
- `tests_backup/` - 測試備份（遷移期間）

---

## 🔄 遷移計劃

### 階段 0: 準備階段

**目標**: 備份現有代碼和測試，創建新目錄結構

**任務**:

1. 備份現有測試代碼到 `tests_backup/`
2. 創建新目錄結構（空目錄）
3. 創建遷移日誌文件
4. 設置 Git 分支用於遷移

**具體步驟**:
\`\`\`bash

# 1. 創建測試備份目錄

mkdir -p tests_backup

# 2. 備份現有測試（如果有）

find . -name "test_*.py" -o -name "*_test.py" 2>/dev/null | while read file; do
    mkdir -p tests_backup/$(dirname "$file")
    cp "$file" "tests_backup/$file"
done

# 3. 備份測試配置

[ -f pytest.ini ] && cp pytest.ini tests_backup/

# 4. 創建新目錄結構

mkdir -p database/{chromadb,arangodb,redis,personnel}
mkdir -p llm/{moe,abstraction,clients,routing/strategies}
mkdir -p mcp/{server/{protocol,tools},client/connection}
mkdir -p genai/{api/{routers,services,models},workflows/{langchain,rag,context},prompt}
mkdir -p agents/{services/{registry,orchestrator,processing,file_service},core/{planning,execution,review},workflows/{langchain_graph,crewai,autogen},task_analyzer}
mkdir -p system/{security,infra/{config,logging,monitoring},n8n/workflows}
mkdir -p api/{routers,middleware,core}
mkdir -p storage
mkdir -p tests/{genai,mcp,database,llm,agents,system,api}

# 5. 創建 Git 分支

git checkout -b refactoring/directory-restructure
\`\`\`

**檢查點**:

- [ ] 所有測試文件已備份到 `tests_backup/`
- [ ] 新目錄結構已創建
- [ ] Git 分支已創建
- [ ] 遷移日誌文件已創建

---

### 階段 1: Database 模組遷移

**目標**: 遷移所有數據庫相關代碼

**遷移內容**:

- `databases/chromadb/` → `database/chromadb/`
- `databases/arangodb/` → `database/arangodb/`
- Redis 客戶端（如有）→ `database/redis/`
- Personnel Data 服務 → `database/personnel/`

**具體步驟**:

1. 創建 `database/` 目錄結構（已在階段 0 完成）
2. 遷移 ChromaDB 代碼
   - 複製 `databases/chromadb/` 到 `database/chromadb/`
   - 更新內部導入路徑
3. 遷移 ArangoDB 代碼
   - 複製 `databases/arangodb/` 到 `database/arangodb/`
   - 更新內部導入路徑
4. 更新所有引用這些模組的文件中的導入路徑
5. 運行測試驗證

**更新導入路徑**:
\`\`\`python

# 需要替換的導入路徑

# databases.chromadb -> database.chromadb

# databases.arangodb -> database.arangodb

\`\`\`

**測試重點**:

- [ ] ChromaDB 連接和操作正常
- [ ] ArangoDB 連接和操作正常
- [ ] 所有數據庫客戶端功能正常
- [ ] 向量檢索功能正常
- [ ] 圖查詢功能正常

**預計時間**: 1-2 天

---

### 階段 2: LLM 模組遷移

**目標**: 遷移 LLM 模型層代碼，重組內部結構

**遷移內容**:

- `llm/moe_manager.py` → `llm/moe/moe_manager.py`
- `llm/clients/` → `llm/clients/` (保持，但更新導入)
- `llm/routing/` → `llm/routing/` (保持，但更新導入)
- `llm/load_balancer.py` → `llm/load_balancer.py` (保持)
- `llm/failover.py` → `llm/failover.py` (保持)
- 創建 `llm/abstraction/` 目錄，提取抽象層

**具體步驟**:

1. 創建 `llm/moe/` 目錄
2. 遷移 MoE 管理器
   - 移動 `llm/moe_manager.py` → `llm/moe/moe_manager.py`
   - 更新內部導入
3. 創建 `llm/abstraction/` 目錄
   - 提取基礎 LLM 客戶端接口
   - 創建工廠和適配器
4. 重組 `llm/clients/` 結構（如有需要）
5. 更新所有導入路徑
6. 運行測試驗證

**更新導入路徑**:
\`\`\`python

# 需要替換的導入路徑

# llm.moe_manager -> llm.moe.moe_manager

# from llm.moe_manager import LLMMoEManager

# -> from llm.moe.moe_manager import LLMMoEManager

\`\`\`

**測試重點**:

- [ ] LLM 客戶端正常運行
- [ ] MoE 管理器功能正常
- [ ] 路由策略正常工作
- [ ] 負載均衡和故障轉移正常
- [ ] 抽象層接口正常

**預計時間**: 2-3 天

---

### 階段 3: MCP 模組遷移

**目標**: 遷移 MCP Server 和 Client 代碼

**遷移內容**:

- `mcp_server/` → `mcp/server/`
- `mcp_client/` → `mcp/client/`
- `services/mcp_server/` → 整合到 `mcp/server/`
- `agents/*/mcp_server.py` → `agents/core/*/handlers.py` (重命名並遷移)

**具體步驟**:

1. 創建 `mcp/server/` 目錄結構
2. 遷移 MCP Server 核心代碼
   - 移動 `mcp_server/server.py` → `mcp/server/server.py`
   - 移動 `mcp_server/protocol/` → `mcp/server/protocol/`
3. 遷移 MCP Server 工具和配置
   - 移動 `services/mcp_server/tools/` → `mcp/server/tools/`
   - 移動 `services/mcp_server/config.py` → `mcp/server/config.py`
   - 移動 `services/mcp_server/monitoring.py` → `mcp/server/monitoring.py`
4. 創建 `mcp/client/` 目錄
5. 遷移 MCP Client 代碼
   - 移動 `mcp_client/client.py` → `mcp/client/client.py`
   - 移動 `mcp_client/connection/` → `mcp/client/connection/`
6. 重命名 Agent handlers
   - `agents/planning/mcp_server.py` → `agents/core/planning/handlers.py`
   - `agents/execution/mcp_server.py` → `agents/core/execution/handlers.py`
7. 更新所有導入路徑
8. 運行測試驗證

**更新導入路徑**:
\`\`\`python

# 需要替換的導入路徑

# mcp_server -> mcp.server

# mcp_client -> mcp.client

# services.mcp_server -> mcp.server

\`\`\`

**測試重點**:

- [ ] MCP Server 啟動正常
- [ ] MCP Client 連接正常
- [ ] MCP 工具調用正常
- [ ] Agent handlers 正常工作
- [ ] MCP 協議通信正常

**預計時間**: 2-3 天

---

### 階段 4: GenAI 模組遷移

**目標**: 遷移所有 GenAI 相關代碼

**遷移內容**:

**路由層**:

- `services/api/routers/ner.py` → `genai/api/routers/ner.py`
- `services/api/routers/re.py` → `genai/api/routers/re.py`
- `services/api/routers/rt.py` → `genai/api/routers/rt.py`
- `services/api/routers/triple_extraction.py` → `genai/api/routers/triple_extraction.py`
- `services/api/routers/kg_builder.py` → `genai/api/routers/kg_builder.py`
- `services/api/routers/kg_query.py` → `genai/api/routers/kg_query.py`
- `services/api/routers/aam_async_tasks.py` → `genai/api/routers/aam_async_tasks.py`
- `services/api/routers/chunk_processing.py` → `genai/api/routers/chunk_processing.py`

**服務層**:

- `services/api/services/ner_service.py` → `genai/api/services/ner_service.py`
- `services/api/services/re_service.py` → `genai/api/services/re_service.py`
- `services/api/services/rt_service.py` → `genai/api/services/rt_service.py`
- `services/api/services/triple_extraction_service.py` → `genai/api/services/triple_extraction_service.py`
- `services/api/services/kg_builder_service.py` → `genai/api/services/kg_builder_service.py`

**模型層**:

- `services/api/models/ner_models.py` → `genai/api/models/ner_models.py`
- `services/api/models/re_models.py` → `genai/api/models/re_models.py`
- `services/api/models/rt_models.py` → `genai/api/models/rt_models.py`
- `services/api/models/triple_models.py` → `genai/api/models/triple_models.py`

**工作流層**:

- `agent_process/memory/aam/hybrid_rag.py` → `genai/workflows/rag/hybrid_rag.py`
- `agent_process/retrieval/` → `genai/workflows/rag/`
- `agent_process/context/` → `genai/workflows/context/`
- `agent_process/prompt/` → `genai/prompt/`
- `agents/workflows/langchain_graph/` → `genai/workflows/langchain/`

**具體步驟**:

1. 創建 `genai/` 目錄結構
2. 遷移路由層代碼
3. 遷移服務層代碼
4. 遷移模型層代碼
5. 遷移工作流代碼
6. 更新所有導入路徑
7. 在 `api/routers/` 中創建適配器，引用 `genai/api/routers/`
8. 運行測試驗證

**測試重點**:

- [ ] NER/RE/RT 服務正常
- [ ] 三元組提取正常
- [ ] 知識圖譜構建和查詢正常
- [ ] RAG 檢索功能正常
- [ ] Context Record 正常
- [ ] LangChain 工作流正常

**預計時間**: 3-4 天

---

### 階段 5: Agent 模組遷移

**目標**: 遷移 Agent 服務層代碼

**遷移內容**:

**服務層**:

- `services/agent_registry/` → `agents/services/registry/`
- `services/result_processor/` → `agents/services/processing/`
- `services/file_server/` → `agents/services/file_service/`
- `agents/orchestrator/` → `agents/services/orchestrator/`

**核心 Agent**:

- `agents/planning/` → `agents/core/planning/` (agent.py 和 handlers.py)
- `agents/execution/` → `agents/core/execution/` (agent.py 和 handlers.py)
- `agents/review/` → `agents/core/review/` (agent.py 和 handlers.py)

**工作流引擎**:

- `agents/workflows/crewai/` → `agents/workflows/crewai/`
- `agents/workflows/autogen/` → `agents/workflows/autogen/`
- `agents/workflows/hybrid_orchestrator.py` → `agents/workflows/hybrid_orchestrator.py`

**任務分析**:

- `agents/task_analyzer/` → `agents/task_analyzer/` (保持位置)

**具體步驟**:

1. 創建 `agents/services/` 目錄結構
2. 遷移 Agent Registry 服務
3. 遷移 Result Processor 服務
4. 遷移 File Service
5. 遷移 Orchestrator
6. 遷移核心 Agent
7. 遷移工作流引擎
8. 更新所有導入路徑
9. 運行測試驗證

**測試重點**:

- [ ] Agent Registry 註冊和發現正常
- [ ] Agent Orchestrator 協調正常
- [ ] 核心 Agent 執行正常
- [ ] 工作流引擎（CrewAI、AutoGen、Hybrid）正常
- [ ] 結果聚合和報告生成正常
- [ ] 文件服務正常

**預計時間**: 4-5 天

---

### 階段 6: System 模組遷移

**目標**: 遷移系統管理相關代碼

**遷移內容**:

- `services/security/` → `system/security/`
- `core/config.py` → `system/infra/config/config.py`
- 日誌相關代碼 → `system/infra/logging/`
- 監控相關代碼 → `system/infra/monitoring/`

**具體步驟**:

1. 創建 `system/` 目錄結構
2. 遷移 Security 服務
   - 移動 `services/security/` → `system/security/`
3. 遷移配置管理
   - 移動 `core/config.py` → `system/infra/config/config.py`
   - 更新配置讀取邏輯
4. 遷移日誌管理
   - 提取日誌相關代碼到 `system/infra/logging/`
5. 遷移監控服務
   - 提取監控代碼到 `system/infra/monitoring/`
6. 更新所有導入路徑
7. 運行測試驗證

**測試重點**:

- [ ] 安全認證正常
- [ ] 配置讀取正常
- [ ] 日誌記錄正常
- [ ] 監控指標正常

**預計時間**: 2-3 天

---

### 階段 7: API 界面層整合

**目標**: 整合所有 API 路由到統一入口

**遷移內容**:

- `services/api/main.py` → `api/main.py`
- `services/api/routers/*` → `api/routers/*` (整合並引用新位置)
- `services/api/middleware/` → `api/middleware/`
- `services/api/core/` → `api/core/`
- `services/api/storage/` → `storage/`

**具體步驟**:

1. 創建 `api/` 目錄結構
2. 遷移 API 主應用
   - 移動 `services/api/main.py` → `api/main.py`
3. 遷移中間件
   - 移動 `services/api/middleware/` → `api/middleware/`
4. 遷移 API 核心功能
   - 移動 `services/api/core/` → `api/core/`
5. 遷移文件存儲
   - 移動 `services/api/storage/` → `storage/`
6. 整合路由（引用新位置的 GenAI 路由）
7. 更新所有導入路徑
8. 運行測試驗證

**測試重點**:

- [ ] API 服務啟動正常
- [ ] 所有路由正常訪問
- [ ] 中間件正常工作
- [ ] 文件上傳下載正常
- [ ] API 版本管理正常

**預計時間**: 2-3 天

---

### 階段 8: 清理和優化

**目標**: 清理舊代碼，優化導入路徑

**任務**:

1. 刪除舊目錄（確認新代碼完全正常後）
2. 更新所有文檔中的路徑引用
3. 優化導入路徑，移除不必要的適配器
4. 代碼格式化
5. 運行完整測試套件

**清理順序**:

1. 確認所有新代碼正常工作
2. 備份舊目錄到 `backup/refactoring/`
3. 刪除舊目錄
4. 運行 pre-commit hooks
5. 運行完整測試

**測試重點**:

- [ ] 所有功能正常
- [ ] 沒有導入錯誤
- [ ] 代碼格式符合規範
- [ ] 沒有遺留的舊代碼引用

**預計時間**: 2-3 天

---

## 📝 遷移檢查清單

### 每個階段完成後檢查

- [ ] 代碼已遷移到新位置
- [ ] 導入路徑已更新（使用 grep 檢查舊路徑）
- [ ] 新模組通過單元測試
- [ ] 新模組通過集成測試
- [ ] 沒有循環依賴（使用工具檢查）
- [ ] 代碼格式符合規範（black, ruff）
- [ ] 類型檢查通過（mypy）
- [ ] 文檔已更新

### 最終檢查

- [ ] 所有模組已遷移
- [ ] 所有測試通過
- [ ] 文檔完整
- [ ] 沒有遺留的舊代碼
- [ ] Git 歷史已整理
- [ ] 性能基準測試通過

---

## 🧪 測試策略

### 單元測試

**每個模組遷移後**:

1. 為新模組編寫單元測試
2. 測試核心功能
3. 測試邊界情況
4. 確保覆蓋率 > 80%

**測試工具**:

- pytest
- pytest-cov (覆蓋率)

### 集成測試

**每完成一個大模組後**:

1. 測試模組間的集成
2. 測試 API 端點
3. 測試數據流

**測試重點**:

- API 端點響應
- 數據庫操作
- 模組間通信

### 端到端測試

**所有模組遷移完成後**:

1. 測試完整的工作流
2. 測試 Agent 協調流程
3. 測試性能基準

---

## 🔄 備份策略

### 測試代碼備份

**位置**: `tests_backup/`

**備份命令**:
\`\`\`bash

# 創建備份目錄

mkdir -p tests_backup

# 備份現有測試（如果有）

find . -type f -name "test_*.py" -o -name "*_test.py" 2>/dev/null | \
    while read file; do
        dir="tests_backup/$(dirname "$file" | sed 's|^\./||')"
        mkdir -p "$dir"
        cp "$file" "tests_backup/$file"
    done

# 備份測試配置

[ -f pytest.ini ] && cp pytest.ini tests_backup/
[ -f pyproject.toml ] && grep -A 20 "\[tool.pytest" pyproject.toml > tests_backup/pytest_config.txt || true
\`\`\`

### 代碼備份

**使用 Git 分支**:
\`\`\`bash

# 創建遷移分支

git checkout -b refactoring/directory-restructure

# 每個階段完成後提交

git add .
git commit -m "階段 X: 完成 [模組名] 遷移"

# 創建階段標籤

git tag -a "refactor/stage-X-[module]" -m "完成階段 X 遷移"
\`\`\`

### 舊代碼備份

**位置**: `backup/refactoring/`

**清理前備份**:
\`\`\`bash

# 在階段 8 清理前執行

mkdir -p backup/refactoring

# 備份舊目錄

cp -r services backup/refactoring/ 2>/dev/null || true
cp -r databases backup/refactoring/ 2>/dev/null || true
cp -r agent_process backup/refactoring/ 2>/dev/null || true
\`\`\`

---

## 📊 進度追蹤

### 遷移狀態表

| 階段 | 模組 | 狀態 | 開始日期 | 完成日期 | 測試狀態 | 備註 |
|------|------|------|---------|---------|---------|------|
| 0 | 準備階段 | ⏸️ 待開始 | - | - | - | - |
| 1 | Database | ⏸️ 待開始 | - | - | - | - |
| 2 | LLM | ⏸️ 待開始 | - | - | - | - |
| 3 | MCP | ⏸️ 待開始 | - | - | - | - |
| 4 | GenAI | ⏸️ 待開始 | - | - | - | - |
| 5 | Agent | ⏸️ 待開始 | - | - | - | - |
| 6 | System | ⏸️ 待開始 | - | - | - | - |
| 7 | API | ⏸️ 待開始 | - | - | - | - |
| 8 | 清理優化 | ⏸️ 待開始 | - | - | - | - |

**狀態標記**:

- ⏸️ 待開始
- 🔄 進行中
- ✅ 已完成
- ❌ 遇到問題
- ⚠️ 需要審查

### 問題追蹤

記錄每個階段遇到的問題和解決方案：

\`\`\`markdown

## 問題追蹤

### 階段 X - [模組名]

**問題 1**: [問題描述]

- **原因**: [原因分析]
- **解決方案**: [解決方案]
- **狀態**: [已解決/進行中]

\`\`\`

---

## ⚠️ 風險管理

### 主要風險

1. **導入路徑錯誤**
   - **風險**: 導入路徑錯誤導致運行時錯誤
   - **緩解**:
     - 使用 IDE 全局替換，逐步驗證
     - 使用靜態分析工具檢查
   - **檢查**: 運行 mypy 和 pylint

2. **循環依賴**
   - **風險**: 模組間出現循環依賴
   - **緩解**:
     - 仔細規劃模組依賴關係
     - 使用依賴注入
   - **檢查**: 使用工具檢測循環依賴

3. **功能回歸**
   - **風險**: 遷移後功能異常
   - **緩解**:
     - 每個階段完成後立即測試
     - 保留舊代碼直到確認新代碼正常
   - **檢查**: 運行完整測試套件

4. **代碼衝突**
   - **風險**: 遷移期間代碼衝突
   - **緩解**:
     - 使用 Git 分支，避免並行開發
     - 定期合併主分支
   - **檢查**: Git 狀態檢查

---

## 📚 參考資源

### 相關文檔

- [AI-Box 架構規劃](./AI-Box-架構規劃.md)
- [AI-Box 開發規範](../AI-Box-開發規範與實作範例.md)
- [目錄結構文字稿](./DIRECTORY_STRUCTURE.md)（待創建）

### 工具和命令

**導入路徑更新**:
\`\`\`bash

# 使用 sed 批量替換導入路徑（Mac）

find . -name "*.py" -type f -exec sed -i '' 's/from databases\./from database./g' {} \;

# 使用 sed 批量替換導入路徑（Linux）

find . -name "*.py" -type f -exec sed -i 's/from databases\./from database./g' {} \;
\`\`\`

**檢查導入**:
\`\`\`bash

# 檢查舊路徑的導入

grep -r "from databases" . --include="*.py"
grep -r "from services.api" . --include="*.py"
\`\`\`

**靜態檢查**:
\`\`\`bash

# mypy 類型檢查

mypy .

# ruff 代碼檢查

ruff check .

# black 格式化檢查

black --check .
\`\`\`

**循環依賴檢查**:
\`\`\`bash

# 使用 pydeps 檢查循環依賴

pip install pydeps
pydeps --show-deps --max-bacon=2 .
\`\`\`

---

## 🎯 成功標準

### 階段完成標準

每個階段被認為完成當：

1. ✅ 代碼已遷移到新位置
2. ✅ 所有導入路徑已更新
3. ✅ 單元測試通過（覆蓋率 > 80%）
4. ✅ 集成測試通過
5. ✅ 沒有 lint 錯誤
6. ✅ 沒有類型錯誤
7. ✅ 文檔已更新

### 項目完成標準

整個重構被認為完成當：

1. ✅ 所有階段已完成
2. ✅ 所有測試通過
3. ✅ 代碼符合規範
4. ✅ 文檔完整
5. ✅ 性能沒有退化
6. ✅ 沒有遺留的舊代碼

---

## 📅 時間估算

| 階段 | 預計時間 | 累計時間 | 緩衝時間 |
|------|---------|---------|---------|
| 階段 0: 準備 | 0.5 天 | 0.5 天 | 0.5 天 |
| 階段 1: Database | 1-2 天 | 1.5-2.5 天 | 1 天 |
| 階段 2: LLM | 2-3 天 | 3.5-5.5 天 | 1 天 |
| 階段 3: MCP | 2-3 天 | 5.5-8.5 天 | 1 天 |
| 階段 4: GenAI | 3-4 天 | 8.5-12.5 天 | 1.5 天 |
| 階段 5: Agent | 4-5 天 | 12.5-17.5 天 | 2 天 |
| 階段 6: System | 2-3 天 | 14.5-20.5 天 | 1 天 |
| 階段 7: API | 2-3 天 | 16.5-23.5 天 | 1 天 |
| 階段 8: 清理 | 2-3 天 | 18.5-26.5 天 | 1 天 |

**總預計時間**:

- **基礎時間**: 18.5-26.5 天
- **加上緩衝**: 約 4-6 週（考慮測試和調試時間）

---

## 📝 遷移日誌模板

每個階段遷移時，在 `REFACTORING_LOG.md` 中記錄以下信息：

\`\`\`markdown

## 階段 X: [模組名] 遷移日誌

**開始日期**: YYYY-MM-DD
**完成日期**: YYYY-MM-DD
**負責人**: [姓名]

### 遷移文件列表

- [ ] 文件1 (原路徑 -> 新路徑)
- [ ] 文件2 (原路徑 -> 新路徑)

### 導入路徑更新

- `from old.module` -> `from new.module`

### 遇到的問題

1. **問題描述**: [描述]
   - **原因**: [原因分析]
   - **解決方案**: [解決方案]
   - **狀態**: [已解決/進行中]

### 測試結果

- [ ] 單元測試: ✅ 通過 / ❌ 失敗
  - 覆蓋率: XX%
- [ ] 集成測試: ✅ 通過 / ❌ 失敗
- [ ] 靜態檢查: ✅ 通過 / ❌ 失敗
  - mypy: ✅ / ❌
  - ruff: ✅ / ❌
  - black: ✅ / ❌

### 備註

- 其他需要注意的事項
- 後續需要跟進的工作
\`\`\`

---

## 🔗 相關鏈接

- [GitHub Issues](https://github.com/your-repo/issues) - 記錄遷移問題
- [遷移日誌](./REFACTORING_LOG.md) - 詳細遷移記錄（待創建）
- [測試報告](./TEST_REPORT.md) - 測試結果報告（待創建）

---

**最後更新**: 2025-01-27
**下次審查**: 每階段完成後
**維護者**: Daniel Chung
