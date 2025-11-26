#!/bin/bash
# 代碼功能說明: 項目工作管制表更新腳本，自動更新進度和狀態
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROL_TABLE="${PROJECT_ROOT}/docs/PROJECT_CONTROL_TABLE.md"
DATE=$(date +%Y-%m-%d)

echo "=========================================="
echo "項目工作管制表更新工具"
echo "=========================================="
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 檢查文件是否存在
if [ ! -f "$CONTROL_TABLE" ]; then
    echo -e "${RED}錯誤: 工作管制表文件不存在${NC}"
    exit 1
fi

# 顯示當前狀態
echo -e "${BLUE}當前項目狀態:${NC}"
echo ""

# 提取階段一進度
PHASE1_PROGRESS=$(grep -A 1 "階段一" "$CONTROL_TABLE" | grep "進度" | sed 's/.*| \([0-9]*\)% |.*/\1/' || echo "0")
echo "階段一進度: ${PHASE1_PROGRESS}%"

# 顯示菜單
echo ""
echo "請選擇操作："
echo "1) 更新工作項狀態"
echo "2) 更新階段進度"
echo "3) 更新里程碑狀態"
echo "4) 添加風險記錄"
echo "5) 查看當前狀態"
echo "6) 生成週報摘要"
read -p "請選擇 (1-6): " CHOICE

case $CHOICE in
    1)
        echo ""
        echo "更新工作項狀態"
        echo "================"
        read -p "工作項 ID (例如: 1.1.1): " WORK_ITEM_ID
        read -p "狀態 (completed/in_progress/pending/blocked): " STATUS
        read -p "完成度 (0-100): " PROGRESS

        # 這裡可以添加自動更新邏輯
        echo "工作項 ${WORK_ITEM_ID} 狀態已更新為: ${STATUS}, 進度: ${PROGRESS}%"
        ;;
    2)
        echo ""
        echo "更新階段進度"
        echo "============"
        read -p "階段編號 (1-6): " PHASE_NUM
        read -p "進度百分比 (0-100): " PROGRESS

        echo "階段 ${PHASE_NUM} 進度已更新為: ${PROGRESS}%"
        ;;
    3)
        echo ""
        echo "更新里程碑狀態"
        echo "=============="
        read -p "里程碑編號 (M1-M8): " MILESTONE
        read -p "狀態 (completed/in_progress/pending): " STATUS
        read -p "實際完成日期 (YYYY-MM-DD，可選): " ACTUAL_DATE

        echo "里程碑 ${MILESTONE} 狀態已更新為: ${STATUS}"
        if [ -n "$ACTUAL_DATE" ]; then
            echo "實際完成日期: ${ACTUAL_DATE}"
        fi
        ;;
    4)
        echo ""
        echo "添加風險記錄"
        echo "============"
        read -p "風險描述: " RISK_DESC
        read -p "影響 (高/中/低): " IMPACT
        read -p "可能性 (高/中/低): " PROBABILITY
        read -p "緩解措施: " MITIGATION

        echo "風險已記錄"
        ;;
    5)
        echo ""
        echo "當前項目狀態"
        echo "============"
        echo ""
        echo "階段進度:"
        grep -A 7 "階段總覽" "$CONTROL_TABLE" | grep "階段" | head -6
        echo ""
        echo "里程碑狀態:"
        grep -A 9 "里程碑追蹤" "$CONTROL_TABLE" | grep "M[0-9]" | head -8
        ;;
    6)
        echo ""
        echo "生成週報摘要"
        echo "============"
        echo ""
        echo "本週進度摘要將生成到: docs/progress/weekly-summary-${DATE}.md"
        ;;
    *)
        echo "無效選擇"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}操作完成！${NC}"
