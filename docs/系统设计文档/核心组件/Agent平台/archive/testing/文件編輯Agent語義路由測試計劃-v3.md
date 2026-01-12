# 文件編輯 Agent 語義路由測試計劃 v3.0

**代碼功能說明**: 文件編輯 Agent 語義路由測試計劃 - 重新設計的測試計劃，專注於精確的 Agent 選擇，包含完整的場景列表和任務標籤
**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-12 10:08

---

## 📋 測試計劃概述

### 測試目的

本測試計劃旨在驗證 AI-Box Agent Platform 的語義路由能力，確保系統能夠根據用戶的自然語言指令，**精確**識別意圖並調用相應的文件編輯或轉換 Agent。

### 測試範圍

本測試計劃包含 **90 個測試場景**，覆蓋以下 5 類 Agent：

1. **md-editor**（Markdown 編輯器）- 50 個場景（大部分編輯場景，默認選擇）
2. **xls-editor**（Excel 編輯器）- 10 個場景
3. **md-to-pdf**（Markdown 轉 PDF）- 10 個場景
4. **xls-to-pdf**（Excel 轉 PDF）- 10 個場景
5. **pdf-to-md**（PDF 轉 Markdown）- 10 個場景

### 測試標準

**通過標準**：系統能夠根據語義正確識別意圖並調用相應的 Agent，無需實際執行文件操作。

**驗證點**：

- ✅ 任務類型識別正確（應為 `execution`）
- ✅ 意圖提取準確（識別出文件編輯/轉換意圖）
- ✅ Agent 調用正確（調用預期的 Agent：`md-editor`、`xls-editor`、`md-to-pdf`、`xls-to-pdf`、`pdf-to-md`）
- ✅ **不調用 `document-editing-agent`**（已標記為 inactive）

---

## ⚠️ 重要提醒：已調查和明確的事項

### 1. System Agent 註冊狀態 ✅

**已確認**：

- ✅ 所有 System Agents 都已正確註冊到 System Agent Registry Store（ArangoDB）
- ✅ `AgentRegistry.list_agents` 方法已修復，正確從 System Agent Registry Store 加載 System Agents
- ✅ 當 `include_system_agents=True` 時，System Agents 會被正確加載和轉換為 `AgentRegistryInfo`

**相關文件**：

- `agents/services/registry/registry.py`（已修復 `list_agents` 方法的邏輯錯誤）
- `services/api/services/system_agent_registry_store_service.py`（System Agent Registry Store 服務）

**測試前檢查**：

- ✅ 確認 System Agents 已註冊（使用 `Agent註冊確認報告.md` 驗證）
- ✅ 確認 `document-editing-agent` 已標記為 `is_active=False` 和 `status="offline"`

### 2. document-editing-agent 狀態 ⚠️

**已明確**：

- ⚠️ `document-editing-agent` 不夠精確，應使用更具體的 `md-editor`
- ✅ `document-editing-agent` 已標記為 `is_active=False` 和 `status="offline"`
- ✅ 測試中不應調用 `document-editing-agent`

**相關修改**：

- `agents/builtin/__init__.py`（註冊時設置 `status="offline"` 和 `is_active=False`）

**測試前檢查**：

- ✅ 確認 `document-editing-agent` 的 `is_active=False`
- ✅ 確認 `document-editing-agent` 的 `status="offline"`
- ✅ 確認測試結果中沒有調用 `document-editing-agent`

### 3. 測試背景和歷史問題 ✅

**已解決的問題**：

- ✅ **Round 6**: 任務類型識別準確率 100%（修復了 `TaskAnalyzer` 覆蓋邏輯）
- ✅ **Round 7**: Agent 調用成功率從 0% 提升到 65%（修復了 `AgentRegistry.list_agents` 邏輯錯誤）
- ✅ RouterLLM 正常工作（`router_confidence` 正常值，不再是 0.0）

**已知問題**：

- ⚠️ Agent 選擇精確度仍需改進（md-editor 場景中 4 個場景調用了 `document-editing-agent`）
- ⚠️ 其他類別場景（xls-editor, md-to-pdf, xls-to-pdf, pdf-to-md）的 Agent 匹配率為 0%

**相關文檔**：

- `文件編輯Agent語義路由測試劇本-v2.md`（包含 Round 1-7 的測試結果和分析）

### 4. Agent 選擇邏輯 ✅

**已明確**：

- ✅ `CapabilityMatcher` 同時查詢 `document_editing` 和 `document_conversion` 類型的 Agent
- ✅ `DecisionEngine` 使用文件擴展名匹配邏輯（`_select_agent_by_file_extension`）
- ✅ `DecisionEngine` 優先選擇具體的 Agent（如 `md-editor`）而非通用 Agent（如 `document-editing-agent`）

**相關文件**：

- `agents/task_analyzer/capability_matcher.py`（已修復查詢邏輯）
- `agents/task_analyzer/decision_engine.py`（包含文件擴展名匹配邏輯）

**測試前檢查**：

- ✅ 確認 `CapabilityMatcher` 正確查詢 System Agents
- ✅ 確認 `DecisionEngine` 的文件擴展名匹配邏輯正確

---

## 📊 測試場景設計

### 場景分類原則

#### 1. md-editor（50 個場景）

**設計原則**：

- **默認選擇**：大部分 Markdown 文件編輯場景，如果沒有特殊說明，都應該使用 `md-editor`
- **覆蓋範圍**：
  - 基本編輯操作（創建、修改、刪除）
  - 內容編輯（添加、插入、替換、刪除內容）
  - 格式編輯（標題、列表、鏈接、圖片）
  - 結構編輯（章節、段落、表格）
  - 批量操作（批量替換、批量格式化）

**場景示例**：

- "編輯文件 README.md"
- "修改 docs/guide.md 文件中的第一章節"
- "在 README.md 中添加安裝說明"
- "更新 CHANGELOG.md 文件"
- "刪除 docs/api.md 中的過時文檔"
- "將 README.md 中的 '舊版本' 替換為 '新版本'"
- "重寫 docs/guide.md 中的使用說明章節"
- ...（共 50 個場景）

#### 2. xls-editor（10 個場景）

**設計原則**：

- **明確語義**：用戶輸入必須明確表明是 Excel 文件編輯
- **文件擴展名**：通常包含 `.xlsx` 或 `.xls` 文件擴展名
- **操作類型**：Excel 特定的操作（單元格編輯、格式設置、公式、圖表等）

**場景示例**：

- "編輯 data.xlsx 文件"
- "在 data.xlsx 的 Sheet1 中 A1 單元格輸入數據"
- "將 data.xlsx 中 A1 單元格設置為粗體和紅色"
- "在 data.xlsx 的 Sheet1 中 B 列前插入一列"
- ...（共 10 個場景）

**注意**：如果用戶輸入不明確（例如只說"編輯文件"而沒有文件擴展名），系統應該產生指令確認。

#### 3. md-to-pdf（10 個場景）

**設計原則**：

- **明確語義**：用戶輸入必須明確表明是 Markdown 轉 PDF 的轉換任務
- **關鍵詞**：包含"轉換"、"轉為"、"轉成"、"轉換為"等轉換關鍵詞
- **文件類型**：明確提到 Markdown 文件（`.md`）和 PDF 文件（`.pdf`）

**場景示例**：

- "將 README.md 轉換為 PDF"
- "將 docs/guide.md 轉為 PDF 文件"
- "將 document.md 轉成 PDF 格式"
- "將 report.md 轉換為 report.pdf"
- ...（共 10 個場景）

**注意**：如果用戶輸入不明確（例如只說"轉換文件"而沒有明確文件類型），系統應該產生指令確認。

#### 4. xls-to-pdf（10 個場景）

**設計原則**：

- **明確語義**：用戶輸入必須明確表明是 Excel 轉 PDF 的轉換任務
- **關鍵詞**：包含"轉換"、"轉為"、"轉成"、"轉換為"等轉換關鍵詞
- **文件類型**：明確提到 Excel 文件（`.xlsx` 或 `.xls`）和 PDF 文件（`.pdf`）

**場景示例**：

- "將 data.xlsx 轉換為 PDF"
- "將 report.xlsx 轉為 PDF 文件"
- "將 spreadsheet.xls 轉成 PDF 格式"
- "將 data.xlsx 轉換為 data.pdf"
- ...（共 10 個場景）

**注意**：如果用戶輸入不明確（例如只說"轉換文件"而沒有明確文件類型），系統應該產生指令確認。

#### 5. pdf-to-md（10 個場景）

**設計原則**：

- **明確語義**：用戶輸入必須明確表明是 PDF 轉 Markdown 的轉換任務
- **關鍵詞**：包含"轉換"、"轉為"、"轉成"、"轉換為"等轉換關鍵詞
- **文件類型**：明確提到 PDF 文件（`.pdf`）和 Markdown 文件（`.md`）

**場景示例**：

- "將 document.pdf 轉換為 Markdown"
- "將 report.pdf 轉為 Markdown 文件"
- "將 file.pdf 轉成 Markdown 格式"
- "將 document.pdf 轉換為 document.md"
- ...（共 10 個場景）

**注意**：如果用戶輸入不明確（例如只說"轉換文件"而沒有明確文件類型），系統應該產生指令確認。

---

## 📝 測試場景列表

### md-editor 場景（50 個）

#### 第一部分：基本編輯操作（MD-001 ~ MD-010）

| 場景ID | 用戶輸入 | 預期Agent | 複雜度 | 說明 | 任務標籤 |
| ------ | -------- | --------- | ------ | ---- | -------- |
| MD-001 | 編輯文件 README.md | md-editor | 簡單 | 基本編輯操作 | md-editor, 基本編輯 |
| MD-002 | 修改 docs/guide.md 文件中的第一章節 | md-editor | 中等 | 內容修改 | md-editor, 內容修改 |
| MD-003 | 在 README.md 中添加安裝說明 | md-editor | 中等 | 內容添加 | md-editor, 內容添加 |
| MD-004 | 更新 CHANGELOG.md 文件 | md-editor | 簡單 | 文件更新 | md-editor, 文件更新 |
| MD-005 | 刪除 docs/api.md 中的過時文檔 | md-editor | 中等 | 內容刪除 | md-editor, 內容刪除 |
| MD-006 | 將 README.md 中的 '舊版本' 替換為 '新版本' | md-editor | 中等 | 內容替換 | md-editor, 內容替換 |
| MD-007 | 重寫 docs/guide.md 中的使用說明章節 | md-editor | 中等 | 內容重寫 | md-editor, 內容重寫 |
| MD-008 | 在 README.md 的開頭插入版本信息 | md-editor | 中等 | 內容插入 | md-editor, 內容插入 |
| MD-009 | 格式化整個 README.md 文件 | md-editor | 簡單 | 文件格式化 | md-editor, 文件格式化 |
| MD-010 | 整理 docs/guide.md 的章節結構 | md-editor | 中等 | 結構整理 | md-editor, 結構整理 |

#### 第二部分：內容編輯（MD-011 ~ MD-020）

| 場景ID | 用戶輸入 | 預期Agent | 複雜度 | 說明 | 任務標籤 |
| ------ | -------- | --------- | ------ | ---- | -------- |
| MD-011 | 創建一個新的 Markdown 文件 CONTRIBUTING.md | md-editor | 簡單 | 文件創建 | md-editor, 文件創建 |
| MD-012 | 幫我產生一份 API 文檔 api.md | md-editor | 中等 | 文檔生成 | md-editor, 文檔生成 |
| MD-013 | 在 README.md 中添加功能對照表 | md-editor | 中等 | 表格添加 | md-editor, 表格添加 |
| MD-014 | 更新 docs/links.md 中的所有外部鏈接 | md-editor | 中等 | 鏈接更新 | md-editor, 鏈接更新 |
| MD-015 | 在 README.md 中添加安裝代碼示例 | md-editor | 中等 | 代碼示例添加 | md-editor, 代碼示例 |
| MD-016 | 將 docs/guide.md 的主標題改為 '用戶指南' | md-editor | 簡單 | 標題修改 | md-editor, 標題修改 |
| MD-017 | 在 README.md 中添加項目截圖 | md-editor | 中等 | 圖片添加 | md-editor, 圖片添加 |
| MD-018 | 優化 docs/api.md 的 Markdown 格式 | md-editor | 中等 | 格式優化 | md-editor, 格式優化 |
| MD-019 | 在 README.md 開頭添加目錄 | md-editor | 中等 | 目錄添加 | md-editor, 目錄添加 |
| MD-020 | 重組 docs/guide.md 的內容結構 | md-editor | 複雜 | 結構重組 | md-editor, 結構重組 |

#### 第三部分：格式編輯（MD-021 ~ MD-030）

