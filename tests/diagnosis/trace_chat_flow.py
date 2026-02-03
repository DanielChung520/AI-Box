# 代碼功能說明: Chat 流程診斷腳本 - 模擬「你好」+ Ollama 完整流程並追蹤各步驟耗時
# 創建日期: 2026-02-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-01 UTC+8

"""
模擬前端發送「你好」、模型選單「Ollama」的完整 Chat 流程，追蹤各步驟耗時。

用法:
  cd /home/daniel/ai-box
  PYTHONPATH=. ./venv/bin/python tests/diagnosis/trace_chat_flow.py

前置條件:
  - Ollama 需運行且 qwen3:32b 已拉取（若使用 Router LLM）
  - ArangoDB、Redis 等依賴需可用（若啟用 memory 檢索）
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path

# 加載 .env 和項目路徑
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
env_file = project_root / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file, override=True)


def _ts() -> str:
    return f"[{time.strftime('%H:%M:%S')}]"


def _elapsed(start: float) -> float:
    return (time.perf_counter() - start) * 1000


async def main() -> None:
    print("=" * 70)
    print("Chat 流程診斷：模擬「你好」+ Ollama 模型")
    print("=" * 70)

    user_text = "你好"
    session_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    user_id = "trace-test-user"

    # 模擬 Ollama 模型選擇
    model_id = os.getenv("TRACE_MODEL_ID", "qwen3:32b")

    print(f"\n{_ts()} 輸入: {user_text}")
    print(f"{_ts()} 模型: Ollama / {model_id}")
    print(f"{_ts()} session_id: {session_id[:8]}...")
    print()

    timings: dict[str, float] = {}

    # ========== Step 1: Task Analyzer ==========
    print(f"{_ts()} [Step 1] 調用 Task Analyzer...")
    t1 = time.perf_counter()
    try:
        from agents.task_analyzer.analyzer import TaskAnalyzer
        from agents.task_analyzer.models import TaskAnalysisRequest

        analyzer = TaskAnalyzer()
        # 模擬用戶選擇 Ollama（manual 模式）
        request = TaskAnalysisRequest(
            task=user_text,
            context={
                "user_id": user_id,
                "session_id": session_id,
                "task_id": task_id,
                "request_id": request_id,
                "model_selector": {"mode": "manual", "model_id": model_id},
            },
            user_id=user_id,
            session_id=session_id,
        )
        analysis_result = await analyzer.analyze(request)
        elapsed = _elapsed(t1)
        timings["task_analyzer"] = elapsed
        print(f"{_ts()} [Step 1] Task Analyzer 完成: {elapsed:.0f}ms")
        print(f"         - direct_answer: {analysis_result.analysis_details.get('direct_answer', False)}")
        print(f"         - requires_agent: {analysis_result.requires_agent}")
        if analysis_result.decision_result:
            print(f"         - chosen_agent: {analysis_result.decision_result.chosen_agent}")
    except Exception as e:
        elapsed = _elapsed(t1)
        timings["task_analyzer"] = elapsed
        print(f"{_ts()} [Step 1] Task Analyzer 失敗 ({elapsed:.0f}ms): {e}")
        import traceback
        traceback.print_exc()
        return

    # ========== Step 2: Memory Retrieval ==========
    print(f"\n{_ts()} [Step 2] 調用 Memory Retrieval...")
    t2 = time.perf_counter()
    try:
        from services.api.services.chat_memory_service import get_chat_memory_service

        memory_service = get_chat_memory_service()
        memory_result = await memory_service.retrieve_for_prompt(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            request_id=request_id,
            query=user_text,
            attachments=None,
        )
        elapsed = _elapsed(t2)
        timings["memory_retrieval"] = elapsed
        print(f"{_ts()} [Step 2] Memory Retrieval 完成: {elapsed:.0f}ms")
        print(f"         - memory_hit_count: {memory_result.memory_hit_count}")
    except Exception as e:
        elapsed = _elapsed(t2)
        timings["memory_retrieval"] = elapsed
        print(f"{_ts()} [Step 2] Memory Retrieval 失敗 ({elapsed:.0f}ms): {e}")

    # ========== Step 3: MoE / LLM 生成（若需要） ==========
    if analysis_result.analysis_details.get("direct_answer"):
        print(f"\n{_ts()} [Step 3] 跳過（Direct Answer 已返回）")
        timings["llm_generate"] = 0
    else:
        print(f"\n{_ts()} [Step 3] 調用 MoE/LLM 生成...")
        t3 = time.perf_counter()
        try:
            from llm.clients.factory import LLMClientFactory
            from services.api.models.llm_model import LLMProvider

            client = LLMClientFactory.create_client(LLMProvider.OLLAMA, use_cache=True)
            messages = [
                {"role": "system", "content": "你是一個友善的 AI 助手。"},
                {"role": "user", "content": user_text},
            ]
            resp = await client.chat(messages=messages, model=model_id)
            content = resp.get("content", "") or resp.get("text", "")
            elapsed = _elapsed(t3)
            timings["llm_generate"] = elapsed
            print(f"{_ts()} [Step 3] LLM 生成完成: {elapsed:.0f}ms")
            print(f"         - 回應長度: {len(content)} 字元")
        except Exception as e:
            elapsed = _elapsed(t3)
            timings["llm_generate"] = elapsed
            print(f"{_ts()} [Step 3] LLM 生成失敗 ({elapsed:.0f}ms): {e}")
            import traceback
            traceback.print_exc()

    # ========== 匯總 ==========
    print("\n" + "=" * 70)
    print("耗時匯總")
    print("=" * 70)
    total = 0
    for name, ms in timings.items():
        print(f"  {name}: {ms:.0f}ms")
        total += ms
    print(f"  總計: {total:.0f}ms ({total/1000:.2f}s)")
    print()
    if timings.get("task_analyzer", 0) > 2000:
        print("⚠️  Task Analyzer 耗時 > 2s，建議檢查：")
        print("   - Router LLM 模型是否可用（qwen3:32b）")
        print("   - 是否走了 _try_direct_answer 快速路徑")
    if timings.get("memory_retrieval", 0) > 1000:
        print("⚠️  Memory Retrieval 耗時 > 1s，建議檢查 Qdrant/向量檢索")
    if timings.get("llm_generate", 0) > 5000:
        print("⚠️  LLM 生成耗時 > 5s，建議檢查 Ollama 模型負載")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
