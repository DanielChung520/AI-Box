# System Agent 註冊清冊

**代碼功能說明**: System Agent 註冊清冊 - 記錄所有已在 System Agent Registry 中註冊的內建 Agent 的詳細信息
**創建日期**: 2026-01-13
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-28 07:31 UTC+8

---

## 📋 概述

本文檔記錄了所有已在 System Agent Registry（ArangoDB）中註冊的內建 Agent 的詳細信息，包括：

- Agent ID 和名稱
- 代碼位置
- 功能說明
- 功能觸發時機
- 必要說明和注意事項

**註冊位置**：`agents/builtin/__init__.py` → `register_builtin_agents()`

**存儲位置**：ArangoDB Collection `system_agents`

---

## 📊 Agent 清冊總覽

| Agent ID | Agent 名稱 | Agent 類型 | 版本 | 狀態 | 類別 |
|----------|-----------|-----------|------|------|------|
| `document-editing-agent` | Document Editing Agent | document_editing | 1.0.0 | ⚠️ 已停用 | system_support |
| `md-editor` | Markdown Editor Agent (v2.0) | document_editing | 2.0.0 | ✅ 啟用 | document_editing |
| `xls-editor` | Excel Editor Agent (v2.0) | document_editing | 2.0.0 | ✅ 啟用 | document_editing |
| `md-to-pdf` | Markdown to PDF Agent (v2.0) | document_conversion | 2.0.0 | ✅ 啟用 | document_conversion |
| `xls-to-pdf` | Excel to PDF Agent (v2.0) | document_conversion | 2.0.0 | ✅ 啟用 | document_conversion |
| `pdf-to-md` | PDF to Markdown Agent (v2.0) | document_conversion | 2.0.0 | ✅ 啟用 | document_conversion |
| `security-manager-agent` | Security Manager Agent | security_audit | 1.0.0 | ✅ 啟用 | system_support |
| `ka-agent` | Knowledge Architect Agent (v1.5) | knowledge_service | 1.5.0 | ✅ 啟用 | knowledge_service |
| `registry-manager-agent` | Registry Manager Agent | registry_management | 1.0.0 | ⚠️ 未註冊 | system_support |
| `orchestrator-manager-agent` | Orchestrator Manager Agent | orchestrator_management | 1.0.0 | ⚠️ 未註冊 | system_support |
| `storage-manager-agent` | Storage Manager Agent | storage_management | 1.0.0 | ⚠️ 未註冊 | system_support |
| `system-config-agent` | System Config Agent | system_config | 1.0.0 | ⚠️ 未註冊 | system_support |

**總計**：12 個 Agent（其中 1 個已停用，7 個已註冊並啟用，4 個已初始化但未註冊）

---

## 📝 詳細清冊

### 1. document-editing-agent ⚠️ 已停用

**Agent ID**: `document-editing-agent`  
**Agent 名稱**: Document Editing Agent  
**Agent 類型**: `document_editing`  
**版本**: `1.0.0`  
**狀態**: ⚠️ **已停用** (`is_active=False`, `status="offline"`)

#### 代碼位置

- **主類**: `agents/builtin/document_editing/agent.py`
- **註冊代碼**: `agents/builtin/__init__.py` (第 288-434 行)

#### 功能說明

提供文件編輯服務，支持 Markdown 文件的 AI 驅動編輯。基於流式編輯（Streaming Editing）機制。

**核心能力**：
- `document_editing`: 文件編輯能力
- `file_editing`: 文件編輯操作
- `markdown_editing`: Markdown 文件編輯
- `streaming_editing`: 流式編輯支持
- `execution`: 執行能力
- `action`: 動作執行

#### 功能觸發時機

**已停用**：此 Agent 已被標記為停用，不應被調用。

**停用原因**：
- 功能不夠精確，應使用更具體的 `md-editor` Agent
- 已被 `md-editor`（Document Editing Agent v2.0）取代

#### 必要說明

⚠️ **重要**：此 Agent 已停用，系統會自動標記為 `is_active=False` 和 `status="offline"`，避免被 Decision Engine 選中。

**替代方案**：使用 `md-editor` Agent 進行 Markdown 文件編輯。

---

### 2. md-editor ✅

**Agent ID**: `md-editor`  
**Agent 名稱**: Markdown Editor Agent (v2.0)  
**Agent 類型**: `document_editing`  
**版本**: `2.0.0`  
**狀態**: ✅ **啟用** (`is_active=True`, `status="online"`)

#### 代碼位置