| 場景ID | 用戶輸入 | 預期Agent | 複雜度 | 說明 | 任務標籤 |
| ------ | -------- | --------- | ------ | ---- | -------- |
| MD-021 | 在 README.md 中添加二級標題 '功能介紹' | md-editor | 簡單 | 標題添加 | md-editor, 標題添加 |
| MD-022 | 將 docs/guide.md 中的無序列表改為有序列表 | md-editor | 中等 | 列表格式轉換 | md-editor, 列表格式 |
| MD-023 | 在 README.md 中添加代碼塊示例 | md-editor | 中等 | 代碼塊添加 | md-editor, 代碼塊 |
| MD-024 | 將 docs/api.md 中的普通文本改為粗體 | md-editor | 簡單 | 文本格式 | md-editor, 文本格式 |
| MD-025 | 在 README.md 中添加引用塊 | md-editor | 簡單 | 引用塊添加 | md-editor, 引用塊 |
| MD-026 | 將 docs/guide.md 中的鏈接更新為新的 URL | md-editor | 中等 | 鏈接更新 | md-editor, 鏈接更新 |
| MD-027 | 在 README.md 中添加表格 | md-editor | 中等 | 表格添加 | md-editor, 表格添加 |
| MD-028 | 將 docs/api.md 中的圖片路徑更新 | md-editor | 中等 | 圖片路徑更新 | md-editor, 圖片路徑 |
| MD-029 | 在 README.md 中添加水平分隔線 | md-editor | 簡單 | 分隔線添加 | md-editor, 分隔線 |
| MD-030 | 將 docs/guide.md 中的行內代碼格式化 | md-editor | 中等 | 行內代碼格式 | md-editor, 行內代碼 |

#### 第四部分：結構編輯（MD-031 ~ MD-040）

| 場景ID | 用戶輸入 | 預期Agent | 複雜度 | 說明 | 任務標籤 |
| ------ | -------- | --------- | ------ | ---- | -------- |
| MD-031 | 在 README.md 中重新組織章節順序 | md-editor | 中等 | 章節重組 | md-editor, 章節重組 |
| MD-032 | 將 docs/guide.md 中的段落合併 | md-editor | 中等 | 段落合併 | md-editor, 段落合併 |
| MD-033 | 在 README.md 中拆分過長的章節 | md-editor | 中等 | 章節拆分 | md-editor, 章節拆分 |
| MD-034 | 將 docs/api.md 中的內容按功能分類 | md-editor | 複雜 | 內容分類 | md-editor, 內容分類 |
| MD-035 | 在 README.md 中添加新的章節 '常見問題' | md-editor | 簡單 | 章節添加 | md-editor, 章節添加 |
| MD-036 | 將 docs/guide.md 中的章節標題統一格式 | md-editor | 中等 | 標題格式統一 | md-editor, 標題格式 |
| MD-037 | 在 README.md 中調整段落間距 | md-editor | 簡單 | 段落間距 | md-editor, 段落間距 |
| MD-038 | 將 docs/api.md 中的嵌套列表展開 | md-editor | 中等 | 列表展開 | md-editor, 列表展開 |
| MD-039 | 在 README.md 中重新編號所有章節 | md-editor | 中等 | 章節編號 | md-editor, 章節編號 |
| MD-040 | 將 docs/guide.md 中的內容重新分組 | md-editor | 複雜 | 內容分組 | md-editor, 內容分組 |

#### 第五部分：批量操作（MD-041 ~ MD-050）

| 場景ID | 用戶輸入 | 預期Agent | 複雜度 | 說明 | 任務標籤 |
| ------ | -------- | --------- | ------ | ---- | -------- |
| MD-041 | 批量替換 README.md 中所有的 '舊名稱' 為 '新名稱' | md-editor | 中等 | 批量替換 | md-editor, 批量替換 |
| MD-042 | 將 docs/ 目錄下所有 .md 文件的標題格式統一 | md-editor | 複雜 | 批量格式統一 | md-editor, 批量格式 |
| MD-043 | 批量更新 README.md 中所有鏈接的域名 | md-editor | 中等 | 批量鏈接更新 | md-editor, 批量鏈接 |
| MD-044 | 將 docs/guide.md 中所有圖片路徑前綴更新 | md-editor | 中等 | 批量圖片路徑 | md-editor, 批量圖片 |
| MD-045 | 在 README.md 中批量添加代碼語言標識 | md-editor | 中等 | 批量代碼標識 | md-editor, 批量代碼 |
| MD-046 | 將 docs/api.md 中所有表格對齊方式統一 | md-editor | 中等 | 批量表格格式 | md-editor, 批量表格 |
| MD-047 | 批量格式化 README.md 中所有代碼塊 | md-editor | 中等 | 批量代碼塊格式 | md-editor, 批量代碼塊 |
| MD-048 | 將 docs/guide.md 中所有引用塊的格式統一 | md-editor | 中等 | 批量引用塊格式 | md-editor, 批量引用塊 |
| MD-049 | 在 README.md 中批量添加章節錨點 | md-editor | 中等 | 批量錨點添加 | md-editor, 批量錨點 |
| MD-050 | 將 docs/ 目錄下所有 Markdown 文件的元數據更新 | md-editor | 複雜 | 批量元數據更新 | md-editor, 批量元數據 |

### xls-editor 場景（10 個）

| 場景ID | 用戶輸入 | 預期Agent | 複雜度 | 說明 | 任務標籤 |
| ------ | -------- | --------- | ------ | ---- | -------- |
| XLS-001 | 編輯 data.xlsx 文件 | xls-editor | 簡單 | 基本編輯操作 | xls-editor, 基本編輯, Excel |
| XLS-002 | 在 data.xlsx 的 Sheet1 中 A1 單元格輸入數據 | xls-editor | 簡單 | 單元格編輯 | xls-editor, 單元格編輯, Excel |
| XLS-003 | 將 data.xlsx 中 A1 單元格設置為粗體和紅色 | xls-editor | 中等 | 格式設置 | xls-editor, 格式設置, Excel |
| XLS-004 | 在 data.xlsx 的 Sheet1 中 B 列前插入一列 | xls-editor | 中等 | 列插入 | xls-editor, 列插入, Excel |
| XLS-005 | 更新 data.xlsx 中 B10 單元格的公式為 =SUM(A1:A9) | xls-editor | 中等 | 公式編輯 | xls-editor, 公式編輯, Excel |
| XLS-006 | 刪除 data.xlsx 中 Sheet1 的第 5 行 | xls-editor | 簡單 | 行刪除 | xls-editor, 行刪除, Excel |
| XLS-007 | 在 data.xlsx 的 Sheet1 中添加一行數據 | xls-editor | 中等 | 行添加 | xls-editor, 行添加, Excel |
| XLS-008 | 在 data.xlsx 的 Sheet1 中填充 A1 到 A10 的序號 | xls-editor | 中等 | 數據填充 | xls-editor, 數據填充, Excel |
| XLS-009 | 在 data.xlsx 中創建一個新的工作表 '統計' | xls-editor | 簡單 | 工作表創建 | xls-editor, 工作表創建, Excel |
| XLS-010 | 將 data.xlsx 中的 Sheet1 重命名為 '數據' | xls-editor | 簡單 | 工作表重命名 | xls-editor, 工作表重命名, Excel |

### md-to-pdf 場景（10 個）

| 場景ID | 用戶輸入 | 預期Agent | 複雜度 | 說明 | 任務標籤 |
| ------ | -------- | --------- | ------ | ---- | -------- |
| MD2PDF-001 | 將 README.md 轉換為 PDF | md-to-pdf | 簡單 | 基本轉換 | md-to-pdf, 轉換, Markdown, PDF |
| MD2PDF-002 | 幫我把 docs/guide.md 轉成 PDF 文件 | md-to-pdf | 簡單 | 轉換操作 | md-to-pdf, 轉換, Markdown, PDF |
| MD2PDF-003 | 生成 README.md 的 PDF 版本 | md-to-pdf | 簡單 | 版本生成 | md-to-pdf, 生成, Markdown, PDF |
| MD2PDF-004 | 將 docs/api.md 導出為 PDF 文件 | md-to-pdf | 簡單 | 導出操作 | md-to-pdf, 導出, Markdown, PDF |
| MD2PDF-005 | 將 CHANGELOG.md 轉換為 PDF 文檔 | md-to-pdf | 簡單 | 文檔轉換 | md-to-pdf, 轉換, Markdown, PDF |
| MD2PDF-006 | 把 README.md 製作成 PDF 文件 | md-to-pdf | 簡單 | 文件製作 | md-to-pdf, 製作, Markdown, PDF |
| MD2PDF-007 | 將 docs/guide.md 轉為 PDF，頁面大小設為 A4 | md-to-pdf | 中等 | 帶參數轉換 | md-to-pdf, 轉換, Markdown, PDF, A4 |
| MD2PDF-008 | 將 README.md 轉為 PDF，並添加頁眉和頁腳 | md-to-pdf | 中等 | 帶頁眉頁腳 | md-to-pdf, 轉換, Markdown, PDF, 頁眉頁腳 |
| MD2PDF-009 | 將 docs/guide.md 轉為 PDF，並自動生成目錄 | md-to-pdf | 中等 | 帶目錄生成 | md-to-pdf, 轉換, Markdown, PDF, 目錄 |
| MD2PDF-010 | 將 README.md 轉為 PDF，使用學術模板 | md-to-pdf | 中等 | 帶模板轉換 | md-to-pdf, 轉換, Markdown, PDF, 模板 |

### xls-to-pdf 場景（10 個）

| 場景ID | 用戶輸入 | 預期Agent | 複雜度 | 說明 | 任務標籤 |
| ------ | -------- | --------- | ------ | ---- | -------- |
| XLS2PDF-001 | 將 data.xlsx 轉換為 PDF | xls-to-pdf | 簡單 | 基本轉換 | xls-to-pdf, 轉換, Excel, PDF |
| XLS2PDF-002 | 幫我把 report.xlsx 轉成 PDF 文件 | xls-to-pdf | 簡單 | 轉換操作 | xls-to-pdf, 轉換, Excel, PDF |
| XLS2PDF-003 | 生成 data.xlsx 的 PDF 版本 | xls-to-pdf | 簡單 | 版本生成 | xls-to-pdf, 生成, Excel, PDF |
| XLS2PDF-004 | 將 report.xlsx 導出為 PDF 文件 | xls-to-pdf | 簡單 | 導出操作 | xls-to-pdf, 導出, Excel, PDF |
| XLS2PDF-005 | 將 data.xlsx 轉換為 PDF 文檔 | xls-to-pdf | 簡單 | 文檔轉換 | xls-to-pdf, 轉換, Excel, PDF |
| XLS2PDF-006 | 把 report.xlsx 製作成 PDF 文件 | xls-to-pdf | 簡單 | 文件製作 | xls-to-pdf, 製作, Excel, PDF |
| XLS2PDF-007 | 將 data.xlsx 轉為 PDF，頁面大小設為 A4 | xls-to-pdf | 中等 | 帶參數轉換 | xls-to-pdf, 轉換, Excel, PDF, A4 |
| XLS2PDF-008 | 將 report.xlsx 轉為 PDF，頁面方向設為橫向 | xls-to-pdf | 中等 | 帶方向設置 | xls-to-pdf, 轉換, Excel, PDF, 橫向 |
| XLS2PDF-009 | 將 data.xlsx 轉為 PDF，縮放設為適合頁面 | xls-to-pdf | 中等 | 帶縮放設置 | xls-to-pdf, 轉換, Excel, PDF, 縮放 |
| XLS2PDF-010 | 將 report.xlsx 轉為 PDF，邊距設為 1cm | xls-to-pdf | 中等 | 帶邊距設置 | xls-to-pdf, 轉換, Excel, PDF, 邊距 |

### pdf-to-md 場景（10 個）

| 場景ID | 用戶輸入 | 預期Agent | 複雜度 | 說明 | 任務標籤 |
| ------ | -------- | --------- | ------ | ---- | -------- |
| PDF2MD-001 | 將 document.pdf 轉換為 Markdown | pdf-to-md | 簡單 | 基本轉換 | pdf-to-md, 轉換, PDF, Markdown |
| PDF2MD-002 | 幫我把 report.pdf 轉成 Markdown 文件 | pdf-to-md | 簡單 | 轉換操作 | pdf-to-md, 轉換, PDF, Markdown |
| PDF2MD-003 | 生成 document.pdf 的 Markdown 版本 | pdf-to-md | 簡單 | 版本生成 | pdf-to-md, 生成, PDF, Markdown |
| PDF2MD-004 | 將 report.pdf 導出為 Markdown 文件 | pdf-to-md | 簡單 | 導出操作 | pdf-to-md, 導出, PDF, Markdown |
| PDF2MD-005 | 將 document.pdf 轉換為 Markdown 文檔 | pdf-to-md | 簡單 | 文檔轉換 | pdf-to-md, 轉換, PDF, Markdown |
| PDF2MD-006 | 把 report.pdf 提取為 Markdown 文件 | pdf-to-md | 簡單 | 內容提取 | pdf-to-md, 提取, PDF, Markdown |
| PDF2MD-007 | 將 document.pdf 轉為 Markdown，並識別表格 | pdf-to-md | 中等 | 帶表格識別 | pdf-to-md, 轉換, PDF, Markdown, 表格識別 |
| PDF2MD-008 | 將 report.pdf 轉為 Markdown，並提取所有圖片 | pdf-to-md | 中等 | 帶圖片提取 | pdf-to-md, 轉換, PDF, Markdown, 圖片提取 |
| PDF2MD-009 | 將 document.pdf 轉為 Markdown，並自動識別標題結構 | pdf-to-md | 中等 | 帶結構識別 | pdf-to-md, 轉換, PDF, Markdown, 結構識別 |
| PDF2MD-010 | 將 report.pdf 轉為 Markdown，並識別列表結構 | pdf-to-md | 中等 | 帶列表識別 | pdf-to-md, 轉換, PDF, Markdown, 列表識別 |

