# 文件編輯 Agent 系統規格書 v2.2

**代碼功能說明**: 文件編輯 Agent 系統規格書 v2.0 - 多格式文件編輯與轉換系統
**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-21

---

## 📋 文檔信息

- **版本**: v2.2
- **狀態**: 草案（Draft）
- **適用範圍**: AI-Box 文件編輯 Agent 系統
- **相關文檔**:
  - 《文件編輯-Agent-v2-重構計劃書.md》（**主要實施文檔**，已整合執行摘要）
  - 《文件編輯-Agent（Markdown）工程系統規格書-v2.md》（已歸檔，見 `archive/v1.0/`）
  - 《AI-Box-IEE-式-Markdown-文件編輯器開發規格書.md》（已歸檔，見 `archive/v1.0/`）

---

## 更新記錄

| 日期       | 版本 | 變更內容                                                                                                          |
| ---------- | ---- | ----------------------------------------------------------------------------------------------------------------- |
| 2026-01-11 | v2.0 | 初始版本                                                                                                          |
| 2026-01-21 | v2.1 | 更新文件路徑格式為 S3 URI（SeaWeedFS）；更新 VectorDB 為 Qdrant                                                   |
| 2026-01-21 | v2.2 | 更新前端文件預覽組件規範：統一使用 FilePreview 組件；向量頁面顯示條件和規格；Point 列表顯示格式；相似向量搜索功能 |

## 1. 系統概述

### 1.1 系統定位

文件編輯 Agent 系統（Document Editing Agent System，以下簡稱 DEAS）是一個**多格式文件編輯與轉換系統**，基於 AI-Box Agent 平台架構，提供結構化、可審計、可重現的文件編輯能力。

### 1.2 核心價值

1. **多格式支持**：支持 Markdown 和 Excel 兩種核心格式的編輯
2. **格式轉換**：支持 Markdown/Excel 與 PDF/Word 之間的轉換
3. **精準編輯**：基於結構化 Intent 的局部編輯，避免全量重寫
4. **可審計性**：所有編輯行為可追溯、可回滾
5. **模組化設計**：各 Agent 職責清晰，易於擴展和維護

### 1.3 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Orchestrator                          │
│              (任務分析與路由決策)                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                                   ↓
┌───────────────────────┐      ┌───────────────────────┐
│   編輯類 Agents        │      │   轉換類 Agents        │
│                       │      │                       │
│  ┌─────────────────┐  │      │  ┌─────────────────┐  │
│  │  md-editor      │  │      │  │  md-to-pdf      │  │
│  │  (Markdown編輯)  │  │      │  │  (MD→PDF轉換)   │  │
│  └─────────────────┘  │      │  └─────────────────┘  │
│                       │      │                       │
│  ┌─────────────────┐  │      │  ┌─────────────────┐  │
│  │  xls-editor     │  │      │  │  xls-to-pdf     │  │
│  │  (Excel編輯)     │  │      │  │  (XLS→PDF轉換)  │  │
│  └─────────────────┘  │      │  └─────────────────┘  │
│                       │      │                       │
│                       │      │  ┌─────────────────┐  │
│                       │      │  │  pdf-to-md      │  │
│                       │      │  │  (PDF→MD轉換)   │  │
│                       │      │  └─────────────────┘  │
└───────────────────────┘      └───────────────────────┘
        ↓                                   ↓
┌─────────────────────────────────────────────────────────────┐
│              基礎設施層 (Infrastructure)                     │
│  - TaskWorkspaceService (任務工作區管理)                    │
│  - FileMetadataService (文件元數據管理)                     │
│  - VersionController (版本控制)                             │
│  - Storage (文件存儲)                                       │
│  - AuditLogger (審計日誌)                                   │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 Agent 列表

| Agent 名稱           | Agent ID       | 職責              | 輸入格式         | 輸出格式         |
| -------------------- | -------------- | ----------------- | ---------------- | ---------------- |
| **md-editor**  | `md-editor`  | Markdown 文件編輯 | Markdown         | Markdown (Patch) |
| **xls-editor** | `xls-editor` | Excel 文件編輯    | Excel (xlsx/xls) | Excel (Patch)    |
| **md-to-pdf**  | `md-to-pdf`  | Markdown 轉 PDF   | Markdown         | PDF              |
| **xls-to-pdf** | `xls-to-pdf` | Excel 轉 PDF      | Excel (xlsx/xls) | PDF              |
| **pdf-to-md**  | `pdf-to-md`  | PDF 轉 Markdown   | PDF              | Markdown         |

---

## 2. 系統設計原則

### 2.1 核心設計原則

1. **單一職責原則**

   - 每個 Agent 只負責一種格式的編輯或轉換
   - 編輯 Agent 和轉換 Agent 職責分離
2. **統一接口規範**

   - 所有 Agent 遵循相同的 MCP Tool 接口規範
   - 編輯類 Agent 統一使用 Intent DSL + Patch 模型
   - 轉換類 Agent 統一使用轉換配置 + 輸出文件
