# 重構計劃書 - 完整 Agent 實現說明

**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11

---

## 📋 說明

本文檔說明《文件編輯-Agent-v2-重構計劃書.md》的完整實現計劃，確認完成後可以獲得所有 5 個 Agent。

---

## ✅ 確認：完成後可獲得所有 5 個 Agent

### 編輯類 Agents（2 個）

1. **md-editor（Markdown 編輯器）**
   - **實現階段**：階段一（基礎設施）+ 階段二（核心功能）
   - **時間**：約 11-15 週
   - **功能**：
     - Intent DSL 解析與驗證
     - Markdown AST 解析
     - Target Selector（heading/anchor/block）
     - Block Patch + Text Patch 生成
     - Draft State、Commit、Rollback
     - 完整的驗證與審計

2. **xls-editor（Excel 編輯器）**
   - **實現階段**：階段三（其他編輯類 Agent 實現）
   - **時間**：約 3-4 週
   - **功能**：
     - Excel 文件解析（openpyxl）
     - Excel Intent DSL 擴展
     - Structured Patch 生成
     - 單元格、行、列、工作表操作
     - 公式和樣式處理
     - Draft State、Commit、Rollback

### 轉換類 Agents（3 個）

3. **md-to-pdf（Markdown 轉 PDF）**
   - **實現階段**：階段四（轉換類 Agents）
   - **時間**：約 2-3 週
   - **功能**：
     - Pandoc 集成
     - 模板和樣式支持
     - Mermaid 圖表渲染
     - 程式碼高亮
     - 數學公式支持

4. **xls-to-pdf（Excel 轉 PDF）**
   - **實現階段**：階段四（轉換類 Agents）
   - **時間**：約 1-2 週
   - **功能**：
     - openpyxl + reportlab 集成
     - 多工作表支持
     - 自定義布局和樣式
     - 圖表轉換

5. **pdf-to-md（PDF 轉 Markdown）**
   - **實現階段**：階段四（轉換類 Agents）
   - **時間**：約 2-3 週
   - **功能**：
     - Marker 集成
     - OCR 支持（掃描版 PDF）
     - 表格和圖片提取
     - 結構識別（標題、列表）

---

## 📅 完整實現時間線

| 階段 | 時間 | 工作週數 | 交付的 Agent | 里程碑 |
|------|------|---------|-------------|--------|
| **階段一：基礎設施** | 第 1-6 週 | 4-6 週 | - | Intent DSL、AST 解析、可重現配置完成 |
| **階段二：md-editor 核心功能** | 第 7-15 週 | 7-9 週 | ✅ md-editor | Target Selector、Block Patch、上下文策略完成 |
| **階段三：xls-editor 實現** | 第 16-19 週 | 3-4 週 | ✅ xls-editor | Excel 編輯器完成 |
| **階段四：轉換類 Agents** | 第 20-25 週 | 4-6 週 | ✅ md-to-pdf<br>✅ xls-to-pdf<br>✅ pdf-to-md | 所有轉換類 Agents 完成 |
| **階段五：驗證與品質** | 第 26-32 週 | 5-7 週 | - | 驗證與 Linter、錯誤處理、審計完成 |
| **階段六：整合** | 第 33-37 週 | 4-5 週 | - | 任務工作區整合、前端整合完成 |
| **測試與優化** | 第 38-39 週 | 2 週 | - | 集成測試、性能優化、文檔更新 |
| **總計** | **39 週** | **29-37 週** | **5 個 Agent** | 約 **7-9 個月** |

---

## 🎯 各階段詳細說明

### 階段一：基礎設施（4-6 週）

**目標**：為所有編輯類 Agents 建立基礎設施

**交付物**：

- Intent DSL 解析器（適用於 md-editor 和 xls-editor）
- Markdown AST 解析器（適用於 md-editor）
- LLM 可重現配置（適用於所有需要 LLM 的 Agents）

**不交付 Agent**：本階段只建立基礎設施

---

### 階段二：md-editor 核心功能（7-9 週）

**目標**：實現 md-editor 的核心功能

**交付物**：

- ✅ **md-editor**（Markdown 編輯器）
  - Target Selector（heading/anchor/block，含模糊匹配）
  - Block Patch 生成
  - Text Patch 轉換
  - 最小上下文策略

**功能完整性**：約 80%（缺少驗證與審計，在階段五完成）

---

### 階段三：xls-editor 實現（3-4 週）

**目標**：實現 xls-editor 的完整功能

**交付物**：

- ✅ **xls-editor**（Excel 編輯器）
  - Excel 文件解析
  - Excel Intent DSL 擴展
  - Structured Patch 生成
  - 公式和樣式處理

**功能完整性**：約 80%（缺少驗證與審計，在階段五完成）

---

### 階段四：轉換類 Agents（4-6 週）

**目標**：實現所有轉換類 Agents

**交付物**：

- ✅ **md-to-pdf**（Markdown 轉 PDF）
  - Pandoc 集成
  - 模板和樣式支持
  - Mermaid 和程式碼高亮處理

- ✅ **xls-to-pdf**（Excel 轉 PDF）
  - openpyxl + reportlab 集成
  - 多工作表支持
  - 圖表和樣式處理

- ✅ **pdf-to-md**（PDF 轉 Markdown）
  - Marker 集成
  - OCR 支持
  - 表格和圖片提取

**功能完整性**：約 90%（轉換類 Agents 相對簡單，不需要複雜的驗證）

---

### 階段五：驗證與品質（5-7 週）

**目標**：為所有編輯類 Agents 實現驗證與審計功能

**適用範圍**：

- md-editor：驗證與 Linter、錯誤處理、觀測性與審計
- xls-editor：驗證與 Linter、錯誤處理、觀測性與審計

**交付物**：

- 驗證與 Linter（結構、長度、樣式、語義漂移、外部參照）
- 錯誤處理機制（14 個錯誤碼 + 修正建議）
- 觀測性與審計（9 個審計事件、AI 智慧變更摘要）

**功能完整性**：md-editor 和 xls-editor 達到 100%

---

### 階段六：任務工作區整合與前端整合（4-5 週）

**目標**：整合任務工作區和前端 API

**適用範圍**：所有 Agents

**交付物**：

- 任務工作區整合（新文件創建在任務工作區下）
- 前端 API（文件創建、編輯、刪除、Draft State、Commit & Rollback、Diff）
- 流式傳輸支持（WebSocket/SSE）

**功能完整性**：所有 Agents 達到 100%

---

## ✅ 最終交付確認

完成所有階段後，可以獲得：

| Agent | 狀態 | 功能完整性 |
|-------|------|-----------|
| **md-editor** | ✅ 完整實現 | 100% |
| **xls-editor** | ✅ 完整實現 | 100% |
| **md-to-pdf** | ✅ 完整實現 | 100% |
| **xls-to-pdf** | ✅ 完整實現 | 100% |
| **pdf-to-md** | ✅ 完整實現 | 100% |

**總計**：**5 個 Agent**，全部完整實現

---

## 📝 注意事項

1. **階段順序**：必須按順序執行，因為後續階段依賴前面階段的基礎設施
2. **並行開發**：階段四的 3 個轉換類 Agents 可以並行開發
3. **測試覆蓋**：每個階段完成後都需要進行單元測試和集成測試
4. **文檔更新**：每個階段完成後都需要更新 API 文檔和使用指南

---

**文件版本**: v1.0
**最後更新日期**: 2026-01-11
**維護人**: Daniel Chung
