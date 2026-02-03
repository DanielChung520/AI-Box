# AI-Box Governed Conversational System Management

## 文檔說明

本文檔有兩種格式：

| 格式 | 檔案 | 說明 |
|------|------|------|
| Markdown | `AI-Box-Governed-Conversational-System-Management.md` | 原始格式，可編輯 |
| HTML | `AI-Box-Governed-Conversational-System-Management.html` | 瀏覽器預覽，可列印為 PDF |
| PDF | `AI-Box-Governed-Conversational-System-Management.pdf` | 最終發布格式 |

## 轉換為 PDF

### 方法 1：瀏覽器列印（推薦）

1. 用瀏覽器打開 `AI-Box-Governed-Conversational-System-Management.html`
2. 按 `Ctrl+P` (Windows/Linux) 或 `Cmd+P` (Mac)
3. 選擇「儲存為 PDF」
4. 設定邊距為「無」或「預設」
5. 儲存

**優點**：Mermaid 圖形會正確渲染，無需額外安裝

### 方法 2：使用指令

```bash
# 進入專案根目錄
cd /Users/daniel/GitHub/AI-Box

# 執行轉換腳本
python3 scripts/test_md_to_pdf.py
```

### 方法 3：手動轉換

```bash
# 安裝依賴
./scripts/install_md_to_pdf_deps.sh

# 轉換為 PDF
python3 -c "
from agents.builtin.md_to_pdf.pandoc_converter import PandocConverter
from pathlib import Path

converter = PandocConverter()
markdown = Path('docs/白皮書/AI-Box-Governed-Conversational-System-Management.md').read_text()
converter.convert(markdown, 'output.pdf', {})
"
```

## Mermaid 圖形

本文檔包含以下 Mermaid 圖形：

1. 架構圖 - 高層架構流程
2. 序列圖 - 時序互動流程
3. MCP 整合圖 - Orchestrator vs Execution

圖形會在 HTML 和 PDF 中自動渲染。

## 更新本文檔

1. 編輯 Markdown 檔案
2. 執行轉換：
   ```bash
   python3 scripts/test_md_to_pdf.py
   ```
3. 或手動重新產生 HTML：
   ```bash
   pandoc docs/白皮書/AI-Box-Governed-Conversational-System-Management.md \
       -o docs/白皮書/AI-Box-Governed-Conversational-System-Management.html \
       --standalone
   ```

## 系統需求

| 依賴 | 版本 | 用途 |
|------|------|------|
| Pandoc | >= 3.0 | LaTeX PDF 生成 (選項 1) |
| md-to-pdf | >= 5.0 | Node.js PDF 生成 (選項 2 - 推薦) |
| Mermaid CLI | >= 11.0 | 圖形渲染 |
| Weasyprint | >= 68.0 | Python PDF 生成 (選項 3) |

## 故障排除

### Mermaid 圖形未顯示

確保 Mermaid CLI 已安裝：
```bash
mmdc --version
```

### PDF 生成失敗

1. 檢查是否有可用的 PDF 引擎：
   ```bash
   # 檢查 md-to-pdf (推薦)
   md-to-pdf --version
   
   # 檢查 Pandoc
   pandoc --version
   ```

2. 執行安裝腳本：
   ```bash
   ./scripts/install_md_to_pdf_deps.sh
   ```