- **主類**: `agents/builtin/document_editing_v2/agent.py` → `DocumentEditingAgentV2`
- **註冊代碼**: `agents/builtin/__init__.py` (第 489-589 行)
- **核心組件**:
  - `agents/core/editing_v2/intent_validator.py` - Intent 驗證
  - `agents/core/editing_v2/target_locator.py` - 目標定位
  - `agents/core/editing_v2/patch_generator.py` - Patch 生成
  - `agents/core/editing_v2/markdown_parser.py` - Markdown 解析
  - `agents/core/editing_v2/audit_logger.py` - 審計日誌

#### 功能說明

基於 Intent DSL 和 Block Patch 的結構化 Markdown 文件編輯服務。

**核心能力**：
- `document_editing`: 文件編輯能力
- `markdown_editing`: Markdown 文件編輯
- `structured_editing`: 結構化編輯
- `block_patch`: Block Patch 機制
- `execution`: 執行能力
- `action`: 動作執行

**主要功能**：
1. **結構化編輯**：基於 Block Patch 的精確編輯
2. **Intent 驗證**：驗證編輯意圖的正確性
3. **目標定位**：精確定位要編輯的內容位置
4. **審計日誌**：記錄所有編輯操作
5. **模糊匹配**：支持模糊匹配標題和內容

#### 功能觸發時機

**觸發條件**：
1. 用戶查詢包含 Markdown 文件擴展名（`.md`, `.markdown`）
2. 查詢包含編輯相關關鍵詞（"編輯", "修改", "更新", "添加", "刪除"等）
3. 任務類型為 `execution`
4. Decision Engine 匹配到 `document_editing` 類型的 Capability

**典型場景**：
- "編輯 README.md 文件"
- "在 docs/guide.md 中添加安裝說明"
- "修改 CHANGELOG.md 中的版本號"
- "刪除 docs/api.md 中的過時文檔"

#### 必要說明

1. **輸入參數**：
   - `document_context`: 文檔上下文（包含 `file_path`, `content` 等）
   - `edit_intent`: 編輯意圖（Intent DSL 格式）

2. **輸出格式**：
   - `PatchResponse`: 包含 `patches`（編輯補丁列表）和 `audit_log_id`（審計日誌 ID）

3. **依賴服務**：
   - ArangoDB（用於審計日誌存儲，可選）
   - Workspace Integration（文件系統操作）

4. **測試狀態**：
   - ✅ Agent 匹配率：88% (44/50) - 已通過測試
   - ✅ 路由正確性：已驗證

---

### 3. xls-editor ✅

**Agent ID**: `xls-editor`  
**Agent 名稱**: Excel Editor Agent (v2.0)  
**Agent 類型**: `document_editing`  
**版本**: `2.0.0`  
**狀態**: ✅ **啟用** (`is_active=True`, `status="online"`)

#### 代碼位置

- **主類**: `agents/builtin/xls_editor/agent.py` → `XlsEditingAgent`
- **註冊代碼**: `agents/builtin/__init__.py` (第 591-609 行)
- **核心組件**:
  - `agents/core/editing_v2/excel_intent_validator.py` - Excel Intent 驗證
  - `agents/core/editing_v2/excel_target_locator.py` - Excel 目標定位
  - `agents/core/editing_v2/excel_patch_generator.py` - Excel Patch 生成
  - `agents/core/editing_v2/excel_parser.py` - Excel 解析

#### 功能說明

基於 Intent DSL 和 Structured Patch 的結構化 Excel 文件編輯服務。

**核心能力**：
- `document_editing`: 文件編輯能力
- `excel_editing`: Excel 文件編輯
- `structured_editing`: 結構化編輯
- `structured_patch`: Structured Patch 機制

**主要功能**：
1. **Excel 文件編輯**：支持單元格、行、列、工作表操作
2. **結構化 Patch**：精確的 Excel 結構化編輯
3. **Intent 驗證**：驗證 Excel 編輯意圖
4. **目標定位**：精確定位 Excel 單元格、行、列

#### 功能觸發時機

**觸發條件**：
1. 用戶查詢包含 Excel 文件擴展名（`.xlsx`, `.xls`）
2. 查詢包含編輯相關關鍵詞（"編輯", "修改", "輸入", "設置", "插入", "刪除"等）
3. 任務類型為 `execution`
4. Decision Engine 匹配到 `document_editing` 類型的 Capability

**典型場景**：
- "在 data.xlsx 的 Sheet1 中 A1 單元格輸入數據"
- "編輯 report.xlsx 文件，在 B 列添加新數據"
- "修改 sales.xlsx 中的公式"
- "在 budget.xlsx 中插入新行"

#### 必要說明

1. **輸入參數**：
   - `document_context`: 文檔上下文（包含 `file_path`, `content` 等）
   - `edit_intent`: 編輯意圖（Excel Intent DSL 格式）

2. **輸出格式**：
   - `ExcelPatchResponse`: 包含 `patches`（Excel 編輯補丁列表）

