#!/bin/bash
#===============================================================================
# System Architecture Agent - 文檔查詢腳本 (MVP)
#
# 功能：
# 根據關鍵字搜尋文檔，返回相關段落
#
# 使用方式：
#   bash scripts/query_arch.sh "文件上傳"
#   bash scripts/query_arch.sh "MoE 模型"
#   bash scripts/query_arch.sh "Qdrant 配置"
#===============================================================================

set -e

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 目錄定義
DOCS_DIR="/Users/daniel/GitHub/AI-Box/docs"
AGENT_DOCS_DIR="/Users/daniel/GitHub/AI-Box/.docs"
INVENTORY_FILE="$AGENT_DOCS_DIR/document_inventory.json"

#-------------------------------------------------------------------------------
# 檢查參數
#-------------------------------------------------------------------------------
if [ -z "$1" ]; then
    echo -e "${RED}錯誤: 請提供搜尋關鍵字${NC}"
    echo ""
    echo "使用方式："
    echo "  $0 \"文件上傳\""
    echo "  $0 \"MoE 模型\""
    echo "  $0 \"Qdrant 配置\""
    exit 1
fi

SEARCH_QUERY="$1"

echo -e "${GREEN}=== System Architecture Agent ===${NC}"
echo -e "${YELLOW}搜尋關鍵字: ${SEARCH_QUERY}${NC}"
echo ""

#-------------------------------------------------------------------------------
# 檢查文檔清單
#-------------------------------------------------------------------------------
if [ ! -f "$INVENTORY_FILE" ]; then
    echo -e "${RED}錯誤: 文檔清單不存在${NC}"
    echo "請先運行："
    echo "  bash scripts/prepare_arch_agent.sh"
    exit 1
fi

#-------------------------------------------------------------------------------
# 使用 Python 進行搜尋
#-------------------------------------------------------------------------------
echo -e "${BLUE}搜尋結果：${NC}"
echo ""

python3 - "$SEARCH_QUERY" "$DOCS_DIR" "$INVENTORY_FILE" << 'PYEOF'
import json
import os
import sys
from pathlib import Path

SEARCH_QUERY = sys.argv[1]
DOCS_DIR = Path(sys.argv[2])
INVENTORY_FILE = Path(sys.argv[3])

# 讀取清單
with open(INVENTORY_FILE, encoding="utf-8") as f:
    inventory = json.load(f)

# 簡單關鍵字搜尋
results = []
for doc in inventory["all_documents"]:
    filepath = DOCS_DIR / doc["path"]

    if not filepath.exists():
        continue

    # 讀取檔案內容
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except:
        continue

    # 搜尋關鍵字
    query_lower = SEARCH_QUERY.lower()
    content_lower = content.lower()

    if query_lower in content_lower:
        # 找到相關內容
        lines = content.split('\n')
        relevant_lines = []

        for i, line in enumerate(lines):
            if query_lower in line.lower():
                # 取得上下文 (前後各 2 行)
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                relevant_lines.extend(lines[start:end])

        # 去重並截取
        unique_lines = []
        seen = set()
        for line in relevant_lines:
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                unique_lines.append(line)

        if unique_lines:
            # 取得標題 (第一個 # 開頭的行)
            title = doc["filename"]
            for line in lines[:20]:
                if line.strip().startswith('#'):
                    title = line.strip().lstrip('#').strip()
                    break

            results.append({
                "file": doc["path"],
                "title": title,
                "relevance": content_lower.count(query_lower),
                "preview": ' ... '.join(unique_lines[:5])
            })
    else:
        # 檢查標題和檔名
        if query_lower in doc["filename"].lower() or query_lower in doc["path"].lower():
            results.append({
                "file": doc["path"],
                "title": doc["filename"],
                "relevance": 1,
                "preview": "（標題或路徑匹配）"
            })

# 排序結果
results.sort(key=lambda x: x["relevance"], reverse=True)

# 輸出結果
if results:
    for i, r in enumerate(results[:10], 1):
        print(f"{i}. {r['title']}")
        print(f"   📄 {r['file']}")
        if r['preview'] and r['preview'] != "（標題或路徑匹配）":
            preview_text = r['preview'][:200].replace('\n', ' ')
            print(f"   💡 {preview_text}...")
        print()

    if len(results) > 10:
        print(f"... 還有 {len(results) - 10} 個相關結果")
else:
    print("未找到相關文檔")

print("-" * 60)
print(f"搜尋完成: {len(results)} 個結果")
PYEOF

echo ""
echo "使用說明："
echo "  - 查看完整文檔: open $DOCS_DIR/相對路徑"
echo "  - 更新文檔清單: bash scripts/prepare_arch_agent.sh"
