#!/bin/bash
# 实时监控 FastAPI 和 Agent 日志
# 用于诊断前端知识库查询问题

echo "=================================="
echo "KA-Agent 调用链路实时监控"
echo "=================================="
echo ""
echo "准备监控日志..."
echo ""
echo "请在前端输入查询："
echo "  告诉我你的知识库或文件区有多少文件？"
echo ""
echo "=================================="
echo ""

# 清空之前的输出
> /tmp/ka_agent_monitor.log

# 监控 fastapi.log 和 agent.log
tail -f logs/fastapi.log logs/agent.log 2>/dev/null | while read line; do
    # 检查关键词
    if echo "$line" | grep -iq "task.analyzer\|semantic\|knowledge\|chosen_agent\|ka-agent\|internal.agent"; then
        timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$timestamp] $line" | tee -a /tmp/ka_agent_monitor.log
        
        # 高亮关键信息
        if echo "$line" | grep -iq "chosen_agent.*ka-agent"; then
            echo "  ✅ KA-Agent 被选中！" | tee -a /tmp/ka_agent_monitor.log
        fi
        
        if echo "$line" | grep -iq "internal agent detected.*ka-agent"; then
            echo "  ✅ 开始执行 KA-Agent！" | tee -a /tmp/ka_agent_monitor.log
        fi
        
        if echo "$line" | grep -iq "進入檢索流程"; then
            echo "  ✅ KA-Agent 进入检索流程！" | tee -a /tmp/ka_agent_monitor.log
        fi
        
        if echo "$line" | grep -iq "檢索流程完成"; then
            echo "  ✅ KA-Agent 检索完成！" | tee -a /tmp/ka_agent_monitor.log
        fi
    fi
done