3. **Document ≠ File**

   - 文件是具備生命週期、版本與治理規則的「知識物件」
   - 所有操作基於 DocumentContext（包含 doc_id、version_id 等）
4. **Edit ≠ Generate**

   - 所有編輯行為必須以 Patch/Diff 形式表達
   - 不支持全量重寫，僅支持局部修改
5. **Governance-first**

   - 無 DocumentContext、無合法版本狀態，不得編輯
   - 所有操作必須經過授權和審計
6. **Auditable & Deterministic**

   - 每一次操作皆可追溯來源、原因與影響範圍
   - 結果必須可重現（固定 LLM 參數、固定種子等）

### 2.2 Agent 分類

#### 2.2.1 編輯類 Agents（Editing Agents）

- **職責**：對文件進行結構化編輯（插入、修改、刪除、移動）
- **輸出**：Patch/Diff（不直接修改文件）
- **特點**：
  - 使用 Intent DSL 定義編輯意圖
  - 輸出 Block Patch 或 Structured Patch
  - 支持 Draft State、Commit、Rollback
  - 完整的審計和版本追蹤

**包含 Agents**：

- `md-editor`：Markdown 編輯器
- `xls-editor`：Excel 編輯器

#### 2.2.2 轉換類 Agents（Conversion Agents）

- **職責**：將文件從一種格式轉換為另一種格式
- **輸出**：新格式的文件（創建新文件，不修改原文件）
- **特點**：
  - 使用轉換配置定義轉換參數
  - 輸出新文件到任務工作區
  - 轉換過程可追蹤和審計
  - 支持轉換選項和模板

**包含 Agents**：

- `md-to-pdf`：Markdown 轉 PDF
- `xls-to-pdf`：Excel 轉 PDF
- `pdf-to-md`：PDF 轉 Markdown

---

## 3. 編輯類 Agents 詳細規格

### 3.1 md-editor（Markdown 編輯器）

#### 3.1.1 職責範圍

- 對 Markdown 文件進行結構化編輯
- 支持 CommonMark 1.x + GFM 標準
- 支持局部編輯（基於 Block Patch）
- 支持 Draft State、Commit、Rollback

#### 3.1.2 輸入規範

**DocumentContext**：

```json
{
  "doc_id": "uuid",
  "version_id": "uuid",
  "file_path": "s3://bucket-ai-box-assets/tasks/{task_id}/workspace/{file_id}.md",
  "task_id": "uuid",
  "user_id": "uuid",
  "tenant_id": "uuid"
}
```

**Edit Intent DSL**：

```json
{
  "intent_id": "uuid",
  "intent_type": "insert|update|delete|move|replace",
  "target_selector": {
    "type": "heading|anchor|block",
    "selector": { /* selector spec */ }
  },
  "action": {
    "mode": "insert|update|delete|move|replace",
    "content": "markdown content or null",
    "position": "before|after|inside|start|end"
  },
  "constraints": {
    "max_tokens": 300,
    "style_guide": "enterprise-tech-v1",
    "semantic_drift": { /* drift config */ },
    "no_external_reference": true
  }
}
```

#### 3.1.3 輸出規範

**Patch Response**：

```json
{
  "patch_id": "uuid",
  "intent_id": "uuid",
  "block_patch": { /* Block Patch */ },
  "text_patch": "unified diff format",
  "preview": "preview content (optional)",
  "audit_info": {
    "model_version": "gpt-4-turbo-preview-2026-01-09",
    "context_digest": "sha256",
    "generated_at": "ISO8601",
    "generated_by": "md-editor-v2.0"
  }
}
```

#### 3.1.4 技術規範

- **Markdown 標準**：CommonMark 1.x + GFM
- **AST 解析器**：markdown-it-py 或 mistune
- **Patch 格式**：Block Patch + Text Patch (unified diff)
- **LLM 配置**：temperature=0, fixed seed, fixed model version

#### 3.1.5 詳細規格參考

詳細規格請參考：《文件編輯-Agent（Markdown）工程系統規格書-v2.md》

---

### 3.2 xls-editor（Excel 編輯器）

#### 3.2.1 職責範圍

- 對 Excel 文件進行結構化編輯
- 支持 .xlsx 和 .xls 格式
- 支持工作表、行、列、單元格的局部編輯
- 支持 Draft State、Commit、Rollback

#### 3.2.2 輸入規範

**DocumentContext**：

```json
{
  "doc_id": "uuid",
  "version_id": "uuid",
  "file_path": "s3://bucket-ai-box-assets/tasks/{task_id}/workspace/{file_id}.xlsx",
  "task_id": "uuid",
  "user_id": "uuid",
  "tenant_id": "uuid"
}
```

**Edit Intent DSL**：

