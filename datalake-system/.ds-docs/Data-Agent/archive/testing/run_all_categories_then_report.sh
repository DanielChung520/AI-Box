#!/usr/bin/env bash
# 依類別執行全部測試並產出「統一報告」
# 用法: ./run_all_categories_then_report.sh
# 或: bash run_all_categories_then_report.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JSON_PATH="${SCRIPT_DIR}/Data-Agent-100場景-合併結果.json"
# 移除舊合併結果，從頭累積
rm -f "$JSON_PATH"

for cat in A B C D E F G H I J; do
  echo ""
  echo ">>> 執行類別 $cat ..."
  python3 "$SCRIPT_DIR/run_full_tests.py" --category "$cat" --output-json "$JSON_PATH" < /dev/null || true
done

echo ""
echo ">>> 產出統一報告 ..."
python3 "$SCRIPT_DIR/run_full_tests.py" --from-json "$JSON_PATH" --report-only < /dev/null

echo ""
echo "完成。統一報告見: ${SCRIPT_DIR}/Data-Agent-100場景測試報告-新結構-統一-*.md"
