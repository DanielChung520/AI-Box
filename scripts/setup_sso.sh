#!/bin/bash
# 代碼功能說明: 快速設置 AI-Box SSO 腳本
# 創建日期: 2026-01-18 14:09 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 14:09 UTC+8

set -e

echo "================================"
echo "AI-Box SSO 快速設置"
echo "================================"
echo ""

# 1. 檢查必要的工具
echo "📋 檢查必要的工具..."
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 未安裝"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker 未安裝"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose 未安裝"; exit 1; }
echo "✅ 所有必要的工具已安裝"
echo ""

# 2. 生成隨機密鑰
echo "🔑 生成隨機密鑰..."
OAUTH2_CLIENT_SECRET=$(openssl rand -hex 32)
OAUTH2_COOKIE_SECRET=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)

echo "✅ 密鑰生成成功"
echo "   OAUTH2_CLIENT_SECRET=${OAUTH2_CLIENT_SECRET:0:16}..."
echo "   OAUTH2_COOKIE_SECRET=${OAUTH2_COOKIE_SECRET:0:16}..."
echo "   JWT_SECRET=${JWT_SECRET:0:16}..."
echo ""

# 3. 更新 .env 文件
echo "📝 更新 .env 文件..."

# 創建或更新 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，從示例複製..."
    cp .env.example .env 2>/dev/null || true
fi

# 追加 SSO 配置（如果不存在）
if ! grep -q "OAUTH2_CLIENT_ID" .env; then
    cat >> .env << EOF

# ============================================
# OAuth2 SSO 配置（用於 Grafana/Prometheus SSO）
# ============================================
OAUTH2_CLIENT_ID=ai-box-oauth2-client
OAUTH2_CLIENT_SECRET=${OAUTH2_CLIENT_SECRET}
OAUTH2_COOKIE_SECRET=${OAUTH2_COOKIE_SECRET}
JWT_SECRET=${JWT_SECRET}
GRAFANA_URL=http://localhost:3001
PROMETHEUS_URL=http://localhost:9090
EOF
    echo "✅ 已添加 SSO 配置到 .env"
else
    echo "ℹ️  .env 文件中已存在 SSO 配置，跳過"
fi
echo ""

# 4. 創建必要的目錄
echo "📁 創建必要的目錄..."
mkdir -p monitoring/oauth2-proxy
mkdir -p monitoring/grafana/provisioning/datasources
echo "✅ 目錄創建成功"
echo ""

# 5. 更新 Grafana admin 密碼
echo "🔐 更新 Grafana admin 密碼..."
GRAFANA_ADMIN_PASSWORD=$(openssl rand -hex 16)
sed -i '' "s/GF_SECURITY_ADMIN_PASSWORD=admin/GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}/" docker-compose.monitoring.yml
echo "✅ Grafana admin 密碼已更新"
echo "   🔑 密碼: ${GRAFANA_ADMIN_PASSWORD}"
echo "   ⚠️  請記住此密碼！"
echo ""

# 6. 啟動監控服務
echo "🚀 啟動監控服務..."
docker-compose -f docker-compose.monitoring.yml up -d
echo "✅ 監控服務已啟動"
echo ""

# 7. 等待服務就緒
echo "⏳ 等待服務就緒..."
sleep 10

# 檢查服務狀態
echo "📊 檢查服務狀態..."
docker-compose -f docker-compose.monitoring.yml ps
echo ""

# 8. 顯示摘要
echo "================================"
echo "✅ SSO 設置完成"
echo "================================"
echo ""
echo "📋 下一步："
echo ""
echo "1. 啟動 AI-Box 服務："
echo "   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "2. 創建 system_admin 用戶（如果不存在）："
echo "   curl -X POST http://localhost:8000/api/v1/auth/register \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"username\":\"system_admin\",\"password\":\"YourPassword\",\"email\":\"admin@ai-box.local\",\"roles\":[\"system_admin\"]}'"
echo ""
echo "3. 登錄 AI-Box："
echo "   http://localhost:5173/login"
echo ""
echo "4. 訪問監控工具："
echo "   http://localhost:5173/admin/monitoring-tools"
echo ""
echo "⚠️  重要："
echo "   - 只有擁有 system_admin 角色的用戶才能訪問監控工具"
echo "   - OAuth2 密鑰已保存到 .env 文件，請妥善保管"
echo "   - Grafana admin 密碼: ${GRAFANA_ADMIN_PASSWORD}"
echo ""
echo "📚 更多信息："
echo "   查看 SSO 集成指南：docs/系統設計文檔/核心組件/系統管理/AI-Box-SSO集成指南.md"
echo ""
echo "================================"
