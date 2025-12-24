#!/bin/bash
# 代碼功能說明: 生成週報摘要腳本，從工作管制表提取本週進度
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROL_TABLE="${PROJECT_ROOT}/docs/PROJECT_CONTROL_TABLE.md"
WEEKLY_DIR="${PROJECT_ROOT}/docs/progress/weekly"
DATE=$(date +%Y-%m-%d)
WEEK_NUM=$(date +%V)

mkdir -p "$WEEKLY_DIR"

OUTPUT_FILE="${WEEKLY_DIR}/summary-week-${WEEK_NUM}-${DATE}.md"

echo "=========================================="
echo "生成週報摘要"
echo "=========================================="
echo ""

cat > "$OUTPUT_FILE" << EOF
# 週報摘要 - 第 ${WEEK_NUM} 週

**生成日期**: ${DATE}
**週次**: 第 ${WEEK_NUM} 週
**報告期間**: $(date -v-6d +%Y-%m-%d) 至 ${DATE}

---

## 本週進度總覽

### 階段進度

$(grep -A 7 "階段總覽" "$CONTROL_TABLE" | grep "階段" | head -6 | sed 's/^/| /')

### 里程碑狀態

$(grep -A 9 "里程碑追蹤" "$CONTROL_TABLE" | grep "M[0-9]" | head -8 | sed 's/^/| /')

---

## 本週完成工作

### 階段一：基礎建設階段

$(grep -A 8 "階段一.*工作項詳情" "$CONTROL_TABLE" | grep "1\." | head -7 | sed 's/^/| /')

---

## 風險與問題

$(grep -A 6 "風險追蹤" "$CONTROL_TABLE" | grep "R[0-9]" | head -4 | sed 's/^/| /')

---

## 下週計劃

- [ ] 繼續階段一工作項部署和測試
- [ ] 準備階段二開發環境
- [ ] 更新工作管制表

---

**生成時間**: $(date '+%Y-%m-%d %H:%M:%S')

EOF

echo -e "\033[0;32m✅ 週報摘要已生成: ${OUTPUT_FILE}\033[0m"
echo ""
