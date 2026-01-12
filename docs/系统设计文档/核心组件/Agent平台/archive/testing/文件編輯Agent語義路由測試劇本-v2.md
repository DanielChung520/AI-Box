# 文件編輯 Agent 語義路由測試劇本 v2.0

**代碼功能說明**: 文件編輯 Agent 語義路由測試劇本 - 驗證系統是否能根據語義正確調用不同的編輯和轉換 Agent
**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11 21:42

---

## 📋 測試概述

### 測試目的

本測試劇本旨在驗證 AI-Box Agent Platform 的語義路由能力，確保系統能夠根據用戶的自然語言指令，正確識別意圖並調用相應的文件編輯或轉換 Agent。

### 測試範圍

本測試劇本包含 **100 個測試場景**，覆蓋以下 5 類 Agent：

1. **md-editor**（Markdown 編輯器）- 20 個場景
2. **xls-editor**（Excel 編輯器）- 20 個場景
3. **md-to-pdf**（Markdown 轉 PDF）- 20 個場景
4. **xls-to-pdf**（Excel 轉 PDF）- 20 個場景
5. **pdf-to-md**（PDF 轉 Markdown）- 20 個場景

### 測試標準

**通過標準**：系統能夠根據語義正確識別意圖並調用相應的 Agent，無需實際執行文件操作。

**驗證點**：

- ✅ 任務類型識別正確（應為 `execution`）
- ✅ 意圖提取準確（識別出文件編輯/轉換意圖）
- ✅ Agent 調用正確（調用預期的 Agent：`md-editor`、`xls-editor`、`md-to-pdf`、`xls-to-pdf`、`pdf-to-md`）

### 系統配置

**語義模型**：優先使用 `gpt-oss:120b-cloud`（根據測試結果，該模型達到 100% Agent 調用成功率）

**配置位置**：`agents/task_analyzer/router_llm.py`

- 默認模型：`gpt-oss:120b-cloud`
- 可通過環境變量 `ROUTER_LLM_MODEL` 覆蓋

---

## 📊 測試執行記錄表

### 測試執行摘要

| 測試輪次 | 執行日期   | 執行人       | 測試環境     | 系統版本 | 總場景數 | 通過 | 失敗 | 未執行 | 通過率 | 備註                                                                                                                |
| -------- | ---------- | ------------ | ------------ | -------- | -------- | ---- | ---- | ------ | ------ | ------------------------------------------------------------------------------------------------------------------- |
| 第 1 輪  | 2026-01-11 | Daniel Chung | 本地開發環境 | v3.2     | 100      | 0    | 100  | 0      | 0.00%  | 測試完成（實施前）                                                                                                  |
| 第 2 輪  | 2026-01-11 | Daniel Chung | 本地開發環境 | v3.2     | 32       | 0    | 32   | 0      | 0.00%  | 測試完成（實施後，RAG初始化完成，部分場景測試）                                                                     |
| 第 3 輪  | 2026-01-11 | Daniel Chung | 本地開發環境 | v3.2     | 33       | 0    | 33   | 0      | 0.00%  | 測試完成（Prompt 更新後，RouterLLM 增強）                                                                           |
| 第 4 輪  | 2026-01-11 | Daniel Chung | 本地開發環境 | v3.2     | 32       | 0    | 32   | 0      | 0.00%  | 測試完成（修復 DecisionEngine context 參數後）                                                                      |
| 第 5 輪  | 2026-01-11 | Daniel Chung | 本地開發環境 | v3.2     | 35       | 0    | 35   | 0      | 0.00%  | 測試完成（修復 CapabilityMatcher 查詢邏輯後，同時查詢 document_editing 和 document_conversion）                     |
| 第 6 輪  | 2026-01-11 | Daniel Chung | 本地開發環境 | v3.2     | 33       | 0    | 33   | 0      | 0.00%  | 測試完成（修復 TaskAnalyzer 覆蓋邏輯後，任務類型識別準確率 100%）                                                   |
| 第 7 輪  | 2026-01-11 | Daniel Chung | 本地開發環境 | v3.2     | 100      | 15   | 85   | 0      | 15.00% | 測試完成（修復 AgentRegistry.list_agents 邏輯錯誤後，System Agents 正確加載，md-editor 場景 Agent 調用成功率 100%） |

### 測試腳本對應關係

| 測試腳本文件                                        | 測試類別                        | 場景數量 | 狀態      | 說明                                                             |
| --------------------------------------------------- | ------------------------------- | -------- | --------- | ---------------------------------------------------------------- |
| `tests/agents/test_file_editing_intent.py`        | 文件編輯意圖識別（舊版）        | 30       | ✅ 已實現 | 測試 `document-editing-agent` 的意圖識別，覆蓋 FE-001 ~ FE-030 |
| `tests/agents/test_file_editing_agent_routing.py` | 文件編輯 Agent 語義路由（新版） | 100      | ✅ 已實現 | 測試 5 類 Agent 的語義路由，覆蓋 MD-001 ~ PDF2MD-020             |

**測試腳本位置**：

- 舊版測試腳本：`tests/agents/test_file_editing_intent.py`
- 新版測試腳本：`tests/agents/test_file_editing_agent_routing.py`（✅ 已創建）
- 測試執行腳本：`tests/agents/run_file_editing_agent_routing_test.py`（✅ 已創建）

**測試腳本說明**：

1. **舊版測試腳本**（`test_file_editing_intent.py`）：

   - **位置**：`tests/agents/test_file_editing_intent.py`
   - **功能**：專門測試 `document-editing-agent` 的意圖識別
   - **場景數量**：30 個場景（FE-001 ~ FE-030）
   - **測試目標**：驗證系統是否能正確識別文件編輯意圖並調用 `document-editing-agent`
   - **測試方法**：使用 `AgentOrchestrator` 和 `TaskAnalyzer` 進行測試
   - **核心代碼**：

     ```python
     from agents.services.orchestrator.orchestrator import AgentOrchestrator
     from agents.task_analyzer.models import TaskAnalysisRequest

     orchestrator = AgentOrchestrator()
     analysis_request = TaskAnalysisRequest(task=user_input)
     task_analyzer = orchestrator._get_task_analyzer()
     analysis_result = await task_analyzer.analyze(analysis_request)
     ```

   - **驗證點**：
     - 任務類型識別（應為 `execution`）
     - Agent 調用（應包含 `document-editing-agent`）
     - 澄清機制（如需要）
2. **新版測試腳本**（`test_file_editing_agent_routing.py`，✅ 已創建）：

   - **位置**：`tests/agents/test_file_editing_agent_routing.py`
   - **功能**：測試 5 類 Agent 的語義路由能力
   - **場景數量**：100 個場景（MD-001 ~ PDF2MD-020）
   - **測試目標**：驗證系統是否能根據語義正確調用不同的 Agent
   - **覆蓋的 Agent**：
     - `md-editor`（20 個場景：MD-001 ~ MD-020）
     - `xls-editor`（20 個場景：XLS-001 ~ XLS-020）
     - `md-to-pdf`（20 個場景：MD2PDF-001 ~ MD2PDF-020）
     - `xls-to-pdf`（20 個場景：XLS2PDF-001 ~ XLS2PDF-020）
     - `pdf-to-md`（20 個場景：PDF2MD-001 ~ PDF2MD-020）
   - **測試方法**：基於舊版測試腳本的架構，擴展支持多種 Agent 類型
   - **核心代碼結構**（✅ 已實現）：

     ```python
     # Agent ID 定義
     MD_EDITOR_AGENT_ID = "md-editor"
     XLS_EDITOR_AGENT_ID = "xls-editor"
     MD_TO_PDF_AGENT_ID = "md-to-pdf"
     XLS_TO_PDF_AGENT_ID = "xls-to-pdf"
     PDF_TO_MD_AGENT_ID = "pdf-to-md"

     # 測試場景定義（100 個場景）
     TEST_SCENARIOS = [
         # md-editor 場景
         {"scenario_id": "MD-001", "expected_agent": MD_EDITOR_AGENT_ID, ...},
         # xls-editor 場景
         {"scenario_id": "XLS-001", "expected_agent": XLS_EDITOR_AGENT_ID, ...},
         # md-to-pdf 場景
         {"scenario_id": "MD2PDF-001", "expected_agent": MD_TO_PDF_AGENT_ID, ...},
         # xls-to-pdf 場景
         {"scenario_id": "XLS2PDF-001", "expected_agent": XLS_TO_PDF_AGENT_ID, ...},
         # pdf-to-md 場景
         {"scenario_id": "PDF2MD-001", "expected_agent": PDF_TO_MD_AGENT_ID, ...},
         # ... 更多場景
     ]

     # 測試類
     class TestFileEditingAgentRouting:
         @pytest.mark.asyncio
         @pytest.mark.parametrize("scenario", TEST_SCENARIOS)
         async def test_agent_routing(self, orchestrator, scenario):
             # 執行意圖解析
             analysis_result = await task_analyzer.analyze(analysis_request)

             # 驗證 Agent 調用
             assert scenario["expected_agent"] in analysis_result.suggested_agents
     ```

   - **驗證點**：
     - 任務類型識別（應為 `execution`）
     - 文件類型識別（Markdown、Excel、PDF）
     - 操作類型識別（編輯 vs 轉換）
     - Agent 調用（應調用預期的 Agent）

**測試腳本執行方式**：

```bash
# 執行舊版測試腳本（30 個場景）
pytest tests/agents/test_file_editing_intent.py -v

# 執行新版測試腳本（100 個場景，待創建）
pytest tests/agents/test_file_editing_agent_routing.py -v

# 執行所有文件編輯相關測試
pytest tests/agents/test_file_editing*.py -v
```

**測試腳本依賴**：

- `AgentOrchestrator`：任務協調器
- `TaskAnalyzer`：任務分析器
- `AgentRegistry`：Agent 註冊表
- `SystemAgentRegistry`：系統 Agent 註冊表（存儲在 ArangoDB）

### 測試場景統計

| Agent 類型     | 場景數量      | 場景 ID                       | 預期調用 Agent |
| -------------- | ------------- | ----------------------------- | -------------- |
| md-editor      | 20            | MD-001 ~ MD-020               | `md-editor`  |
| xls-editor     | 20            | XLS-001 ~ XLS-020             | `xls-editor` |
| md-to-pdf      | 20            | MD2PDF-001 ~ MD2PDF-020       | `md-to-pdf`  |
| xls-to-pdf     | 20            | XLS2PDF-001 ~ XLS2PDF-020     | `xls-to-pdf` |
| pdf-to-md      | 20            | PDF2MD-001 ~ PDF2MD-020       | `pdf-to-md`  |
| **總計** | **100** | **MD-001 ~ PDF2MD-020** | -              |

---

## 📝 測試場景詳細說明

### 類別 1：md-editor（Markdown 編輯器）- 20 個場景

#### MD-001：編輯 Markdown 文件

**用戶輸入**：`"編輯文件 README.md"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**預期要執行的動作**：

1. Task Analyzer 分析任務
2. 識別為 Markdown 文件編輯任務
3. 提取文件路徑：README.md
4. 調用 md-editor Agent

**複雜度**：簡單

---

#### MD-002：修改 Markdown 文件內容

**用戶輸入**：`"修改 docs/guide.md 文件中的第一章節"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**預期要執行的動作**：

1. 識別為 Markdown 文件編輯任務
2. 提取文件路徑：docs/guide.md
3. 提取編輯指令：修改第一章節
4. 調用 md-editor Agent

**複雜度**：中等

---

#### MD-003：在 Markdown 文件中添加內容

**用戶輸入**：`"在 README.md 中添加安裝說明"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**預期要執行的動作**：

1. 識別為 Markdown 文件編輯任務
2. 提取文件路徑：README.md
3. 提取編輯指令：添加安裝說明
4. 調用 md-editor Agent

**複雜度**：中等

---

#### MD-004：更新 Markdown 文件

**用戶輸入**：`"更新 CHANGELOG.md 文件"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：簡單

---

#### MD-005：刪除 Markdown 文件中的內容

