#!/usr/bin/env python3
# 代碼功能說明: 檢查 Agent 實例註冊狀態
# 創建日期: 2026-01-28 18:10 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28 18:10 UTC+8

"""
檢查 Agent 實例註冊狀態的診斷腳本
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

try:
    from agents.services.registry.registry import get_agent_registry
    from agents.builtin import initialize_builtin_agents, register_builtin_agents
    
    print("=" * 80)
    print("Agent 實例註冊狀態檢查")
    print("=" * 80)
    print()
    
    # 初始化內建 Agent
    print("[步驟 1] 初始化內建 Agent...")
    agents_dict = initialize_builtin_agents()
    print(f"✅ 初始化完成，找到 {len(agents_dict)} 個 Agent")
    print(f"   Agent keys: {list(agents_dict.keys())}")
    print()
    
    # 檢查 KA-Agent 是否在字典中
    ka_agent = agents_dict.get("ka_agent")
    if ka_agent:
        print(f"✅ KA-Agent 實例存在: {type(ka_agent).__name__}")
        print(f"   agent_id: {getattr(ka_agent, 'agent_id', 'N/A')}")
    else:
        print("❌ KA-Agent 實例不存在於 agents_dict")
    print()
    
    # 註冊 Agent
    print("[步驟 2] 註冊 Agent 到 Registry...")
    registered_agents = register_builtin_agents()
    print(f"✅ 註冊完成，註冊了 {len(registered_agents)} 個 Agent")
    print()
    
    # 獲取 Registry
    print("[步驟 3] 檢查 Registry 狀態...")
    registry = get_agent_registry()
    
    # 檢查 Agent 信息
    ka_agent_info = registry.get_agent_info("ka-agent")
    if ka_agent_info:
        print(f"✅ KA-Agent 信息存在於 Registry")
        print(f"   agent_id: {ka_agent_info.agent_id}")
        print(f"   name: {ka_agent_info.name}")
        print(f"   status: {ka_agent_info.status}")
        print(f"   is_internal: {ka_agent_info.endpoints.is_internal}")
    else:
        print("❌ KA-Agent 信息不存在於 Registry")
    print()
    
    # 檢查 Agent 實例
    print("[步驟 4] 檢查 Agent 實例...")
    ka_agent_instance = registry.get_agent("ka-agent")
    if ka_agent_instance:
        print(f"✅ KA-Agent 實例存在於 Registry")
        print(f"   類型: {type(ka_agent_instance).__name__}")
    else:
        print("❌ KA-Agent 實例不存在於 Registry")
        print("   這可能是導致 CHAT_PRODUCT_FAILED 的原因")
    print()
    
    # 檢查所有內部 Agent 實例
    print("[步驟 5] 檢查所有內部 Agent 實例...")
    all_agents = registry.get_all_agents()
    internal_agents = [a for a in all_agents if a.endpoints.is_internal]
    print(f"找到 {len(internal_agents)} 個內部 Agent:")
    for agent in internal_agents:
        instance = registry.get_agent(agent.agent_id)
        status = "✅ 有實例" if instance else "❌ 無實例"
        print(f"  - {agent.agent_id}: {status}")
    
    print()
    print("=" * 80)
    print("檢查完成")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ 檢查失敗: {e}")
    import traceback
    traceback.print_exc()
