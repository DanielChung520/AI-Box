#!/bin/bash
# 停止批量处理脚本

echo "查找批量处理脚本进程..."
PID=$(ps aux | grep "kg_extract_all_with_progress.py" | grep -v grep | awk '{print $2}')

if [ -z "$PID" ]; then
    echo "✅ 没有找到运行中的批量处理脚本"
    exit 0
fi

echo "找到进程: PID=$PID"
echo "正在优雅停止（发送 SIGTERM 信号）..."
kill -TERM $PID

# 等待进程退出（最多等待 10 秒）
for i in {1..10}; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "✅ 进程已优雅退出"
        exit 0
    fi
    sleep 1
done

# 如果还在运行，强制中止
if ps -p $PID > /dev/null 2>&1; then
    echo "⚠️  进程未在 10 秒内退出，强制中止..."
    kill -9 $PID
    echo "✅ 进程已强制中止"
else
    echo "✅ 进程已退出"
fi