```json
{
  "intent_id": "uuid",
  "intent_type": "insert|update|delete|move|replace",
  "target_selector": {
    "type": "worksheet|range|cell|row|column",
    "selector": {
      "worksheet": "Sheet1",
      "range": "A1:C10",
      "cell": "B5",
      "row": 3,
      "column": "B"
    }
  },
  "action": {
    "mode": "insert|update|delete|move|replace",
    "content": {
      "values": [["value1", "value2"], ["value3", "value4"]],
      "formulas": ["=SUM(A1:A10)", "=AVERAGE(B1:B10)"],
      "styles": { /* style config */ },
      "format": { /* format config */ }
    },
    "position": "before|after|inside|start|end"
  },
  "constraints": {
    "max_cells": 1000,
    "preserve_formulas": true,
    "preserve_styles": true,
    "no_external_reference": true
  }
}
```

#### 3.2.3 輸出規範

**Patch Response**：

```json
{
  "patch_id": "uuid",
  "intent_id": "uuid",
  "structured_patch": {
    "operations": [
      {
        "op": "update",
        "target": "Sheet1!B5",
        "old_value": "old value",
        "new_value": "new value"
      }
    ]
  },
  "preview": { /* preview data */ },
  "audit_info": {
    "model_version": "gpt-4-turbo-preview-2026-01-09",
    "context_digest": "sha256",
    "generated_at": "ISO8601",
    "generated_by": "xls-editor-v2.0"
  }
}
```

#### 3.2.4 技術規範

- **Excel 庫**：openpyxl（.xlsx）或 xlrd/xlwt（.xls）
- **Patch 格式**：Structured Patch（JSON 格式的操作列表）
- **LLM 配置**：temperature=0, fixed seed, fixed model version
- **支持的操作**：
  - 單元格值更新
  - 公式更新
  - 樣式更新（字體、顏色、對齊等）
  - 行/列插入/刪除
  - 工作表操作（創建、重命名、刪除）

#### 3.2.5 特殊考慮

- **公式處理**：必須保留公式依賴關係，避免循環引用
- **樣式保留**：編輯時盡量保留原有樣式和格式
- **大文件處理**：對於大型 Excel 文件（>10MB），使用增量讀取和寫入

---

## 4. 轉換類 Agents 詳細規格

### 4.1 md-to-pdf（Markdown 轉 PDF）

#### 4.1.1 職責範圍

- 將 Markdown 文件轉換為 PDF 文件
- 支持自定義 PDF 樣式和模板
- 輸出新文件到任務工作區

#### 4.1.2 輸入規範

**DocumentContext**：

```json
{
  "source_doc_id": "uuid",
  "source_file_path": "s3://bucket-ai-box-assets/tasks/{task_id}/workspace/{file_id}.md",
  "task_id": "uuid",
  "user_id": "uuid",
  "tenant_id": "uuid"
}
```

**Conversion Config**：

```json
{
  "conversion_id": "uuid",
  "output_file_name": "output.pdf",
  "template": "default|academic|business|custom",
  "options": {
    "page_size": "A4|Letter|Legal",
    "margin": { "top": "2cm", "bottom": "2cm", "left": "2cm", "right": "2cm" },
    "font": { "family": "Times New Roman", "size": 12 },
    "header": { "enabled": true, "content": "{{title}}" },
    "footer": { "enabled": true, "content": "Page {{page}} of {{pages}}" },
    "toc": { "enabled": true, "depth": 3 },
    "code_highlighting": true,
    "mermaid_rendering": true
  }
}
```

#### 4.1.3 輸出規範

**Conversion Response**：

```json
{
  "conversion_id": "uuid",
  "source_doc_id": "uuid",
  "output_doc_id": "uuid",
  "output_file_path": "s3://bucket-ai-box-assets/tasks/{task_id}/workspace/{output_file_id}.pdf",
  "status": "success|failed",
  "message": "conversion message",
  "metadata": {
    "page_count": 10,
    "file_size": 1024000,
    "conversion_time": 5.2
  },
  "audit_info": {
    "converted_at": "ISO8601",
    "converted_by": "md-to-pdf-v2.0",
    "tool_version": "pandoc-3.0.0"
  }
}
```

#### 4.1.4 技術規範

- **轉換工具**：Pandoc（推薦）或 WeasyPrint / pdfkit
- **模板支持**：LaTeX 模板（通過 Pandoc）或 HTML/CSS 模板（通過 WeasyPrint）
- **特殊處理**：
  - Mermaid 圖表：先渲染為 SVG，再嵌入 PDF
  - 程式碼高亮：使用 Pygments 或 highlight.js
  - 數學公式：支持 LaTeX 數學公式（通過 MathJax 或 KaTeX）

---

### 4.2 xls-to-pdf（Excel 轉 PDF）

#### 4.2.1 職責範圍

- 將 Excel 文件轉換為 PDF 文件
- 支持多工作表 PDF 或單工作表 PDF
- 支持自定義 PDF 樣式和布局

#### 4.2.2 輸入規範

**DocumentContext**：

