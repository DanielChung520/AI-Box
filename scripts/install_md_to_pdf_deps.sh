#!/bin/bash

# 安裝 Markdown to PDF 所需依賴
# 創建日期: 2026-01-23
# 創建人: Daniel Chung

set -e

echo "======================================"
echo "Markdown to PDF 依賴安裝腳本"
echo "======================================"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 函數：檢查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. 安裝 Pandoc
echo ""
echo "1. 檢查 Pandoc..."
if command_exists pandoc; then
    echo -e "${GREEN}✓ Pandoc 已安裝: $(pandoc --version | head -1)${NC}"
else
    echo -e "${YELLOW}正在安裝 Pandoc...${NC}"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install pandoc
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        wget -q https://github.com/jgm/pandoc/releases/download/3.1.13/pandoc-3.1.13-1-amd64.deb
        sudo dpkg -i pandoc-3.1.13-1-amd64.deb
        rm pandoc-3.1.13-1-amd64.deb
    else
        echo -e "${RED}不支援的作業系統，請手動安裝 Pandoc${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Pandoc 安裝完成${NC}"
fi

# 2. 安裝 Mermaid CLI (mmdc)
echo ""
echo "2. 檢查 Mermaid CLI..."
if command_exists mmdc; then
    echo -e "${GREEN}✓ Mermaid CLI 已安裝: $(mmdc --version 2>&1 | head -1)${NC}"
else
    echo -e "${YELLOW}正在安裝 Mermaid CLI...${NC}"
    
    npm install -g @mermaid-js/mermaid-cli
    echo -e "${GREEN}✓ Mermaid CLI 安裝完成${NC}"
fi

# 3. 安裝 Python 依賴
echo ""
echo "3. 檢查 Python 依賴..."
if python3 -c "import weasyprint" 2>/dev/null; then
    echo -e "${GREEN}✓ Weasyprint 已安裝${NC}"
else
    echo -e "${YELLOW}正在安裝 Weasyprint...${NC}"
    
    # 檢查系統依賴
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS 需要額外的系統庫
        brew install pango cairo
        # 使用 pipx 或虛擬環境安裝
        pip3 install weasyprint --break-system-packages || \
        pip3 install weasyprint
    else
        pip3 install weasyprint
    fi
    
    if python3 -c "import weasyprint" 2>/dev/null; then
        echo -e "${GREEN}✓ Weasyprint 安裝完成${NC}"
    else
        echo -e "${YELLOW}⚠ Weasyprint 安裝遇到問題，但 Pandoc + HTML 仍可正常運作${NC}"
    fi
fi

# 4. 安裝 md-to-pdf (Node.js)
echo ""
echo "4. 檢查 md-to-pdf..."
if command_exists md-to-pdf; then
    echo -e "${GREEN}✓ md-to-pdf 已安裝: $(md-to-pdf --version)${NC}"
else
    echo -e "${YELLOW}正在安裝 md-to-pdf...${NC}"
    npm install -g md-to-pdf
    echo -e "${GREEN}✓ md-to-pdf 安裝完成${NC}"
fi

# 5. 驗證安裝
echo ""
echo "======================================"
echo "安裝狀態驗證"
echo "======================================"

STATUS=0

echo ""
echo "md-to-pdf: $(command_exists md-to-pdf && echo '✓ OK (推薦)' || echo '✗ MISSING')"
echo "Pandoc: $(command_exists pandoc && echo '✓ OK' || echo '✗ MISSING')"
echo "Mermaid CLI: $(command_exists mmdc && echo '✓ OK' || echo '✗ MISSING')"
echo "Weasyprint: $(python3 -c 'import weasyprint' 2>/dev/null && echo '✓ OK' || echo '⚠ OPTIONAL')"

if command_exists md-to-pdf || (command_exists mmdc && command_exists pandoc); then
    echo ""
    echo -e "${GREEN}至少一種轉換方案已就緒！${NC}"
else
    echo ""
    echo -e "${RED}無法安裝任何 PDF 轉換工具，請參考錯誤信息${NC}"
    STATUS=1
fi

echo ""
echo "======================================"
echo "可用轉換模式"
echo "======================================"
echo ""
echo "1. md-to-pdf (Node.js - 推薦)"
echo "   - 內建 Chromium，樣式美觀"
echo "   - 支援自動分頁"
echo ""
echo "2. Pandoc + LaTeX"
echo "   - 支援完整 PDF 格式"
echo "   - 需要 sudo 安裝 LaTeX"
echo ""
echo "3. Pandoc + Weasyprint (Python)"
echo "   - 不需要 LaTeX"
echo "   - 需要系統依賴 (pango, cairo)"
echo ""
echo "3. Pandoc → HTML → 瀏覽器列印"
echo "   - 最簡單的方案"
echo "   - 開啟 HTML 檔案 → 右鍵 → 列印為 PDF"

echo ""
echo "======================================"
echo "快速使用"
echo "======================================"
echo ""
echo "# 轉換 Markdown 為 PDF"
echo "python3 scripts/test_md_to_pdf.py"
echo ""
echo "# 或直接使用 API"
echo "from agents.builtin.md_to_pdf.agent import MdToPdfAgent"

echo ""
echo "======================================"
echo "安裝腳本執行完成"
echo "======================================"