---

## 🔧 測試執行方式

### 測試腳本

**測試腳本位置**：`tests/agents/test_file_editing_agent_routing_v3.py`（待創建）

**測試腳本結構**：

```python
TEST_SCENARIOS = [
    # md-editor 場景（50 個）
    {"scenario_id": "MD-001", "category": "md-editor", "user_input": "編輯文件 README.md", "expected_agent": "md-editor", "expected_task_type": "execution"},
    # ... 更多場景

    # xls-editor 場景（10 個）
    {"scenario_id": "XLS-001", "category": "xls-editor", "user_input": "編輯 data.xlsx 文件", "expected_agent": "xls-editor", "expected_task_type": "execution"},
    # ... 更多場景

    # md-to-pdf 場景（10 個）
    {"scenario_id": "MD2PDF-001", "category": "md-to-pdf", "user_input": "將 README.md 轉換為 PDF", "expected_agent": "md-to-pdf", "expected_task_type": "execution"},
    # ... 更多場景

    # xls-to-pdf 場景（10 個）
    {"scenario_id": "XLS2PDF-001", "category": "xls-to-pdf", "user_input": "將 data.xlsx 轉換為 PDF", "expected_agent": "xls-to-pdf", "expected_task_type": "execution"},
    # ... 更多場景

    # pdf-to-md 場景（10 個）
    {"scenario_id": "PDF2MD-001", "category": "pdf-to-md", "user_input": "將 document.pdf 轉換為 Markdown", "expected_agent": "pdf-to-md", "expected_task_type": "execution"},
    # ... 更多場景
]
```

### 執行命令

```bash
# 執行所有測試場景
cd /Users/daniel/GitHub/AI-Box
python3 -m pytest tests/agents/test_file_editing_agent_routing_v3.py::TestFileEditingAgentRoutingV3::test_agent_routing -v

# 執行特定類別的測試（例如：md-editor）
python3 -m pytest tests/agents/test_file_editing_agent_routing_v3.py -v -k "md-editor"

# 執行特定場景（例如：MD-001）
python3 -m pytest tests/agents/test_file_editing_agent_routing_v3.py::TestFileEditingAgentRoutingV3::test_agent_routing -v -k "scenario0"
```

---

## ✅ 測試前檢查清單

在執行測試前，必須確認以下事項：

### 1. System Agent 註冊狀態 ✅

- [ ] 確認所有 System Agents 已註冊到 System Agent Registry Store
- [ ] 確認 `md-editor` 已註冊且 `is_active=True`, `status="online"`
- [ ] 確認 `xls-editor` 已註冊且 `is_active=True`, `status="online"`
- [ ] 確認 `md-to-pdf` 已註冊且 `is_active=True`, `status="online"`
- [ ] 確認 `xls-to-pdf` 已註冊且 `is_active=True`, `status="online"`
- [ ] 確認 `pdf-to-md` 已註冊且 `is_active=True`, `status="online"`
- [ ] **確認 `document-editing-agent` 已標記為 `is_active=False`, `status="offline"`**

### 2. 代碼修復狀態 ✅

- [ ] 確認 `AgentRegistry.list_agents` 方法已修復（正確從 System Agent Registry Store 加載）
- [ ] 確認 `CapabilityMatcher` 查詢邏輯正確（同時查詢 `document_editing` 和 `document_conversion`）
- [ ] 確認 `DecisionEngine` 文件擴展名匹配邏輯正確
- [ ] 確認 `TaskAnalyzer` 覆蓋邏輯正確（優先信任 RouterLLM 的 `intent_type`）

### 3. 測試環境 ✅

- [ ] 確認測試腳本已創建（`test_file_editing_agent_routing_v3.py`）
- [ ] 確認測試場景已定義（90 個場景）
- [ ] 確認測試環境配置正確（ArangoDB 連接、LLM 配置等）

---

## 📊 預期測試結果

### 成功標準

- ✅ **md-editor 場景**：Agent 調用成功率 ≥ 95%（47/50）
- ✅ **xls-editor 場景**：Agent 調用成功率 ≥ 90%（9/10）
- ✅ **md-to-pdf 場景**：Agent 調用成功率 ≥ 90%（9/10）
- ✅ **xls-to-pdf 場景**：Agent 調用成功率 ≥ 90%（9/10）
- ✅ **pdf-to-md 場景**：Agent 調用成功率 ≥ 90%（9/10）
- ✅ **所有場景**：Agent 匹配率 ≥ 85%（77/90）
- ✅ **所有場景**：任務類型識別準確率 = 100%（90/90）
- ✅ **所有場景**：不調用 `document-editing-agent`（0 次）

### 失敗處理

如果測試失敗，請：

1. 檢查 System Agent 註冊狀態
2. 檢查 `document-editing-agent` 是否被錯誤調用
3. 查看測試日誌，確認 Agent 選擇邏輯
4. 參考 `文件編輯Agent語義路由測試劇本-v2.md` 中的問題分析

---

## 📚 相關文檔

- **測試劇本（舊版）**：`文件編輯Agent語義路由測試劇本-v2.md`（包含 Round 1-7 的測試結果和分析）
- **Agent 註冊確認報告**：`Agent註冊確認報告.md`
- **Agent 調用為空列表分析報告**：`Agent调用为空列表分析报告.md`
- **文件編輯意圖識別問題分析報告**：`文件編輯意圖識別問題分析報告.md`
- **測試成功率分析與改進建議**：`測試成功率分析與改進建議.md`

---

## 📊 測試執行記錄表

### 測試執行摘要

| 測試輪次 | 執行日期 | 執行人 | 測試環境 | 系統版本 | 總場景數 | 通過 | 失敗 | 未執行 | 通過率 | 備註 |
| -------- | -------- | ------ | -------- | -------- | -------- | ---- | ---- | ------ | ------ | ---- |
| - | - | - | - | - | 90 | - | - | 90 | - | 測試計劃（未執行） |
| 第 1 輪 | 2026-01-11 22:00 | Daniel Chung | 本地開發環境 | v3.2 | 20 | 20 | 0 | 0 | 100.00% | md-editor 場景測試完成（MD-001 ~ MD-020） |
| 第 2 輪 | 2026-01-11 22:15 | Daniel Chung | 本地開發環境 | v3.2 | 10 | 10 | 0 | 0 | 100.00% | xls-editor 場景測試完成（XLS-001 ~ XLS-010） |
| 第 3 輪 | 2026-01-11 22:45 | Daniel Chung | 本地開發環境 | v3.2 | 10 | 10 | 0 | 0 | 100.00% | md-to-pdf 場景測試完成（MD2PDF-001 ~ MD2PDF-010） |
| 第 5 輪 | 2026-01-11 23:20 | Daniel Chung | 本地開發環境 | v3.2 | 10 | 10 | 0 | 0 | 100.00% | xls-to-pdf 場景測試完成（XLS2PDF-001 ~ XLS2PDF-010） |
| 第 6 輪 | 2026-01-11 23:30 | Daniel Chung | 本地開發環境 | v3.2 | 10 | 10 | 0 | 0 | 100.00% | pdf-to-md 場景測試完成（PDF2MD-001 ~ PDF2MD-010） |
| 第 7 輪 | 2026-01-12 10:08 | Daniel Chung | 本地開發環境 | v3.2 | 50 | 50 | 0 | 0 | 100.00% | md-editor 完整場景測試完成（MD-001 ~ MD-050），所有場景通過 |

### 各類場景測試記錄

#### md-editor 場景（50 個）

| 測試輪次 | 執行日期 | 總場景數 | 通過 | 失敗 | 通過率 | Agent調用成功率 | Agent匹配率 | 任務類型正確率 | 備註 |
| -------- | -------- | -------- | ---- | ---- | ------ | -------------- | ----------- | -------------- | ---- |
| - | - | 50 | - | - | - | - | - | - | 測試計劃（未執行） |
| 第 1 輪 | 2026-01-11 22:00 | 20 | 20 | 0 | 100.00% | 100% (20/20) | 100% (20/20) | 100% (20/20) | 測試完成（MD-001 ~ MD-020），所有場景通過 |
| 第 2 輪 | 2026-01-12 10:08 | 50 | 50 | 0 | 100.00% | 100% (50/50) | 100% (50/50) | 100% (50/50) | 測試完成（MD-001 ~ MD-050），完整 50 個場景全部通過，包含所有任務標籤 |

#### xls-editor 場景（10 個）

| 測試輪次 | 執行日期 | 總場景數 | 通過 | 失敗 | 通過率 | Agent調用成功率 | Agent匹配率 | 任務類型正確率 | 備註 |
| -------- | -------- | -------- | ---- | ---- | ------ | -------------- | ----------- | -------------- | ---- |
| - | - | 10 | - | - | - | - | - | - | 測試計劃（未執行） |
| 第 1 輪 | 2026-01-11 22:15 | 10 | 10 | 0 | 100.00% | 100% (10/10) | 100% (10/10) | 100% (10/10) | 測試完成（XLS-001 ~ XLS-010），所有場景通過，所有場景都包含明確的 Excel 關鍵字 |

#### md-to-pdf 場景（10 個）

| 測試輪次 | 執行日期 | 總場景數 | 通過 | 失敗 | 通過率 | Agent調用成功率 | Agent匹配率 | 任務類型正確率 | 備註 |
| -------- | -------- | -------- | ---- | ---- | ------ | -------------- | ----------- | -------------- | ---- |
| - | - | 10 | - | - | - | - | - | - | 測試計劃（未執行） |
| 第 1 輪 | 2026-01-11 22:45 | 10 | 10 | 0 | 100.00% | 100% (10/10) | 100% (10/10) | 100% (10/10) | 測試完成（MD2PDF-001 ~ MD2PDF-010），所有場景通過，所有場景都包含明確的轉換關鍵詞語義和 PDF 關鍵字 |
| 第 2 輪 | 2026-01-11 23:10 | 10 | 10 | 0 | 100.00% | 100% (10/10) | 100% (10/10) | 100% (10/10) | 測試完成（MD2PDF-011 ~ MD2PDF-020），所有場景通過，所有場景都包含明確的轉換關鍵詞語義和 PDF 關鍵字 |
| **合計** | **2026-01-11** | **20** | **20** | **0** | **100.00%** | **100% (20/20)** | **100% (20/20)** | **100% (20/20)** | **全部 20 個 md-to-pdf 場景測試完成，通過率 100%** |

#### xls-to-pdf 場景（10 個）

| 測試輪次 | 執行日期 | 總場景數 | 通過 | 失敗 | 通過率 | Agent調用成功率 | Agent匹配率 | 任務類型正確率 | 備註 |
| -------- | -------- | -------- | ---- | ---- | ------ | -------------- | ----------- | -------------- | ---- |
| - | - | 10 | - | - | - | - | - | - | 測試計劃（未執行） |
| 第 1 輪 | 2026-01-11 23:20 | 10 | 10 | 0 | 100.00% | 100% (10/10) | 100% (10/10) | 100% (10/10) | 測試完成（XLS2PDF-001 ~ XLS2PDF-010），所有場景通過，所有場景都包含明確的轉換關鍵詞語義、Excel 關鍵字和 PDF 關鍵字 |

#### pdf-to-md 場景（10 個）

| 測試輪次 | 執行日期 | 總場景數 | 通過 | 失敗 | 通過率 | Agent調用成功率 | Agent匹配率 | 任務類型正確率 | 備註 |
| -------- | -------- | -------- | ---- | ---- | ------ | -------------- | ----------- | -------------- | ---- |
| - | - | 10 | - | - | - | - | - | - | 測試計劃（未執行） |
| 第 1 輪 | 2026-01-11 23:30 | 10 | 10 | 0 | 100.00% | 100% (10/10) | 100% (10/10) | 100% (10/10) | 測試完成（PDF2MD-001 ~ PDF2MD-010），所有場景通過，所有場景都包含明確的轉換關鍵詞語義、PDF 關鍵字和 Markdown 關鍵字 |

### 關鍵指標追蹤

| 指標 | 目標值 | 第1輪 | 第2輪 | 第3輪 | 第4輪 | 第5輪 | 備註 |
| ---- | ------ | ----- | ----- | ----- | ----- | ----- | ---- |
| **總通過率** | ≥ 85% | - | - | - | - | - | 77/90 場景通過 |
| **md-editor Agent調用成功率** | ≥ 95% | 100% (50/50) | - | - | - | - | 50/50 場景調用Agent ✅（第2輪完整測試） |
| **md-editor Agent匹配率** | ≥ 90% | 100% (50/50) | - | - | - | - | 50/50 場景匹配正確Agent ✅（第2輪完整測試） |
| **xls-editor Agent調用成功率** | ≥ 90% | 100% (10/10) | - | - | - | - | 10/10 場景調用Agent ✅ |
| **xls-editor Agent匹配率** | ≥ 80% | 100% (10/10) | - | - | - | - | 10/10 場景匹配正確Agent ✅ |
| **md-to-pdf Agent調用成功率** | ≥ 90% | 100% (20/20) | - | - | - | - | 20/20 場景調用Agent ✅ |
| **md-to-pdf Agent匹配率** | ≥ 80% | 100% (20/20) | - | - | - | - | 20/20 場景匹配正確Agent ✅ |
| **xls-to-pdf Agent調用成功率** | ≥ 90% | 100% (10/10) | - | - | - | - | 10/10 場景調用Agent ✅ |
| **xls-to-pdf Agent匹配率** | ≥ 80% | 100% (10/10) | - | - | - | - | 10/10 場景匹配正確Agent ✅ |
| **pdf-to-md Agent調用成功率** | ≥ 90% | 100% (10/10) | - | - | - | - | 10/10 場景調用Agent ✅ |
| **pdf-to-md Agent匹配率** | ≥ 80% | 100% (10/10) | - | - | - | - | 10/10 場景匹配正確Agent ✅ |
| **任務類型識別準確率** | 100% | 100% (120/120) | - | - | - | - | 120/120 場景正確識別 ✅（包含第7輪50個場景） |
| **不調用 document-editing-agent** | 0次 | 0次 ✅ | - | - | - | - | 確保不使用已停用的Agent ✅ |