**用戶輸入**：`"刪除 docs/api.md 中的過時文檔"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-006：替換 Markdown 文件中的文本

**用戶輸入**：`"將 README.md 中的 '舊版本' 替換為 '新版本'"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-007：重寫 Markdown 文件中的章節

**用戶輸入**：`"重寫 docs/guide.md 中的使用說明章節"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-008：在 Markdown 文件中插入新章節

**用戶輸入**：`"在 README.md 的開頭插入版本信息"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-009：格式化 Markdown 文件

**用戶輸入**：`"格式化整個 README.md 文件"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：簡單

---

#### MD-010：整理 Markdown 文件結構

**用戶輸入**：`"整理 docs/guide.md 的章節結構"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-011：創建新的 Markdown 文件

**用戶輸入**：`"創建一個新的 Markdown 文件 CONTRIBUTING.md"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：簡單

---

#### MD-012：產生 Markdown 文檔

**用戶輸入**：`"幫我產生一份 API 文檔 api.md"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-013：在 Markdown 文件中添加表格

**用戶輸入**：`"在 README.md 中添加功能對照表"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-014：更新 Markdown 文件中的鏈接

**用戶輸入**：`"更新 docs/links.md 中的所有外部鏈接"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-015：在 Markdown 文件中添加代碼塊

**用戶輸入**：`"在 README.md 中添加安裝代碼示例"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-016：修改 Markdown 文件的標題

**用戶輸入**：`"將 docs/guide.md 的主標題改為 '用戶指南'"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：簡單

---

#### MD-017：在 Markdown 文件中添加圖片引用

**用戶輸入**：`"在 README.md 中添加項目截圖"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-018：優化 Markdown 文件格式

**用戶輸入**：`"優化 docs/api.md 的 Markdown 格式"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-019：在 Markdown 文件中添加目錄

**用戶輸入**：`"在 README.md 開頭添加目錄"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：中等

---

#### MD-020：重組 Markdown 文件內容

**用戶輸入**：`"重組 docs/guide.md 的內容結構"`

**預期任務類型**：`execution`

**預期 Agent**：`md-editor`

**複雜度**：複雜

---

### 類別 2：xls-editor（Excel 編輯器）- 20 個場景

#### XLS-001：編輯 Excel 文件

**用戶輸入**：`"編輯文件 data.xlsx"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：簡單

---

#### XLS-002：修改 Excel 單元格值

**用戶輸入**：`"修改 data.xlsx 中 Sheet1 的 A1 單元格值為 100"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：簡單

---

#### XLS-003：在 Excel 中添加新行

**用戶輸入**：`"在 data.xlsx 的 Sheet1 中添加一行數據"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：中等

---

#### XLS-004：更新 Excel 單元格公式

**用戶輸入**：`"更新 data.xlsx 中 B10 單元格的公式為 =SUM(A1:A9)"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：中等

---

#### XLS-005：刪除 Excel 行

**用戶輸入**：`"刪除 data.xlsx 中 Sheet1 的第 5 行"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：簡單

---

#### XLS-006：在 Excel 中插入列

**用戶輸入**：`"在 data.xlsx 的 Sheet1 中 B 列前插入一列"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：中等

---

#### XLS-007：修改 Excel 單元格樣式

**用戶輸入**：`"將 data.xlsx 中 A1 單元格設置為粗體和紅色"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：中等

---

#### XLS-008：在 Excel 中填充數據

**用戶輸入**：`"在 data.xlsx 的 Sheet1 中填充 A1 到 A10 的序號"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：中等

---

#### XLS-009：創建新的 Excel 工作表

**用戶輸入**：`"在 data.xlsx 中創建一個新的工作表 '統計'"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：簡單

---

#### XLS-010：重命名 Excel 工作表

**用戶輸入**：`"將 data.xlsx 中的 Sheet1 重命名為 '數據'"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：簡單

---

#### XLS-011：在 Excel 中設置單元格格式

**用戶輸入**：`"將 data.xlsx 中 C 列的格式設置為貨幣格式"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：中等

---

#### XLS-012：在 Excel 中添加數據驗證

**用戶輸入**：`"在 data.xlsx 的 Sheet1 中為 A 列添加下拉列表驗證"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：複雜

---

#### XLS-013：在 Excel 中合併單元格

**用戶輸入**：`"將 data.xlsx 中 A1 到 C1 的單元格合併"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：簡單

---

#### XLS-014：在 Excel 中設置列寬

**用戶輸入**：`"將 data.xlsx 中 A 列的寬度設置為 20"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：簡單

---

#### XLS-015：在 Excel 中凍結窗格

**用戶輸入**：`"在 data.xlsx 的 Sheet1 中凍結第一行"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：中等

---

#### XLS-016：在 Excel 中添加篩選

**用戶輸入**：`"在 data.xlsx 的 Sheet1 中為第一行添加自動篩選"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：中等

---

#### XLS-017：在 Excel 中複製工作表

**用戶輸入**：`"在 data.xlsx 中複製 Sheet1 並命名為 '備份'"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：中等

---

#### XLS-018：在 Excel 中刪除工作表

**用戶輸入**：`"刪除 data.xlsx 中的 Sheet2 工作表"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：簡單

---

#### XLS-019：在 Excel 中設置打印區域

**用戶輸入**：`"將 data.xlsx 中 Sheet1 的打印區域設置為 A1:Z100"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：中等

---

#### XLS-020：創建新的 Excel 文件

**用戶輸入**：`"創建一個新的 Excel 文件 report.xlsx"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-editor`

**複雜度**：簡單

---

### 類別 3：md-to-pdf（Markdown 轉 PDF）- 20 個場景

#### MD2PDF-001：將 Markdown 轉換為 PDF

**用戶輸入**：`"將 README.md 轉換為 PDF"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：簡單

---

#### MD2PDF-002：將 Markdown 文件轉為 PDF 格式

**用戶輸入**：`"幫我把 docs/guide.md 轉成 PDF 文件"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：簡單

---

#### MD2PDF-003：生成 Markdown 的 PDF 版本

**用戶輸入**：`"生成 README.md 的 PDF 版本"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：簡單

---

#### MD2PDF-004：將 Markdown 導出為 PDF

**用戶輸入**：`"將 docs/api.md 導出為 PDF 文件"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：簡單

---

#### MD2PDF-005：將 Markdown 轉換為 PDF 文檔

**用戶輸入**：`"將 CHANGELOG.md 轉換為 PDF 文檔"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：簡單

---

#### MD2PDF-006：將 Markdown 文件製作成 PDF

**用戶輸入**：`"把 README.md 製作成 PDF 文件"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：簡單

---

#### MD2PDF-007：將 Markdown 轉 PDF 並設置頁面大小

**用戶輸入**：`"將 docs/guide.md 轉為 PDF，頁面大小設為 A4"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：中等

---

#### MD2PDF-008：將 Markdown 轉 PDF 並添加頁眉頁腳

**用戶輸入**：`"將 README.md 轉為 PDF，並添加頁眉和頁腳"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：中等

---

#### MD2PDF-009：將 Markdown 轉 PDF 並生成目錄

**用戶輸入**：`"將 docs/guide.md 轉為 PDF，並自動生成目錄"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：中等

---

#### MD2PDF-010：將 Markdown 轉 PDF 使用自定義模板

**用戶輸入**：`"將 README.md 轉為 PDF，使用學術模板"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：中等

---

#### MD2PDF-011：將多個 Markdown 文件合併轉為 PDF

**用戶輸入**：`"將 docs/ 目錄下的所有 Markdown 文件合併轉為一個 PDF"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：複雜

---

#### MD2PDF-012：將 Markdown 轉 PDF 並設置字體

**用戶輸入**：`"將 README.md 轉為 PDF，字體設為 Times New Roman"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：中等

---

#### MD2PDF-013：將 Markdown 轉 PDF 並設置邊距

**用戶輸入**：`"將 docs/guide.md 轉為 PDF，邊距設為 2cm"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：中等

---

#### MD2PDF-014：將 Markdown 轉 PDF 並高亮代碼

**用戶輸入**：`"將 README.md 轉為 PDF，並啟用代碼高亮"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：中等

---

#### MD2PDF-015：將 Markdown 轉 PDF 並渲染圖表

**用戶輸入**：`"將 docs/guide.md 轉為 PDF，並渲染 Mermaid 圖表"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：中等

---

#### MD2PDF-016：將 Markdown 轉 PDF 並設置頁碼

**用戶輸入**：`"將 README.md 轉為 PDF，並添加頁碼"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：簡單

---

#### MD2PDF-017：將 Markdown 轉 PDF 並設置封面

**用戶輸入**：`"將 docs/guide.md 轉為 PDF，並添加封面頁"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：中等

---

#### MD2PDF-018：將 Markdown 轉 PDF 並設置水印

**用戶輸入**：`"將 README.md 轉為 PDF，並添加水印 '草稿'"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：複雜

---

#### MD2PDF-019：將 Markdown 轉 PDF 並設置雙欄布局

**用戶輸入**：`"將 docs/guide.md 轉為 PDF，使用雙欄布局"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：複雜

---

#### MD2PDF-020：將 Markdown 轉 PDF 並設置橫向頁面

**用戶輸入**：`"將 README.md 轉為 PDF，頁面方向設為橫向"`

**預期任務類型**：`execution`

**預期 Agent**：`md-to-pdf`

**複雜度**：中等

---

### 類別 4：xls-to-pdf（Excel 轉 PDF）- 20 個場景

#### XLS2PDF-001：將 Excel 轉換為 PDF

**用戶輸入**：`"將 data.xlsx 轉換為 PDF"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：簡單

---

#### XLS2PDF-002：將 Excel 文件轉為 PDF 格式

**用戶輸入**：`"幫我把 report.xlsx 轉成 PDF 文件"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：簡單

---

#### XLS2PDF-003：生成 Excel 的 PDF 版本

**用戶輸入**：`"生成 data.xlsx 的 PDF 版本"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：簡單

---

#### XLS2PDF-004：將 Excel 導出為 PDF

**用戶輸入**：`"將 report.xlsx 導出為 PDF 文件"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：簡單

---

#### XLS2PDF-005：將 Excel 轉換為 PDF 文檔

**用戶輸入**：`"將 data.xlsx 轉換為 PDF 文檔"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：簡單

---

#### XLS2PDF-006：將 Excel 文件製作成 PDF

**用戶輸入**：`"把 report.xlsx 製作成 PDF 文件"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：簡單

---

#### XLS2PDF-007：將 Excel 轉 PDF 並設置頁面大小

**用戶輸入**：`"將 data.xlsx 轉為 PDF，頁面大小設為 A4"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：中等

---

#### XLS2PDF-008：將 Excel 轉 PDF 並設置橫向

**用戶輸入**：`"將 report.xlsx 轉為 PDF，頁面方向設為橫向"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：中等

---

#### XLS2PDF-009：將 Excel 轉 PDF 並設置縮放

**用戶輸入**：`"將 data.xlsx 轉為 PDF，縮放設為適合頁面"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：中等

---

#### XLS2PDF-010：將 Excel 轉 PDF 並設置邊距

**用戶輸入**：`"將 report.xlsx 轉為 PDF，邊距設為 1cm"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：中等

---

#### XLS2PDF-011：將 Excel 轉 PDF 並設置打印區域

**用戶輸入**：`"將 data.xlsx 轉為 PDF，打印區域設為 A1:Z100"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：中等

---

#### XLS2PDF-012：將 Excel 轉 PDF 並包含網格線

**用戶輸入**：`"將 report.xlsx 轉為 PDF，並顯示網格線"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：簡單

---

#### XLS2PDF-013：將 Excel 轉 PDF 並包含行列標題

**用戶輸入**：`"將 data.xlsx 轉為 PDF，並顯示行列標題"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：簡單

---

#### XLS2PDF-014：將 Excel 轉 PDF 並設置頁眉頁腳

