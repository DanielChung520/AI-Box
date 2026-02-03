#!/bin/bash
# 诊断 KA-Agent 调用问题
# 检查各个环节是否正常

echo "=================================="
echo "KA-Agent 系统诊断"
echo "=================================="
echo ""

# 1. 检查 FastAPI 进程
echo "[1] 检查 FastAPI 进程状态..."
if ps aux | grep -q "[u]vicorn.*8000"; then
    echo "  ✅ FastAPI 正在运行"
    ps aux | grep "[u]vicorn.*8000" | awk '{print "     PID:", $2, "启动时间:", $9}'
else
    echo "  ❌ FastAPI 未运行！"
    echo "     请运行: ./scripts/start_services.sh api"
fi
echo ""

# 2. 检查日志文件
echo "[2] 检查日志文件..."
if [ -f "logs/fastapi.log" ]; then
    size=$(du -h logs/fastapi.log | awk '{print $1}')
    mod_time=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" logs/fastapi.log)
    echo "  ✅ fastapi.log 存在 (大小: $size, 修改时间: $mod_time)"
else
    echo "  ❌ fastapi.log 不存在！"
fi

if [ -f "logs/agent.log" ]; then
    size=$(du -h logs/agent.log | awk '{print $1}')
    mod_time=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" logs/agent.log)
    echo "  ✅ agent.log 存在 (大小: $size, 修改时间: $mod_time)"
else
    echo "  ❌ agent.log 不存在！"
fi
echo ""

# 3. 检查 KA-Agent 注册状态
echo "[3] 检查 KA-Agent 注册状态..."
if grep -q "ka-agent.*registered successfully" logs/agent.log 2>/dev/null; then
    echo "  ✅ KA-Agent 已注册"
    grep "ka-agent.*registered" logs/agent.log | tail -1
else
    echo "  ❌ 未找到 KA-Agent 注册记录"
fi
echo ""

# 4. 检查最近的前端请求
echo "[4] 检查最近的聊天请求..."
last_chat=$(grep -i "chat.*stream\|POST.*chat" logs/fastapi.log 2>/dev/null | tail -1)
if [ -n "$last_chat" ]; then
    echo "  最后一次聊天请求:"
    echo "     $last_chat"
else
    echo "  ❌ 未找到聊天请求记录"
    echo "     可能前端请求未到达后端"
fi
echo ""

# 5. 检查是否有 KA-Agent 执行记录
echo "[5] 检查 KA-Agent 执行记录..."
if grep -q "chosen_agent.*ka-agent\|Internal agent.*ka-agent" logs/fastapi.log 2>/dev/null; then
    echo "  ✅ 找到 KA-Agent 执行记录："
    grep "chosen_agent.*ka-agent\|Internal agent.*ka-agent" logs/fastapi.log | tail -3
else
    echo "  ❌ 没有 KA-Agent 执行记录！"
    echo "     这是问题的关键：KA-Agent 没有被选中"
fi
echo ""

# 6. 检查 Task Analyzer 执行
echo "[6] 检查 Task Analyzer 执行..."
if grep -q "Task.Analyzer\|semantic.understanding" logs/fastapi.log 2>/dev/null; then
    echo "  ✅ 找到 Task Analyzer 执行记录"
else
    echo "  ⚠️ 没有 Task Analyzer 执行记录"
    echo "     可能 Task Analyzer 没有被触发"
fi
echo ""

# 7. 总结
echo "=================================="
echo "诊断总结"
echo "=================================="
echo ""

if ! grep -q "chosen_agent.*ka-agent" logs/fastapi.log 2>/dev/null; then
    echo "🚨 主要问题：KA-Agent 没有被选中！"
    echo ""
    echo "可能原因："
    echo "  1. Task Analyzer 没有被触发"
    echo "  2. Knowledge Signal Mapper 没有识别知识库查询"
    echo "  3. Decision Engine 没有选择 KA-Agent"
    echo ""
    echo "建议："
    echo "  1. 运行 ./monitor_ka_agent.sh 实时监控"
    echo "  2. 在前端重新发送查询"
    echo "  3. 观察日志输出，定位具体问题"
else
    echo "✅ KA-Agent 调用链路正常"
    echo ""
    echo "如果前端仍然失败，可能是："
    echo "  1. Agent 执行结果未正确注入到 LLM 上下文"
    echo "  2. LLM 忽略了检索结果"
fi
echo ""
echo "=================================="