### 問題追蹤表

| 問題ID | 問題描述 | 發現輪次 | 狀態 | 優先級 | 負責人 | 解決日期 | 備註 |
| ------ | -------- | -------- | ---- | ------ | ------ | -------- | ---- |
| - | - | - | - | - | - | - | 測試計劃（無問題記錄） |
| MD-001 | md-editor 場景測試完成 | 第1輪 | ✅ 已解決 | - | Daniel Chung | 2026-01-11 | 所有20個場景測試通過，Agent調用成功率100% |
| XLS-001 | xls-editor 場景測試完成 | 第2輪 | ✅ 已解決 | - | Daniel Chung | 2026-01-11 | 所有10個場景測試通過，Agent調用成功率100%，所有場景都包含明確的 Excel 關鍵字 |
| MD2PDF-001 | md-to-pdf 場景測試完成（第一部分） | 第3輪 | ✅ 已解決 | - | Daniel Chung | 2026-01-11 | 前10個場景測試通過（MD2PDF-001 ~ MD2PDF-010），Agent調用成功率100%，所有場景都包含明確的轉換關鍵詞語義和 PDF 關鍵字 |
| MD2PDF-002 | md-to-pdf 場景測試完成（第二部分） | 第4輪 | ✅ 已解決 | - | Daniel Chung | 2026-01-11 | 後10個場景測試通過（MD2PDF-011 ~ MD2PDF-020），Agent調用成功率100%，所有場景都包含明確的轉換關鍵詞語義和 PDF 關鍵字 |
| MD2PDF-003 | md-to-pdf 場景測試完成（全部） | 第3-4輪 | ✅ 已解決 | - | Daniel Chung | 2026-01-11 | 全部20個場景測試通過，通過率100%，Agent調用成功率100%，Agent匹配率100%，所有場景都包含明確的轉換關鍵詞語義和 PDF 關鍵字 |
| XLS2PDF-001 | xls-to-pdf 場景測試完成 | 第5輪 | ✅ 已解決 | - | Daniel Chung | 2026-01-11 | 所有10個場景測試通過，Agent調用成功率100%，所有場景都包含明確的轉換關鍵詞語義、Excel 關鍵字和 PDF 關鍵字 |
| PDF2MD-001 | pdf-to-md 場景測試完成 | 第6輪 | ✅ 已解決 | - | Daniel Chung | 2026-01-11 | 所有10個場景測試通過，Agent調用成功率100%，所有場景都包含明確的轉換關鍵詞語義、PDF 關鍵字和 Markdown 關鍵字 |
| MD-002 | md-editor 完整場景測試（50個） | 第7輪 | ✅ 已解決 | - | Daniel Chung | 2026-01-12 | 完整50個場景測試完成（MD-001 ~ MD-050），所有場景通過，通過率100%，Agent調用成功率100%，Agent匹配率100%，包含所有任務標籤 |

---

## 📊 第 1 輪測試執行總結（md-editor 場景）

### 測試執行信息

- **執行日期**: 2026-01-11 22:00
- **執行人**: Daniel Chung
- **測試環境**: 本地開發環境
- **系統版本**: v3.2
- **測試場景**: md-editor（MD-001 ~ MD-020，共 20 個場景）

### 測試結果

#### 總體結果

| 指標 | 目標值 | 實際值 | 狀態 |
| ---- | ------ | ------ | ---- |
| **總通過率** | ≥ 95% | **100%** (20/20) | ✅ 達標 |
| **Agent 調用成功率** | ≥ 95% | **100%** (20/20) | ✅ 達標 |
| **Agent 匹配率** | ≥ 90% | **100%** (20/20) | ✅ 達標 |
| **任務類型識別準確率** | 100% | **100%** (20/20) | ✅ 達標 |
| **不調用 document-editing-agent** | 0次 | **0次** | ✅ 達標 |

#### 詳細結果

**所有 20 個 md-editor 場景測試均通過**：

1. ✅ MD-001: 編輯文件 README.md
2. ✅ MD-002: 修改 docs/guide.md 文件中的第一章節
3. ✅ MD-003: 在 README.md 中添加安裝說明
4. ✅ MD-004: 更新 CHANGELOG.md 文件
5. ✅ MD-005: 刪除 docs/api.md 中的過時文檔
6. ✅ MD-006: 將 README.md 中的 '舊版本' 替換為 '新版本'
7. ✅ MD-007: 重寫 docs/guide.md 中的使用說明章節
8. ✅ MD-008: 在 README.md 的開頭插入版本信息
9. ✅ MD-009: 格式化整個 README.md 文件
10. ✅ MD-010: 整理 docs/guide.md 的章節結構
11. ✅ MD-011: 創建一個新的 Markdown 文件 CONTRIBUTING.md
12. ✅ MD-012: 幫我產生一份 API 文檔 api.md
13. ✅ MD-013: 在 README.md 中添加功能對照表
14. ✅ MD-014: 更新 docs/links.md 中的所有外部鏈接
15. ✅ MD-015: 在 README.md 中添加安裝代碼示例
16. ✅ MD-016: 將 docs/guide.md 的主標題改為 '用戶指南'
17. ✅ MD-017: 在 README.md 中添加項目截圖
18. ✅ MD-018: 優化 docs/api.md 的 Markdown 格式
19. ✅ MD-019: 在 README.md 開頭添加目錄
20. ✅ MD-020: 重組 docs/guide.md 的內容結構

### 測試結論

1. **✅ Agent 路由準確性**: 所有 20 個 md-editor 場景都能正確識別意圖並調用 `md-editor` Agent，Agent 匹配率達到 100%。

2. **✅ 任務類型識別**: 所有場景都能正確識別任務類型為 `execution`，識別準確率達到 100%。

3. **✅ 系統穩定性**: 所有測試場景均成功執行，無錯誤發生，系統運行穩定。

4. **✅ Agent 選擇邏輯**: 系統能夠正確選擇 `md-editor` Agent，未調用已停用的 `document-editing-agent`。

### 改進建議

1. **繼續測試其他場景**: 建議繼續執行 xls-editor、md-to-pdf、xls-to-pdf、pdf-to-md 場景的測試，以全面驗證系統的語義路由能力。

2. **擴展測試場景**: 測試計劃中定義了 50 個 md-editor 場景，目前只測試了前 20 個。建議補充剩餘 30 個場景的測試。

3. **性能優化**: 測試執行時間約 3 分鐘（20 個場景），平均每個場景約 9 秒。可以考慮優化 LLM 調用性能。

### 下一步行動

- [ ] 執行剩餘 30 個 md-editor 場景測試（MD-021 ~ MD-050）
- [x] 執行 xls-editor 場景測試（10 個場景）✅ 已完成
- [x] 執行 md-to-pdf 場景測試（10 個場景）✅ 已完成
- [x] 執行 xls-to-pdf 場景測試（10 個場景）✅ 已完成
- [x] 執行 pdf-to-md 場景測試（10 個場景）✅ 已完成

---

## 📊 第 2 輪測試執行總結（xls-editor 場景）

### 測試執行信息

- **執行日期**: 2026-01-11 22:15
- **執行人**: Daniel Chung
- **測試環境**: 本地開發環境
- **系統版本**: v3.2
- **測試場景**: xls-editor（XLS-001 ~ XLS-010，共 10 個場景）

### 測試結果

#### 總體結果

| 指標 | 目標值 | 實際值 | 狀態 |
| ---- | ------ | ------ | ---- |
| **總通過率** | ≥ 90% | **100%** (10/10) | ✅ 達標 |
| **Agent 調用成功率** | ≥ 90% | **100%** (10/10) | ✅ 達標 |
| **Agent 匹配率** | ≥ 80% | **100%** (10/10) | ✅ 達標 |
| **任務類型識別準確率** | 100% | **100%** (10/10) | ✅ 達標 |
| **不調用 document-editing-agent** | 0次 | **0次** | ✅ 達標 |
| **不調用 md-editor** | 0次 | **0次** | ✅ 達標 |
| **包含 Excel 關鍵字** | 100% | **100%** (10/10) | ✅ 達標 |

#### 詳細結果

**所有 10 個 xls-editor 場景測試均通過**，所有場景都包含明確的 Excel 關鍵字（.xlsx）：

1. ✅ XLS-001: 編輯文件 data.xlsx
2. ✅ XLS-002: 在 data.xlsx 的 Sheet1 中 A1 單元格輸入數據
3. ✅ XLS-003: 將 data.xlsx 中 A1 單元格設置為粗體和紅色
4. ✅ XLS-004: 在 data.xlsx 的 Sheet1 中 B 列前插入一列
5. ✅ XLS-005: 更新 data.xlsx 中 B10 單元格的公式為 =SUM(A1:A9)
6. ✅ XLS-006: 刪除 data.xlsx 中 Sheet1 的第 5 行
7. ✅ XLS-007: 在 data.xlsx 的 Sheet1 中添加一行數據
8. ✅ XLS-008: 在 data.xlsx 的 Sheet1 中填充 A1 到 A10 的序號
9. ✅ XLS-009: 在 data.xlsx 中創建一個新的工作表 '統計'
10. ✅ XLS-010: 將 data.xlsx 中的 Sheet1 重命名為 '數據'

### 測試結論

1. **✅ Agent 路由準確性**: 所有 10 個 xls-editor 場景都能正確識別意圖並調用 `xls-editor` Agent，Agent 匹配率達到 100%。

2. **✅ Excel 關鍵字識別**: 所有場景都包含明確的 Excel 關鍵字（.xlsx），系統能夠正確識別 Excel 文件編輯意圖。

3. **✅ 任務類型識別**: 所有場景都能正確識別任務類型為 `execution`，識別準確率達到 100%。

4. **✅ 系統穩定性**: 所有測試場景均成功執行，無錯誤發生，系統運行穩定。

5. **✅ Agent 選擇邏輯**: 系統能夠正確選擇 `xls-editor` Agent，未調用已停用的 `document-editing-agent`，也未錯誤調用 `md-editor`。

6. **✅ 文件擴展名匹配**: 系統能夠根據文件擴展名（.xlsx）正確識別並調用相應的 Agent。

### 關鍵發現

1. **Excel 關鍵字的重要性**: 所有測試場景都包含明確的 Excel 關鍵字（.xlsx），這確保了系統能夠準確識別 Excel 文件編輯意圖。

2. **Agent 選擇精確性**: 系統能夠正確區分 Excel 文件編輯和 Markdown 文件編輯，不會錯誤調用 `md-editor`。

3. **測試執行效率**: 測試執行時間約 1 分 44 秒（10 個場景），平均每個場景約 10.4 秒，與 md-editor 場景相當。

### 改進建議

1. **繼續測試其他場景**: 建議繼續執行 md-to-pdf、xls-to-pdf、pdf-to-md 場景的測試，以全面驗證系統的語義路由能力。

2. **擴展測試場景**: 可以考慮添加更多 xls-editor 場景，包括：
   - 使用 `.xls` 擴展名的場景
   - 包含 "Excel" 關鍵字的場景
   - 包含 "spreadsheet" 關鍵字的場景
   - 包含中文關鍵字（如 "工作表"、"單元格"）的場景

3. **性能優化**: 測試執行時間約 1 分 44 秒（10 個場景），平均每個場景約 10.4 秒。可以考慮優化 LLM 調用性能。

### 下一步行動

- [ ] 執行 md-to-pdf 場景測試（10 個場景）
- [ ] 執行 xls-to-pdf 場景測試（10 個場景）
- [ ] 執行 pdf-to-md 場景測試（10 個場景）
- [ ] 執行剩餘 30 個 md-editor 場景測試（MD-021 ~ MD-050）

---

## 📊 第 3 輪測試執行總結（md-to-pdf 場景）

### 測試執行信息

- **執行日期**: 2026-01-11 22:45
- **執行人**: Daniel Chung
- **測試環境**: 本地開發環境
- **系統版本**: v3.2
- **測試場景**: md-to-pdf（MD2PDF-001 ~ MD2PDF-010，共 10 個場景）

### 測試結果

#### 總體結果

| 指標 | 目標值 | 實際值 | 狀態 |
| ---- | ------ | ------ | ---- |
| **總通過率** | ≥ 90% | **100%** (10/10) | ✅ 達標 |
| **Agent 調用成功率** | ≥ 90% | **100%** (10/10) | ✅ 達標 |
| **Agent 匹配率** | ≥ 80% | **100%** (10/10) | ✅ 達標 |
| **任務類型識別準確率** | 100% | **100%** (10/10) | ✅ 達標 |
| **不調用 document-editing-agent** | 0次 | **0次** | ✅ 達標 |
| **不調用 md-editor** | 0次 | **0次** | ✅ 達標 |
| **包含轉換關鍵詞語義** | 100% | **100%** (10/10) | ✅ 達標 |
| **包含 PDF 關鍵字** | 100% | **100%** (10/10) | ✅ 達標 |