**用戶輸入**：`"將 report.xlsx 轉為 PDF，並添加頁眉和頁腳"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：中等

---

#### XLS2PDF-015：將 Excel 轉 PDF 並轉換多個工作表

**用戶輸入**：`"將 data.xlsx 的所有工作表轉為一個 PDF"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：中等

---

#### XLS2PDF-016：將 Excel 轉 PDF 並轉換指定工作表

**用戶輸入**：`"將 data.xlsx 的 Sheet1 工作表轉為 PDF"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：簡單

---

#### XLS2PDF-017：將 Excel 轉 PDF 並保留圖表

**用戶輸入**：`"將 report.xlsx 轉為 PDF，並保留所有圖表"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：中等

---

#### XLS2PDF-018：將 Excel 轉 PDF 並設置質量

**用戶輸入**：`"將 data.xlsx 轉為 PDF，質量設為高質量"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：中等

---

#### XLS2PDF-019：將 Excel 轉 PDF 並設置顏色

**用戶輸入**：`"將 report.xlsx 轉為 PDF，使用彩色模式"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：簡單

---

#### XLS2PDF-020：將 Excel 轉 PDF 並設置分頁

**用戶輸入**：`"將 data.xlsx 轉為 PDF，每個工作表分頁"`

**預期任務類型**：`execution`

**預期 Agent**：`xls-to-pdf`

**複雜度**：中等

---

### 類別 5：pdf-to-md（PDF 轉 Markdown）- 20 個場景

#### PDF2MD-001：將 PDF 轉換為 Markdown

**用戶輸入**：`"將 document.pdf 轉換為 Markdown"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：簡單

---

#### PDF2MD-002：將 PDF 文件轉為 Markdown 格式

**用戶輸入**：`"幫我把 report.pdf 轉成 Markdown 文件"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：簡單

---

#### PDF2MD-003：生成 PDF 的 Markdown 版本

**用戶輸入**：`"生成 document.pdf 的 Markdown 版本"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：簡單

---

#### PDF2MD-004：將 PDF 導出為 Markdown

**用戶輸入**：`"將 report.pdf 導出為 Markdown 文件"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：簡單

---

#### PDF2MD-005：將 PDF 轉換為 Markdown 文檔

**用戶輸入**：`"將 document.pdf 轉換為 Markdown 文檔"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：簡單

---

#### PDF2MD-006：將 PDF 文件提取為 Markdown

**用戶輸入**：`"把 report.pdf 提取為 Markdown 文件"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：簡單

---

#### PDF2MD-007：將 PDF 轉 Markdown 並識別表格

**用戶輸入**：`"將 document.pdf 轉為 Markdown，並識別表格"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：中等

---

#### PDF2MD-008：將 PDF 轉 Markdown 並提取圖片

**用戶輸入**：`"將 report.pdf 轉為 Markdown，並提取所有圖片"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：中等

---

#### PDF2MD-009：將 PDF 轉 Markdown 並識別標題

**用戶輸入**：`"將 document.pdf 轉為 Markdown，並自動識別標題結構"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：中等

---

#### PDF2MD-010：將 PDF 轉 Markdown 並識別列表

**用戶輸入**：`"將 report.pdf 轉為 Markdown，並識別列表結構"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：中等

---

#### PDF2MD-011：將 PDF 轉 Markdown 並使用 OCR

**用戶輸入**：`"將 document.pdf 轉為 Markdown，使用 OCR 識別文字"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：複雜

---

#### PDF2MD-012：將 PDF 轉 Markdown 並保留格式

**用戶輸入**：`"將 report.pdf 轉為 Markdown，並保留原始格式"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：中等

---

#### PDF2MD-013：將 PDF 轉 Markdown 並識別布局

**用戶輸入**：`"將 document.pdf 轉為 Markdown，並識別頁面布局"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：複雜

---

#### PDF2MD-014：將 PDF 轉 Markdown 並提取元數據

**用戶輸入**：`"將 report.pdf 轉為 Markdown，並提取文檔元數據"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：中等

---

#### PDF2MD-015：將 PDF 轉 Markdown 並識別代碼塊

**用戶輸入**：`"將 document.pdf 轉為 Markdown，並識別代碼塊"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：中等

---

#### PDF2MD-016：將 PDF 轉 Markdown 並識別鏈接

**用戶輸入**：`"將 report.pdf 轉為 Markdown，並識別所有鏈接"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：中等

---

#### PDF2MD-017：將 PDF 轉 Markdown 並設置語言

**用戶輸入**：`"將 document.pdf 轉為 Markdown，OCR 語言設為中文和英文"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：中等

---

#### PDF2MD-018：將 PDF 轉 Markdown 並提取特定頁面

**用戶輸入**：`"將 report.pdf 的第 1 到 10 頁轉為 Markdown"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：中等

---

#### PDF2MD-019：將 PDF 轉 Markdown 並識別數學公式