```json
{
  "source_doc_id": "uuid",
  "source_file_path": "s3://bucket-ai-box-assets/tasks/{task_id}/workspace/{file_id}.xlsx",
  "task_id": "uuid",
  "user_id": "uuid",
  "tenant_id": "uuid"
}
```

**Conversion Config**：

```json
{
  "conversion_id": "uuid",
  "output_file_name": "output.pdf",
  "options": {
    "worksheets": ["Sheet1", "Sheet2"] | "all",
    "page_size": "A4|Letter|Legal|A3",
    "orientation": "portrait|landscape",
    "scale": "fit|actual|custom",
    "margin": { "top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm" },
    "print_area": "A1:Z100" | "auto",
    "header_footer": {
      "header": { "left": "{{filename}}", "center": "", "right": "{{date}}" },
      "footer": { "left": "", "center": "Page {{page}}", "right": "" }
    },
    "gridlines": true,
    "row_column_headings": true
  }
}
```

#### 4.2.3 輸出規範

**Conversion Response**：

```json
{
  "conversion_id": "uuid",
  "source_doc_id": "uuid",
  "output_doc_id": "uuid",
  "output_file_path": "s3://bucket-ai-box-assets/tasks/{task_id}/workspace/{output_file_id}.pdf",
  "status": "success|failed",
  "message": "conversion message",
  "metadata": {
    "page_count": 5,
    "file_size": 512000,
    "worksheets_converted": ["Sheet1", "Sheet2"],
    "conversion_time": 3.5
  },
  "audit_info": {
    "converted_at": "ISO8601",
    "converted_by": "xls-to-pdf-v2.0",
    "tool_version": "openpyxl-3.1.0"
  }
}
```

#### 4.2.4 技術規範

- **轉換工具**：
  - openpyxl + reportlab（推薦，Python 原生）
  - 或 LibreOffice headless（通過 subprocess）
  - 或 xlsxwriter + pdfkit
- **特殊處理**：
  - 大表格：自動分頁和頁眉頁腳
  - 圖表：將 Excel 圖表轉換為圖片嵌入 PDF
  - 樣式：盡量保留 Excel 的樣式和格式

---

### 4.3 pdf-to-md（PDF 轉 Markdown）

#### 4.3.1 職責範圍

- 將 PDF 文件轉換為 Markdown 文件
- 支持文本提取和結構化識別
- 輸出新文件到任務工作區

#### 4.3.2 輸入規範

**DocumentContext**：

```json
{
  "source_doc_id": "uuid",
  "source_file_path": "s3://bucket-ai-box-assets/tasks/{task_id}/workspace/{file_id}.pdf",
  "task_id": "uuid",
  "user_id": "uuid",
  "tenant_id": "uuid"
}
```

**Conversion Config**：

```json
{
  "conversion_id": "uuid",
  "output_file_name": "output.md",
  "options": {
    "extraction_mode": "text|layout|ocr",
    "ocr_language": "chi_sim+eng",
    "table_detection": true,
    "image_extraction": true,
    "heading_detection": true,
    "list_detection": true,
    "preserve_formatting": true
  }
}
```

#### 4.3.3 輸出規範

**Conversion Response**：

```json
{
  "conversion_id": "uuid",
  "source_doc_id": "uuid",
  "output_doc_id": "uuid",
  "output_file_path": "s3://bucket-ai-box-assets/tasks/{task_id}/workspace/{output_file_id}.md",
  "status": "success|failed",
  "message": "conversion message",
  "metadata": {
    "page_count": 20,
    "extracted_text_length": 50000,
    "tables_detected": 5,
    "images_extracted": 10,
    "conversion_time": 15.8
  },
  "audit_info": {
    "converted_at": "ISO8601",
    "converted_by": "pdf-to-md-v2.0",
    "tool_version": "marker-0.3.0"
  }
}
```

#### 4.3.4 技術規範

- **轉換工具**：
  - Marker（推薦，高質量 PDF 轉 Markdown）
  - 或 LlamaParse（替代方案）
  - 或 PyMuPDF（fitz）+ OCR（Tesseract）
- **特殊處理**：
  - 表格：使用 Marker 的表格識別，轉換為 Markdown 表格
  - 圖片：提取圖片並保存到任務工作區，在 Markdown 中引用
  - OCR：對於掃描版 PDF，使用 Tesseract OCR
  - 結構識別：使用 AI 模型識別標題、列表等結構

---

## 5. Agent 協作機制

### 5.1 編輯 + 轉換工作流

**場景**：用戶編輯 Markdown 文件後，需要轉換為 PDF

```
1. 用戶發起編輯請求
   → Orchestrator 路由到 md-editor

2. md-editor 執行編輯
   → 返回 Patch

3. 用戶提交變更（Commit）
   → 文件更新為新版本

4. 用戶請求轉換為 PDF
   → Orchestrator 路由到 md-to-pdf

5. md-to-pdf 執行轉換
   → 讀取最新版本的文件
   → 轉換為 PDF
   → 創建新文件到任務工作區
   → 返回轉換結果
```