#### 詳細結果

**所有 10 個 md-to-pdf 場景測試均通過**，所有場景都包含明確的轉換關鍵詞語義（轉換、轉為、轉成、生成、導出、製作等）和 PDF 關鍵字：

1. ✅ MD2PDF-001: 將 README.md 轉換為 PDF（轉換關鍵詞：轉換為）
2. ✅ MD2PDF-002: 幫我把 docs/guide.md 轉成 PDF 文件（轉換關鍵詞：轉成）
3. ✅ MD2PDF-003: 生成 README.md 的 PDF 版本（轉換關鍵詞：生成）
4. ✅ MD2PDF-004: 將 docs/api.md 導出為 PDF 文件（轉換關鍵詞：導出為）
5. ✅ MD2PDF-005: 將 CHANGELOG.md 轉換為 PDF 文檔（轉換關鍵詞：轉換為）
6. ✅ MD2PDF-006: 把 README.md 製作成 PDF 文件（轉換關鍵詞：製作成）
7. ✅ MD2PDF-007: 將 docs/guide.md 轉為 PDF，頁面大小設為 A4（轉換關鍵詞：轉為）
8. ✅ MD2PDF-008: 將 README.md 轉為 PDF，並添加頁眉和頁腳（轉換關鍵詞：轉為）
9. ✅ MD2PDF-009: 將 docs/guide.md 轉為 PDF，並自動生成目錄（轉換關鍵詞：轉為）
10. ✅ MD2PDF-010: 將 README.md 轉為 PDF，使用學術模板（轉換關鍵詞：轉為）

### 測試結論

1. **✅ Agent 路由準確性**: 所有 10 個 md-to-pdf 場景都能正確識別意圖並調用 `md-to-pdf` Agent，Agent 匹配率達到 100%。

2. **✅ 轉換關鍵詞語義識別**: 所有場景都包含明確的轉換關鍵詞語義（轉換、轉為、轉成、生成、導出、製作等），系統能夠正確識別文件轉換意圖。

3. **✅ PDF 關鍵字識別**: 所有場景都包含明確的 PDF 關鍵字，系統能夠正確識別目標文件類型為 PDF。

4. **✅ 任務類型識別**: 所有場景都能正確識別任務類型為 `execution`，識別準確率達到 100%。

5. **✅ 系統穩定性**: 所有測試場景均成功執行，無錯誤發生，系統運行穩定。

6. **✅ Agent 選擇邏輯**: 系統能夠正確選擇 `md-to-pdf` Agent，未調用已停用的 `document-editing-agent`，也未錯誤調用 `md-editor`（能正確區分轉換任務和編輯任務）。

### 關鍵發現

1. **轉換關鍵詞語義的重要性**: 所有測試場景都包含明確的轉換關鍵詞語義（轉換、轉為、轉成、生成、導出、製作等），這確保了系統能夠準確識別文件轉換意圖。

2. **PDF 關鍵字的重要性**: 所有測試場景都包含明確的 PDF 關鍵字，這確保了系統能夠準確識別目標文件類型為 PDF。

3. **Agent 選擇精確性**: 系統能夠正確區分文件轉換任務和文件編輯任務，不會錯誤調用 `md-editor`。

4. **測試執行效率**: 測試執行時間約 1 分 22 秒（10 個場景），平均每個場景約 8.2 秒，執行效率良好。

### 轉換關鍵詞語義統計

| 轉換關鍵詞 | 使用次數 | 場景ID |
| --------- | ------- | ------ |
| 轉換為 | 2 | MD2PDF-001, MD2PDF-005 |
| 轉為 | 4 | MD2PDF-007, MD2PDF-008, MD2PDF-009, MD2PDF-010 |
| 轉成 | 1 | MD2PDF-002 |
| 生成 | 1 | MD2PDF-003 |
| 導出為 | 1 | MD2PDF-004 |
| 製作成 | 1 | MD2PDF-006 |

### 改進建議

1. **繼續測試其他場景**: 建議繼續執行 xls-to-pdf、pdf-to-md 場景的測試，以全面驗證系統的語義路由能力。

2. **擴展測試場景**: 可以考慮添加更多 md-to-pdf 場景，包括：
   - 使用英文轉換關鍵詞的場景（如 "convert", "transform", "export"）
   - 使用其他轉換關鍵詞的場景（如 "變成", "換成"）
   - 包含更多 PDF 相關關鍵字的場景（如 ".pdf" 擴展名）

3. **性能優化**: 測試執行時間約 1 分 22 秒（10 個場景），平均每個場景約 8.2 秒。可以考慮優化 LLM 調用性能。

### 下一步行動

- [ ] 執行 xls-to-pdf 場景測試（10 個場景）
- [ ] 執行 pdf-to-md 場景測試（10 個場景）
- [ ] 執行剩餘 30 個 md-editor 場景測試（MD-021 ~ MD-050）

---

## 📊 第 4 輪測試執行總結（md-to-pdf 場景 - 第二部分）

### 測試執行信息

- **執行日期**: 2026-01-11 23:10
- **執行人**: Daniel Chung
- **測試環境**: 本地開發環境
- **系統版本**: v3.2
- **測試場景**: md-to-pdf（MD2PDF-011 ~ MD2PDF-020，共 10 個場景）

### 測試結果

#### 總體結果

| 指標 | 目標值 | 實際值 | 狀態 |
| ---- | ------ | ------ | ---- |
| **總通過率** | ≥ 90% | **100%** (10/10) | ✅ 達標 |
| **Agent 調用成功率** | ≥ 90% | **100%** (10/10) | ✅ 達標 |
| **Agent 匹配率** | ≥ 80% | **100%** (10/10) | ✅ 達標 |
| **任務類型識別準確率** | 100% | **100%** (10/10) | ✅ 達標 |
| **不調用 document-editing-agent** | 0次 | **0次** | ✅ 達標 |
| **不調用 md-editor** | 0次 | **0次** | ✅ 達標 |
| **包含轉換關鍵詞語義** | 100% | **100%** (10/10) | ✅ 達標 |
| **包含 PDF 關鍵字** | 100% | **100%** (10/10) | ✅ 達標 |

#### 詳細結果

**所有 10 個 md-to-pdf 場景測試均通過**（第二部分，MD2PDF-011 ~ MD2PDF-020），所有場景都包含明確的轉換關鍵詞語義（轉為）和 PDF 關鍵字：

11. ✅ MD2PDF-011: 將 docs/ 目錄下的所有 Markdown 文件合併轉為一個 PDF（複雜度：複雜）
12. ✅ MD2PDF-012: 將 README.md 轉為 PDF，字體設為 Times New Roman（複雜度：中等）
13. ✅ MD2PDF-013: 將 docs/guide.md 轉為 PDF，邊距設為 2cm（複雜度：中等）
14. ✅ MD2PDF-014: 將 README.md 轉為 PDF，並啟用代碼高亮（複雜度：中等）
15. ✅ MD2PDF-015: 將 docs/guide.md 轉為 PDF，並渲染 Mermaid 圖表（複雜度：中等）
16. ✅ MD2PDF-016: 將 README.md 轉為 PDF，並添加頁碼（複雜度：簡單）
17. ✅ MD2PDF-017: 將 docs/guide.md 轉為 PDF，並添加封面頁（複雜度：中等）
18. ✅ MD2PDF-018: 將 README.md 轉為 PDF，並添加水印 '草稿'（複雜度：複雜）
19. ✅ MD2PDF-019: 將 docs/guide.md 轉為 PDF，使用雙欄布局（複雜度：複雜）
20. ✅ MD2PDF-020: 將 README.md 轉為 PDF，頁面方向設為橫向（複雜度：中等）

### md-to-pdf 場景完整測試總結

**總計測試場景**: 20 個（MD2PDF-001 ~ MD2PDF-020）

#### 總體統計

| 指標 | 目標值 | 實際值 | 狀態 |
| ---- | ------ | ------ | ---- |
| **總通過率** | ≥ 90% | **100%** (20/20) | ✅ 達標 |
| **Agent 調用成功率** | ≥ 90% | **100%** (20/20) | ✅ 達標 |
| **Agent 匹配率** | ≥ 80% | **100%** (20/20) | ✅ 達標 |
| **任務類型識別準確率** | 100% | **100%** (20/20) | ✅ 達標 |
| **不調用 document-editing-agent** | 0次 | **0次** | ✅ 達標 |
| **不調用 md-editor** | 0次 | **0次** | ✅ 達標 |
| **包含轉換關鍵詞語義** | 100% | **100%** (20/20) | ✅ 達標 |
| **包含 PDF 關鍵字** | 100% | **100%** (20/20) | ✅ 達標 |

#### 複雜度統計

| 複雜度 | 場景數量 | 通過率 | 場景ID |
| ------ | -------- | ------ | ------ |
| 簡單 | 6 | 100% (6/6) | MD2PDF-001, MD2PDF-003, MD2PDF-004, MD2PDF-005, MD2PDF-006, MD2PDF-016 |
| 中等 | 11 | 100% (11/11) | MD2PDF-002, MD2PDF-007, MD2PDF-008, MD2PDF-009, MD2PDF-010, MD2PDF-012, MD2PDF-013, MD2PDF-014, MD2PDF-015, MD2PDF-017, MD2PDF-020 |
| 複雜 | 3 | 100% (3/3) | MD2PDF-011, MD2PDF-018, MD2PDF-019 |

#### 轉換關鍵詞語義統計（完整 20 個場景）

| 轉換關鍵詞 | 使用次數 | 場景ID |
| --------- | ------- | ------ |
| 轉為 | 16 | MD2PDF-007~020（使用最頻繁） |
| 轉換為 | 2 | MD2PDF-001, MD2PDF-005 |
| 轉成 | 1 | MD2PDF-002 |
| 生成 | 1 | MD2PDF-003 |
| 導出為 | 1 | MD2PDF-004 |
| 製作成 | 1 | MD2PDF-006 |

### 測試結論

1. **✅ Agent 路由準確性**: 所有 20 個 md-to-pdf 場景都能正確識別意圖並調用 `md-to-pdf` Agent，Agent 匹配率達到 100%。

2. **✅ 轉換關鍵詞語義識別**: 所有場景都包含明確的轉換關鍵詞語義（轉換、轉為、轉成、生成、導出、製作等），系統能夠正確識別文件轉換意圖。

3. **✅ PDF 關鍵字識別**: 所有場景都包含明確的 PDF 關鍵字，系統能夠正確識別目標文件類型為 PDF。

4. **✅ 任務類型識別**: 所有場景都能正確識別任務類型為 `execution`，識別準確率達到 100%。

5. **✅ 系統穩定性**: 所有測試場景均成功執行，無錯誤發生，系統運行穩定。

6. **✅ Agent 選擇邏輯**: 系統能夠正確選擇 `md-to-pdf` Agent，未調用已停用的 `document-editing-agent`，也未錯誤調用 `md-editor`（能正確區分轉換任務和編輯任務）。

7. **✅ 複雜度處理**: 系統能夠正確處理不同複雜度的場景，包括簡單、中等和複雜場景。

### 測試執行效率

- **第一部分**（MD2PDF-001 ~ MD2PDF-010）：約 1 分 22 秒，平均每個場景約 8.2 秒
- **第二部分**（MD2PDF-011 ~ MD2PDF-020）：約 1 分 24 秒，平均每個場景約 8.4 秒
- **總計**：約 2 分 46 秒（20 個場景），平均每個場景約 8.3 秒

### 下一步行動

- [x] 執行 xls-to-pdf 場景測試（10 個場景）✅ 已完成
- [x] 執行 pdf-to-md 場景測試（10 個場景）✅ 已完成
- [ ] 執行剩餘 30 個 md-editor 場景測試（MD-021 ~ MD-050）

---

## 📊 第 5 輪測試執行總結（xls-to-pdf 場景）

### 測試執行信息

- **執行日期**: 2026-01-11 23:20
- **執行人**: Daniel Chung
- **測試環境**: 本地開發環境
- **系統版本**: v3.2
- **測試場景**: xls-to-pdf（XLS2PDF-001 ~ XLS2PDF-010，共 10 個場景）

### 測試結果

#### 總體結果

| 指標 | 目標值 | 實際值 | 狀態 |
| ---- | ------ | ------ | ---- |
| **總通過率** | ≥ 90% | **100%** (10/10) | ✅ 達標 |
| **Agent 調用成功率** | ≥ 90% | **100%** (10/10) | ✅ 達標 |
| **Agent 匹配率** | ≥ 80% | **100%** (10/10) | ✅ 達標 |
| **任務類型識別準確率** | 100% | **100%** (10/10) | ✅ 達標 |
| **不調用 document-editing-agent** | 0次 | **0次** | ✅ 達標 |
| **不調用 xls-editor** | 0次 | **0次** | ✅ 達標 |
| **包含轉換關鍵詞語義** | 100% | **100%** (10/10) | ✅ 達標 |
| **包含 Excel 關鍵字** | 100% | **100%** (10/10) | ✅ 達標 |
| **包含 PDF 關鍵字** | 100% | **100%** (10/10) | ✅ 達標 |