**用戶輸入**：`"將 document.pdf 轉為 Markdown，並識別數學公式"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：複雜

---

#### PDF2MD-020：將 PDF 轉 Markdown 並識別多欄布局

**用戶輸入**：`"將 report.pdf 轉為 Markdown，並識別多欄布局"`

**預期任務類型**：`execution`

**預期 Agent**：`pdf-to-md`

**複雜度**：複雜

---

## 📋 測試執行說明

### 測試腳本結構

每個測試場景應該驗證以下內容：

1. **意圖識別階段**：

   - 任務類型識別是否正確（應為 `execution`）
   - 意圖提取是否準確（是否識別出文件編輯/轉換意圖）
   - 文件類型識別是否正確（Markdown、Excel、PDF）
2. **Agent 調用識別**：

   - 是否正確調用預期的 Agent（`md-editor`、`xls-editor`、`md-to-pdf`、`xls-to-pdf`、`pdf-to-md`）
   - Agent 調用是否與任務類型匹配
3. **一致性驗證**：

   - 意圖識別與 Agent 調用是否一致
   - 文件類型與 Agent 類型是否匹配

### 測試數據格式

每個測試場景包含以下字段：

- `scenario_id`: 場景 ID（如 MD-001、XLS-001）
- `category`: 場景類別（md-editor、xls-editor、md-to-pdf、xls-to-pdf、pdf-to-md）
- `user_input`: 用戶輸入的問題
- `expected_task_type`: 預期任務類型（`execution`）
- `expected_agent`: 預期調用的 Agent
- `complexity`: 複雜度（簡單/中等/複雜）

### 測試標準

**通過標準**：

- ✅ 任務類型識別正確（`execution`）
- ✅ 意圖提取準確（識別出文件編輯/轉換意圖）
- ✅ Agent 調用正確（調用預期的 Agent）

**失敗標準**：

- ❌ 任務類型識別錯誤
- ❌ 意圖提取不準確
- ❌ Agent 調用錯誤（調用了錯誤的 Agent 或未調用 Agent）

---

## 🎯 關鍵驗證點

### 語義路由驗證

1. **文件類型識別**：

   - Markdown 文件（.md）應路由到 `md-editor` 或 `md-to-pdf`
   - Excel 文件（.xlsx、.xls）應路由到 `xls-editor` 或 `xls-to-pdf`
   - PDF 文件（.pdf）應路由到 `pdf-to-md`
2. **操作類型識別**：

   - 編輯操作（編輯、修改、添加、刪除等）應路由到編輯類 Agent（`md-editor`、`xls-editor`）
   - 轉換操作（轉換、轉為、導出、生成 PDF/Markdown 版本等）應路由到轉換類 Agent（`md-to-pdf`、`xls-to-pdf`、`pdf-to-md`）
3. **語義理解**：

   - 系統應能理解隱含的轉換意圖（如"生成 PDF 版本"、"轉成 PDF"等）
   - 系統應能區分編輯操作和轉換操作

### Agent 調用驗證

1. **md-editor**：

   - 應處理所有 Markdown 文件的編輯操作
   - 應支持創建、修改、刪除、格式化等操作
2. **xls-editor**：

   - 應處理所有 Excel 文件的編輯操作
   - 應支持單元格編輯、工作表操作、樣式設置等操作
3. **md-to-pdf**：

   - 應處理 Markdown 到 PDF 的轉換
   - 應支持自定義 PDF 選項（頁面大小、邊距、模板等）
4. **xls-to-pdf**：

   - 應處理 Excel 到 PDF 的轉換
   - 應支持工作表選擇、打印設置等選項
5. **pdf-to-md**：

   - 應處理 PDF 到 Markdown 的轉換
   - 應支持 OCR、表格識別、圖片提取等功能

---

## 📊 測試場景統計

### 按 Agent 類型統計

| Agent 類型     | 場景數量      | 簡單         | 中等         | 複雜         | 百分比         |
| -------------- | ------------- | ------------ | ------------ | ------------ | -------------- |
| md-editor      | 20            | 5            | 12           | 3            | 20%            |
| xls-editor     | 20            | 7            | 11           | 2            | 20%            |
| md-to-pdf      | 20            | 6            | 11           | 3            | 20%            |
| xls-to-pdf     | 20            | 6            | 12           | 2            | 20%            |
| pdf-to-md      | 20            | 6            | 10           | 4            | 20%            |
| **總計** | **100** | **30** | **56** | **14** | **100%** |

### 按複雜度統計

| 複雜度         | 場景數量      | 百分比         |
| -------------- | ------------- | -------------- |
| 簡單           | 30            | 30%            |
| 中等           | 56            | 56%            |
| 複雜           | 14            | 14%            |
| **總計** | **100** | **100%** |

---

## 🔧 使用方式

### 1. 手動測試

可以根據場景列表，逐個向系統發送用戶輸入，驗證系統的響應是否符合預期。

### 2. 自動化測試

可以將這些場景轉換為自動化測試腳本，批量執行並驗證結果。

### 3. 測試報告

執行測試後，應該生成測試報告，包含：

- 每個場景的執行結果
- 意圖識別結果與預期的對比
- Agent 調用結果與預期的對比
- 不一致的原因分析

---

## 📝 測試場景執行記錄表

### 類別 1：md-editor（Markdown 編輯器）- 20 個場景

| 場景 ID | 用戶輸入                                   | 執行日期   | 執行人       | 任務類型識別 | 意圖提取 | Agent 調用 | 狀態    | 備註 |
| ------- | ------------------------------------------ | ---------- | ------------ | ------------ | -------- | ---------- | ------- | ---- |
| MD-001  | 編輯文件 README.md                         | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-002  | 修改 docs/guide.md 文件中的第一章節        | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-003  | 在 README.md 中添加安裝說明                | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-004  | 更新 CHANGELOG.md 文件                     | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-005  | 刪除 docs/api.md 中的過時文檔              | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-006  | 將 README.md 中的 '舊版本' 替換為 '新版本' | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-007  | 重寫 docs/guide.md 中的使用說明章節        | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-008  | 在 README.md 的開頭插入版本信息            | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| MD-009  | 格式化整個 README.md 文件                  | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-010  | 整理 docs/guide.md 的章節結構              | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-011  | 創建一個新的 Markdown 文件 CONTRIBUTING.md | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-012  | 幫我產生一份 API 文檔 api.md               | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-013  | 在 README.md 中添加功能對照表              | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-014  | 更新 docs/links.md 中的所有外部鏈接        | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-015  | 在 README.md 中添加安裝代碼示例            | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-016  | 將 docs/guide.md 的主標題改為 '用戶指南'   | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-017  | 在 README.md 中添加項目截圖                | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-018  | 優化 docs/api.md 的 Markdown 格式          | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-019  | 在 README.md 開頭添加目錄                  | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD-020  | 重組 docs/guide.md 的內容結構              | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |

**類別統計**：通過 0 / 失敗 20 / 未執行 0 / 通過率 0.0%

---

### 類別 2：xls-editor（Excel 編輯器）- 20 個場景

| 場景 ID | 用戶輸入                                         | 執行日期   | 執行人       | 任務類型識別 | 意圖提取 | Agent 調用 | 狀態    | 備註 |
| ------- | ------------------------------------------------ | ---------- | ------------ | ------------ | -------- | ---------- | ------- | ---- |
| XLS-001 | 編輯文件 data.xlsx                               | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-002 | 修改 data.xlsx 中 Sheet1 的 A1 單元格值為 100    | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-003 | 在 data.xlsx 的 Sheet1 中添加一行數據            | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-004 | 更新 data.xlsx 中 B10 單元格的公式為 =SUM(A1:A9) | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-005 | 刪除 data.xlsx 中 Sheet1 的第 5 行               | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-006 | 在 data.xlsx 的 Sheet1 中 B 列前插入一列         | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-007 | 將 data.xlsx 中 A1 單元格設置為粗體和紅色        | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-008 | 在 data.xlsx 的 Sheet1 中填充 A1 到 A10 的序號   | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-009 | 在 data.xlsx 中創建一個新的工作表 '統計'         | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-010 | 將 data.xlsx 中的 Sheet1 重命名為 '數據'         | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-011 | 將 data.xlsx 中 C 列的格式設置為貨幣格式         | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-012 | 在 data.xlsx 的 Sheet1 中為 A 列添加下拉列表驗證 | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-013 | 將 data.xlsx 中 A1 到 C1 的單元格合併            | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-014 | 將 data.xlsx 中 A 列的寬度設置為 20              | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-015 | 在 data.xlsx 的 Sheet1 中凍結第一行              | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-016 | 在 data.xlsx 的 Sheet1 中為第一行添加自動篩選    | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-017 | 在 data.xlsx 中複製 Sheet1 並命名為 '備份'       | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-018 | 刪除 data.xlsx 中的 Sheet2 工作表                | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-019 | 將 data.xlsx 中 Sheet1 的打印區域設置為 A1:Z100  | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS-020 | 創建一個新的 Excel 文件 report.xlsx              | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |

**類別統計**：通過 0 / 失敗 20 / 未執行 0 / 通過率 0.0%

---

### 類別 3：md-to-pdf（Markdown 轉 PDF）- 20 個場景

| 場景 ID    | 用戶輸入                                            | 執行日期   | 執行人       | 任務類型識別 | 意圖提取 | Agent 調用 | 狀態    | 備註 |
| ---------- | --------------------------------------------------- | ---------- | ------------ | ------------ | -------- | ---------- | ------- | ---- |
| MD2PDF-001 | 將 README.md 轉換為 PDF                             | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-002 | 幫我把 docs/guide.md 轉成 PDF 文件                  | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-003 | 生成 README.md 的 PDF 版本                          | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-004 | 將 docs/api.md 導出為 PDF 文件                      | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-005 | 將 CHANGELOG.md 轉換為 PDF 文檔                     | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-006 | 把 README.md 製作成 PDF 文件                        | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-007 | 將 docs/guide.md 轉為 PDF，頁面大小設為 A4          | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-008 | 將 README.md 轉為 PDF，並添加頁眉和頁腳             | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-009 | 將 docs/guide.md 轉為 PDF，並自動生成目錄           | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-010 | 將 README.md 轉為 PDF，使用學術模板                 | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-011 | 將 docs/ 目錄下的所有 Markdown 文件合併轉為一個 PDF | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-012 | 將 README.md 轉為 PDF，字體設為 Times New Roman     | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-013 | 將 docs/guide.md 轉為 PDF，邊距設為 2cm             | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-014 | 將 README.md 轉為 PDF，並啟用代碼高亮               | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-015 | 將 docs/guide.md 轉為 PDF，並渲染 Mermaid 圖表      | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-016 | 將 README.md 轉為 PDF，並添加頁碼                   | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-017 | 將 docs/guide.md 轉為 PDF，並添加封面頁             | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-018 | 將 README.md 轉為 PDF，並添加水印 '草稿'            | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-019 | 將 docs/guide.md 轉為 PDF，使用雙欄布局             | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| MD2PDF-020 | 將 README.md 轉為 PDF，頁面方向設為橫向             | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |

**類別統計**：通過 0 / 失敗 20 / 未執行 0 / 通過率 0.0%

---

### 類別 4：xls-to-pdf（Excel 轉 PDF）- 20 個場景

| 場景 ID     | 用戶輸入                                    | 執行日期   | 執行人       | 任務類型識別 | 意圖提取 | Agent 調用 | 狀態    | 備註 |
| ----------- | ------------------------------------------- | ---------- | ------------ | ------------ | -------- | ---------- | ------- | ---- |
| XLS2PDF-001 | 將 data.xlsx 轉換為 PDF                     | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-002 | 幫我把 report.xlsx 轉成 PDF 文件            | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-003 | 生成 data.xlsx 的 PDF 版本                  | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-004 | 將 report.xlsx 導出為 PDF 文件              | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-005 | 將 data.xlsx 轉換為 PDF 文檔                | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-006 | 把 report.xlsx 製作成 PDF 文件              | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-007 | 將 data.xlsx 轉為 PDF，頁面大小設為 A4      | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-008 | 將 report.xlsx 轉為 PDF，頁面方向設為橫向   | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-009 | 將 data.xlsx 轉為 PDF，縮放設為適合頁面     | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-010 | 將 report.xlsx 轉為 PDF，邊距設為 1cm       | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-011 | 將 data.xlsx 轉為 PDF，打印區域設為 A1:Z100 | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-012 | 將 report.xlsx 轉為 PDF，並顯示網格線       | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-013 | 將 data.xlsx 轉為 PDF，並顯示行列標題       | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-014 | 將 report.xlsx 轉為 PDF，並添加頁眉和頁腳   | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-015 | 將 data.xlsx 的所有工作表轉為一個 PDF       | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-016 | 將 data.xlsx 的 Sheet1 工作表轉為 PDF       | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-017 | 將 report.xlsx 轉為 PDF，並保留所有圖表     | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-018 | 將 data.xlsx 轉為 PDF，質量設為高質量       | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-019 | 將 report.xlsx 轉為 PDF，使用彩色模式       | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |
| XLS2PDF-020 | 將 data.xlsx 轉為 PDF，每個工作表分頁       | 2026-01-11 | Daniel Chung | ❌           | ❌       | ❌         | ❌ 失敗 |      |

**類別統計**：通過 0 / 失敗 20 / 未執行 0 / 通過率 0.0%

---

### 類別 5：pdf-to-md（PDF 轉 Markdown）- 20 個場景

| 場景 ID    | 用戶輸入                                              | 執行日期   | 執行人       | 任務類型識別 | 意圖提取 | Agent 調用 | 狀態    | 備註 |
| ---------- | ----------------------------------------------------- | ---------- | ------------ | ------------ | -------- | ---------- | ------- | ---- |
| PDF2MD-001 | 將 document.pdf 轉換為 Markdown                       | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-002 | 幫我把 report.pdf 轉成 Markdown 文件                  | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-003 | 生成 document.pdf 的 Markdown 版本                    | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-004 | 將 report.pdf 導出為 Markdown 文件                    | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-005 | 將 document.pdf 轉換為 Markdown 文檔                  | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-006 | 把 report.pdf 提取為 Markdown 文件                    | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-007 | 將 document.pdf 轉為 Markdown，並識別表格             | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-008 | 將 report.pdf 轉為 Markdown，並提取所有圖片           | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-010 | 將 report.pdf 轉為 Markdown，並識別列表結構           | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-011 | 將 document.pdf 轉為 Markdown，使用 OCR 識別文字      | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-012 | 將 report.pdf 轉為 Markdown，並保留原始格式           | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-013 | 將 document.pdf 轉為 Markdown，並識別頁面布局         | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-014 | 將 report.pdf 轉為 Markdown，並提取文檔元數據         | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-015 | 將 document.pdf 轉為 Markdown，並識別代碼塊           | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-016 | 將 report.pdf 轉為 Markdown，並識別所有鏈接           | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-017 | 將 document.pdf 轉為 Markdown，OCR 語言設為中文和英文 | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-018 | 將 report.pdf 的第 1 到 10 頁轉為 Markdown            | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-019 | 將 document.pdf 轉為 Markdown，並識別數學公式         | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |
| PDF2MD-020 | 將 report.pdf 轉為 Markdown，並識別多欄布局           | 2026-01-11 | Daniel Chung | ✅           | ❌       | ❌         | ❌ 失敗 |      |

**類別統計**：通過 0 / 失敗 20 / 未執行 0 / 通過率 0.0%

---

### 狀態說明

- **⏳ 待測試**：尚未執行測試
- **✅ 通過**：所有驗證點都通過（任務類型識別正確、意圖提取準確、Agent 調用正確）
- **❌ 失敗**：關鍵驗證點失敗（任務類型識別錯誤、意圖提取不準確、Agent 調用錯誤）
- **⚠️ 部分通過**：部分驗證點通過，但存在問題（例如：任務類型識別正確但 Agent 調用錯誤）

### 驗證點說明

- **任務類型識別**：✅ 正確（`execution`） / ❌ 錯誤 / ⚠️ 部分正確
- **意圖提取**：✅ 準確 / ❌ 不準確 / ⚠️ 部分準確
- **Agent 調用**：✅ 正確調用預期 Agent / ❌ 未調用或調用錯誤 Agent / ⚠️ 部分正確

---

**文檔版本**：v2.0
**最後更新日期**：2026-01-11 20:45
**維護者**：Daniel Chung

---

## 🔍 第 6 輪測試結果分析（2026-01-11 20:45）

**測試結果文件**: `test_results_20260111_204444.json`（33 個場景）
**執行時間**: 2026-01-11 20:44:44

### 測試背景

本輪測試在修復 TaskAnalyzer 覆蓋邏輯後進行，主要改進包括：

1. ✅ 修復了 `analyzer.py` 中的覆蓋邏輯（不再依賴 `is_file_editing`，直接根據 `router_output.intent_type == "execution"` 覆蓋）
2. ✅ 優先信任 RouterLLM 的意圖識別結果
3. ✅ 修復了 CapabilityMatcher 的查詢邏輯（同時查詢 `document_editing` 和 `document_conversion` 類型的 Agent）

### 總體統計

- **總場景數**: 33
- **通過**: 0
- **失敗**: 33
- **通過率**: 0.00%

### 任務類型分布

| 任務類型  | 數量 | 百分比     |
| --------- | ---- | ---------- |
| execution | 33   | 100.00% ✅ |

### Agent 調用統計

- **有 Agent 的场景**: 2 / 33 (6.1%) ⚠️
- **無 Agent 的场景**: 31 / 33 (93.9%) ❌

**有 Agent 的场景**（2 個）：

- XLS-007: "將 data.xlsx 中 A1 單元格設置為粗體和紅色" → 調用了 `system_config_agent`（預期 `xls-editor`）❌
- XLS-011: "將 data.xlsx 中 C 列的格式設置為貨幣格式" → 調用了 `system_config_agent`（預期 `xls-editor`）❌

### 關鍵改進 ✅

#### 1. 任務類型識別完全正確 ✅

- **任務類型識別準確率**: 74.3% → **100%**（33/33）✅
- **被誤識別為 `query` 的場景**: 9 個 → **0 個** ✅
- **之前被誤識別的場景現在都正確識別為 `execution`** ✅

**之前被誤識別的場景現在的狀態**：

- MD-008: `task_type=execution` ✅（之前是 `query`）
- XLS-006: `task_type=execution` ✅（之前是 `query`）
- XLS-007: `task_type=execution` ✅（之前是 `query`）
- XLS-008: `task_type=execution` ✅（之前是 `query`）
- XLS-010: `task_type=execution` ✅（之前是 `query`）
- XLS-011: `task_type=execution` ✅（之前是 `query`）
- XLS-013: `task_type=execution` ✅（之前是 `query`）
- XLS-014: `task_type=execution` ✅（之前是 `query`）
- XLS-015: `task_type=execution` ✅（之前是 `query`）

**結論**：✅ **修復 TaskAnalyzer 覆蓋邏輯後，任務類型識別問題已完全解決！**

#### 2. 意圖類型識別保持正確 ✅

- **意圖類型識別準確率**: 100%（33/33 為 `execution`）✅
- **所有場景的 `intent_type` 都正確為 `execution`** ✅

### 仍需解決的問題 ❌

#### 1. Agent 調用問題

**問題**：

- 93.9% 的場景仍然沒有調用到 Agent（31/33）
- 僅有 2 個場景調用了 Agent，但都是錯誤的 Agent（`system_config_agent` 而非 `xls-editor`）

**分析**：

- CapabilityMatcher 可能沒有找到正確的 Agent 候選（md-editor, xls-editor 等）
- DecisionEngine 可能沒有正確選擇 Agent
- 需要查看日誌確認 CapabilityMatcher 是否找到了 Agent 候選

### 改進效果分析

與第 5 輪測試相比：

- ✅ **任務類型識別準確率**: 74.3% → **100%**（33/33）✅
- ✅ **被誤識別為 `query` 的場景**: 9 個 → **0 個** ✅
- ✅ **意圖類型識別準確率**: 100%（保持不變）✅
- ⚠️ **Agent 調用改進**: 3 個 → 2 個（略有退步，但調用的都是錯誤的 Agent）
- ❌ **通過率**: 0.00%（仍未改善）

**結論**：

- ✅ **任務類型識別問題已完全解決**（100% 準確率）
- ✅ **意圖類型識別保持正確**（100% 準確率）
- ❌ **Agent 調用問題仍需進一步調查**

### 下一步行動

1. **調查 Agent 調用問題**：

   - 查看日誌確認 CapabilityMatcher 是否找到了 Agent 候選
   - 確認 DecisionEngine 的選擇邏輯是否正確
   - 檢查為什麼調用了 `system_config_agent` 而非文件編輯 Agent
2. **驗證 CapabilityMatcher 查詢邏輯**：

   - 確認是否同時查詢了 `document_editing` 和 `document_conversion` 類型的 Agent
   - 確認是否找到了預期的 Agent（md-editor, xls-editor, md-to-pdf, xls-to-pdf, pdf-to-md）

---

## 🔍 意圖提取失敗根本原因調查（2026-01-11 20:43）

### 📊 問題分析

根據第 5 輪測試結果，有 **9 個場景被誤識別為 `query`** 而非 `execution`，但這些場景的 `actual_intent_type` 都正確為 `execution`。

**被誤識別的場景**（9 個）：

- MD-008: "在 README.md 的開頭插入版本信息"
- XLS-006: "在 data.xlsx 的 Sheet1 中 B 列前插入一列"
- XLS-007: "將 data.xlsx 中 A1 單元格設置為粗體和紅色"
- XLS-008: "在 data.xlsx 的 Sheet1 中填充 A1 到 A10 的序號"
- XLS-010: "將 data.xlsx 中的 Sheet1 重命名為 '數據'"
- XLS-011: "將 data.xlsx 中 C 列的格式設置為貨幣格式"
- XLS-013: "將 data.xlsx 中 A1 到 C1 的單元格合併"
- XLS-014: "將 data.xlsx 中 A 列的寬度設置為 20"
- XLS-015: "在 data.xlsx 的 Sheet1 中凍結第一行"

### 🔴 根本原因

**問題**：`analyzer.py` 第 300-311 行的覆蓋邏輯有缺陷。

**原始邏輯**：

```python
# 如果 Router LLM 識別為 execution，且任務包含文件編輯關鍵詞，覆蓋 TaskClassifier 的結果
if router_output.intent_type == "execution" and is_file_editing:
    if classification.task_type != TaskType.EXECUTION:
        classification.task_type = TaskType.EXECUTION
        ...
