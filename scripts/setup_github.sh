#!/bin/bash
# 代碼功能說明: GitHub 遠程倉庫設置腳本
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

set -e

echo "=========================================="
echo "GitHub 遠程倉庫設置"
echo "=========================================="
echo ""

# 檢查是否已有遠程倉庫
if git remote | grep -q origin; then
    echo "⚠️  遠程倉庫 'origin' 已存在"
    echo "當前配置："
    git remote -v
    echo ""
    read -p "是否要更新遠程倉庫地址？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote remove origin
        echo "✅ 已移除現有遠程倉庫"
    else
        echo "取消操作"
        exit 0
    fi
fi

# 獲取 GitHub 用戶名
read -p "請輸入您的 GitHub 用戶名: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ 用戶名不能為空"
    exit 1
fi

# 選擇協議
echo ""
echo "請選擇協議："
echo "1) HTTPS (推薦，需要 Personal Access Token)"
echo "2) SSH (需要配置 SSH 密鑰)"
read -p "請選擇 (1/2，默認 1): " PROTOCOL
PROTOCOL=${PROTOCOL:-1}

case $PROTOCOL in
    1)
        REPO_URL="https://github.com/${GITHUB_USERNAME}/AI-Box.git"
        ;;
    2)
        REPO_URL="git@github.com:${GITHUB_USERNAME}/AI-Box.git"
        ;;
    *)
        echo "❌ 無效選擇，使用 HTTPS"
        REPO_URL="https://github.com/${GITHUB_USERNAME}/AI-Box.git"
        ;;
esac

# 添加遠程倉庫
echo ""
echo "添加遠程倉庫: $REPO_URL"
git remote add origin "$REPO_URL"

# 驗證
echo ""
echo "✅ 遠程倉庫設置完成！"
echo ""
echo "當前遠程倉庫配置："
git remote -v

echo ""
echo "=========================================="
echo "下一步操作"
echo "=========================================="
echo ""
echo "1. 在 GitHub 創建倉庫："
echo "   - 訪問: https://github.com/new"
echo "   - 倉庫名稱: AI-Box"
echo "   - 選擇 Private 或 Public"
echo "   - 不要初始化 README、.gitignore 或 license"
echo "   - 點擊 'Create repository'"
echo ""
echo "2. 推送代碼到 GitHub："
echo "   git push -u origin develop"
echo ""
echo "3. 創建 main 分支並推送："
echo "   git checkout -b main"
echo "   git push -u origin main"
echo ""
echo "4. 設置分支保護規則："
echo "   - 訪問: https://github.com/${GITHUB_USERNAME}/AI-Box/settings/branches"
echo "   - 為 main 分支設置保護規則"
echo ""