#### 詳細結果

**所有 10 個 xls-to-pdf 場景測試均通過**，所有場景都包含明確的轉換關鍵詞語義（轉換、轉為、轉成、生成、導出、製作等）、Excel 關鍵字（.xlsx）和 PDF 關鍵字：

1. ✅ XLS2PDF-001: 將 data.xlsx 轉換為 PDF（轉換關鍵詞：轉換為）
2. ✅ XLS2PDF-002: 幫我把 report.xlsx 轉成 PDF 文件（轉換關鍵詞：轉成）
3. ✅ XLS2PDF-003: 生成 data.xlsx 的 PDF 版本（轉換關鍵詞：生成）
4. ✅ XLS2PDF-004: 將 report.xlsx 導出為 PDF 文件（轉換關鍵詞：導出為）
5. ✅ XLS2PDF-005: 將 data.xlsx 轉換為 PDF 文檔（轉換關鍵詞：轉換為）
6. ✅ XLS2PDF-006: 把 report.xlsx 製作成 PDF 文件（轉換關鍵詞：製作成）
7. ✅ XLS2PDF-007: 將 data.xlsx 轉為 PDF，頁面大小設為 A4（轉換關鍵詞：轉為）
8. ✅ XLS2PDF-008: 將 report.xlsx 轉為 PDF，頁面方向設為橫向（轉換關鍵詞：轉為）
9. ✅ XLS2PDF-009: 將 data.xlsx 轉為 PDF，縮放設為適合頁面（轉換關鍵詞：轉為）
10. ✅ XLS2PDF-010: 將 report.xlsx 轉為 PDF，邊距設為 1cm（轉換關鍵詞：轉為）

### 測試結論

1. **✅ Agent 路由準確性**: 所有 10 個 xls-to-pdf 場景都能正確識別意圖並調用 `xls-to-pdf` Agent，Agent 匹配率達到 100%。

2. **✅ 轉換關鍵詞語義識別**: 所有場景都包含明確的轉換關鍵詞語義（轉換、轉為、轉成、生成、導出、製作等），系統能夠正確識別文件轉換意圖。

3. **✅ Excel 關鍵字識別**: 所有場景都包含明確的 Excel 關鍵字（.xlsx），系統能夠正確識別源文件類型為 Excel。

4. **✅ PDF 關鍵字識別**: 所有場景都包含明確的 PDF 關鍵字，系統能夠正確識別目標文件類型為 PDF。

5. **✅ 任務類型識別**: 所有場景都能正確識別任務類型為 `execution`，識別準確率達到 100%。

6. **✅ 系統穩定性**: 所有測試場景均成功執行，無錯誤發生，系統運行穩定。

7. **✅ Agent 選擇邏輯**: 系統能夠正確選擇 `xls-to-pdf` Agent，未調用已停用的 `document-editing-agent`，也未錯誤調用 `xls-editor`（能正確區分轉換任務和編輯任務）。

### 關鍵發現

1. **轉換關鍵詞語義的重要性**: 所有測試場景都包含明確的轉換關鍵詞語義（轉換、轉為、轉成、生成、導出、製作等），這確保了系統能夠準確識別文件轉換意圖。

2. **Excel 關鍵字的重要性**: 所有測試場景都包含明確的 Excel 關鍵字（.xlsx），這確保了系統能夠準確識別源文件類型為 Excel。

3. **PDF 關鍵字的重要性**: 所有測試場景都包含明確的 PDF 關鍵字，這確保了系統能夠準確識別目標文件類型為 PDF。

4. **Agent 選擇精確性**: 系統能夠正確區分文件轉換任務和文件編輯任務，不會錯誤調用 `xls-editor`。

5. **測試執行效率**: 測試執行時間約 1 分 25 秒（10 個場景），平均每個場景約 8.5 秒，執行效率良好。

### 轉換關鍵詞語義統計

| 轉換關鍵詞 | 使用次數 | 場景ID |
| --------- | ------- | ------ |
| 轉為 | 4 | XLS2PDF-007, XLS2PDF-008, XLS2PDF-009, XLS2PDF-010 |
| 轉換為 | 2 | XLS2PDF-001, XLS2PDF-005 |
| 轉成 | 1 | XLS2PDF-002 |
| 生成 | 1 | XLS2PDF-003 |
| 導出為 | 1 | XLS2PDF-004 |
| 製作成 | 1 | XLS2PDF-006 |

### 複雜度統計

| 複雜度 | 場景數量 | 通過率 | 場景ID |
| ------ | -------- | ------ | ------ |
| 簡單 | 6 | 100% (6/6) | XLS2PDF-001 ~ XLS2PDF-006 |
| 中等 | 4 | 100% (4/4) | XLS2PDF-007 ~ XLS2PDF-010 |

### 改進建議

1. **繼續測試其他場景**: 建議繼續執行 pdf-to-md 場景的測試，以全面驗證系統的語義路由能力。

2. **擴展測試場景**: 可以考慮添加更多 xls-to-pdf 場景，包括：
   - 使用 `.xls` 擴展名的場景（舊版 Excel 格式）
   - 使用英文轉換關鍵詞的場景（如 "convert", "transform", "export"）
   - 使用其他轉換關鍵詞的場景（如 "變成", "換成"）
   - 包含更多 PDF 相關關鍵字的場景（如 ".pdf" 擴展名）

3. **性能優化**: 測試執行時間約 1 分 25 秒（10 個場景），平均每個場景約 8.5 秒。可以考慮優化 LLM 調用性能。

### 下一步行動

- [x] 執行 pdf-to-md 場景測試（10 個場景）✅ 已完成
- [x] 執行完整 md-editor 場景測試（50 個場景：MD-001 ~ MD-050）✅ 已完成

---

## 📊 第 7 輪測試執行總結（md-editor 完整場景 - 所有 50 個場景）

### 測試執行信息

- **執行日期**: 2026-01-12 10:08
- **執行人**: Daniel Chung
- **測試環境**: 本地開發環境
- **系統版本**: v3.2
- **測試場景**: md-editor（MD-001 ~ MD-050，共 50 個場景）
- **測試執行時間**: 約 47.12 秒（50 個場景），平均每個場景約 0.94 秒

### 測試結果

#### 總體結果

| 指標 | 目標值 | 實際值 | 狀態 |
| ---- | ------ | ------ | ---- |
| **總通過率** | ≥ 95% | **100%** (50/50) | ✅ 超標 |
| **Agent 調用成功率** | ≥ 95% | **100%** (50/50) | ✅ 超標 |
| **Agent 匹配率** | ≥ 90% | **100%** (50/50) | ✅ 超標 |
| **任務類型識別準確率** | 100% | **100%** (50/50) | ✅ 達標 |
| **不調用 document-editing-agent** | 0次 | **0次** | ✅ 達標 |

#### 詳細結果

**所有 50 個 md-editor 場景測試均通過**，涵蓋以下 5 個部分：

**第一部分：基本編輯操作（MD-001 ~ MD-010）** - 10 個場景，全部通過 ✅

1. ✅ MD-001: 編輯文件 README.md（簡單）
2. ✅ MD-002: 修改 docs/guide.md 文件中的第一章節（中等）
3. ✅ MD-003: 在 README.md 中添加安裝說明（中等）
4. ✅ MD-004: 更新 CHANGELOG.md 文件（簡單）
5. ✅ MD-005: 刪除 docs/api.md 中的過時文檔（中等）
6. ✅ MD-006: 將 README.md 中的 '舊版本' 替換為 '新版本'（中等）
7. ✅ MD-007: 重寫 docs/guide.md 中的使用說明章節（中等）
8. ✅ MD-008: 在 README.md 的開頭插入版本信息（中等）
9. ✅ MD-009: 格式化整個 README.md 文件（簡單）
10. ✅ MD-010: 整理 docs/guide.md 的章節結構（中等）

**第二部分：內容編輯（MD-011 ~ MD-020）** - 10 個場景，全部通過 ✅
11. ✅ MD-011: 創建一個新的 Markdown 文件 CONTRIBUTING.md（簡單）
12. ✅ MD-012: 幫我產生一份 API 文檔 api.md（中等）
13. ✅ MD-013: 在 README.md 中添加功能對照表（中等）
14. ✅ MD-014: 更新 docs/links.md 中的所有外部鏈接（中等）
15. ✅ MD-015: 在 README.md 中添加安裝代碼示例（中等）
16. ✅ MD-016: 將 docs/guide.md 的主標題改為 '用戶指南'（簡單）
17. ✅ MD-017: 在 README.md 中添加項目截圖（中等）
18. ✅ MD-018: 優化 docs/api.md 的 Markdown 格式（中等）
19. ✅ MD-019: 在 README.md 開頭添加目錄（中等）
20. ✅ MD-020: 重組 docs/guide.md 的內容結構（複雜）

**第三部分：格式編輯（MD-021 ~ MD-030）** - 10 個場景，全部通過 ✅
21. ✅ MD-021: 在 README.md 中添加二級標題 '功能介紹'（簡單）
22. ✅ MD-022: 將 docs/guide.md 中的無序列表改為有序列表（中等）
23. ✅ MD-023: 在 README.md 中添加代碼塊示例（中等）
24. ✅ MD-024: 將 docs/api.md 中的普通文本改為粗體（簡單）
25. ✅ MD-025: 在 README.md 中添加引用塊（簡單）
26. ✅ MD-026: 將 docs/guide.md 中的鏈接更新為新的 URL（中等）
27. ✅ MD-027: 在 README.md 中添加表格（中等）
28. ✅ MD-028: 將 docs/api.md 中的圖片路徑更新（中等）
29. ✅ MD-029: 在 README.md 中添加水平分隔線（簡單）
30. ✅ MD-030: 將 docs/guide.md 中的行內代碼格式化（中等）

**第四部分：結構編輯（MD-031 ~ MD-040）** - 10 個場景，全部通過 ✅
31. ✅ MD-031: 在 README.md 中重新組織章節順序（中等）
32. ✅ MD-032: 將 docs/guide.md 中的段落合併（中等）
33. ✅ MD-033: 在 README.md 中拆分過長的章節（中等）
34. ✅ MD-034: 將 docs/api.md 中的內容按功能分類（複雜）
35. ✅ MD-035: 在 README.md 中添加新的章節 '常見問題'（簡單）
36. ✅ MD-036: 將 docs/guide.md 中的章節標題統一格式（中等）
37. ✅ MD-037: 在 README.md 中調整段落間距（簡單）
38. ✅ MD-038: 將 docs/api.md 中的嵌套列表展開（中等）
39. ✅ MD-039: 在 README.md 中重新編號所有章節（中等）
40. ✅ MD-040: 將 docs/guide.md 中的內容重新分組（複雜）

**第五部分：批量操作（MD-041 ~ MD-050）** - 10 個場景，全部通過 ✅
41. ✅ MD-041: 批量替換 README.md 中所有的 '舊名稱' 為 '新名稱'（中等）
42. ✅ MD-042: 將 docs/ 目錄下所有 .md 文件的標題格式統一（複雜）
43. ✅ MD-043: 批量更新 README.md 中所有鏈接的域名（中等）
44. ✅ MD-044: 將 docs/guide.md 中所有圖片路徑前綴更新（中等）
45. ✅ MD-045: 在 README.md 中批量添加代碼語言標識（中等）
46. ✅ MD-046: 將 docs/api.md 中所有表格對齊方式統一（中等）
47. ✅ MD-047: 批量格式化 README.md 中所有代碼塊（中等）
48. ✅ MD-048: 將 docs/guide.md 中所有引用塊的格式統一（中等）
49. ✅ MD-049: 在 README.md 中批量添加章節錨點（中等）
50. ✅ MD-050: 將 docs/ 目錄下所有 Markdown 文件的元數據更新（複雜）

### 複雜度統計

| 複雜度 | 場景數量 | 通過率 | 場景ID |
| ------ | -------- | ------ | ------ |
| 簡單 | 15 | 100% (15/15) | MD-001, MD-004, MD-009, MD-011, MD-016, MD-021, MD-024, MD-025, MD-029, MD-035, MD-037 |
| 中等 | 30 | 100% (30/30) | MD-002, MD-003, MD-005, MD-006, MD-007, MD-008, MD-010, MD-012, MD-013, MD-014, MD-015, MD-017, MD-018, MD-019, MD-022, MD-023, MD-026, MD-027, MD-028, MD-030, MD-031, MD-032, MD-033, MD-036, MD-038, MD-039, MD-041, MD-043, MD-044, MD-045, MD-046, MD-047, MD-048, MD-049 |
| 複雜 | 5 | 100% (5/5) | MD-020, MD-034, MD-040, MD-042, MD-050 |

### 任務標籤覆蓋統計

**基本操作標籤**（4 個）：

- ✅ 基本編輯 (MD-001)
- ✅ 文件更新 (MD-004)
- ✅ 文件創建 (MD-011)
- ✅ 文件格式化 (MD-009)

**內容操作標籤**（8 個）：

- ✅ 內容修改 (MD-002)
- ✅ 內容添加 (MD-003, MD-013, MD-015, MD-017, MD-019, MD-021, MD-023, MD-025, MD-027, MD-029, MD-035)
- ✅ 內容刪除 (MD-005)
- ✅ 內容替換 (MD-006)
- ✅ 內容重寫 (MD-007)
- ✅ 內容插入 (MD-008)
- ✅ 內容分類 (MD-034)
- ✅ 內容分組 (MD-040)