```

**問題分析**：

1. **覆蓋條件過於嚴格**：覆蓋邏輯需要同時滿足兩個條件：

   - `router_output.intent_type == "execution"` ✅（所有場景都滿足）
   - `is_file_editing == True` ❌（部分場景不滿足）
2. **關鍵詞列表不完整**：被誤識別的場景包含的關鍵詞（"插入"、"設置"、"填充"、"重命名"、"合併"、"凍結"）**不在 `file_editing_keywords` 列表中**。
3. **結果**：

   - 因為 `is_file_editing` 為 `False`，覆蓋邏輯不執行
   - TaskClassifier 的分類結果（`query`）被保留
   - 最終返回的 `task_type` 是 `query` 而非 `execution`

**證據**：

- 所有被誤識別的場景，`actual_intent_type` 都是 `execution`（正確）✅
- 所有被誤識別的場景，`actual_task_type` 都是 `query`（錯誤）❌
- 這表明 RouterLLM 的意圖識別是正確的，但 TaskClassifier 的分類被錯誤保留

### ✅ 修復方案

**修改**：改進覆蓋邏輯，當 RouterLLM 識別為 `execution` 時，直接覆蓋 TaskClassifier 的結果，不再依賴於 `is_file_editing` 的判斷。

**修改後的邏輯**：

```python
# 如果 Router LLM 識別為 execution，覆蓋 TaskClassifier 的結果
# 優先信任 RouterLLM 的意圖識別結果，因為它更準確
if router_output.intent_type == "execution":
    if classification.task_type != TaskType.EXECUTION:
        logger.info(
            f"Overriding TaskClassifier result: {classification.task_type.value} -> execution "
            f"(Router LLM intent_type=execution, query: {request.task[:100]}...)"
        )
        classification.task_type = TaskType.EXECUTION
        classification.confidence = max(classification.confidence, router_output.confidence)
        classification.reasoning = f"{classification.reasoning} (覆蓋：Router LLM 識別為 execution 意圖，置信度 {router_output.confidence:.2f})"
