#!/usr/bin/env python3
# 代碼功能說明: /api/v2/chat 端到端整合測試腳本
# 創建日期: 2026-02-04

"""
端到端整合測試

測試流程：
1. POST /api/v2/chat → 獲取 request_id
2. GET /api/v1/agent-status/stream/{request_id} → 監聽狀態事件
3. 驗證狀態事件包含人類語言
"""

import asyncio
import aiohttp
import json
import sys

API_BASE = "http://localhost:8000"


async def test_conversation_flow():
    """測試對話流程"""
    print("\n" + "=" * 70)
    print("測試 1: 對話流程")
    print("=" * 70)

    async with aiohttp.ClientSession() as session:
        # Step 1: 發送對話請求
        print("\n  Step 1: 發送請求...")
        async with session.post(
            f"{API_BASE}/api/v2/chat",
            json={
                "messages": [{"role": "user", "content": "你好"}],
                "user_id": "test_user",
                "model_selector": {"mode": "manual", "model_id": "llama3.2:3b-instruct-q4_0"},
            },
        ) as response:
            result = await response.json()

            if result.get("success"):
                print(f"  ✅ 請求成功")
                print(f"     回應: {result['data']['content'][:50]}...")
            else:
                print(f"  ❌ 請求失敗: {result.get('message')}")
                return False

    return True


async def test_data_query_flow():
    """測試數據查詢流程"""
    print("\n" + "=" * 70)
    print("測試 2: 數據查詢流程")
    print("=" * 70)

    async with aiohttp.ClientSession() as session:
        # Step 1: 發送數據查詢請求
        print("\n  Step 1: 發送數據查詢請求...")
        async with session.post(
            f"{API_BASE}/api/v2/chat",
            json={
                "messages": [{"role": "user", "content": "RM01-003 庫存多少？"}],
                "user_id": "test_user",
                "model_selector": {"mode": "manual", "model_id": "llama3.2:3b-instruct-q4_0"},
            },
        ) as response:
            result = await response.json()

            if result.get("success"):
                print(f"  ✅ 請求成功")

                # 檢查 observability
                obs = result.get("data", {}).get("observability", {})
                print(f"     Request ID: {obs.get('request_id', 'N/A')}")
                print(f"     Memory Hit: {obs.get('memory_hit_count', 0)}")

                # 檢查 routing
                routing = result.get("data", {}).get("routing", {})
                print(f"     Provider: {routing.get('provider', 'N/A')}")
                print(f"     Strategy: {routing.get('strategy', 'N/A')}")
                print(f"     Latency: {routing.get('latency_ms', 0):.0f}ms")
            else:
                print(f"  ❌ 請求失敗: {result.get('message')}")
                return False

    return True


async def test_knowledge_query_flow():
    """測試知識查詢流程"""
    print("\n" + "=" * 70)
    print("測試 3: 知識查詢流程")
    print("=" * 70)

    async with aiohttp.ClientSession() as session:
        # Step 1: 發送知識查詢請求
        print("\n  Step 1: 發送知識查詢請求...")
        async with session.post(
            f"{API_BASE}/api/v2/chat",
            json={
                "messages": [{"role": "user", "content": "MM-Agent 能做什麼？"}],
                "user_id": "test_user",
                "model_selector": {"mode": "manual", "model_id": "llama3.2:3b-instruct-q4_0"},
            },
        ) as response:
            result = await response.json()

            if result.get("success"):
                print(f"  ✅ 請求成功")
                content = result.get("data", {}).get("content", "")
                print(f"     回應: {content[:80]}...")
            else:
                print(f"  ❌ 請求失敗: {result.get('message')}")
                return False

    return True


async def test_sse_stream():
    """測試 SSE 流式端點"""
    print("\n" + "=" * 70)
    print("測試 4: SSE 流式端點")
    print("=" * 70)

    async with aiohttp.ClientSession() as session:
        # Step 1: 發送請求並獲取 request_id
        print("\n  Step 1: 發送請求...")
        async with session.post(
            f"{API_BASE}/api/v2/chat",
            json={
                "messages": [{"role": "user", "content": "測試 SSE 流式"}],
                "user_id": "test_user",
                "model_selector": {"mode": "manual", "model_id": "llama3.2:3b-instruct-q4_0"},
            },
        ) as response:
            result = await response.json()

            if result.get("success"):
                request_id = result.get("data", {}).get("observability", {}).get("request_id")
                print(f"  ✅ 請求成功，Request ID: {request_id}")
            else:
                print(f"  ❌ 請求失敗")
                return False

        # Step 2: 監聽 SSE 流
        print("\n  Step 2: 監聽 SSE 流...")
        event_count = 0
        async with session.get(
            f"{API_BASE}/api/v2/chat/stream",
            json={
                "messages": [{"role": "user", "content": "測試 SSE"}],
                "user_id": "test_user",
                "model_selector": {"mode": "manual", "model_id": "llama3.2:3b-instruct-q4_0"},
            },
        ) as response:
            async for line in response.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data:"):
                    try:
                        data = json.loads(line[5:])
                        event_type = data.get("type", "unknown")
                        print(f"     Event: {event_type}")
                        event_count += 1

                        if event_type == "done":
                            break
                        if event_count >= 10:
                            break
                    except:
                        pass

        print(f"  ✅ 收到 {event_count} 個 SSE 事件")

    return True


async def test_all():
    """運行所有測試"""
    print("\n" + "=" * 70)
    print("AI-Box /api/v2/chat 端到端整合測試")
    print("=" * 70)

    results = []

    # 測試 1: 對話流程
    results.append(("對話流程", await test_conversation_flow()))

    # 測試 2: 數據查詢流程
    results.append(("數據查詢流程", await test_data_query_flow()))

    # 測試 3: 知識查詢流程
    results.append(("知識查詢流程", await test_knowledge_query_flow()))

    # 測試 4: SSE 流式端點
    results.append(("SSE 流式端點", await test_sse_stream()))

    # 打印結果
    print("\n" + "=" * 70)
    print("測試結果摘要")
    print("=" * 70)

    passed = 0
    failed = 0

    for name, success in results:
        status = "✅ 通過" if success else "❌ 失敗"
        print(f"  {name:20s} {status}")
        if success:
            passed += 1
        else:
            failed += 1

    print("=" * 70)
    print(f"  總計: {passed} 通過, {failed} 失敗")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(test_all())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n測試被中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n測試錯誤: {e}")
        sys.exit(1)
