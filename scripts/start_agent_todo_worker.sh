#!/usr/bin/env bash
# MM-Agent RQ Task Worker Startup Script
# 专门处理 agent_todo 队列

set -e

cd /home/daniel/ai-box

# 加载环境变量
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 验证配置
if [ -z "$AI_BOX_CONFIG_PATH" ]; then
    export AI_BOX_CONFIG_PATH=/home/daniel/ai-box/config/config.json
fi

echo "[RQ-Worker] AI_BOX_CONFIG_PATH: $AI_BOX_CONFIG_PATH"

# venv Python 路径
VENV_PYTHON="/home/daniel/ai-box/venv/bin/python"

# 验证 venv Python 存在
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Error: venv Python not found at $VENV_PYTHON"
    exit 1
fi

echo "✅ Using venv Python: $VENV_PYTHON"

# 验证 required modules
echo "🔍 Verifying required modules..."
REQUIRED_MODULES="rq redis httpx"
MISSING_MODULES=""

for module in $REQUIRED_MODULES; do
    if ! "$VENV_PYTHON" -c "import $module" 2>/dev/null; then
        MISSING_MODULES="$MISSING_MODULES $module"
    fi
done

if [ -n "$MISSING_MODULES" ]; then
    echo "❌ Error: Missing modules:$MISSING_MODULES"
    echo "📦 Installing missing modules..."
    "$VENV_PYTHON" -m pip install $MISSING_MODULES
fi

echo "✅ All required modules available"

# 创建 logs 目录
mkdir -p logs

echo "🚀 Starting MM-Agent RQ Task Worker..."

# 启动 worker，队列名称放在最后
exec "$VENV_PYTHON" workers/agent_todo_worker.py \
    --host localhost \
    --port 6379 \
    --name rq_worker_agent_todo \
    agent_todo