3. **依賴庫**：
   - `openpyxl`（Excel 文件讀寫）

4. **測試狀態**：
   - ✅ Agent 匹配率：100% (10/10) - 已通過測試
   - ✅ 路由正確性：已驗證

---

### 4. md-to-pdf ✅

**Agent ID**: `md-to-pdf`  
**Agent 名稱**: Markdown to PDF Agent (v2.0)  
**Agent 類型**: `document_conversion`  
**版本**: `2.0.0`  
**狀態**: ✅ **啟用** (`is_active=True`, `status="online"`)

#### 代碼位置

- **主類**: `agents/builtin/md_to_pdf/agent.py` → `MdToPdfAgent`
- **註冊代碼**: `agents/builtin/__init__.py` (第 611-628 行)
- **核心組件**:
  - `agents/builtin/md_to_pdf/pandoc_converter.py` - Pandoc 轉換器
  - `agents/builtin/md_to_pdf/models.py` - 數據模型

#### 功能說明

將 Markdown 文件轉換為 PDF 文件。

**核心能力**：
- `document_conversion`: 文檔轉換能力
- `markdown_to_pdf`: Markdown 轉 PDF
- `pdf_generation`: PDF 生成

**主要功能**：
1. **Markdown 轉 PDF**：使用 Pandoc 將 Markdown 轉換為 PDF
2. **配置支持**：支持頁面大小、頁眉頁腳、目錄等配置
3. **模板支持**：支持自定義 PDF 模板

#### 功能觸發時機

**觸發條件**：
1. 用戶查詢同時包含 Markdown 文件擴展名（`.md`, `.markdown`）和 `pdf` 關鍵詞
2. 查詢包含轉換相關關鍵詞（"轉換", "轉為", "轉成", "生成", "導出", "輸出"等）
3. 任務類型為 `execution`
4. Decision Engine 匹配到 `document_conversion` 類型的 Capability

**典型場景**：
- "將 README.md 轉換為 PDF"
- "生成 docs/guide.md 的 PDF 版本"
- "把 CHANGELOG.md 導出為 PDF 文件"
- "將 README.md 轉為 PDF，並添加頁眉和頁腳"

#### 必要說明

1. **輸入參數**：
   - `document_context`: 文檔上下文（包含 `file_path`）
   - `conversion_config`: 轉換配置（頁面大小、頁眉頁腳等）

2. **輸出格式**：
   - `ConversionResponse`: 包含 `output_file_path`（輸出 PDF 文件路徑）

3. **依賴工具**：
   - Pandoc（必須安裝在系統中）

4. **測試狀態**：
   - ✅ Agent 匹配率：100% (10/10) - 已通過測試
   - ✅ 路由正確性：已驗證

---

### 5. xls-to-pdf ✅

**Agent ID**: `xls-to-pdf`  
**Agent 名稱**: Excel to PDF Agent (v2.0)  
**Agent 類型**: `document_conversion`  
**版本**: `2.0.0`  
**狀態**: ✅ **啟用** (`is_active=True`, `status="online"`)

#### 代碼位置

- **主類**: `agents/builtin/xls_to_pdf/agent.py` → `XlsToPdfAgent`
- **註冊代碼**: `agents/builtin/__init__.py` (第 630-647 行)
- **核心組件**:
  - `agents/builtin/xls_to_pdf/excel_pdf_converter.py` - Excel PDF 轉換器
  - `agents/builtin/xls_to_pdf/models.py` - 數據模型

#### 功能說明

將 Excel 文件轉換為 PDF 文件。

**核心能力**：
- `document_conversion`: 文檔轉換能力
- `excel_to_pdf`: Excel 轉 PDF
- `pdf_generation`: PDF 生成

**主要功能**：
1. **Excel 轉 PDF**：將 Excel 文件轉換為 PDF
2. **配置支持**：支持頁面大小、頁面方向、縮放、邊距等配置
3. **工作表選擇**：支持選擇特定工作表進行轉換

#### 功能觸發時機

**觸發條件**：
1. 用戶查詢同時包含 Excel 文件擴展名（`.xlsx`, `.xls`）和 `pdf` 關鍵詞
2. 查詢包含轉換相關關鍵詞（"轉換", "轉為", "轉成", "生成", "導出", "輸出"等）
3. 任務類型為 `execution`
4. Decision Engine 匹配到 `document_conversion` 類型的 Capability

**典型場景**：
- "將 data.xlsx 轉換為 PDF"
- "幫我把 report.xlsx 轉成 PDF 文件"
- "生成 sales.xlsx 的 PDF 版本"
- "將 budget.xlsx 轉為 PDF，頁面大小設為 A4"

