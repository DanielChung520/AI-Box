#!/bin/bash
#===============================================================================
# System Architecture Agent - 準備腳本
#
# 功能：
# 1. 清理 .docs 目錄結構
# 2. 生成文檔清單
# 3. 建立向量索引 (未來擴展)
#
# 使用方式：
#   bash scripts/prepare_arch_agent.sh
#   bash scripts/prepare_arch_agent.sh --full  # 包含向量索引
#===============================================================================

set -e

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== System Architecture Agent 準備腳本 ===${NC}"
echo ""

# 目錄定義
DOCS_DIR="/Users/daniel/GitHub/AI-Box/docs"
AGENT_DOCS_DIR="/Users/daniel/GitHub/AI-Box/.docs"
INVENTORY_FILE="$AGENT_DOCS_DIR/document_inventory.json"

#-------------------------------------------------------------------------------
# Step 1: 清理並重置目錄結構
#-------------------------------------------------------------------------------
echo -e "${YELLOW}Step 1: 清理目錄結構...${NC}"

# 刪除不需要的檔案
rm -f "$AGENT_DOCS_DIR/README_20260108.md" 2>/dev/null || true
rm -f "$AGENT_DOCS_DIR/SYSTEM_ARCHITECTURE_AGENT.md" 2>/dev/null || true
rm -f "$AGENT_DOCS_DIR/INDEX.md" 2>/dev/null || true
rm -f "$AGENT_DOCS_DIR/sync_report.json" 2>/dev/null || true
rm -f "$AGENT_DOCS_DIR/sync_report_v2.json" 2>/dev/null || true

# 清理空目錄
for dir in "計劃" "報告" "00-核心架構" "01-Agent平台" "02-文件編輯" \
           "03-文件上傳" "04-存儲架構" "05-監控系統" "06-安全架構" \
           "07-MoE系統" "08-RAG系統" "09-MCP工具" "10-數據庫Schema"; do
    rmdir "$AGENT_DOCS_DIR/03-開發指南/$dir" 2>/dev/null || true
    rmdir "$AGENT_DOCS_DIR/01-系統架構/$dir" 2>/dev/null || true
done

# 重置 .docs 為簡單結構
mkdir -p "$AGENT_DOCS_DIR/01-系統架構"
mkdir -p "$AGENT_DOCS_DIR/02-API文檔"
mkdir -p "$AGENT_DOCS_DIR/03-開發指南"
mkdir -p "$AGENT_DOCS_DIR/04-運維文檔"
mkdir -p "$AGENT_DOCS_DIR/05-測試報告"
mkdir -p "$AGENT_DOCS_DIR/99-歷史歸檔"

echo -e "${GREEN}✅ 目錄結構已重置${NC}"
echo ""

#-------------------------------------------------------------------------------
# Step 2: 生成文檔清單
#-------------------------------------------------------------------------------
echo -e "${YELLOW}Step 2: 生成文檔清單...${NC}"

python3 << 'EOF'
import os
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DOCS_DIR = Path("/Users/daniel/GitHub/AI-Box/docs")
AGENT_DOCS_DIR = Path("/Users/daniel/GitHub/AI-Box/.docs")

# 目錄分類
CATEGORY_MAP = {
    "系統設計文檔/核心組件/文件上傳向量圖譜": "01-系統架構",
    "系統設計文檔/核心組件/系統管理": "04-運維文檔",
    "系統設計文檔/核心組件/Agent平台": "01-系統架構",
    "系統設計文檔/核心組件/存儲架構": "01-系統架構",
    "系統設計文檔/核心組件/語義與任務分析": "01-系統架構",
    "系統設計文檔/核心組件/IEE對話式開發文件編輯": "01-系統架構",
    "系統設計文檔/核心組件/MCP工具": "01-系統架構",
    "系統設計文檔/API文檔": "02-API文檔",
    "开发进度": "03-開發指南",
    "開發過程文件": "03-開發指南",
    "测试报告": "05-測試報告",
    "測試報告": "05-測試報告",
    "运维文档": "04-運維文檔",
    "備份與歸檔": "99-歷史歸檔",
}

EXCLUDE_DIRS = ["archive", "備份與歸檔/文件管理歸檔"]

# 收集文檔
all_docs = []
for filepath in DOCS_DIR.rglob("*.md"):
    path_str = str(filepath)

    # 排除
    if any(ex in path_str for ex in EXCLUDE_DIRS):
        continue

    stat = os.stat(filepath)

    # 決定類別
    category = "01-系統架構"  # 預設
    for key, cat in CATEGORY_MAP.items():
        if key in path_str:
            category = cat
            break

    doc = {
        "path": str(filepath.relative_to(DOCS_DIR)),
        "category": category,
        "filename": filepath.name,
        "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }
    all_docs.append(doc)

# 生成清單
inventory = {
    "generated_at": datetime.now().isoformat(),
    "total_documents": len(all_docs),
    "by_category": {},
    "all_documents": all_docs
}

# 按類別統計
for doc in all_docs:
    cat = doc["category"]
    inventory["by_category"][cat] = inventory["by_category"].get(cat, 0) + 1

# 保存
AGENT_DOCS_DIR.mkdir(parents=True, exist_ok=True)
with open(AGENT_DOCS_DIR / "document_inventory.json", "w", encoding="utf-8") as f:
    json.dump(inventory, f, ensure_ascii=False, indent=2)

print(f"✅ 已生成文檔清單: {len(all_docs)} 個文檔")
for cat, count in inventory["by_category"].items():
    print(f"   {cat}: {count}")
EOF

echo ""

#-------------------------------------------------------------------------------
# Step 3: 創建簡單 README
#-------------------------------------------------------------------------------
echo -e "${YELLOW}Step 3: 創建 README...${NC}"

cat > "$AGENT_DOCS_DIR/README.md" << 'EOF'
# AI-Box 系統文檔

## 目錄結構

| 目錄 | 說明 | 文檔數 |
|------|------|--------|
| 01-系統架構 | 架構設計、規格書、Schema | - |
| 02-API文檔 | API 規格和接口定義 | - |
| 03-開發指南 | 開發規範和指南 | - |
| 04-運維文檔 | 部署和運維指南 | - |
| 05-測試報告 | 測試計劃和報告 | - |
| 99-歷史歸檔 | 歸檔的舊版本文檔 | - |

**維護命令**

```bash
# 更新文檔清單
bash scripts/prepare_arch_agent.sh

# 生成向量索引（未來擴展）
bash scripts/prepare_arch_agent.sh --vector
```

---
*最後更新: 2026-01-20*
EOF

echo -e "${GREEN}✅ README 已創建${NC}"
echo ""

#-------------------------------------------------------------------------------
# 完成
#-------------------------------------------------------------------------------
echo -e "${GREEN}=== 準備完成 ===${NC}"
echo ""
echo "下一步："
echo "  1. 查看文檔清單: cat $INVENTORY_FILE"
echo "  2. 測試查詢: python3 scripts/query_arch.py '文件上傳流程'"
echo "  3. 未來擴展: bash scripts/prepare_arch_agent.sh --vector"
echo ""

#-------------------------------------------------------------------------------
# 參數處理
#-------------------------------------------------------------------------------
if [ "$1" == "--vector" ]; then
    echo -e "${YELLOW}未來擴展：向量索引功能${NC}"
    echo "  需要時可實現："
    echo "  - 使用 Qdrant 存儲文檔向量"
    echo "  - 提供語義搜尋功能"
fi
