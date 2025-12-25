# Phase 6: 高級功能開發計劃

**版本**: 1.1
**創建日期**: 2025-12-20
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-20
**階段狀態**: 🔄 進行中
**完成度**: 75%

---

## 📋 階段概述

Phase 6 旨在實現高級功能，包括模組化文檔架構和 Agent 自動化增強，提升系統處理超長文件和自動化工作流的能力。

**預計工期**: 5-7 週
**優先級**: 🟢 低優先級

---

## 📊 任務列表

### 任務 6.1: 模組化文檔架構

**狀態**: 🔄 進行中
**完成度**: 75%
**預計工期**: 3-4 週
**開始日期**: 2025-12-20
**完成日期**: -

#### 任務描述

實現主從架構，實現 Transclusion 語法，實現虛擬合併預覽。

#### 詳細任務

1. **主從架構設計** (4-5 天)
   - [x] 設計主文檔和分文檔數據結構（ModularDocument, SubDocumentRef 模型）
   - [x] 實現文檔關聯管理（ModularDocumentService）
   - [x] 實現主文檔解析邏輯
   - [x] 實現分文檔管理邏輯

2. **Transclusion 語法實現** (5-6 天)
   - [x] 實現 `![[filename]]` 語法解析（transclusion_parser.py）
   - [x] 實現引用鏈接解析
   - [x] 實現引用驗證（文件存在性檢查）
   - [x] 實現循環引用檢測（DFS 算法）
   - [x] 實現引用更新邏輯

3. **自動拆解功能** (4-5 天)
   - [x] 實現 H1-H3 標題識別（利用現有 AST 驅動策略）
   - [x] 實現自動切分邏輯（document_splitter_service.py）
   - [x] 實現主文檔生成
   - [x] 實現分文檔創建
   - [x] 實現引用關係建立

4. **虛擬合併預覽** (5-6 天)
   - [x] 實現 Transclusion 語法解析工具函數（`modularDocument.ts`）
   - [x] 實現虛擬合併預覽組件基礎架構（`ModularDocumentViewer.tsx`）
   - [x] 實現內容合併邏輯
   - [ ] 實現文件查找 API（根據文件名查找文件 ID）（待後續實現）
   - [ ] 實現完整的異步加載邏輯（待後續實現）
   - [ ] 實現跨檔案同步（主文標題更新分文元數據）（待後續實現）
   - [ ] 實現性能優化（待後續實現）

5. **導出編譯引擎** (4-5 天)
   - [ ] 實現標題層級校準（待後續實現）
   - [ ] 實現變數注入（全局變數）（待後續實現）
   - [ ] 實現格式統一化（Pandoc）（待後續實現）
   - [ ] 實現 PDF/Word 導出（待後續實現）

#### 代碼規範要求

- ✅ 遵循 `develop-rule.mdc` 規範
- ✅ 遵循 `pyproject.toml` 配置
- ✅ 後端代碼必須通過 `ruff check --fix .` 和 `mypy .`
- ✅ 前端代碼必須通過 TypeScript 和 ESLint 檢查
- ✅ 所有函數參數必須有類型注解
- ✅ 異常處理必須完整
- ✅ 數據庫操作必須有錯誤處理

#### 測試要求

- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] 測試文件:
  - [ ] `tests/services/document/modular_document_test.py` (後端)
  - [ ] `tests/frontend/components/VirtualMerge.test.tsx` (前端)
- [ ] 測試場景:
  - [ ] 主從架構數據結構
  - [ ] Transclusion 語法解析
  - [ ] 引用驗證和循環檢測
  - [ ] 自動拆解邏輯
  - [ ] 虛擬合併預覽
  - [ ] 無縫滾動和異步加載
  - [ ] 跨檔案同步
  - [ ] 導出編譯引擎
  - [ ] 性能測試（大量分文檔）

#### 測試記錄

- **測試日期**: -
- **測試人員**: -
- **單元測試**: 0/0 通過
- **集成測試**: 0/0 通過
- **代碼覆蓋率**: 0%
- **Ruff 檢查**: ⏸️ 未執行
- **Mypy 檢查**: ⏸️ 未執行
- **備註**: -

---

### 任務 6.2: Agent 自動化增強

**狀態**: 🔄 進行中
**完成度**: 50%
**預計工期**: 2-3 週
**開始日期**: 2025-12-20
**完成日期**: -

#### 任務描述

增強 Execution Agent，實現沙盒執行環境，實現自動化工作流。

#### 詳細任務

