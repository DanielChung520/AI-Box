#!/bin/bash
# 快速測試腳本 - 交付前必須執行

echo "========================================"
echo "  前端組件快速測試"
echo "========================================"
echo ""

COMPONENT=$1
if [ -z "$COMPONENT" ]; then
    echo "用法: ./test_component_quick.sh 组件名稱"
    echo "範例: ./test_component_quick.sh KnowledgeBaseModal"
    exit 1
fi

FILE="/home/daniel/ai-box/ai-bot/src/components/$COMPONENT.tsx"

if [ ! -f "$FILE" ]; then
    echo "❌ 檔案不存在: $FILE"
    exit 1
fi

echo "1. 測試檔案: $COMPONENT.tsx"
echo ""

# 1. 檢查 React import
echo "   [1] React hooks import 檢查..."
HOOKS=$(grep -oE "useState|useEffect|useRef|useCallback|useMemo" "$FILE" | sort -u)
IMPORT_LINE=$(head -20 "$FILE" | grep "import.*from 'react'")
MISSING=""
for HOOK in $HOOKS; do
    if ! echo "$IMPORT_LINE" | grep -q "$HOOK"; then
        MISSING="$MISSING $HOOK"
    fi
done
if [ -z "$MISSING" ]; then
    echo "      ✅ 所有 hooks 都有 import"
else
    echo "      ❌ 缺少 hooks:$MISSING"
fi

# 2. 檢查文件頭註釋
echo ""
echo "   [2] 文件頭註釋檢查..."
if head -10 "$FILE" | grep -q "代碼功能說明"; then
    echo "      ✅ 文件頭註釋存在"
else
    echo "      ⚠️  缺少文件頭註釋"
fi

# 3. 檢查 API endpoint
echo ""
echo "   [3] API endpoint 檢查..."
if grep -q "fetch\|API_BASE" "$FILE"; then
    API_URLS=$(grep -oE "fetch\(['\"][^'\"]+['\"]|API_BASE" "$FILE" | head -3)
    echo "      發現 API 調用:"
    echo "$API_URLS" | while read line; do
        echo "        - $line"
    done
else
    echo "      ✅ 無 API 調用"
fi

# 4. Vite 編譯測試
echo ""
echo "   [4] Vite 編譯測試..."
cd /home/daniel/ai-box/ai-bot
BUILD_OUTPUT=$(timeout 60 npx vite build 2>&1)
BUILD_RESULT=$?

if [ $BUILD_RESULT -eq 0 ]; then
    echo "      ✅ Vite 編譯成功"
    ERRORS=$(echo "$BUILD_OUTPUT" | grep -E "$COMPONENT" | grep -i "error" | wc -l)
    if [ "$ERRORS" -gt 0 ]; then
        echo "      ⚠️  發現 $ERRORS 個相關錯誤"
        echo "$BUILD_OUTPUT" | grep -E "$COMPONENT" | grep -i "error" | head -5
    fi
else
    echo "      ❌ Vite 編譯失敗"
    echo "$BUILD_OUTPUT" | grep -i "error" | head -10
fi

echo ""
echo "========================================"
echo "  測試完成"
echo "========================================"