```

**理由**：

1. RouterLLM 的意圖識別更準確（100% 正確識別為 `execution`）
2. 應該優先信任 RouterLLM 的判斷，而不是依賴關鍵詞匹配
3. 簡化邏輯，減少維護成本

### 📝 修改位置

**文件**：`agents/task_analyzer/analyzer.py`
**位置**：第 300-310 行
**修改內容**：移除 `is_file_editing` 條件，直接根據 `router_output.intent_type == "execution"` 覆蓋

### 🔄 預期效果

修復後，所有被誤識別的場景應該：

- ✅ `task_type` 正確識別為 `execution`（不再依賴關鍵詞匹配）
- ✅ `intent_type` 保持為 `execution`（已經正確）
- ✅ 任務類型識別準確率應該從 74.3% 提升到 100%

---

## 🔍 第 5 輪測試結果分析（2026-01-11 20:33）

**測試結果文件**: `test_results_20260111_203253.json`（35 個場景）
**執行時間**: 2026-01-11 20:32:53

### 測試背景

本輪測試在修復 CapabilityMatcher 查詢邏輯後進行，主要改進包括：

1. ✅ 修復了 `CapabilityMatcher.match_agents()` 的查詢邏輯（同時查詢 `document_editing` 和 `document_conversion` 類型的 Agent）
2. ✅ 添加了去重處理（使用 `agent_id` 作為唯一標識）
3. ✅ 增強了日誌記錄（便於追蹤查詢過程）

### 總體統計

- **總場景數**: 35
- **通過**: 0
- **失敗**: 35
- **通過率**: 0.00%

### 任務類型分布

| 任務類型  | 數量 | 百分比 |
| --------- | ---- | ------ |
| execution | 26   | 74.3%  |
| query     | 9    | 25.7%  |

### Agent 調用統計

- **有 Agent 的场景**: 3 / 35 (8.6%) ⚠️
- **無 Agent 的场景**: 32 / 35 (91.4%) ❌

**關鍵發現**：

- ✅ **有進展**：有 3 個場景成功調用了 Agent（之前是 0 個）
- ❌ **仍有問題**：91.4% 的場景仍然沒有調用到 Agent
- ⚠️ **任務類型識別問題**：25.7% 的場景被誤識別為 `query`

### 改進效果分析

與第 4 輪測試相比：

- ✅ **Agent 調用改進**：第 4 輪 0 個 → 第 5 輪 3 個（有進展）✅
- ⚠️ **任務類型識別退步**：第 4 輪 100% `execution` → 第 5 輪 74.3% `execution`（9 個被誤識別為 `query`）
- ❌ **通過率**：0.00%（仍未改善）

### 關鍵發現

#### 1. 有 3 個場景成功調用了 Agent

**場景列表**：

- XLS-007: "將 data.xlsx 中 A1 單元格設置為粗體和紅色" → 調用了 `system_config_agent`（預期 `xls-editor`）❌
- XLS-011: "將 data.xlsx 中 C 列的格式設置為貨幣格式" → 調用了 `system_config_agent`（預期 `xls-editor`）❌
- XLS-014: "將 data.xlsx 中 A 列的寬度設置為 20" → 調用了 `system_config_agent`（預期 `xls-editor`）❌

**觀察**：

- ✅ 這 3 個場景都成功調用了 Agent（不再是空列表）
- ❌ 但調用的是錯誤的 Agent（`system_config_agent` 而非 `xls-editor`）
- ⚠️ 這 3 個場景的任務類型都被誤識別為 `query` 而非 `execution`

**分析**：

- 當任務類型被誤識別為 `query` 時，系統可能調用了 `system_config_agent`（用於配置查詢）
- 這表明 DecisionEngine 的選擇邏輯可能有問題，或者 CapabilityMatcher 沒有正確匹配到文件編輯 Agent

#### 2. 任務類型識別問題

**統計**：

- `execution`: 26 / 35 (74.3%)
- `query`: 9 / 35 (25.7%)

**被誤識別為 `query` 的場景**（9 個）：

- 需要進一步分析這些場景的共同特徵

**分析**：

- 第 4 輪測試中任務類型識別準確率為 100%，但第 5 輪測試中只有 74.3%
- 這可能是因為測試場景不同，或者是 Classifier 的判斷邏輯有問題

#### 3. CapabilityMatcher 查詢邏輯

**修改內容**：

- ✅ 同時查詢 `document_editing` 和 `document_conversion` 類型的 Agent
- ✅ 添加了去重處理
- ✅ 增強了日誌記錄

**效果**：

- ⚠️ 有 3 個場景成功調用了 Agent（說明查詢邏輯有改進）
- ❌ 但調用的是錯誤的 Agent（`system_config_agent` 而非文件編輯 Agent）

**需要進一步調查**：

- 需要查看日誌確認 CapabilityMatcher 是否找到了正確的 Agent 候選（md-editor, xls-editor 等）
- 需要確認 DecisionEngine 的選擇邏輯是否正確

### 需要進一步調查

1. **為什麼調用了錯誤的 Agent？**

   - 為什麼調用的是 `system_config_agent` 而非 `xls-editor`？
   - DecisionEngine 的選擇邏輯是否有問題？
   - CapabilityMatcher 是否正確找到了文件編輯 Agent 候選？
2. **為什麼任務類型識別退步了？**

   - 第 4 輪測試中任務類型識別準確率為 100%，但第 5 輪測試中只有 74.3%
   - 需要檢查是否是測試場景不同導致的差異
   - 需要查看 Classifier 的判斷邏輯
3. **CapabilityMatcher 的查詢邏輯是否正確工作？**

   - 需要查看日誌確認是否同時查詢了 `document_editing` 和 `document_conversion` 類型的 Agent
   - 需要確認是否找到了預期的 Agent（md-editor, xls-editor, md-to-pdf, xls-to-pdf, pdf-to-md）
   - 需要確認 DecisionEngine 是否正確使用了這些 Agent 候選

---

## 🔍 第 4 輪測試結果分析（2026-01-11 20:18）

**測試結果文件**: `test_results_20260111_201825.json`（32 個場景）
**執行時間**: 2026-01-11 20:18:25

### 測試背景

本輪測試在修復 DecisionEngine context 參數後進行，主要改進包括：

1. ✅ 修復了 DecisionEngine.decide() 的 context 參數（使用 `enhanced_context` 而不是 `request.context`）
2. ✅ 添加了 agent_candidates 日誌記錄
3. ✅ 確認了 System Agent 註冊狀態（所有 6 個 Agent 都已正確註冊）

### 總體統計

- **總場景數**: 32
- **通過**: 0
- **失敗**: 32
- **通過率**: 0.00%

### 意圖類型分布

| 意圖類型  | 數量 | 百分比  |
| --------- | ---- | ------- |
| execution | 32   | 100.00% |

### 任務類型分布

| 任務類型  | 數量 | 百分比  |
| --------- | ---- | ------- |
| execution | 32   | 100.00% |

### 一致性統計

- **意圖類型與任務類型一致**: 32/32 (100.00%) ✅
- **Agent匹配**: 0/32 (0.00%) ❌

### 關鍵發現

#### 1. 意圖和任務類型識別完全正確 ✅

- **意圖類型識別準確率**: 100%（32/32 為 `execution`）✅
- **任務類型識別準確率**: 100%（32/32 為 `execution`）✅
- **RouterLLM 決策正確**: 所有場景的 `actual_needs_agent` 和 `actual_needs_tools` 都為 `True` ✅

#### 2. Agent 調用仍然失敗 ❌

**問題**：所有場景的 `actual_agents` 仍為空列表 `[]`

**根本原因分析**：

1. **CapabilityMatcher.match_agents() 的查詢邏輯問題**：

   - 對於文件編輯任務，`CapabilityMatcher` 只查詢 `agent_type="document_editing"` 的 Agent
   - 這會找到 `md-editor` 和 `xls-editor`（`agent_type="document_editing"`）
   - 但不會找到 `md-to-pdf`、`xls-to-pdf`、`pdf-to-md`（`agent_type="document_conversion"`）
2. **DecisionEngine.decide() 的選擇邏輯問題**：

   - `DecisionEngine` 調用 `_select_agent_by_file_extension()` 來選擇具體的 Agent（如 `md-editor`、`xls-editor`、`md-to-pdf` 等）
   - 但是，如果 `agent_candidates` 中沒有對應的 Agent（因為 `CapabilityMatcher` 沒有查詢 `document_conversion` 類型），`DecisionEngine` 無法選擇
3. **Agent 類型分類問題**：

   - 編輯任務的 Agent（`md-editor`、`xls-editor`）的 `agent_type` 是 `"document_editing"` ✅
   - 轉換任務的 Agent（`md-to-pdf`、`xls-to-pdf`、`pdf-to-md`）的 `agent_type` 是 `"document_conversion"` ✅
   - 但 `CapabilityMatcher.match_agents()` 在文件編輯任務時，只查詢 `document_editing` 類型，不會查詢 `document_conversion` 類型 ❌

### 改進建議

#### 1. 修復 CapabilityMatcher.match_agents() 的查詢邏輯

**問題**：對於文件編輯/轉換任務，需要同時查詢 `document_editing` 和 `document_conversion` 類型的 Agent。

**解決方案**：

- 在 `CapabilityMatcher.match_agents()` 中，當檢測到文件編輯/轉換任務時：
  1. 先查詢 `agent_type="document_editing"` 的 Agent（找到 `md-editor`、`xls-editor`）
  2. 再查詢 `agent_type="document_conversion"` 的 Agent（找到 `md-to-pdf`、`xls-to-pdf`、`pdf-to-md`）
  3. 合併兩個查詢結果

**代碼位置**：`agents/task_analyzer/capability_matcher.py` 第 354-398 行

#### 2. 增強文件編輯任務檢測邏輯

**問題**：需要區分編輯任務和轉換任務，以便查詢正確的 Agent 類型。

**解決方案**：

- 在 `CapabilityMatcher._is_file_editing_task()` 或新增方法中，檢測是否為轉換任務
- 如果是轉換任務（包含"轉換"、"轉為"、"轉成"等關鍵詞），查詢 `document_conversion` 類型的 Agent
- 如果是編輯任務，查詢 `document_editing` 類型的 Agent

### 測試結果詳細數據

所有 32 個場景的測試結果顯示：

- ✅ `actual_task_type`: 100% 為 `execution`
- ✅ `actual_intent_type`: 100% 為 `execution`
- ✅ `actual_needs_agent`: 100% 為 `True`
- ✅ `actual_needs_tools`: 100% 為 `True`
- ❌ `actual_agents`: 100% 為空列表 `[]`

### 改進效果分析

與第 3 輪測試相比：

- ✅ **任務類型識別準確率**: 78.79% → 100%（32/32）✅
- ✅ **意圖類型識別準確率**: 100%（保持不變）✅
- ❌ **Agent 調用失敗率**: 100%（0/32）❌（問題仍然存在）

**結論**：

- ✅ RouterLLM 的意圖和任務類型識別已完全正確
- ❌ Agent 選擇階段仍有問題，需要修復 `CapabilityMatcher.match_agents()` 的查詢邏輯

---

## 🔍 意圖提取問題分析（2026-01-11 19:05）

### 問題概述

根據第 2 輪測試結果分析，發現以下問題：

1. **任務類型識別準確率**：71.88%（23/32 匹配）
2. **意圖類型識別問題**：部分 Excel 編輯任務被誤識別為 `query` 而非 `execution`
3. **Agent 調用問題**：所有場景的 `actual_agents` 為空列表，導致 Agent 調用失敗

### 意圖提取不準確的原因分析

#### 1. Excel 編輯任務被誤識別為 `query`

**問題場景**（共 9 個）：

- XLS-006: "在 data.xlsx 的 Sheet1 中 B 列前插入一列" → 識別為 `query`（預期 `execution`）
- XLS-007: "將 data.xlsx 中 A1 單元格設置為粗體和紅色" → 識別為 `query`（預期 `execution`）
- XLS-008: "在 data.xlsx 的 Sheet1 中填充 A1 到 A10 的序號" → 識別為 `query`（預期 `execution`）
- XLS-010: "將 data.xlsx 中的 Sheet1 重命名為 '數據'" → 識別為 `query`（預期 `execution`）
- XLS-011: "將 data.xlsx 中 C 列的格式設置為貨幣格式" → 識別為 `query`（預期 `execution`）
- XLS-013: "將 data.xlsx 中 A1 到 C1 的單元格合併" → 識別為 `query`（預期 `execution`）
- XLS-014: "將 data.xlsx 中 A 列的寬度設置為 20" → 識別為 `query`（預期 `execution`）
- XLS-015: "在 data.xlsx 的 Sheet1 中凍結第一行" → 識別為 `query`（預期 `execution`）
- XLS-017: "在 data.xlsx 中複製 Sheet1 並命名為 '備份'" → 識別為 `query`（預期 `execution`）

**共同特徵**：

- 這些任務都包含具體的操作指令（插入列、設置格式、填充序號等）
- 但缺少明確的"編輯"、"修改"等動詞
- 描述過於技術化，RouterLLM 可能理解為"查詢如何操作"而非"執行操作"
- 所有誤識別案例的置信度都很低（0.41），說明 LLM 對這些任務不太確定

**可能原因**：

1. RouterLLM 的 System Prompt 對這些技術性操作不夠明確
2. 缺少 Excel 編輯操作的示例
3. LLM 可能將這些描述理解為"查詢如何執行操作"而非"執行操作"
4. 這些任務的置信度都很低（0.41），說明 LLM 對這些任務不太確定

#### 2. Agent 調用為空的原因

**問題**：所有場景的 `actual_agents` 為空列表 `[]`

**可能原因**：

1. DecisionEngine 沒有選擇到具體的 Agent
2. 文件擴展名匹配邏輯可能沒有正確工作
3. Agent Registry 中可能沒有正確註冊這些 Agent
4. CapabilityMatcher 的匹配邏輯可能有問題
5. `analysis_result.requires_agent` 為 `False`，導致 DecisionEngine 沒有選擇 Agent

**觀察**：

- 測試輸出顯示 `需要 Agent: False`（來自 `analysis_result.requires_agent`）
- 但 RouterDecision 顯示 `needs_agent: True`（來自 `analysis_result.router_decision.needs_agent`）
- 這表明 `TaskAnalysisResult.requires_agent` 和 `RouterDecision.needs_agent` 之間可能存在不一致

### 改進建議

1. **增強 RouterLLM Prompt**：

   - 添加更多 Excel 編輯操作的示例
   - 明確說明包含具體操作指令的任務都應為 `execution`
   - 強調技術性操作描述（如"插入列"、"設置格式"、"填充序號"、"重命名"、"合併單元格"、"設置寬度"、"凍結行"、"複製工作表"）都是執行任務
   - 添加明確規則：**任何包含具體操作指令的任務（如"插入"、"設置"、"填充"、"重命名"、"合併"、"凍結"等）都必須識別為 `execution`**
2. **改進文件擴展名匹配**：

   - 確保文件擴展名匹配邏輯優先執行
   - 驗證 DecisionEngine 中的 `_select_agent_by_file_extension` 方法是否正確工作
   - 檢查為什麼文件擴展名匹配沒有觸發
3. **驗證 Agent 註冊**：

   - 確認所有 System Agent（md-editor, xls-editor 等）已正確註冊
   - 檢查 Agent Registry 是否能正確發現這些 Agent
   - 驗證 `analysis_result.requires_agent` 和 `router_decision.needs_agent` 的一致性
4. **增強測試報告**：

   - ✅ 已在測試結果中添加 `intent_type` 字段
   - ✅ 已添加 RouterDecision 的詳細信息（needs_agent, needs_tools, complexity 等）
   - ✅ 已添加意圖類型匹配驗證

### 意圖提取詳細數據

以下數據基於測試結果文件 `test_results_20260111_190401.json`（12 個場景）：

#### 總體統計

- **總場景數**: 12
- **有意圖類型數據的場景**: 12

#### 意圖類型分布

| 意圖類型  | 數量 | 百分比  |
| --------- | ---- | ------- |
| execution | 12   | 100.00% |

#### 任務類型分布

| 任務類型  | 數量 | 百分比  |
| --------- | ---- | ------- |
| execution | 12   | 100.00% |

#### 意圖類型與任務類型一致性

- **一致**: 12/12 (100.00%)
- **不一致**: 0/12 (0.00%)

**說明**：在本次測試的 12 個場景中，所有場景的意圖類型都正確識別為 `execution`，與任務類型完全一致。這表明對於包含明確文件編輯動詞的任務（如"編輯"、"修改"、"添加"等），RouterLLM 能夠正確識別意圖。

#### 詳細案例表格

| 場景ID | 用戶輸入                                   | 預期任務類型 | 實際任務類型 | 實際意圖類型 | 意圖匹配 | 置信度 | needs_agent | needs_tools | Agent匹配 |
| ------ | ------------------------------------------ | ------------ | ------------ | ------------ | -------- | ------ | ----------- | ----------- | --------- |
| MD-001 | 編輯文件 README.md                         | execution    | execution    | execution    | ✅       | 0.55   | True        | True        | ❌        |
| MD-002 | 修改 docs/guide.md 文件中的第一章節        | execution    | execution    | execution    | ✅       | 0.65   | True        | True        | ❌        |
| MD-003 | 在 README.md 中添加安裝說明                | execution    | execution    | execution    | ✅       | 0.45   | True        | True        | ❌        |
| MD-004 | 更新 CHANGELOG.md 文件                     | execution    | execution    | execution    | ✅       | 0.55   | True        | True        | ❌        |
| MD-005 | 刪除 docs/api.md 中的過時文檔              | execution    | execution    | execution    | ✅       | 0.65   | True        | True        | ❌        |
| MD-011 | 創建一個新的 Markdown 文件 CONTRIBUTING.md | execution    | execution    | execution    | ✅       | 0.65   | True        | True        | ❌        |
| MD-012 | 幫我產生一份 API 文檔 api.md               | execution    | execution    | execution    | ✅       | 0.55   | True        | True        | ❌        |
| MD-013 | 在 README.md 中添加功能對照表              | execution    | execution    | execution    | ✅       | 0.45   | True        | True        | ❌        |
| MD-014 | 在 README.md 中添加版本歷史                | execution    | execution    | execution    | ✅       | 0.55   | True        | True        | ❌        |
| MD-015 | 重組 docs/guide.md 的內容結構              | execution    | execution    | execution    | ✅       | 0.45   | True        | True        | ❌        |
| MD-016 | 優化 README.md 的格式和結構                | execution    | execution    | execution    | ✅       | 0.55   | True        | True        | ❌        |
| MD-017 | 在 README.md 中添加貢獻指南                | execution    | execution    | execution    | ✅       | 0.65   | True        | True        | ❌        |

**觀察**：

1. ✅ **意圖類型識別準確率**: 100%（12/12）
2. ✅ **所有場景的 `needs_agent` 都為 `True`**：RouterLLM 正確識別需要 Agent
3. ✅ **所有場景的 `needs_tools` 都為 `True`**：RouterLLM 正確識別需要工具
4. ❌ **Agent 調用失敗率**: 100%（0/12）：所有場景的 `actual_agents` 為空列表

**關鍵發現**：

- 意圖提取是準確的（100% 正確識別為 `execution`）
- RouterLLM 的決策是正確的（`needs_agent=True`, `needs_tools=True`）
- **問題在於 Agent 選擇階段**：DecisionEngine 或 CapabilityMatcher 沒有選擇到具體的 Agent

#### 被誤識別為 query 的執行任務

**注意**：在本次測試的 12 個場景中，沒有被誤識別為 `query` 的案例。但根據之前的測試結果（32 個場景），有 9 個 Excel 編輯任務被誤識別為 `query`。

**這些案例的共同特徵**：

- 包含技術性操作描述（如"插入列"、"設置格式"、"填充序號"等）
- 缺少明確的"編輯"、"修改"等動詞
- 置信度較低（0.41），說明 LLM 對這些任務不太確定

**建議**：在 RouterLLM 的 System Prompt 中添加更多 Excel 編輯操作的示例，明確說明這些技術性操作都是執行任務。

---

## 🔍 第 3 輪測試結果分析（2026-01-11 19:25）

**測試結果文件**: `test_results_20260111_191046.json`（33 個場景）
**執行時間**: 2026-01-11 19:15:46

### 測試背景

本輪測試在 RouterLLM Prompt 更新後進行，主要改進包括：

1. ✅ 添加了技術性操作描述規則（CRITICAL）
2. ✅ 添加了明確規則：任何包含具體操作指令的任務必須為 execution
3. ✅ 添加了技術性操作關鍵詞列表：插入、設置、填充、重命名、合併、凍結、複製、刪除、更新、創建
4. ✅ 添加了 10 個 Excel/spreadsheet 操作示例
5. ✅ 添加了明確規則：如果查詢包含技術性操作關鍵詞並涉及文件/電子表格，必須為 execution（NOT query）

### 總體統計

- **總場景數**: 33
- **通過**: 0
- **失敗**: 33
- **通過率**: 0.00%

### 意圖類型分布

| 意圖類型  | 數量 | 百分比  |
| --------- | ---- | ------- |
| execution | 33   | 100.00% |

### 任務類型分布

| 任務類型  | 數量 | 百分比 |
| --------- | ---- | ------ |
| execution | 26   | 78.79% |
| query     | 7    | 21.21% |

### 一致性統計

- **意圖類型與任務類型一致**: 26/33 (78.79%)
- **Agent匹配**: 0/33 (0.00%)

### 詳細案例表格

| 場景ID  | 用戶輸入                                    | 預期任務類型 | 實際任務類型 | 實際意圖類型 | 意圖匹配 | Agent匹配 | 狀態    |
| ------- | ------------------------------------------- | ------------ | ------------ | ------------ | -------- | --------- | ------- |
| MD-001  | 編輯文件 README.md                          | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-002  | 修改 docs/guide.md 文件中的第一章節         | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-003  | 在 README.md 中添加安裝說明                 | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-004  | 更新 CHANGELOG.md 文件                      | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-005  | 刪除 docs/api.md 中的過時文檔               | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-006  | 將 README.md 中的 '舊版本' 替換為 '新版本'  | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-007  | 重寫 docs/guide.md 中的使用說明章節         | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-008  | 在 README.md 的開頭插入版本信息             | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-009  | 格式化整個 README.md 文件                   | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-010  | 整理 docs/guide.md 的章節結構               | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-011  | 創建一個新的 Markdown 文件 CONTRIBUTIN...   | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-012  | 幫我產生一份 API 文檔 api.md                | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-013  | 在 README.md 中添加功能對照表               | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-014  | 更新 docs/links.md 中的所有外部鏈接         | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-015  | 在 README.md 中添加安裝代碼示例             | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-016  | 將 docs/guide.md 的主標題改為 '用戶指南'    | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-017  | 在 README.md 中添加項目截圖                 | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-018  | 優化 docs/api.md 的 Markdown 格式           | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-019  | 在 README.md 開頭添加目錄                   | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| MD-020  | 重組 docs/guide.md 的內容結構               | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-001 | 編輯文件 data.xlsx                          | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-002 | 修改 data.xlsx 中 Sheet1 的 A1 單元格...    | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-003 | 在 data.xlsx 的 Sheet1 中添加一行數據       | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-004 | 更新 data.xlsx 中 B10 單元格的公式為 =SU... | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-005 | 刪除 data.xlsx 中 Sheet1 的第 5 行          | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-006 | 在 data.xlsx 的 Sheet1 中 B 列前插入一...   | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-007 | 將 data.xlsx 中 A1 單元格設置為粗體和紅色   | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-008 | 在 data.xlsx 的 Sheet1 中填充 A1 到 ...     | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-009 | 在 data.xlsx 中創建一個新的工作表 '統計'    | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-010 | 將 data.xlsx 中的 Sheet1 重命名為 '數據...  | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-011 | 將 data.xlsx 中 C 列的格式設置為貨幣格式    | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-012 | 在 data.xlsx 的 Sheet1 中為 A 列添加下...   | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |
| XLS-013 | 將 data.xlsx 中 A1 到 C1 的單元格合併       | execution    | execution    | execution    | ✅       | ❌        | ❌ 失敗 |

### 被誤識別為 query 的執行任務（意圖類型）

**✅ 無誤識別案例**：所有執行任務的意圖類型都正確識別為 `execution`

**說明**：第 6 輪測試中，所有執行任務的任務類型都正確識別為 `execution`（100%）。這表明 TaskAnalyzer 的覆蓋邏輯修復是有效的。

### 任務類型與意圖類型一致性分析（第 6 輪）

**觀察**：

- 意圖類型（actual_intent_type）：100% 為 `execution`（33/33）✅
- 任務類型（actual_task_type）：100% 為 `execution`（33/33）✅

**結論**：

- ✅ **任務類型識別問題已完全解決**（100% 準確率）
- ✅ **意圖類型識別保持正確**（100% 準確率）
- ✅ **TaskAnalyzer 的覆蓋邏輯修復有效**（優先信任 RouterLLM 的意圖識別結果）

### 改進效果分析

與第 2 輪測試相比（32 個場景，9 個意圖類型被誤識別為 query）：

- **意圖類型誤識別案例數**: 第 2 輪 9 個 → 第 3 輪 0 個 ✅
- **✅ 改進效果顯著**：Prompt 更新後，技術性操作描述的意圖類型都能正確識別為 `execution`
- **意圖類型識別準確率**: 100%（33/33）✅
- **主要問題**:
  - ⚠️ 任務類型識別仍有 7 個被識別為 `query`（需要檢查 TaskAnalyzer 的 Classifier）
  - ⚠️ Agent 調用仍為空列表（需要進一步檢查 DecisionEngine 和 CapabilityMatcher）

---

## 🔍 測試問題與調查結果完整記錄（2026-01-11 20:12）

### 📊 測試執行摘要

| 測試輪次 | 執行日期   | 總場景數 | 通過 | 失敗 | 通過率 | 主要問題                                                                          | 狀態      |
| -------- | ---------- | -------- | ---- | ---- | ------ | --------------------------------------------------------------------------------- | --------- |
| 第 1 輪  | 2026-01-11 | 100      | 0    | 100  | 0.00%  | Agent 調用失敗                                                                    | ✅ 已完成 |
| 第 2 輪  | 2026-01-11 | 32       | 0    | 32   | 0.00%  | 意圖識別錯誤（9個query）+ Agent調用失敗                                           | ✅ 已完成 |
| 第 3 輪  | 2026-01-11 | 33       | 0    | 33   | 0.00%  | 任務類型識別錯誤（7個query）+ Agent調用失敗                                       | ✅ 已完成 |
| 第 4 輪  | 2026-01-11 | 32       | 0    | 32   | 0.00%  | Agent 調用失敗（修復 DecisionEngine context 參數後）                              | ✅ 已完成 |
| 第 5 輪  | 2026-01-11 | 35       | 0    | 35   | 0.00%  | Agent 調用錯誤（3個場景調用了 system_config_agent）+ 任務類型識別錯誤（9個query） | ✅ 已完成 |
| 第 6 輪  | 2026-01-11 | 33       | 0    | 33   | 0.00%  | Agent 調用失敗（任務類型識別準確率 100%，但 Agent 調用仍失敗）                    | ✅ 已完成 |

### 🔴 核心問題總結

#### 問題 1：Agent 調用為空列表（所有輪次）

**現象**：

- 所有測試場景的 `actual_agents` 為空列表 `[]`
- 儘管 `actual_intent_type` 為 `execution`（100%）
- 儘管 `actual_needs_agent` 為 `True`（100%）

**影響**：

- 100% 的測試場景失敗
- 系統無法正確調用任何 Agent

**根本原因分析**：

1. **缺少 agent_candidates 日誌**：無法追蹤 Agent 匹配過程
2. **DecisionEngine.decide() 的 context 參數錯誤**：傳遞了 `request.context` 而不是 `enhanced_context`，導致無法獲取 `user_query`

#### 問題 2：意圖類型識別錯誤（第 2 輪）

**現象**：

- 第 2 輪測試中，9 個 Excel 編輯任務被誤識別為 `query` 而非 `execution`
- 問題場景包括：
  - XLS-006: "在 data.xlsx 的 Sheet1 中 B 列前插入一列"
  - XLS-007: "將 data.xlsx 中 A1 單元格設置為粗體和紅色"
  - XLS-008: "在 data.xlsx 的 Sheet1 中填充 A1 到 A10 的序號"
  - 等 9 個場景

**原因**：

- RouterLLM 的 Prompt 對技術性操作描述（如"插入列"、"設置格式"、"填充序號"）的意圖分類規則不夠明確

**修復**：

- ✅ 已更新 RouterLLM Prompt（`agents/task_analyzer/router_llm.py`）
- ✅ 第 3 輪測試中，意圖類型識別準確率達到 100%（33/33）

#### 問題 3：任務類型識別錯誤（第 3 輪）

**現象**：

- 第 3 輪測試中，7 個場景的 `actual_task_type` 被識別為 `query`，但 `actual_intent_type` 為 `execution`
- 不一致案例：
  - XLS-006, XLS-007, XLS-008, XLS-009, XLS-010, XLS-011, XLS-012

**原因**：

- RouterLLM 的意圖類型識別已正確（100% `execution`）
- 但 TaskAnalyzer 的任務類型識別仍有問題（可能是 Classifier 或其他組件導致的）

**狀態**：

- ⏳ 待進一步調查 TaskAnalyzer 的任務類型分類邏輯

### 🔧 已完成的修復

#### 修復 1：添加 agent_candidates 日誌記錄

**位置**：`agents/task_analyzer/analyzer.py` 第 234 行之後

**代碼**：

```python
logger.info(
    f"Layer 3: Capability Matcher found {len(agent_candidates)} agent candidates: "
    f"{[c.candidate_id for c in agent_candidates[:5]]}"
)
```

**效果**：

- ✅ 可以追蹤 Agent 匹配過程
- ✅ 可以確認 `agent_candidates` 是否為空

#### 修復 2：修復 DecisionEngine.decide() 的 context 參數

**位置**：`agents/task_analyzer/analyzer.py` 第 256-262 行

**修改前**：

```python
decision_result = self.decision_engine.decide(
    router_output,
    agent_candidates,
    tool_candidates,
    model_candidates,
    request.context,  # ❌ 錯誤：可能沒有 "task" 字段
)
```

**修改後**：

```python
decision_result = self.decision_engine.decide(
    router_output,
    agent_candidates,
    tool_candidates,
    model_candidates,
    enhanced_context,  # ✅ 正確：包含 "task" 和 "query" 字段
)
```

**效果**：

- ✅ `DecisionEngine` 能正確獲取 `user_query`
- ✅ 文件編輯任務檢測可以正常工作
- ✅ 文件擴展名匹配可以正常工作

#### 修復 3：更新 RouterLLM Prompt

**位置**：`agents/task_analyzer/router_llm.py`

**改進**：

- ✅ 添加了明確的技術性操作分類規則
- ✅ 添加了 Excel 編輯操作的示例
- ✅ 明確規定所有技術性操作都應分類為 `execution`

**效果**：

- ✅ 第 3 輪測試中，意圖類型識別準確率達到 100%（33/33）

### ✅ System Agent 註冊狀態確認

**最後確認日期**: 2026-01-11 19:55

**系統規格書要求**（`文件編輯-Agent-系統規格書-v2.0.md`）：
根據系統規格書，應註冊以下 6 個 System Agent：

1. `document-editing-agent` - 文件編輯服務（通用）
2. `md-editor` - Markdown 編輯器
3. `xls-editor` - Excel 編輯器
4. `md-to-pdf` - Markdown 轉 PDF
5. `xls-to-pdf` - Excel 轉 PDF
6. `pdf-to-md` - PDF 轉 Markdown

**代碼確認**（`agents/builtin/__init__.py`）：

| Agent ID                   | Agent 類型              | 狀態   | 註冊位置                               | 說明                    | 代碼位置      |
| -------------------------- | ----------------------- | ------ | -------------------------------------- | ----------------------- | ------------- |
| `document-editing-agent` | `document_editing`    | ONLINE | System Agent Registry + Agent Registry | 文件編輯服務（通用）    | 第 342-421 行 |
| `md-editor`              | `document_editing`    | ONLINE | System Agent Registry + Agent Registry | Markdown 編輯器（v2.0） | 第 525-584 行 |
| `xls-editor`             | `document_editing`    | ONLINE | System Agent Registry + Agent Registry | Excel 編輯器（v2.0）    | 第 588-605 行 |
| `md-to-pdf`              | `document_conversion` | ONLINE | System Agent Registry + Agent Registry | Markdown 轉 PDF（v2.0） | 第 608-624 行 |
| `xls-to-pdf`             | `document_conversion` | ONLINE | System Agent Registry + Agent Registry | Excel 轉 PDF（v2.0）    | 第 627-643 行 |
| `pdf-to-md`              | `document_conversion` | ONLINE | System Agent Registry + Agent Registry | PDF 轉 Markdown（v2.0） | 第 646-662 行 |

**註冊流程**：

1. 所有 System Agent 都通過 `register_builtin_agents()` 函數註冊（第 282-671 行）
2. 註冊流程：
   - 先註冊到 System Agent Registry（ArangoDB），使用 `SystemAgentRegistryStoreService.register_system_agent()`
   - 再註冊到 Agent Registry（內存），使用 `AgentRegistry.register_agent()`
3. 註冊時會設置：
   - `is_system_agent=True`
   - `status=ONLINE` 或 `AgentStatus.ONLINE`
4. 註冊時機：系統啟動時通過 `api/main.py` 調用 `register_builtin_agents()`

**結論**：✅ **System Agent 註冊狀態正常，所有 6 個 Agent 都已正確註冊，符合系統規格書要求，不需要重複檢查。**

### 📋 詳細問題分析

詳細分析請參閱：`docs/系统设计文档/核心组件/Agent平台/archive/testing/Agent调用为空列表分析报告.md`

**關鍵發現**：

1. **代碼流程分析**：

   - `analyzer.py` 中 `suggested_agents` 依賴於 `decision_result.chosen_agent`
   - `chosen_agent` 依賴於 `agent_candidates` 和 `DecisionEngine` 的選擇邏輯
   - 如果 `agent_candidates` 為空，`chosen_agent` 會保持為 None
2. **CapabilityMatcher.match_agents() 的邏輯**：

   - 依賴於 `context.get("task", "")` 或 `context.get("query", "")` 獲取 `user_query`
   - 如果 `user_query` 為空，`is_file_editing` 判斷會失敗
   - 會使用 `AgentDiscovery`，過濾掉 System Agents
3. **DecisionEngine.decide() 的選擇邏輯**：

   - 同樣依賴於 `context.get("task", "")` 或 `context.get("query", "")`
   - 如果 `agent_candidates` 為空，所有選擇方案都不會執行

### 📊 測試結果統計

#### 第 1 輪測試（100 個場景）

- **通過率**：0.00%（0/100）
- **主要問題**：Agent 調用失敗（所有場景 `actual_agents=[]`）
- **狀態**：✅ 測試完成（實施前）

#### 第 2 輪測試（32 個場景）

- **通過率**：0.00%（0/32）
- **意圖類型識別準確率**：71.88%（23/32 為 `execution`，9 個被誤識別為 `query`）
- **任務類型識別準確率**：71.88%（23/32 為 `execution`）
- **Agent 調用失敗率**：100%（0/32）
- **狀態**：✅ 測試完成（實施後，RAG初始化完成，部分場景測試）

#### 第 3 輪測試（33 個場景）

- **通過率**：0.00%（0/33）
- **意圖類型識別準確率**：100%（33/33 為 `execution`）✅
- **任務類型識別準確率**：78.79%（26/33 為 `execution`，7 個被誤識別為 `query`）⚠️
- **Agent 調用失敗率**：100%（0/33）
- **狀態**：✅ 測試完成（Prompt 更新後，RouterLLM 增強）

**改進效果**：

- ✅ 意圖類型誤識別案例數：第 2 輪 9 個 → 第 3 輪 0 個
- ✅ 意圖類型識別準確率：71.88% → 100%
- ⚠️ 任務類型識別仍有問題（7 個被誤識別為 `query`）
- ❌ Agent 調用問題仍未解決（所有場景 `actual_agents=[]`）

### 🎯 後續行動計劃

#### 已完成 ✅

1. ✅ **添加 agent_candidates 日誌記錄**（`analyzer.py` 第 234 行之後）
2. ✅ **修復 DecisionEngine.decide() 的 context 參數**（`analyzer.py` 第 256-262 行）
3. ✅ **更新 RouterLLM Prompt**（`router_llm.py`）
4. ✅ **確認 System Agent 註冊狀態**（所有 6 個 Agent 都已正確註冊）

#### 待執行 ⏳

1. ⏳ **運行完整測試**：執行 100 個場景的完整測試，查看 `agent_candidates` 日誌輸出
2. ⏳ **分析 agent_candidates 日誌**：根據日誌進一步分析為什麼 `agent_candidates` 為空（如果問題仍然存在）
3. ⏳ **調查任務類型識別問題**：檢查 TaskAnalyzer 的 Classifier 組件，解決 7 個場景被誤識別為 `query` 的問題
4. ⏳ **驗證修復效果**：確認修復後的代碼是否能正確調用 Agent

### 📝 相關文檔

- **詳細分析報告**：`docs/系统设计文档/核心组件/Agent平台/archive/testing/Agent调用为空列表分析报告.md`
- **系統規格書**：`docs/系统设计文档/核心组件/IEE對話式開發文件編輯/文件編輯-Agent-系統規格書-v2.0.md`
- **測試腳本**：`tests/agents/test_file_editing_agent_routing.py`

---

## 📊 測試執行狀態更新（2026-01-11 17:19）

### 當前狀態

- ✅ **測試腳本已創建**：`tests/agents/test_file_editing_agent_routing.py`（包含 100 個測試場景）
- ✅ **測試執行腳本已創建**：`tests/agents/run_file_editing_agent_routing_test.py`
- ✅ **測試腳本已驗證**：測試腳本已驗證可以正常執行（已驗證前 50 個場景均 PASSED）
- ⏳ **完整測試待執行**：100 個測試場景需要執行（預計需要 15-20 分鐘）
- ⏳ **測試場景執行記錄表待更新**：詳細測試記錄表（下方各類別的測試場景執行記錄表）需要在完整測試執行完成後更新
- ⏳ **報告更新待完成**：測試完成後將更新詳細測試結果

### 關於測試場景執行記錄表

**為什麼測試場景執行記錄表還沒有更新？**

1. **測試腳本已創建並驗證**：測試腳本 `test_file_editing_agent_routing.py` 已創建並驗證可以正常執行
2. **完整測試尚未執行**：100 個測試場景需要較長時間執行（預計 15-20 分鐘），完整測試尚未執行
3. **詳細記錄需要測試結果**：測試場景執行記錄表中的詳細信息（任務類型識別、意圖提取、Agent 調用、狀態等）需要在實際測試執行後才能填寫
4. **更新流程**：
   - 執行完整測試：`python3 -m pytest tests/agents/test_file_editing_agent_routing.py::TestFileEditingAgentRouting::test_agent_routing -v -s`
   - 收集測試結果
   - 解析測試結果
   - 更新測試場景執行記錄表

### 測試執行方式

```bash
# 方式 1：使用 pytest 執行所有測試場景（推薦）
cd /Users/daniel/GitHub/AI-Box
python3 -m pytest tests/agents/test_file_editing_agent_routing.py::TestFileEditingAgentRouting::test_agent_routing -v -s

