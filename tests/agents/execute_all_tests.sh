#!/bin/bash
# 執行所有測試並生成報告

cd /Users/daniel/GitHub/AI-Box

echo "開始執行文件編輯 Agent 語義路由測試..."
echo "執行時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 執行所有測試並保存輸出
python3 -m pytest tests/agents/test_file_editing_agent_routing.py::TestFileEditingAgentRouting::test_agent_routing \
    -v \
    --tb=short \
    -x \
    --maxfail=1 \
    2>&1 | tee tests/agents/test_reports/test_execution_$(date '+%Y%m%d_%H%M%S').log

echo ""
echo "測試執行完成: $(date '+%Y-%m-%d %H:%M:%S')"