1. **Execution Agent 增強** (3-4 天)
   - [x] 擴展 Execution Agent 為 Document Editing Agent（添加 edit_document MCP Tool）
   - [x] 實現 Search-and-Replace 協議的 MCP Tool（handlers.py）
   - [x] 實現 Agent 編輯指令交互（DocumentEditingService + generate_and_edit_document Tool）
   - [ ] 集成到現有 Agent Orchestrator（待實現）

2. **沙盒執行環境** (4-5 天)
   - [ ] 設計沙盒架構（Docker 或隔離環境）
   - [ ] 實現腳本執行邏輯
   - [ ] 實現資源限制（CPU、內存、時間）
   - [ ] 實現執行結果捕獲
   - [ ] 實現安全性檢查

3. **自動化工作流** (3-4 天)
   - [ ] 實現工作流定義格式
   - [ ] 實現工作流執行引擎
   - [ ] 實現多 Agent 協作邏輯
   - [ ] 實現工作流狀態管理
   - [ ] 實現工作流錯誤處理

4. **UI/UX 優化** (2-3 天)
   - [ ] 實現狀態標籤顯示
   - [ ] 實現自然語言任務描述
   - [ ] 實現一鍵轉換功能（數據轉表格）
   - [ ] 實現工作流進度顯示

#### 代碼規範要求

- ✅ 遵循 `develop-rule.mdc` 規範
- ✅ 遵循 `pyproject.toml` 配置
- ✅ 所有函數參數必須有類型注解
- ✅ 所有返回值必須有類型注解
- ✅ 可能為 None 的變量使用 `Optional[T]`
- ✅ 必須通過 `ruff check --fix .`
- ✅ 必須通過 `mypy .`
- ✅ 必須通過 `black .`
- ✅ 安全性檢查必須完整

#### 測試要求

- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] 測試文件:
  - [ ] `tests/agents/execution/document_editing_agent_test.py`
  - [ ] `tests/agents/sandbox/execution_sandbox_test.py`
  - [ ] `tests/agents/workflow/workflow_engine_test.py`
- [ ] 測試場景:
  - [ ] Document Editing Agent 功能
  - [ ] Search-and-Replace MCP Tool
  - [ ] Agent 協作邏輯
  - [ ] 沙盒執行環境
  - [ ] 資源限制和安全性
  - [ ] 工作流執行
  - [ ] 多 Agent 協作
  - [ ] 錯誤處理和恢復
  - [ ] UI/UX 功能

#### 測試記錄

- **測試日期**: -
- **測試人員**: -
- **單元測試**: 0/0 通過
- **集成測試**: 0/0 通過
- **代碼覆蓋率**: 0%
- **Ruff 檢查**: ⏸️ 未執行
- **Mypy 檢查**: ⏸️ 未執行
- **備註**: -

---

## 📈 階段進度統計

### 任務完成情況

| 任務 | 狀態 | 完成度 | 開始日期 | 完成日期 |
|------|------|--------|----------|----------|
| 6.1 模組化文檔架構 | 🔄 | 80% | 2025-12-20 | - |
| 6.2 Agent 自動化增強 | 🔄 | 50% | 2025-12-20 | - |

### 測試統計

- **單元測試**: 0/0 通過 (0%) - 待實現
- **集成測試**: 0/0 通過 (0%) - 待實現
- **代碼覆蓋率**: 0% - 待測試
- **代碼規範檢查**: ✅ 已執行
  - **Ruff 檢查**: ✅ 通過（所有文件已通過檢查）
  - **Black 格式化**: ✅ 通過（所有文件已格式化）
  - **Mypy 檢查**: ⚠️ 部分類型錯誤（主要為其他文件的依賴問題，新創建的文件無類型錯誤）

### 風險與問題

| 風險/問題 | 嚴重程度 | 狀態 | 緩解措施 |
|----------|---------|------|---------|
| 模組化架構複雜度 | 高 | ⏸️ | 分階段實現，先實現基礎功能 |
| 沙盒執行安全性 | 高 | ⏸️ | 使用成熟的隔離技術，嚴格資源限制 |
| 性能問題 | 中 | ⏸️ | 使用異步處理和緩存優化 |

---

## 📝 階段完成標準

階段完成必須滿足以下條件：

1. ✅ 所有任務狀態為「已完成」
2. ✅ 所有任務完成度為 100%
3. ✅ 所有單元測試通過，覆蓋率 ≥ 80%
4. ✅ 所有集成測試通過
5. ✅ 代碼規範檢查全部通過（Ruff、Mypy、Black）
6. ✅ 測試記錄完整
7. ✅ 主計劃進度已更新