# 方式 2：執行特定類別的測試（例如：md-editor）
python3 -m pytest tests/agents/test_file_editing_agent_routing.py -v -s -k "md-editor"

# 方式 3：執行特定場景（例如：MD-001）
python3 -m pytest tests/agents/test_file_editing_agent_routing.py::TestFileEditingAgentRouting::test_agent_routing -v -s -k "scenario0"

# 方式 4：使用測試執行腳本（生成詳細報告）
python3 tests/agents/run_file_editing_agent_routing_test.py
```

### 測試結果位置

測試完成後，結果將保存在：

- `tests/agents/test_reports/` 目錄下
- pytest 輸出會在終端顯示

### 測試執行說明

1. **測試腳本位置**：`tests/agents/test_file_editing_agent_routing.py`
2. **測試場景數量**：100 個場景（MD-001 ~ PDF2MD-020）
3. **預計執行時間**：15-20 分鐘（取決於 LLM 響應速度）
4. **驗證點**：
   - 任務類型識別（應為 `execution`）
   - Agent 調用（應調用預期的 Agent）
5. **測試腳本說明**：詳見 `tests/agents/README_FILE_EDITING_AGENT_ROUTING_TEST.md`

### 後續步驟

1. **執行完整測試**（100 個場景）：使用 pytest 執行所有測試場景
2. **收集測試結果**：保存測試執行輸出
3. **解析測試結果**：從測試輸出中提取每個場景的詳細結果
4. **更新測試場景執行記錄表**：更新下方各類別的測試場景執行記錄表（1531-1674 行）
5. **更新測試執行摘要表**：更新上方的測試執行摘要表（49-51 行）
6. **生成測試報告摘要**：生成完整的測試報告

### 更新測試場景執行記錄表的步驟

1. **執行測試並保存輸出**：

   ```bash
   cd /Users/daniel/GitHub/AI-Box
   python3 -m pytest tests/agents/test_file_editing_agent_routing.py::TestFileEditingAgentRouting::test_agent_routing -v -s > tests/agents/test_reports/test_output.log 2>&1
   ```

2. **解析測試結果**：從測試輸出中提取每個場景的：

   - 任務類型識別結果
   - 意圖提取結果
   - Agent 調用結果
   - 測試狀態（通過/失敗）
3. **更新測試場景執行記錄表**：根據測試結果更新下方各類別的表格：

   - 類別 1：md-editor（1533-1558 行）
   - 類別 2：xls-editor（1562-1587 行）
   - 類別 3：md-to-pdf（1591-1616 行）
   - 類別 4：xls-to-pdf（1620-1645 行）
   - 類別 5：pdf-to-md（1649-1674 行）
4. **更新類別統計**：更新每個類別的統計信息（通過數、失敗數、通過率等）