#### 必要說明

1. **輸入參數**：
   - `document_context`: 文檔上下文（包含 `file_path`）
   - `conversion_config`: 轉換配置（頁面大小、方向、縮放、邊距等）

2. **輸出格式**：
   - `ExcelConversionResponse`: 包含 `output_file_path`（輸出 PDF 文件路徑）

3. **依賴庫**：
   - `openpyxl`（Excel 文件讀取）
   - PDF 生成庫（如 `reportlab` 或 `fpdf`）

4. **測試狀態**：
   - ✅ Agent 匹配率：100% (10/10) - 已通過測試
   - ✅ 路由正確性：已驗證

---

### 6. pdf-to-md ✅

**Agent ID**: `pdf-to-md`  
**Agent 名稱**: PDF to Markdown Agent (v2.0)  
**Agent 類型**: `document_conversion`  
**版本**: `2.0.0`  
**狀態**: ✅ **啟用** (`is_active=True`, `status="online"`)

#### 代碼位置

- **主類**: `agents/builtin/pdf_to_md/agent.py` → `PdfToMdAgent`
- **註冊代碼**: `agents/builtin/__init__.py` (第 649-666 行)
- **核心組件**:
  - `agents/builtin/pdf_to_md/pdf_converter.py` - PDF 轉換器
  - `agents/builtin/pdf_to_md/models.py` - 數據模型

#### 功能說明

將 PDF 文件轉換為 Markdown 文件。

**核心能力**：
- `document_conversion`: 文檔轉換能力
- `pdf_to_markdown`: PDF 轉 Markdown
- `text_extraction`: 文本提取

**主要功能**：
1. **PDF 轉 Markdown**：提取 PDF 內容並轉換為 Markdown 格式
2. **結構識別**：自動識別標題、列表、表格等結構
3. **圖片提取**：提取 PDF 中的圖片（可選）
4. **表格識別**：識別並轉換 PDF 中的表格（可選）

#### 功能觸發時機

**觸發條件**：
1. 用戶查詢同時包含 PDF 文件擴展名（`.pdf`）和 Markdown 關鍵詞（`markdown`, `.md`）
2. 查詢包含轉換相關關鍵詞（"轉換", "轉為", "轉成", "生成", "導出", "提取"等）
3. 任務類型為 `execution`
4. Decision Engine 匹配到 `document_conversion` 類型的 Capability

**典型場景**：
- "將 document.pdf 轉換為 Markdown"
- "幫我把 report.pdf 轉成 Markdown 文件"
- "生成 manual.pdf 的 Markdown 版本"
- "將 document.pdf 轉為 Markdown，並識別表格"

#### 必要說明

1. **輸入參數**：
   - `document_context`: 文檔上下文（包含 `file_path`）
   - `conversion_config`: 轉換配置（是否識別表格、提取圖片等）

2. **輸出格式**：
   - `PdfConversionResponse`: 包含 `output_file_path`（輸出 Markdown 文件路徑）

3. **依賴庫**：
   - PDF 解析庫（如 `PyPDF2`, `pdfplumber`, `pymupdf`）

4. **測試狀態**：
   - ✅ Agent 匹配率：100% (10/10) - 已通過測試
   - ✅ 路由正確性：已驗證

---

### 7. security-manager-agent ✅

**Agent ID**: `security-manager-agent`  
**Agent 名稱**: Security Manager Agent  
**Agent 類型**: `security_audit`  
**版本**: `1.0.0`  
**狀態**: ✅ **啟用** (`is_active=True`, `status="online"`)

#### 代碼位置

- **主類**: `agents/builtin/security_manager/agent.py` → `SecurityManagerAgent`
- **註冊代碼**: `agents/builtin/__init__.py` (第 437-487 行)

#### 功能說明

安全審計和管理服務，提供智能風險評估、權限檢查和驗證。

**核心能力**：
- `security_audit`: 安全審計
- `risk_assessment`: 風險評估
- `permission_check`: 權限檢查

**主要功能**：
1. **安全審計**：審計系統操作的安全性
2. **風險評估**：評估操作風險等級
3. **權限檢查**：檢查用戶權限和資源訪問權限
4. **安全驗證**：驗證操作是否符合安全策略

#### 功能觸發時機

**觸發條件**：
1. 系統需要進行安全審計時
2. 需要進行風險評估時
3. 需要進行權限檢查時
4. 由 Orchestrator 或其他 Agent 調用

**典型場景**：
- 文件編輯前的權限檢查
- 系統配置變更前的風險評估
- 敏感操作的安全審計

#### 必要說明

1. **輸入參數**：
   - `action`: 操作類型
   - `resource`: 資源信息
   - `user_id`: 用戶 ID