### 5.2 轉換 + 編輯工作流

**場景**：用戶上傳 PDF，轉換為 Markdown，然後編輯

```
1. 用戶上傳 PDF 文件
   → 存儲到任務工作區

2. 用戶請求轉換為 Markdown
   → Orchestrator 路由到 pdf-to-md

3. pdf-to-md 執行轉換
   → 提取 PDF 內容
   → 轉換為 Markdown
   → 創建新文件到任務工作區
   → 返回轉換結果

4. 用戶請求編輯 Markdown
   → Orchestrator 路由到 md-editor

5. md-editor 執行編輯
   → 基於轉換後的 Markdown 文件
   → 返回 Patch
```

### 5.3 協作接口規範

所有 Agent 通過 **Agent Orchestrator** 進行協作，不直接調用其他 Agent。

**協作方式**：

- Agent 通過返回結果告知 Orchestrator 需要後續操作
- Orchestrator 根據結果決定是否調用其他 Agent
- Agent 之間不直接通信，通過 Orchestrator 協調

---

## 6. 統一接口規範

### 6.1 MCP Tool 規範

所有 Agent 遵循相同的 MCP Tool 接口規範：

**編輯類 Agent Tool**：

```json
{
  "name": "edit_document",
  "description": "Edit a document using structured Intent DSL",
  "inputSchema": {
    "type": "object",
    "properties": {
      "document_context": { /* DocumentContext */ },
      "edit_intent": { /* Edit Intent DSL */ }
    },
    "required": ["document_context", "edit_intent"]
  }
}
```

**轉換類 Agent Tool**：

```json
{
  "name": "convert_document",
  "description": "Convert a document from one format to another",
  "inputSchema": {
    "type": "object",
    "properties": {
      "document_context": { /* DocumentContext */ },
      "conversion_config": { /* Conversion Config */ }
    },
    "required": ["document_context", "conversion_config"]
  }
}
```

### 6.2 錯誤處理規範

所有 Agent 使用統一的錯誤碼和錯誤格式：

**錯誤響應格式**：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "specific error details"
    },
    "suggestions": [
      {
        "action": "suggested action",
        "example": "example value"
      }
    ]
  }
}
```

**通用錯誤碼**：

- `DOCUMENT_NOT_FOUND`：文件不存在
- `VERSION_NOT_FOUND`：版本不存在
- `PERMISSION_DENIED`：權限不足
- `INVALID_FORMAT`：格式無效
- `CONVERSION_FAILED`：轉換失敗
- `VALIDATION_FAILED`：驗證失敗

---

## 7. 技術選型

### 7.1 編輯類 Agents

| Agent      | 核心庫         | AST/解析庫     | Patch 格式                 | LLM 配置                  |
| ---------- | -------------- | -------------- | -------------------------- | ------------------------- |
| md-editor  | markdown-it-py | markdown-it-py | Block Patch + Unified Diff | temperature=0, fixed seed |
| xls-editor | openpyxl       | openpyxl       | Structured Patch (JSON)    | temperature=0, fixed seed |

### 7.2 轉換類 Agents

| Agent      | 核心庫               | 備選方案                  | 特殊處理                 |
| ---------- | -------------------- | ------------------------- | ------------------------ |
| md-to-pdf  | Pandoc               | WeasyPrint, pdfkit        | Mermaid 渲染、程式碼高亮 |
| xls-to-pdf | openpyxl + reportlab | LibreOffice headless      | 圖表轉換、大表格分頁     |
| pdf-to-md  | Marker               | LlamaParse, PyMuPDF + OCR | 表格識別、OCR、結構識別  |

### 7.3 基礎設施

- **文件存儲**：SeaWeedFS S3（`s3://bucket-ai-box-assets/tasks/{task_id}/workspace/{file_id}.{ext}`）
- **向量數據庫**：Qdrant（用於向量化檢索和相似度匹配）
- **版本控制**：VersionController（版本管理）
- **審計日誌**：AuditLogger（操作追蹤）
- **元數據管理**：FileMetadataService（文件元數據）

### 7.4 存儲後端說明

#### 7.4.1 文件存儲（SeaWeedFS S3）

文件使用 SeaWeedFS S3 API 存儲，採用以下 Bucket 結構：

| Bucket                   | 用途                    |
| ------------------------ | ----------------------- |
| `bucket-ai-box-assets` | AI-Box 項目非結構化數據 |

**文件路徑格式**：

```
s3://bucket-ai-box-assets/tasks/{task_id}/workspace/{file_id}.{ext}
```

**示例**：

- Markdown 文件：`s3://bucket-ai-box-assets/tasks/task-123/workspace/cc3d7aee-b5b3-4e11-9458-784575c1dba6.md`
- Excel 文件：`s3://bucket-ai-box-assets/tasks/task-123/workspace/cc3d7aee-b5b3-4e11-9458-784575c1dba6.xlsx`
- PDF 文件：`s3://bucket-ai-box-assets/tasks/task-123/workspace/cc3d7aee-b5b3-4e11-9458-784575c1dba6.pdf`