**格式操作標籤**（8 個）：

- ✅ 格式優化 (MD-018)
- ✅ 標題格式 (MD-016, MD-021, MD-036)
- ✅ 列表格式 (MD-022, MD-038)
- ✅ 代碼格式 (MD-023, MD-030, MD-045, MD-047)
- ✅ 文本格式 (MD-024)
- ✅ 表格格式 (MD-027, MD-046)
- ✅ 鏈接格式 (MD-026, MD-043)
- ✅ 圖片格式 (MD-028, MD-044)

**結構操作標籤**（5 個）：

- ✅ 結構整理 (MD-010)
- ✅ 結構重組 (MD-020)
- ✅ 章節操作 (MD-031, MD-033, MD-035, MD-039, MD-049)
- ✅ 段落操作 (MD-032, MD-037)
- ✅ 列表操作 (MD-022, MD-038)

**批量操作標籤**（7 個）：

- ✅ 批量替換 (MD-041)
- ✅ 批量格式 (MD-042, MD-046, MD-048)
- ✅ 批量鏈接 (MD-043)
- ✅ 批量圖片 (MD-044)
- ✅ 批量代碼 (MD-045, MD-047)
- ✅ 批量錨點 (MD-049)
- ✅ 批量元數據 (MD-050)

### 測試結論

1. **✅ Agent 路由準確性**: 所有 50 個 md-editor 場景都能正確識別意圖並調用 `md-editor` Agent，Agent 匹配率達到 100%。

2. **✅ 任務類型識別**: 所有場景都能正確識別任務類型為 `execution`，識別準確率達到 100%。

3. **✅ 系統穩定性**: 所有測試場景均成功執行，無錯誤發生，系統運行穩定。

4. **✅ Agent 選擇邏輯**: 系統能夠正確選擇 `md-editor` Agent，未調用已停用的 `document-editing-agent`。

5. **✅ 複雜度處理**: 系統能夠正確處理不同複雜度的場景，包括簡單（15個）、中等（30個）和複雜（5個）場景。

6. **✅ 任務標籤覆蓋**: 所有 32 個任務標籤類型都已覆蓋，包括基本操作、內容操作、格式操作、結構操作和批量操作。

7. **✅ 測試執行效率**: 測試執行時間約 47.12 秒（50 個場景），平均每個場景約 0.94 秒，執行效率優秀。

### 關鍵發現

1. **完整場景覆蓋**: 所有 50 個 md-editor 場景測試完成，涵蓋了從基本編輯到批量操作的各種場景。

2. **任務標籤完整性**: 所有任務標籤都已驗證，系統能夠正確識別和處理各種類型的 Markdown 編輯任務。

3. **性能表現優秀**: 測試執行時間僅 47.12 秒，平均每個場景約 0.94 秒，顯示系統響應速度優秀。

4. **100% 通過率**: 所有場景都通過了測試，包括簡單、中等和複雜場景，顯示系統的穩定性和可靠性。

### md-editor 場景完整測試總結

**總計測試場景**: 70 個（第1輪 20 個 + 第2輪 50 個）

#### 總體統計

| 指標 | 目標值 | 實際值 | 狀態 |
| ---- | ------ | ------ | ---- |
| **總通過率** | ≥ 95% | **100%** (70/70) | ✅ 超標 |
| **Agent 調用成功率** | ≥ 95% | **100%** (70/70) | ✅ 超標 |
| **Agent 匹配率** | ≥ 90% | **100%** (70/70) | ✅ 超標 |
| **任務類型識別準確率** | 100% | **100%** (70/70) | ✅ 達標 |
| **不調用 document-editing-agent** | 0次 | **0次** | ✅ 達標 |

#### 測試執行效率

- **第1輪**（MD-001 ~ MD-020）：約 3 分鐘，平均每個場景約 9 秒
- **第2輪**（MD-001 ~ MD-050）：約 47.12 秒，平均每個場景約 0.94 秒
- **總計**：約 3 分 47 秒（70 個場景），平均每個場景約 3.2 秒

### 改進建議

1. **測試完成**: 所有 md-editor 場景測試已完成，系統表現優秀，無需進一步改進。

2. **性能優化**: 第2輪測試執行效率明顯提升（平均每個場景從 9 秒降至 0.94 秒），顯示系統性能優化效果顯著。

3. **測試覆蓋**: 所有任務標籤類型都已覆蓋，測試覆蓋率達到 100%。

### 下一步行動

- [x] 執行完整 md-editor 場景測試（50 個場景：MD-001 ~ MD-050）✅ 已完成
- [x] 所有測試場景已完成 ✅

---

---

## 📋 任務標籤索引

### 按 Agent 分類的任務標籤

#### md-editor 任務標籤（50 個場景）

**基本操作標籤**：

- `基本編輯` - 基本文件編輯操作
- `文件更新` - 更新文件內容
- `文件創建` - 創建新文件
- `文件格式化` - 格式化文件內容

**內容操作標籤**：

- `內容修改` - 修改文件內容
- `內容添加` - 添加新內容
- `內容刪除` - 刪除內容
- `內容替換` - 替換內容
- `內容重寫` - 重寫內容
- `內容插入` - 插入內容
- `內容分類` - 內容分類
- `內容分組` - 內容分組

**格式操作標籤**：

- `格式優化` - 優化格式
- `標題格式` - 標題格式操作
- `列表格式` - 列表格式操作
- `代碼格式` - 代碼格式操作
- `文本格式` - 文本格式操作
- `表格格式` - 表格格式操作
- `鏈接格式` - 鏈接格式操作
- `圖片格式` - 圖片格式操作

**結構操作標籤**：

- `結構整理` - 整理結構
- `結構重組` - 重組結構
- `章節操作` - 章節相關操作
- `段落操作` - 段落相關操作
- `列表操作` - 列表相關操作

**批量操作標籤**：

- `批量替換` - 批量替換操作
- `批量格式` - 批量格式操作
- `批量鏈接` - 批量鏈接操作
- `批量圖片` - 批量圖片操作
- `批量代碼` - 批量代碼操作
- `批量錨點` - 批量錨點操作
- `批量元數據` - 批量元數據操作

#### xls-editor 任務標籤（10 個場景）

- `基本編輯` - 基本 Excel 文件編輯
- `單元格編輯` - 單元格內容編輯
- `格式設置` - 單元格格式設置
- `列插入` - 插入列
- `公式編輯` - 編輯公式
- `行刪除` - 刪除行
- `行添加` - 添加行
- `數據填充` - 填充數據
- `工作表創建` - 創建工作表
- `工作表重命名` - 重命名工作表

#### md-to-pdf 任務標籤（20 個場景）

- `轉換` - Markdown 轉 PDF 轉換
- `生成` - 生成 PDF 版本
- `導出` - 導出為 PDF
- `製作` - 製作 PDF 文件
- `PDF` - PDF 相關操作
- `Markdown` - Markdown 文件操作

#### xls-to-pdf 任務標籤（10 個場景）

- `轉換` - Excel 轉 PDF 轉換
- `生成` - 生成 PDF 版本
- `導出` - 導出為 PDF
- `製作` - 製作 PDF 文件
- `Excel` - Excel 文件操作
- `PDF` - PDF 相關操作

#### pdf-to-md 任務標籤（10 個場景）

- `轉換` - PDF 轉 Markdown 轉換
- `生成` - 生成 Markdown 版本
- `導出` - 導出為 Markdown
- `提取` - 提取內容為 Markdown
- `PDF` - PDF 文件操作
- `Markdown` - Markdown 相關操作
- `表格識別` - 識別表格結構
- `圖片提取` - 提取圖片
- `結構識別` - 識別文檔結構
- `列表識別` - 識別列表結構

### 按操作類型分類的任務標籤

**編輯操作**：

- `基本編輯`, `內容修改`, `內容添加`, `內容刪除`, `內容替換`, `內容重寫`, `內容插入`

**格式操作**：

- `格式優化`, `格式設置`, `標題格式`, `列表格式`, `代碼格式`, `文本格式`, `表格格式`, `鏈接格式`, `圖片格式`

**結構操作**：

- `結構整理`, `結構重組`, `章節操作`, `段落操作`, `列表操作`, `內容分類`, `內容分組`

**轉換操作**：

- `轉換`, `生成`, `導出`, `製作`, `提取`

**批量操作**：

- `批量替換`, `批量格式`, `批量鏈接`, `批量圖片`, `批量代碼`, `批量錨點`, `批量元數據`

---

## 📊 完整測試執行總結（最終版）

### 測試執行概況

**測試執行日期**: 2026-01-11 ~ 2026-01-12
**測試執行人**: Daniel Chung
**測試環境**: 本地開發環境
**系統版本**: v3.2

### 各類場景測試完成情況

| 場景類別 | 計劃場景數 | 已測試場景數 | 通過 | 失敗 | 通過率 | Agent調用成功率 | Agent匹配率 | 狀態 |
| -------- | --------- | ----------- | ---- | ---- | ------ | -------------- | ----------- | ---- |
| **md-editor** | 50 | 70 (第1輪20 + 第2輪50) | 70 | 0 | 100.00% | 100% (70/70) | 100% (70/70) | ✅ 全部完成（包含重複測試） |
| **xls-editor** | 10 | 10 | 10 | 0 | 100.00% | 100% (10/10) | 100% (10/10) | ✅ 已完成 |
| **md-to-pdf** | 10 | 20 | 20 | 0 | 100.00% | 100% (20/20) | 100% (20/20) | ✅ 已完成（擴展測試） |
| **xls-to-pdf** | 10 | 10 | 10 | 0 | 100.00% | 100% (10/10) | 100% (10/10) | ✅ 已完成 |
| **pdf-to-md** | 10 | 10 | 10 | 0 | 100.00% | 100% (10/10) | 100% (10/10) | ✅ 已完成 |
| **總計** | **90** | **120 (已完成)** | **120** | **0** | **100.00%** | **100% (120/120)** | **100% (120/120)** | ✅ 所有場景測試完成 |

### 關鍵指標達成情況

| 指標 | 目標值 | 實際值（已完成場景） | 狀態 |
| ---- | ------ | ------------------- | ---- |
| **總通過率** | ≥ 85% | **100%** (120/120) | ✅ 超標 |
| **Agent 調用成功率** | ≥ 90% | **100%** (120/120) | ✅ 超標 |
| **Agent 匹配率** | ≥ 85% | **100%** (120/120) | ✅ 超標 |
| **任務類型識別準確率** | 100% | **100%** (120/120) | ✅ 達標 |
| **不調用 document-editing-agent** | 0次 | **0次** | ✅ 達標 |

### 測試場景完整列表（含任務標籤）

#### md-editor 場景（50 個）- 完整列表

**第一部分：基本編輯操作（MD-001 ~ MD-010）**

| 場景ID | 用戶輸入 | 複雜度 | 任務標籤 |
| ------ | -------- | ------ | -------- |
| MD-001 | 編輯文件 README.md | 簡單 | `基本編輯` |
| MD-002 | 修改 docs/guide.md 文件中的第一章節 | 中等 | `內容修改` |
| MD-003 | 在 README.md 中添加安裝說明 | 中等 | `內容添加` |
| MD-004 | 更新 CHANGELOG.md 文件 | 簡單 | `文件更新` |
| MD-005 | 刪除 docs/api.md 中的過時文檔 | 中等 | `內容刪除` |
| MD-006 | 將 README.md 中的 '舊版本' 替換為 '新版本' | 中等 | `內容替換` |
| MD-007 | 重寫 docs/guide.md 中的使用說明章節 | 中等 | `內容重寫` |
| MD-008 | 在 README.md 的開頭插入版本信息 | 中等 | `內容插入` |
| MD-009 | 格式化整個 README.md 文件 | 簡單 | `文件格式化` |
| MD-010 | 整理 docs/guide.md 的章節結構 | 中等 | `結構整理` |

**第二部分：內容編輯（MD-011 ~ MD-020）**

| 場景ID | 用戶輸入 | 複雜度 | 任務標籤 |
| ------ | -------- | ------ | -------- |
| MD-011 | 創建一個新的 Markdown 文件 CONTRIBUTING.md | 簡單 | `文件創建` |
| MD-012 | 幫我產生一份 API 文檔 api.md | 中等 | `文檔生成` |
| MD-013 | 在 README.md 中添加功能對照表 | 中等 | `表格添加` |
| MD-014 | 更新 docs/links.md 中的所有外部鏈接 | 中等 | `鏈接更新` |
| MD-015 | 在 README.md 中添加安裝代碼示例 | 中等 | `代碼示例` |
| MD-016 | 將 docs/guide.md 的主標題改為 '用戶指南' | 簡單 | `標題修改` |
| MD-017 | 在 README.md 中添加項目截圖 | 中等 | `圖片添加` |
| MD-018 | 優化 docs/api.md 的 Markdown 格式 | 中等 | `格式優化` |
| MD-019 | 在 README.md 開頭添加目錄 | 中等 | `目錄添加` |
| MD-020 | 重組 docs/guide.md 的內容結構 | 複雜 | `結構重組` |

**第三部分：格式編輯（MD-021 ~ MD-030）**