2. **輸出格式**：
   - 包含審計結果、風險等級、權限檢查結果

3. **依賴服務**：
   - 權限管理系統
   - 審計日誌系統

---

### 8. registry-manager-agent ✅

**Agent ID**: `registry-manager-agent`  
**Agent 名稱**: Registry Manager Agent  
**Agent 類型**: `registry_management`  
**版本**: `1.0.0`  
**狀態**: ✅ **啟用** (`is_active=True`, `status="online"`)

#### 代碼位置

- **主類**: `agents/builtin/registry_manager/agent.py` → `RegistryManagerAgent`
- **註冊代碼**: `agents/builtin/__init__.py` (第 76 行初始化，但**未在 `_do_register_all_agents()` 中註冊**)

#### 註冊狀態

⚠️ **注意**：此 Agent 在 `initialize_builtin_agents()` 中被初始化，但在 `_do_register_all_agents()` 中**未找到註冊代碼**。可能尚未完全實現註冊邏輯。

#### 功能說明

AI 驅動的 Agent 註冊管理服務，提供智能匹配、發現和推薦功能。

**核心能力**：
- `agent_discovery`: Agent 發現
- `agent_matching`: Agent 匹配
- `registry_analysis`: 註冊分析

**主要功能**：
1. **智能 Agent 匹配**：根據任務需求匹配最適合的 Agent
2. **Agent 發現和推薦**：發現可用的 Agent 並提供推薦
3. **註冊分析和優化建議**：分析 Agent 註冊情況並提供優化建議

#### 功能觸發時機

**觸發條件**：
1. 需要查找合適的 Agent 時
2. 需要分析 Agent 註冊情況時
3. 需要獲取 Agent 推薦時
4. 由 Orchestrator 或其他系統組件調用

**典型場景**：
- Agent Discovery 過程
- Agent 推薦系統
- 註冊分析和優化

#### 必要說明

1. **輸入參數**：
   - `action`: 操作類型（`match`, `discover`, `analyze`）
   - `task_description`: 任務描述
   - `capabilities`: 所需能力

2. **輸出格式**：
   - `RegistryManagerResponse`: 包含匹配的 Agent 列表或推薦結果

3. **依賴服務**：
   - Agent Registry
   - Agent Discovery Service
   - LLM 客戶端（用於智能匹配）

---

### 9. orchestrator-manager-agent ✅

**Agent ID**: `orchestrator-manager-agent`  
**Agent 名稱**: Orchestrator Manager Agent  
**Agent 類型**: `orchestrator_management`  
**版本**: `1.0.0`  
**狀態**: ✅ **啟用** (`is_active=True`, `status="online"`)

#### 代碼位置

- **主類**: `agents/builtin/orchestrator_manager/agent.py` → `OrchestratorManagerAgent`
- **註冊代碼**: `agents/builtin/__init__.py` (第 86 行初始化，但**未在 `_do_register_all_agents()` 中註冊**)

#### 註冊狀態

⚠️ **注意**：此 Agent 在 `initialize_builtin_agents()` 中被初始化，但在 `_do_register_all_agents()` 中**未找到註冊代碼**。可能尚未完全實現註冊邏輯。

#### 功能說明

AI 驅動的任務協調服務，提供智能任務路由和負載均衡功能。

**核心能力**：
- `task_routing`: 任務路由
- `load_balancing`: 負載均衡
- `orchestration_decision`: 協調決策

**主要功能**：
1. **智能任務路由**：根據任務特徵路由到最適合的 Agent
2. **負載均衡**：平衡各 Agent 的負載
3. **任務協調決策**：做出任務協調決策

#### 功能觸發時機

**觸發條件**：
1. 需要進行任務路由時
2. 需要進行負載均衡時
3. 需要進行協調決策時
4. 由系統調度器調用

**典型場景**：
- 任務分發和路由
- 負載均衡管理
- 協調策略決策

#### 必要說明

1. **輸入參數**：
   - `action`: 操作類型（`route`, `balance`, `decide`）
   - `task`: 任務信息
   - `agents`: 可用 Agent 列表

2. **輸出格式**：
   - `OrchestratorManagerResponse`: 包含路由決策或負載均衡結果

3. **依賴服務**：
   - Agent Orchestrator
   - Agent Registry
   - LLM 客戶端（用於智能決策）

---

### 10. storage-manager-agent ✅

**Agent ID**: `storage-manager-agent`  
**Agent 名稱**: Storage Manager Agent  
**Agent 類型**: `storage_management`  
**版本**: `1.0.0`  
**狀態**: ✅ **啟用** (`is_active=True`, `status="online"`)

#### 代碼位置