**相關服務**：

- `S3FileStorage`（`storage/s3_storage.py`）：S3/SeaWeedFS 文件存儲實現
- `SeaweedFSService` enum：AI-BOX 和 DATALAKE 服務類型

#### 7.4.2 向量數據庫（Qdrant）

向量檢索使用 Qdrant 向量數據庫，取代原有的 ChromaDB：

**Collection 命名策略**：

- 格式：`file_{file_id}`（每個文件一個 Collection）
- 每個 Collection 包含文件的所有文本塊向量

**向量格式**：

```json
{
  "id": "chunk_0",
  "vector": [0.1, 0.2, ..., 0.768],
  "payload": {
    "file_id": "cc3d7aee-b5b3-4e11-9458-784575c1dba6",
    "chunk_index": 0,
    "chunk_text": "文檔內容...",
    "task_id": "systemAdmin_SystemDocs"
  }
}
```

**相關服務**：

- `QdrantVectorStoreService`（`services/api/services/qdrant_vector_store_service.py`）
- 端口：REST API 6333，gRPC 6334

#### 7.4.3 前端文件預覽組件規範

**修改時間：2026-01-21 13:50 UTC+8**

##### 7.4.3.1 統一使用 FilePreview 組件

**原則**：

- **所有文件預覽統一使用 `FilePreview` 組件**，不再使用 `FileViewer` 或 `MarkdownViewer`
- `FilePreview` 組件整合了所有文件類型的預覽功能，包括：
  - Markdown 渲染（使用 `markdown-to-jsx`）
  - Mermaid 圖表渲染
  - PDF、DOCX、Excel 文件預覽
  - 向量數據顯示
  - 知識圖譜顯示

**組件選擇邏輯**（`ResultPanel.tsx`）：

1. **優先使用 `FilePreview`**：

   - 如果 `selectedFileMetadata` 存在，直接使用 `FilePreview`
   - 如果 `selectedFileMetadata` 不存在，構建基本元數據後使用 `FilePreview`
   - 構建元數據時，根據文件名推斷文件類型（Markdown、PDF、DOCX、Excel 等）
2. **向後兼容**：

   - 僅在無法構建元數據時，才回退到 `FileViewer`（僅顯示文件內容，不支持向量/圖譜查看）

**文件類型處理**：

- **Markdown 文件**：在 `FilePreview` 內部直接渲染，不再使用 `MarkdownViewer` 組件
- **PDF 文件**：使用 `PDFViewer` 組件（通過 `FilePreview` 調用）
- **DOCX 文件**：使用 `DOCXViewer` 組件（通過 `FilePreview` 調用）
- **Excel 文件**：使用 `ExcelViewer` 組件（通過 `FilePreview` 調用）

##### 7.4.3.2 向量頁面顯示條件

**向量數據可用性判斷**（`FilePreview.tsx` - `checkDataAvailability`）：

1. **Collection 存在判斷**：

   - 調用 `getFileVectors(file_id, 1, 0)` API
   - 只要 `collection_name` 存在（`vectorResponse.data.stats?.collection_name` 或 `vectorResponse.data.collection_name`），就認為向量可用
   - **即使 `vector_count` 為 0，只要 collection 存在，也認為可用**
2. **文件存在判斷**（用於避免顯示"生成中"）：

   - 檢查 `file.storage_path` 是否有值（如 `s3://bucket-ai-box-assets/tasks/...`）
   - 或檢查 `file.status === 'completed'`
   - 如果文件已存在但 `processing_status` 為 `null`（可能 TTL 過期），不顯示"生成中"，而是顯示"未成功生成"並提供"重新生成"按鈕
3. **顯示邏輯**：

   - 如果 `vectorAvailable === true` 且已有 `vectorData`，直接顯示 Qdrant 風格界面
   - 如果 `vectorAvailable === false` 但文件已存在，顯示"未成功生成"界面（提供"重新生成"按鈕）
   - 如果 `vectorAvailable === false` 且 `processing_status` 顯示正在處理，顯示"生成中"界面

##### 7.4.3.3 向量頁面顯示規格

**向量視圖界面**（類似 Qdrant Dashboard）：

1. **Collection Info 面板**：

   - **Collection Name**：顯示 Collection 名稱（如 `file_50a3d280-359c-46ba-b453-51a3d5b3ef94`）
   - **Points Count**：顯示向量數量（即使為 0 也顯示）
   - **Status**：顯示 Collection 狀態（`active`、`error` 等）
   - **打開 Dashboard 鏈接**：鏈接到 `http://localhost:6333/dashboard#/collections/{collection_name}`