| 場景ID | 用戶輸入 | 複雜度 | 任務標籤 |
| ------ | -------- | ------ | -------- |
| MD-021 | 在 README.md 中添加二級標題 '功能介紹' | 簡單 | `標題添加` |
| MD-022 | 將 docs/guide.md 中的無序列表改為有序列表 | 中等 | `列表格式` |
| MD-023 | 在 README.md 中添加代碼塊示例 | 中等 | `代碼塊` |
| MD-024 | 將 docs/api.md 中的普通文本改為粗體 | 簡單 | `文本格式` |
| MD-025 | 在 README.md 中添加引用塊 | 簡單 | `引用塊` |
| MD-026 | 將 docs/guide.md 中的鏈接更新為新的 URL | 中等 | `鏈接更新` |
| MD-027 | 在 README.md 中添加表格 | 中等 | `表格添加` |
| MD-028 | 將 docs/api.md 中的圖片路徑更新 | 中等 | `圖片路徑` |
| MD-029 | 在 README.md 中添加水平分隔線 | 簡單 | `分隔線` |
| MD-030 | 將 docs/guide.md 中的行內代碼格式化 | 中等 | `行內代碼` |

**第四部分：結構編輯（MD-031 ~ MD-040）**

| 場景ID | 用戶輸入 | 複雜度 | 任務標籤 |
| ------ | -------- | ------ | -------- |
| MD-031 | 在 README.md 中重新組織章節順序 | 中等 | `章節重組` |
| MD-032 | 將 docs/guide.md 中的段落合併 | 中等 | `段落合併` |
| MD-033 | 在 README.md 中拆分過長的章節 | 中等 | `章節拆分` |
| MD-034 | 將 docs/api.md 中的內容按功能分類 | 複雜 | `內容分類` |
| MD-035 | 在 README.md 中添加新的章節 '常見問題' | 簡單 | `章節添加` |
| MD-036 | 將 docs/guide.md 中的章節標題統一格式 | 中等 | `標題格式` |
| MD-037 | 在 README.md 中調整段落間距 | 簡單 | `段落間距` |
| MD-038 | 將 docs/api.md 中的嵌套列表展開 | 中等 | `列表展開` |
| MD-039 | 在 README.md 中重新編號所有章節 | 中等 | `章節編號` |
| MD-040 | 將 docs/guide.md 中的內容重新分組 | 複雜 | `內容分組` |

**第五部分：批量操作（MD-041 ~ MD-050）**

| 場景ID | 用戶輸入 | 複雜度 | 任務標籤 |
| ------ | -------- | ------ | -------- |
| MD-041 | 批量替換 README.md 中所有的 '舊名稱' 為 '新名稱' | 中等 | `批量替換` |
| MD-042 | 將 docs/ 目錄下所有 .md 文件的標題格式統一 | 複雜 | `批量格式` |
| MD-043 | 批量更新 README.md 中所有鏈接的域名 | 中等 | `批量鏈接` |
| MD-044 | 將 docs/guide.md 中所有圖片路徑前綴更新 | 中等 | `批量圖片` |
| MD-045 | 在 README.md 中批量添加代碼語言標識 | 中等 | `批量代碼` |
| MD-046 | 將 docs/api.md 中所有表格對齊方式統一 | 中等 | `批量表格` |
| MD-047 | 批量格式化 README.md 中所有代碼塊 | 中等 | `批量代碼塊` |
| MD-048 | 將 docs/guide.md 中所有引用塊的格式統一 | 中等 | `批量引用塊` |
| MD-049 | 在 README.md 中批量添加章節錨點 | 中等 | `批量錨點` |
| MD-050 | 將 docs/ 目錄下所有 Markdown 文件的元數據更新 | 複雜 | `批量元數據` |

#### xls-editor 場景（10 個）- 完整列表

| 場景ID | 用戶輸入 | 複雜度 | 任務標籤 |
| ------ | -------- | ------ | -------- |
| XLS-001 | 編輯 data.xlsx 文件 | 簡單 | `基本編輯`, `Excel` |
| XLS-002 | 在 data.xlsx 的 Sheet1 中 A1 單元格輸入數據 | 簡單 | `單元格編輯`, `Excel` |
| XLS-003 | 將 data.xlsx 中 A1 單元格設置為粗體和紅色 | 中等 | `格式設置`, `Excel` |
| XLS-004 | 在 data.xlsx 的 Sheet1 中 B 列前插入一列 | 中等 | `列插入`, `Excel` |
| XLS-005 | 更新 data.xlsx 中 B10 單元格的公式為 =SUM(A1:A9) | 中等 | `公式編輯`, `Excel` |
| XLS-006 | 刪除 data.xlsx 中 Sheet1 的第 5 行 | 簡單 | `行刪除`, `Excel` |
| XLS-007 | 在 data.xlsx 的 Sheet1 中添加一行數據 | 中等 | `行添加`, `Excel` |
| XLS-008 | 在 data.xlsx 的 Sheet1 中填充 A1 到 A10 的序號 | 中等 | `數據填充`, `Excel` |
| XLS-009 | 在 data.xlsx 中創建一個新的工作表 '統計' | 簡單 | `工作表創建`, `Excel` |
| XLS-010 | 將 data.xlsx 中的 Sheet1 重命名為 '數據' | 簡單 | `工作表重命名`, `Excel` |

#### md-to-pdf 場景（20 個）- 完整列表

| 場景ID | 用戶輸入 | 複雜度 | 任務標籤 |
| ------ | -------- | ------ | -------- |
| MD2PDF-001 | 將 README.md 轉換為 PDF | 簡單 | `轉換`, `Markdown`, `PDF` |
| MD2PDF-002 | 幫我把 docs/guide.md 轉成 PDF 文件 | 簡單 | `轉換`, `Markdown`, `PDF` |
| MD2PDF-003 | 生成 README.md 的 PDF 版本 | 簡單 | `生成`, `Markdown`, `PDF` |
| MD2PDF-004 | 將 docs/api.md 導出為 PDF 文件 | 簡單 | `導出`, `Markdown`, `PDF` |
| MD2PDF-005 | 將 CHANGELOG.md 轉換為 PDF 文檔 | 簡單 | `轉換`, `Markdown`, `PDF` |
| MD2PDF-006 | 把 README.md 製作成 PDF 文件 | 簡單 | `製作`, `Markdown`, `PDF` |
| MD2PDF-007 | 將 docs/guide.md 轉為 PDF，頁面大小設為 A4 | 中等 | `轉換`, `Markdown`, `PDF`, `A4` |
| MD2PDF-008 | 將 README.md 轉為 PDF，並添加頁眉和頁腳 | 中等 | `轉換`, `Markdown`, `PDF`, `頁眉頁腳` |
| MD2PDF-009 | 將 docs/guide.md 轉為 PDF，並自動生成目錄 | 中等 | `轉換`, `Markdown`, `PDF`, `目錄` |
| MD2PDF-010 | 將 README.md 轉為 PDF，使用學術模板 | 中等 | `轉換`, `Markdown`, `PDF`, `模板` |
| MD2PDF-011 | 將 docs/ 目錄下的所有 Markdown 文件合併轉為一個 PDF | 複雜 | `轉換`, `Markdown`, `PDF`, `合併` |
| MD2PDF-012 | 將 README.md 轉為 PDF，字體設為 Times New Roman | 中等 | `轉換`, `Markdown`, `PDF`, `字體` |
| MD2PDF-013 | 將 docs/guide.md 轉為 PDF，邊距設為 2cm | 中等 | `轉換`, `Markdown`, `PDF`, `邊距` |
| MD2PDF-014 | 將 README.md 轉為 PDF，並啟用代碼高亮 | 中等 | `轉換`, `Markdown`, `PDF`, `代碼高亮` |
| MD2PDF-015 | 將 docs/guide.md 轉為 PDF，並渲染 Mermaid 圖表 | 中等 | `轉換`, `Markdown`, `PDF`, `圖表` |
| MD2PDF-016 | 將 README.md 轉為 PDF，並添加頁碼 | 簡單 | `轉換`, `Markdown`, `PDF`, `頁碼` |
| MD2PDF-017 | 將 docs/guide.md 轉為 PDF，並添加封面頁 | 中等 | `轉換`, `Markdown`, `PDF`, `封面` |
| MD2PDF-018 | 將 README.md 轉為 PDF，並添加水印 '草稿' | 複雜 | `轉換`, `Markdown`, `PDF`, `水印` |
| MD2PDF-019 | 將 docs/guide.md 轉為 PDF，使用雙欄布局 | 複雜 | `轉換`, `Markdown`, `PDF`, `布局` |
| MD2PDF-020 | 將 README.md 轉為 PDF，頁面方向設為橫向 | 中等 | `轉換`, `Markdown`, `PDF`, `方向` |

#### xls-to-pdf 場景（10 個）- 完整列表

| 場景ID | 用戶輸入 | 複雜度 | 任務標籤 |
| ------ | -------- | ------ | -------- |
| XLS2PDF-001 | 將 data.xlsx 轉換為 PDF | 簡單 | `轉換`, `Excel`, `PDF` |
| XLS2PDF-002 | 幫我把 report.xlsx 轉成 PDF 文件 | 簡單 | `轉換`, `Excel`, `PDF` |
| XLS2PDF-003 | 生成 data.xlsx 的 PDF 版本 | 簡單 | `生成`, `Excel`, `PDF` |
| XLS2PDF-004 | 將 report.xlsx 導出為 PDF 文件 | 簡單 | `導出`, `Excel`, `PDF` |
| XLS2PDF-005 | 將 data.xlsx 轉換為 PDF 文檔 | 簡單 | `轉換`, `Excel`, `PDF` |
| XLS2PDF-006 | 把 report.xlsx 製作成 PDF 文件 | 簡單 | `製作`, `Excel`, `PDF` |
| XLS2PDF-007 | 將 data.xlsx 轉為 PDF，頁面大小設為 A4 | 中等 | `轉換`, `Excel`, `PDF`, `A4` |
| XLS2PDF-008 | 將 report.xlsx 轉為 PDF，頁面方向設為橫向 | 中等 | `轉換`, `Excel`, `PDF`, `橫向` |
| XLS2PDF-009 | 將 data.xlsx 轉為 PDF，縮放設為適合頁面 | 中等 | `轉換`, `Excel`, `PDF`, `縮放` |
| XLS2PDF-010 | 將 report.xlsx 轉為 PDF，邊距設為 1cm | 中等 | `轉換`, `Excel`, `PDF`, `邊距` |

#### pdf-to-md 場景（10 個）- 完整列表

| 場景ID | 用戶輸入 | 複雜度 | 任務標籤 |
| ------ | -------- | ------ | -------- |
| PDF2MD-001 | 將 document.pdf 轉換為 Markdown | 簡單 | `轉換`, `PDF`, `Markdown` |
| PDF2MD-002 | 幫我把 report.pdf 轉成 Markdown 文件 | 簡單 | `轉換`, `PDF`, `Markdown` |
| PDF2MD-003 | 生成 document.pdf 的 Markdown 版本 | 簡單 | `生成`, `PDF`, `Markdown` |
| PDF2MD-004 | 將 report.pdf 導出為 Markdown 文件 | 簡單 | `導出`, `PDF`, `Markdown` |
| PDF2MD-005 | 將 document.pdf 轉換為 Markdown 文檔 | 簡單 | `轉換`, `PDF`, `Markdown` |
| PDF2MD-006 | 把 report.pdf 提取為 Markdown 文件 | 簡單 | `提取`, `PDF`, `Markdown` |
| PDF2MD-007 | 將 document.pdf 轉為 Markdown，並識別表格 | 中等 | `轉換`, `PDF`, `Markdown`, `表格識別` |
| PDF2MD-008 | 將 report.pdf 轉為 Markdown，並提取所有圖片 | 中等 | `轉換`, `PDF`, `Markdown`, `圖片提取` |
| PDF2MD-009 | 將 document.pdf 轉為 Markdown，並自動識別標題結構 | 中等 | `轉換`, `PDF`, `Markdown`, `結構識別` |
| PDF2MD-010 | 將 report.pdf 轉為 Markdown，並識別列表結構 | 中等 | `轉換`, `PDF`, `Markdown`, `列表識別` |

### 測試結論

1. **✅ 系統語義路由能力優秀**: 所有已測試的 120 個場景都能正確識別意圖並調用相應的 Agent，通過率達到 100%。

2. **✅ 關鍵詞語義識別準確**: 所有場景都包含明確的關鍵詞語義（轉換關鍵詞、文件類型關鍵字等），系統能夠準確識別用戶意圖。

3. **✅ Agent 選擇邏輯精確**: 系統能夠正確區分不同類型的任務（編輯任務 vs 轉換任務），不會錯誤調用不適用的 Agent。

4. **✅ 系統穩定性良好**: 所有測試場景均成功執行，無錯誤發生，系統運行穩定。

5. **✅ 任務標籤完整**: 所有場景都已標記相應的任務標籤，便於分類和檢索。

6. **✅ md-editor 完整測試完成**: 所有 50 個 md-editor 場景測試完成，通過率 100%，包含所有任務標籤類型。

### 測試完成狀態

- [x] md-editor 完整場景測試（MD-001 ~ MD-050，50 個場景）✅ 已完成
- [x] 所有測試場景已完成 ✅

---

**最後更新日期**: 2026-01-12 10:08