- **主類**: `agents/builtin/storage_manager/agent.py` → `StorageManagerAgent`
- **註冊代碼**: `agents/builtin/__init__.py` (第 91 行初始化，但**未在 `_do_register_all_agents()` 中註冊**)

#### 註冊狀態

⚠️ **注意**：此 Agent 在 `initialize_builtin_agents()` 中被初始化，但在 `_do_register_all_agents()` 中**未找到註冊代碼**。可能尚未完全實現註冊邏輯。

#### 功能說明

AI 驅動的存儲管理服務，提供智能存儲策略和數據管理功能。

**核心能力**：
- `storage_strategy`: 存儲策略
- `data_management`: 數據管理
- `storage_optimization`: 存儲優化

**主要功能**：
1. **智能存儲策略推薦**：根據數據特徵推薦存儲策略
2. **數據管理和優化**：管理數據存儲和優化存儲空間
3. **存儲分析和建議**：分析存儲使用情況並提供優化建議

#### 功能觸發時機

**觸發條件**：
1. 需要選擇存儲策略時
2. 需要進行數據管理時
3. 需要進行存儲優化時
4. 由文件服務或其他系統組件調用

**典型場景**：
- 文件上傳時的存儲策略選擇
- 數據歸檔和清理
- 存儲空間優化

#### 必要說明

1. **輸入參數**：
   - `action`: 操作類型（`recommend`, `manage`, `optimize`）
   - `data_info`: 數據信息
   - `storage_type`: 存儲類型

2. **輸出格式**：
   - `StorageManagerResponse`: 包含存儲策略推薦或管理結果

3. **依賴服務**：
   - Agent File Service（SeaweedFS）
   - Memory Manager
   - LLM 客戶端（用於智能推薦）

4. **注意事項**：
   - 如果 SeaweedFS 未運行，文件服務可能不可用，但 Agent 仍可繼續運行

---

### 11. ka-agent ✅

**Agent ID**: `ka-agent`  
**Agent 名稱**: Knowledge Architect Agent (v1.5)  
**Agent 類型**: `knowledge_service`  
**版本**: `1.5.0`  
**狀態**: ✅ **啟用** (`is_active=True`, `status="online"`)

#### 代碼位置

- **主類**: `agents/builtin/ka_agent/agent.py` → `KnowledgeArchitectAgent`
- **註冊代碼**: `agents/builtin/__init__.py` (第 678-696 行)
- **核心組件**:
  - `agents/builtin/ka_agent/models.py` - 數據模型
  - `agents/builtin/ka_agent/storage_adapter.py` - 存儲適配器
  - `agents/builtin/knowledge_ontology_agent/agent.py` - 知識圖譜 Agent（協作）

#### 功能說明

知識資產總建築師，負責知識資產化、生命週期管理與混合檢索。

**核心能力**：
- `knowledge.query`: 知識查詢能力
- `ka.lifecycle`: 知識資產生命週期管理
- `ka.list`: 知識資產列表查詢
- `ka.retrieve`: 知識資產檢索

**主要功能**：
1. **知識資產上架**：將文件轉換為知識資產，生成 KNW-Code 和 Metadata
2. **混合檢索**：提供向量檢索 + 圖譜檢索的混合檢索服務
3. **知識資產管理**：管理知識資產的生命週期（Draft → Active → Deprecated → Archived）
4. **版本管理**：支持知識資產的版本控制和版本關聯
5. **Ontology 對齊**：自動對齊 Domain 和 Major Ontology

**檢索策略**（根據 KA-Agent 作業規範）：
- **Domain 過濾**：快速縮小候選知識範圍
- **Major 過濾**：在 Domain 範圍內進一步精準定位
- **Base 向量檢索**：在精選 Major 範圍內查找最相關知識原子（Qdrant）
- **圖譜/Ontology 查詢**：結合知識結構進行推理（ArangoDB）
- **語義重排序**：整合向量檢索 + 圖譜查詢結果，生成最終答案

#### 功能觸發時機

**觸發條件**：
1. 用戶查詢包含知識相關關鍵詞（"知識", "查詢", "檢索", "搜索", "上架", "知識資產"等）
2. 任務類型為 `knowledge_service` 或 `retrieval`
3. Decision Engine 匹配到 `knowledge_service` 類型的 Capability
4. 需要進行知識資產管理操作時（上架、更版、生命週期變更）

**典型場景**：
- **檢索場景**：
  - "我想知道陳經理領導的團隊去年有哪些核心專案？"
  - "查詢物料入庫流程規範"
  - "搜索供應商評估相關知識"
- **管理場景**：
  - "上架新的知識文件"
  - "更新知識資產版本"
  - "查詢知識資產列表"

#### 必要說明

