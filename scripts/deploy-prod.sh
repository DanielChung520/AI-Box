#!/bin/bash
# 代碼功能說明: 生產環境部署腳本
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 檢查環境變數
check_environment() {
    log_info "檢查環境變數..."

    required_vars=(
        "ARANGO_ROOT_PASSWORD"
        "CORS_ORIGINS"
        "API_PORT"
    )

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "環境變數 $var 未設置"
            exit 1
        fi
    done

    log_success "環境變數檢查完成"
}

# 檢查依賴
check_dependencies() {
    log_info "檢查系統依賴..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安裝"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安裝"
        exit 1
    fi

    log_success "系統依賴檢查完成"
}

# 創建必要目錄
create_directories() {
    log_info "創建必要目錄..."

    mkdir -p config
    mkdir -p logs
    mkdir -p data/uploads

    # 創建 .env 文件如果不存在
    if [[ ! -f .env ]]; then
        log_warning ".env 文件不存在，創建範本..."
        cat > .env << EOF
# AI-Box 生產環境配置
ENV=production
LOG_LEVEL=INFO

# API 配置
API_PORT=8000
CORS_ORIGINS=https://yourdomain.com

# 資料庫配置
ARANGO_ROOT_PASSWORD=your_secure_password_here
OLLAMA_HOST=http://ollama:11434
REDIS_HOST=redis:6379
CHROMADB_HOST=chromadb:8000
SEAWEEDFS_HOST=seaweedfs:8333

# 其他配置
TAG=latest
EOF
        log_warning "請編輯 .env 文件並設置正確的密碼"
    fi

    log_success "目錄創建完成"
}

# 構建鏡像
build_images() {
    log_info "構建 Docker 鏡像..."

    # 獲取標籤
    TAG=${TAG:-latest}

    # 構建 API 鏡像
    docker build -f Dockerfile.prod -t ai-box/api:$TAG .

    log_success "鏡像構建完成"
}

# 啟動服務
start_services() {
    log_info "啟動生產服務..."

    # 停止現有服務
    docker-compose -f docker-compose.prod.yml down || true

    # 啟動服務
    docker-compose -f docker-compose.prod.yml up -d

    log_success "服務啟動完成"
}

# 等待服務就緒
wait_for_services() {
    log_info "等待服務就緒..."

    # 等待 API 服務
    log_info "等待 API 服務..."
    for i in {1..30}; do
        if curl -f http://localhost:${API_PORT:-8000}/health &>/dev/null; then
            log_success "API 服務就緒"
            break
        fi
        sleep 10
    done

    # 等待其他服務
    services=("redis:6379" "arangodb:8529" "chromadb:8001" "seaweedfs:8333")
    for service in "${services[@]}"; do
        host=$(echo $service | cut -d: -f1)
        port=$(echo $service | cut -d: -f2)
        log_info "等待 $host:$port..."
        for i in {1..30}; do
            if nc -z $host $port 2>/dev/null; then
                log_success "$host:$port 就緒"
                break
            fi
            sleep 5
        done
    done

    log_success "所有服務就緒"
}

# 運行健康檢查
run_health_checks() {
    log_info "運行健康檢查..."

    # API 健康檢查
    if curl -f http://localhost:${API_PORT:-8000}/health; then
        log_success "API 健康檢查通過"
    else
        log_error "API 健康檢查失敗"
        exit 1
    fi

    # LangGraph 健康檢查
    if curl -f http://localhost:${API_PORT:-8000}/langgraph/health; then
        log_success "LangGraph 健康檢查通過"
    else
        log_error "LangGraph 健康檢查失敗"
        exit 1
    fi

    log_success "健康檢查完成"
}

# 顯示部署信息
show_deployment_info() {
    log_success "部署完成！"
    echo ""
    echo "服務信息:"
    echo "  API: http://localhost:${API_PORT:-8000}"
    echo "  LangGraph: http://localhost:${API_PORT:-8000}/langgraph"
    echo "  ArangoDB: http://localhost:8529"
    echo "  ChromaDB: http://localhost:8001"
    echo "  Redis: localhost:6379"
    echo "  SeaweedFS: http://localhost:8333"
    echo ""
    echo "日誌查看:"
    echo "  docker-compose -f docker-compose.prod.yml logs -f"
    echo ""
    echo "停止服務:"
    echo "  docker-compose -f docker-compose.prod.yml down"
}

# 主函數
main() {
    log_info "開始 AI-Box 生產環境部署..."

    check_environment
    check_dependencies
    create_directories
    build_images
    start_services
    wait_for_services
    run_health_checks
    show_deployment_info

    log_success "AI-Box 生產環境部署成功！"
}

# 解析命令行參數
case "${1:-}" in
    "build")
        check_dependencies
        build_images
        ;;
    "start")
        check_environment
        start_services
        wait_for_services
        ;;
    "stop")
        log_info "停止服務..."
        docker-compose -f docker-compose.prod.yml down
        log_success "服務已停止"
        ;;
    "restart")
        check_environment
        log_info "重啟服務..."
        docker-compose -f docker-compose.prod.yml restart
        wait_for_services
        run_health_checks
        ;;
    "logs")
        docker-compose -f docker-compose.prod.yml logs -f
        ;;
    "status")
        docker-compose -f docker-compose.prod.yml ps
        ;;
    *)
        main
        ;;
esac