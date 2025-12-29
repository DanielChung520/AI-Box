#!/bin/bash

# Docker 服务清理脚本
# 创建日期: 2025-12-29
# 创建人: Daniel Chung
# 功能: 清理重复和旧的 Docker 容器，重启必要的服务

set -e

echo "=== Docker 服务清理脚本 ==="
echo ""

# 重启 ArangoDB
echo "1. 重启 ArangoDB..."
if docker ps -a --format "{{.Names}}" | grep -q "^arangodb$"; then
    docker start arangodb
    sleep 2
    echo "   ✅ ArangoDB 已重启"
else
    echo "   ⚠️  ArangoDB 容器不存在"
fi

# 停止并删除 ChromaDB 重复容器
echo "2. 清理 ChromaDB 重复容器..."
if docker ps -a --format "{{.Names}}" | grep -q "^optimistic_jang$"; then
    docker stop optimistic_jang 2>/dev/null || true
    docker rm optimistic_jang 2>/dev/null || true
    echo "   ✅ ChromaDB 重复容器已删除"
else
    echo "   ℹ️  ChromaDB 重复容器不存在"
fi

# 删除 ArangoDB 重复容器
echo "3. 清理 ArangoDB 重复容器..."
if docker ps -a --format "{{.Names}}" | grep -q "^trusting_hermann$"; then
    docker rm trusting_hermann 2>/dev/null || true
    echo "   ✅ ArangoDB 重复容器已删除"
else
    echo "   ℹ️  ArangoDB 重复容器不存在"
fi

# 删除 Redis 旧容器
echo "4. 清理 Redis 旧容器..."
removed=0
if docker ps -a --format "{{.Names}}" | grep -q "^quirky_sammet$"; then
    docker rm quirky_sammet 2>/dev/null || true
    removed=$((removed + 1))
fi
if docker ps -a --format "{{.Names}}" | grep -q "^wizardly_albattani$"; then
    docker rm wizardly_albattani 2>/dev/null || true
    removed=$((removed + 1))
fi
if [ $removed -gt 0 ]; then
    echo "   ✅ Redis 旧容器已删除 ($removed 个)"
else
    echo "   ℹ️  Redis 旧容器不存在"
fi

# 显示最终状态
echo ""
echo "=== 清理完成，当前容器状态 ==="
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== 服务健康检查 ==="
docker ps --format "  {{.Names}}: {{.Status}}" | grep -E "redis|arangodb|chromadb"