1. **輸入參數**：
   - `query`: 查詢文本（檢索場景）
   - `file_id`: 文件 ID（上架場景）
   - `domain`: Domain 分類（可選，用於過濾）
   - `major`: Major 分類（可選，用於過濾）
   - `query_type`: 查詢類型（`vector`, `graph`, `hybrid`）

2. **輸出格式**：
   - `KAResponse`: 包含檢索結果列表（`results`），每個結果包含：
     - `content`: 知識內容
     - `ka_id`: 知識資產 ID
     - `version`: 版本號
     - `confidence_hint`: 相關度分數
     - `source`: 來源（`vector` 或 `graph`）

3. **依賴服務**：
   - **Qdrant**：向量檢索服務
   - **ArangoDB**：圖譜查詢和知識資產元數據存儲
   - **EmbeddingService**：查詢向量生成
   - **NERService**：實體識別（圖譜檢索）
   - **KGBuilderService**：知識圖譜構建和查詢
   - **KnowledgeOntologyAgent**：圖譜查詢協作
   - **PolicyService**：權限檢查
   - **AuditLogService**：審計日誌

4. **檢索流程**（根據 KA-Agent 作業規範 4.2 節）：
   - 語義解析 & Intent 判斷
   - Domain 過濾（使用 Metadata 中 `domain` 欄位）
   - Major 過濾（使用 Metadata 中 `major` 欄位）
   - Base 向量檢索（Qdrant）
   - 圖譜/Ontology 查詢（ArangoDB）
   - 語義重排序 & RAG Pipeline
   - 結果回傳給 Agent

5. **知識資產編碼**：
   - **KNW-Code 格式**：`KNW-{DOMAIN}-{TYPE}-{SUBDOMAIN}-{OBJECT}-{SCOPE}-v{MAJOR.MINOR}`
   - **範例**：`KNW-ENERGY-SPEC-PYROLYSIS-REACTOR-SYSTEM-v1.0`
   - **Metadata 欄位**：`KNW_Code`, `Domain`, `Major`, `Base`, `Version`, `Provenance`, `International_Classification`

6. **權限與安全**：
   - 所有檢索操作必須通過 `PolicyService.check_permission()` 權限檢查
   - 所有上架操作必須記錄審計日誌
   - 支持 ACL 權限檢查（向量檢索時）

7. **相關文檔**：
   - [KA-Agent 作業規範](../KA-Agent/知識庫/KA-Agent作業規範.md)
   - [KA-Agent 規格書](../KA-Agent/KA-Agent-規格書.md)
   - [Knowledge Asset 版本號規範](../KA-Agent/知識庫/Knowledge-Asset-版本號規範.md)

---

### 12. system-config-agent ✅

**Agent ID**: `system-config-agent`  
**Agent 名稱**: System Config Agent  
**Agent 類型**: `system_config`  
**版本**: `1.0.0`  
**狀態**: ✅ **啟用** (`is_active=True`, `status="online"`)

#### 代碼位置

- **主類**: `agents/builtin/system_config_agent/agent.py` → `SystemConfigAgent`
- **註冊代碼**: `agents/builtin/__init__.py` (第 96 行初始化，但**未在 `_do_register_all_agents()` 中註冊**)

#### 註冊狀態

⚠️ **注意**：此 Agent 在 `initialize_builtin_agents()` 中被初始化，但在 `_do_register_all_agents()` 中**未找到註冊代碼**。可能尚未完全實現註冊邏輯。
- **核心組件**:
  - `agents/builtin/system_config_agent/preview_service.py` - 配置預覽服務
  - `agents/builtin/system_config_agent/rollback_service.py` - 配置回滾服務
  - `agents/builtin/system_config_agent/inspection_service.py` - 配置檢查服務

#### 功能說明

系統設置代理，通過自然語言進行系統配置管理。

**核心能力**：
- `config_query`: 配置查詢
- `config_set`: 配置設置
- `config_validation`: 配置驗證
- `config_preview`: 配置預覽
- `config_rollback`: 配置回滾

**主要功能**：
1. **配置查詢**：查詢系統配置值
2. **配置設置**：設置系統配置值
3. **配置驗證**：驗證配置的合規性
4. **配置預覽**：預覽配置變更效果
5. **配置回滾**：回滾配置變更

#### 功能觸發時機

**觸發條件**：
1. 用戶通過自然語言進行系統配置操作時
2. 查詢包含配置相關關鍵詞（"設置", "配置", "查詢", "修改"等）
3. 任務類型為 `execution` 且 Intent 為配置相關
4. 由 Orchestrator 調用

**典型場景**：
- "查詢系統的 LLM 配置"
- "設置 GenAI 的默認模型為 gpt-4"
- "修改系統的日誌級別為 DEBUG"
- "回滾最近的配置變更"

#### 必要說明