2. **Points 列表**：

   - 每個 Point 顯示為卡片形式
   - **Point Header**：
     - 顯示 Point ID（如 `3`）
     - 顯示 Chunk Text 預覽（最多 20 字符，超出用 "..." 表示）
     - 顯示 Chunk Index（如果有）
     - 顯示 Vector Dimensions（如果有向量數據）
   - **展開/收起**：點擊 Header 可展開查看詳細信息
   - **操作按鈕**：
     - **"尋找相似"按鈕**：查找與該 Point 相似的向量（最多 10 個）
     - **"Open Panel"按鈕**：打開詳細信息模态框
3. **Point 詳細信息模态框**（Open Panel）：

   - **視圖模式切換**：
     - **Details**：顯示 Point 的詳細信息（ID、Chunk Index、Vector Dimensions、Chunk Text、Payload、Vector 數據）
     - **Similar**：顯示相似向量列表（點擊"尋找相似"後自動切換到此視圖）
     - **Graph**：顯示 Qdrant Dashboard Graph 視圖鏈接（由於 X-Frame-Options 限制，無法嵌入，提供新窗口打開鏈接）
   - **Qdrant Dashboard 鏈接**：
     - **"Open Collection"**：打開 Collection 視圖（`http://localhost:6333/dashboard#/collections/{collection_name}`）
     - **"View Points"**：打開 Points 列表視圖（`http://localhost:6333/dashboard#/collections/{collection_name}/points`）
     - **"View Graph"**：打開 Graph 視圖（`http://localhost:6333/dashboard#/collections/{collection_name}/graph`）
4. **相似向量功能**：

   - **API 端點**：`GET /files/{file_id}/vectors/{point_id}/similar?limit=10&score_threshold=0.0`
   - **功能**：
     - 獲取指定 Point 的向量
     - 使用該向量搜索相似的 Points（排除自己）
     - 返回相似度分數和 Payload
   - **顯示**：
     - 在 Similar 視圖中顯示相似向量列表
     - 每個相似向量顯示：ID、相似度分數（百分比）、Chunk Text 預覽、完整 Payload（可折疊）
   - **導航**：提供"← 回到 Details"按鈕返回原始 Point 詳情

**向量數據格式**：

```json
{
  "file_id": "50a3d280-359c-46ba-b453-51a3d5b3ef94",
  "vectors": [
    {
      "id": "3",
      "payload": {
        "file_id": "50a3d280-359c-46ba-b453-51a3d5b3ef94",
        "chunk_index": 0,
        "chunk_text": "文檔內容...",
        "task_id": "systemAdmin_SystemDocs"
      },
      "vector": [0.1, 0.2, ..., 0.768] // 可選，默認不返回以提升性能
    }
  ],
  "total": 100,
  "limit": 100,
  "offset": 0,
  "stats": {
    "collection_name": "file_50a3d280-359c-46ba-b453-51a3d5b3ef94",
    "vector_count": 100,
    "status": "active"
  }
}
```

**相關組件**：

- `FilePreview`（`ai-bot/src/components/FilePreview.tsx`）：主預覽組件
- `VectorPointCard`：Point 卡片組件（在 `FilePreview.tsx` 內部定義）
- `ResultPanel`（`ai-bot/src/components/ResultPanel.tsx`）：文件列表和預覽容器

**相關 API**：

- `GET /files/{file_id}/vectors?limit=100&offset=0`：獲取文件向量列表
- `GET /files/{file_id}/vectors/{point_id}/similar?limit=10&score_threshold=0.0`：查找相似向量

---

## 8. 實現計劃

### 8.1 階段一：核心編輯 Agents（8-10 週）

1. **md-editor**（6-8 週）

   - 基於《文件編輯-Agent（Markdown）工程系統規格書-v2.md》實現
   - 參考《文件編輯-Agent-v2-重構計劃書.md》
2. **xls-editor**（2-3 週）

   - Excel 文件讀寫
   - Structured Patch 生成
   - 單元格、行、列操作

### 8.2 階段二：轉換類 Agents（4-6 週）

1. **md-to-pdf**（2-3 週）

   - Pandoc 集成
   - 模板和樣式支持
   - Mermaid 和程式碼高亮處理
2. **xls-to-pdf**（1-2 週）

   - openpyxl + reportlab 集成
   - 多工作表支持
   - 圖表和樣式處理
3. **pdf-to-md**（2-3 週）

   - Marker 集成
   - OCR 支持
   - 表格和圖片提取

### 8.3 階段三：整合與測試（2-3 週）

1. Agent 註冊與路由
2. 統一接口實現
3. 集成測試
4. 性能優化

### 8.4 階段四：文檔與部署（1-2 週）

1. API 文檔
2. 使用指南
3. 部署配置
4. 監控與日誌

**總計**：約 **15-21 週**（約 **3.5-5 個月**）

---

## 9. 與原有規格的兼容性

### 9.1 功能覆蓋對照

