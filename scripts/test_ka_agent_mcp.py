#!/usr/bin/env python3
"""
KA-Agent MCP 接口測試腳本
"""

import asyncio
import httpx
import json

KA_AGENT_URL = "http://localhost:8000/api/v1/ka"


async def test_ka_stats():
    """測試 ka.stats 接口"""
    print("\n=== 測試 ka.stats ===")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{KA_AGENT_URL}/stats",
                params={"agent_id": "mm-agent"},
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


async def test_ka_list():
    """測試 ka.list 接口"""
    print("\n=== 測試 ka.list ===")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{KA_AGENT_URL}/list",
                params={"agent_id": "mm-agent"},
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


async def test_knowledge_query():
    """測試 knowledge.query 接口"""
    print("\n=== 測試 knowledge.query ===")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{KA_AGENT_URL}/knowledge/query",
                json={
                    "request_id": "test-001",
                    "query": "測試知識庫檢索",
                    "agent_id": "mm-agent",
                    "user_id": "user_001",
                    "session_id": "sess_001",
                    "options": {
                        "top_k": 5,
                        "include_graph": True,
                    },
                },
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


async def test_knowledge_bases_api():
    """測試 Knowledge Base API"""
    print("\n=== 測試 Knowledge Base API ===")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "http://localhost:8000/api/v1/knowledge-bases",
                params={"user_id": "user_001"},
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


async def test_agent_config():
    """測試 Agent 配置 API"""
    print("\n=== 測試 Agent 配置 API ===")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "http://localhost:8000/api/v1/agent-display-configs/agents/mm-agent",
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Agent ID: {data.get('data', {}).get('id')}")
                print(f"Knowledge Bases: {data.get('data', {}).get('knowledge_bases', [])}")
            return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


async def main():
    """主測試函數"""
    print("=" * 60)
    print("KA-Agent MCP 接口測試")
    print("=" * 60)

    results = []

    # 測試 Agent 配置
    results.append(("Agent 配置 API", await test_agent_config()))

    # 測試 Knowledge Base API
    results.append(("Knowledge Base API", await test_knowledge_bases_api()))

    # 測試 KA-Agent MCP 接口
    results.append(("ka.stats", await test_ka_stats()))
    results.append(("ka.list", await test_ka_list()))
    results.append(("knowledge.query", await test_knowledge_query()))

    # 輸出結果摘要
    print("\n" + "=" * 60)
    print("測試結果摘要")
    print("=" * 60)
    passed = 0
    failed = 0
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
        if success:
            passed += 1
        else:
            failed += 1

    print(f"\n總計: {passed} 通過, {failed} 失敗")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