1. **輸入參數**：
   - `intent`: 配置意圖（`ConfigIntent`，由 Orchestrator 解析）
   - `admin_user_id`: 管理員用戶 ID
   - `context`: 上下文信息

2. **輸出格式**：
   - `ConfigOperationResult`: 包含配置查詢結果或設置確認

3. **依賴服務**：
   - Config Store Service（ArangoDB）
   - Log Service
   - Change Proposal Service（可選）

4. **安全要求**：
   - 需要管理員權限
   - 所有配置變更都會記錄審計日誌

5. **配置層級**：
   - System 級配置（全局）
   - Tenant 級配置（租戶）
   - User 級配置（用戶）

---

## 🔍 Agent 分類統計

### 按類別分類

| 類別 | Agent 數量 | Agent 列表 |
|------|-----------|-----------|
| **document_editing** | 3 | md-editor, xls-editor, document-editing-agent (已停用) |
| **document_conversion** | 3 | md-to-pdf, xls-to-pdf, pdf-to-md |
| **knowledge_service** | 1 | ka-agent |
| **system_support** | 5 | security-manager-agent, registry-manager-agent, orchestrator-manager-agent, storage-manager-agent, system-config-agent |

### 按狀態分類

| 狀態 | Agent 數量 | Agent 列表 |
|------|-----------|-----------|
| ✅ **已註冊並啟用** | 7 | md-editor, xls-editor, md-to-pdf, xls-to-pdf, pdf-to-md, security-manager-agent, ka-agent |
| ⚠️ **已停用** | 1 | document-editing-agent |
| ⚠️ **已初始化但未註冊** | 4 | registry-manager-agent, orchestrator-manager-agent, storage-manager-agent, system-config-agent |

---

## 📌 重要說明

### 1. Agent 註冊流程

所有內建 Agent 通過以下流程註冊：

1. **初始化**：`initialize_builtin_agents()` - 創建 Agent 實例
2. **註冊到 System Agent Registry**：`system_agent_store.register_system_agent()` - 存儲到 ArangoDB
3. **註冊到 Agent Registry**：`registry.register_agent()` - 註冊到內存 Registry

### 2. Agent 狀態管理

- **啟用狀態**：`is_active=True` - Agent 可用於路由
- **停用狀態**：`is_active=False` - Agent 不可用於路由
- **在線狀態**：`status="online"` - Agent 在線可用
- **離線狀態**：`status="offline"` - Agent 離線不可用

### 3. Agent 路由優先級

Decision Engine 在選擇 Agent 時的優先級：

1. **文件擴展名匹配**：優先匹配文件擴展名（`.md` → `md-editor`, `.xlsx` → `xls-editor`）
2. **轉換關鍵詞匹配**：匹配轉換關鍵詞（"轉換", "生成", "導出"等）
3. **Capability 匹配**：匹配 Agent 的 Capability
4. **排除已停用 Agent**：自動排除 `is_active=False` 的 Agent

### 4. 測試狀態

**已測試 Agent**（文件編輯相關）：
- ✅ md-editor: 88% (44/50) - 基本達成
- ✅ xls-editor: 100% (10/10) - 已達成
- ✅ md-to-pdf: 100% (10/10) - 已達成
- ✅ xls-to-pdf: 100% (10/10) - 已達成
- ✅ pdf-to-md: 100% (10/10) - 已達成

**未測試 Agent**（系統支持相關）：
- ⚠️ security-manager-agent（已註冊但未測試）
- ⚠️ registry-manager-agent（已初始化但未註冊）
- ⚠️ orchestrator-manager-agent（已初始化但未註冊）
- ⚠️ storage-manager-agent（已初始化但未註冊）
- ⚠️ system-config-agent（已初始化但未註冊）

**待完成工作**：
- [ ] 為 registry-manager-agent、orchestrator-manager-agent、storage-manager-agent、system-config-agent 添加 `agent_id` 屬性
- [ ] 在 `_do_register_all_agents()` 中添加這些 Agent 的註冊邏輯
- [ ] 驗證所有 Agent 的註冊狀態

---

## 🔗 相關文檔

- [Agent 註冊規格書](./Agent-註冊-規格書.md) - Agent 註冊的完整規格
- [System Agent Registry 實施總結](./System-Agent-Registry-實施總結.md) - System Agent Registry 實施總結
- [Agent 開發規範](./Agent-開發規範.md) - Agent 開發規範
- [文件編輯Agent語義路由測試計劃-v4.md](../語義與任務分析/文件編輯Agent語義路由測試計劃-v4.md) - 文件編輯 Agent 測試計劃

---

**最後更新日期**: 2026-01-28 07:31 UTC+8  
**維護人**: Daniel Chung