---

## 🔗 相關文檔

- [IEE開發主計劃](./IEE開發主計劃.md)
- [IEE編輯器可行性分析報告](../IEE編輯器可行性分析報告.md)
- [AI-Box-IEE-式-Markdown-文件編輯器開發規格書](../AI-Box-IEE-式-Markdown-文件編輯器開發規格書.md)

---

**計劃版本**: 1.1
**最後更新**: 2025-12-20
**維護者**: Daniel Chung

---

## 📋 最新更新記錄

### 2025-12-20 更新

- ✅ **Phase 6 核心功能部分完成**（完成度 75%）
  - 任務 6.1: 模組化文檔架構 - 🔄 80% 完成
  - 任務 6.2: Agent 自動化增強 - 🔄 50% 完成
  - 任務 6.2: Agent 自動化增強 - 🔄 40% 完成
- ✅ **代碼規範檢查**: 所有新創建的文件已通過 Ruff、Black 檢查
- ✅ **已完成項目**:
  1. **模組化文檔數據模型**（已完成）
     - 實現 ModularDocument、SubDocumentRef 數據模型
     - 實現創建、更新、查詢請求模型
  2. **Transclusion 語法解析器**（已完成）
     - 實現 `![[filename]]` 語法解析
     - 實現循環引用檢測（DFS 算法）
     - 實現引用驗證功能
  3. **ModularDocumentService**（已完成）
     - 實現主從架構管理
     - 實現文檔關聯管理（創建、更新、查詢、刪除）
     - 實現分文檔添加和移除
     - 實現引用驗證和循環檢測
  4. **自動拆解服務**（已完成）
     - 實現 DocumentSplitterService
     - 利用現有 AST_DRIVEN 策略識別 H1-H3 標題
     - 實現自動切分邏輯和主文檔生成
  5. **模組化文檔 API 端點**（已完成）
     - 實現創建、查詢、更新、刪除 API
     - 實現分文檔添加和移除 API
     - 實現按任務 ID 列出模組化文檔 API
  6. **edit_document MCP Tool**（已完成）
     - 擴展 Execution Agent 添加 edit_document 工具
     - 實現 Search-and-Replace 協議支持
     - 集成到 MCP Server
  7. **前端虛擬合併預覽基礎架構**（已完成）
     - 實現 Transclusion 語法解析工具函數（`modularDocument.ts`）
     - 實現虛擬合併預覽組件（`ModularDocumentViewer.tsx`）
     - 實現內容合併邏輯
     - 實現模組化文檔 API 函數（`api.ts`）
  8. **文件查找 API**（已完成）
     - 實現 `GET /api/v1/files/lookup` 端點（支持文件名模糊匹配）
     - 實現 `GET /api/v1/files/lookup/exact` 端點（精確匹配）
     - 集成到前端虛擬合併預覽組件
  9. **Agent 編輯指令交互**（已完成）
     - 實現 `DocumentEditingService`（文檔編輯服務）
     - 實現 `generate_and_edit_document` MCP Tool（生成並應用文檔編輯）
     - 實現 LLM 調用生成 Search-and-Replace patches
     - 實現意圖解析和 Prompt 構建邏輯
- ⚠️ **待完成項目**:
  1. **前端虛擬合併預覽優化**（基礎功能已完成）
     - ✅ Transclusion 語法解析和內容合併邏輯
     - ✅ 文件查找 API（根據文件名查找文件 ID）
     - ✅ 完整的異步加載邏輯集成
     - ⚠️ 無縫滾動邏輯優化（性能優化，可選）
  2. **導出編譯引擎**（待後續實現）
     - 標題層級校準
     - 變數注入
     - Pandoc 格式統一化
     - PDF/Word 導出
  3. **Agent 編輯指令交互**（已完成）
     - ✅ 意圖解析（DocumentEditingService）
     - ✅ LLM 調用生成 patches
     - ✅ generate_and_edit_document MCP Tool
  4. **自動化工作流**（待實現）
     - Runner → Editor Agent 協作
  5. **單元測試和集成測試**（待實現）
- 📝 **說明**:
  - 所有核心數據模型和服務已實現
  - API 端點已實現並註冊到主應用
  - edit_document 和 generate_and_edit_document MCP Tools 已添加
  - 前端虛擬合併預覽組件已完整實現（包括文件查找和異步加載）
  - Agent 編輯指令交互功能已實現（DocumentEditingService + generate_and_edit_document Tool）
  - 代碼已通過 Ruff 和 Black 檢查
  - TypeScript 類型檢查通過（前端代碼）
