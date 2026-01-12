#!/bin/bash
# 代碼功能說明: 階段2 GRO架構轉型測試運行腳本
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

# 運行階段2的所有測試

echo "=========================================="
echo "階段2 GRO架構轉型測試"
echo "=========================================="

# 設置測試環境
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 運行單元測試
echo ""
echo "1. 運行單元測試..."
echo "----------------------------------------"
pytest tests/agents/services/test_state_store.py -v
pytest tests/agents/services/test_policy_engine.py -v
pytest tests/agents/services/test_observation_collector.py -v
pytest tests/agents/services/test_react_fsm.py -v
pytest tests/agents/services/test_capability_adapter.py -v
pytest tests/agents/services/test_message_bus.py -v

# 運行集成測試
echo ""
echo "2. 運行集成測試..."
echo "----------------------------------------"
pytest tests/integration/phase2/ -v

# 測試覆蓋率報告
echo ""
echo "3. 生成測試覆蓋率報告..."
echo "----------------------------------------"
pytest tests/agents/services/ --cov=agents/services/state_store --cov=agents/services/policy_engine --cov=agents/services/observation_collector --cov=agents/services/react_fsm --cov=agents/services/capability_adapter --cov=agents/services/message_bus --cov-report=html --cov-report=term

echo ""
echo "=========================================="
echo "測試完成"
echo "=========================================="