| 原有規格功能         | v2.0 實現 | Agent                 | 狀態     |
| -------------------- | --------- | --------------------- | -------- |
| Markdown 編輯        | ✅        | md-editor             | 完整實現 |
| PDF/Word 轉 Markdown | ✅        | pdf-to-md             | 完整實現 |
| Markdown 轉 PDF      | ✅        | md-to-pdf             | 完整實現 |
| Excel 編輯           | ✅        | xls-editor            | 新增功能 |
| Excel 轉 PDF         | ✅        | xls-to-pdf            | 新增功能 |
| Draft State          | ✅        | md-editor, xls-editor | 完整實現 |
| Commit & Rollback    | ✅        | md-editor, xls-editor | 完整實現 |
| 審計日誌             | ✅        | 所有 Agents           | 完整實現 |

### 9.2 向後兼容性

- **API 兼容**：新版本提供兼容舊 API 的適配層（可選）
- **數據兼容**：支持讀取舊版本的文件和元數據
- **功能兼容**：原有功能在新版本中完全保留

---

## 10. 擴展性設計

### 10.1 新增格式支持

**添加新的編輯 Agent**：

1. 實現 Edit Intent DSL 解析
2. 實現結構化 Patch 生成
3. 實現 Draft State、Commit、Rollback
4. 註冊到 Agent Orchestrator

**添加新的轉換 Agent**：

1. 實現轉換邏輯
2. 實現轉換配置解析
3. 實現錯誤處理
4. 註冊到 Agent Orchestrator

### 10.2 插件機制

- **模板插件**：支持自定義 PDF 模板
- **轉換插件**：支持第三方轉換工具
- **驗證插件**：支持自定義驗證規則

---

## 11. 安全性與治理

### 11.1 權限控制

- 所有操作必須經過授權（通過 DocumentContext）
- 文件訪問控制（基於 task_id、user_id、tenant_id）
- 操作審計（所有操作記錄到審計日誌）

### 11.2 數據保護

- 敏感數據檢測（PII、API Keys 等）
- 數據脫敏（在發送給 LLM 前）
- 加密存儲（敏感文件加密存儲）

### 11.3 合規性

- 操作可追溯（完整的審計日誌）
- 數據可恢復（版本控制和 Rollback）
- 隱私保護（符合 GDPR 等規範）

---

## 12. 監控與運維

### 12.1 監控指標

- **性能指標**：響應時間、吞吐量、錯誤率
- **業務指標**：編輯次數、轉換次數、成功率
- **資源指標**：CPU、記憶體、存儲使用

### 12.2 日誌規範

- **操作日誌**：所有 Agent 操作記錄
- **錯誤日誌**：錯誤詳情和堆疊追蹤
- **審計日誌**：完整的操作審計記錄

### 12.3 告警機制

- **錯誤告警**：錯誤率超過閾值
- **性能告警**：響應時間超過閾值
- **資源告警**：資源使用超過閾值

---

## 13. 參考文檔

### 當前使用的文檔

1. 《文件編輯-Agent-v2-重構計劃書.md》（當前目錄）
2. 《文件編輯-Agent-原有規格與v2規格功能對照表.md》（當前目錄）
3. 《文件編輯-Agent-功能對照確認報告.md》（當前目錄）
4. 《文件編輯-Agent-現有實現與v2規格比較分析.md》（當前目錄）

### 已歸檔的文檔（歷史參考）

5. 《文件編輯-Agent（Markdown）工程系統規格書-v2.md》（`archive/v1.0/`）
6. 《AI-Box-IEE-式-Markdown-文件編輯器開發規格書.md》（`archive/v1.0/`）
7. 《文件編輯-Agent（Markdown）工程系統規格書.md》（`archive/v1.0/`）
8. 《文件編輯Agent開發規劃書.md》（`archive/v1.0/`）

---

## 14. 附錄

### 14.1 術語表

- **DEAS**：Document Editing Agent System（文件編輯 Agent 系統）
- **DEA**：Document Editing Agent（文件編輯 Agent）
- **Intent DSL**：編輯意圖領域特定語言
- **Patch**：文件變更的結構化表示
- **Block Patch**：基於塊（Block）的 Patch 格式
- **Structured Patch**：結構化的 Patch 格式（用於 Excel）
- **DocumentContext**：文件上下文（包含 doc_id、version_id 等）
- **Draft State**：草稿狀態（未提交的編輯）
- **Commit**：提交（將草稿狀態應用到正式版本）
- **Rollback**：回滾（恢復到之前的版本）

### 14.2 縮寫對照

- **MD**：Markdown
- **XLS**：Excel（.xlsx 或 .xls）
- **PDF**：Portable Document Format
- **DOCX**：Microsoft Word 文檔格式
- **GFM**：GitHub Flavored Markdown
- **MCP**：Model Context Protocol
- **AST**：Abstract Syntax Tree（抽象語法樹）
- **OCR**：Optical Character Recognition（光學字符識別）
- **PII**：Personally Identifiable Information（個人可識別信息）

---

**文件版本**: v2.2
**最後更新日期**: 2026-01-21 13:50 UTC+8
**維護人**: Daniel Chung
