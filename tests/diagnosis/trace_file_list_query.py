# 代碼功能說明: 追蹤「你能檢查你能查看的文件列表嗎」查詢的完整流程
# 創建日期: 2026-02-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-01 UTC+8

"""
追蹤「你能檢查你能查看的文件列表嗎」查詢經歷的工作節點，診斷為何未檢索到文件區資料。

用法:
  cd /home/daniel/ai-box
  PYTHONPATH=. ./venv/bin/python tests/diagnosis/trace_file_list_query.py
  PYTHONPATH=. ./venv/bin/python tests/diagnosis/trace_file_list_query.py --user-id systemAdmin --task-title "MM-Agent"

前置條件:
  - ArangoDB 需運行
  - 需有測試用戶和任務的 file_metadata 資料（可為空）
"""

from __future__ import annotations

import argparse
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


def _step(name: str, result: str, detail: str = "", elapsed_ms: float | None = None) -> None:
    print(f"\n  [{name}]")
    if elapsed_ms is not None:
        print(f"    ⏱️ {elapsed_ms:.0f}ms")
    print(f"    → {result}")
    if detail:
        for line in detail.strip().split("\n"):
            print(f"      {line}")


def _find_task_id_by_title(user_id: str, task_title: str) -> str | None:
    """依 user_id 和任務 title 查詢 task_id"""
    try:
        from database.arangodb import ArangoDBClient

        client = ArangoDBClient()
        if client.db is None or client.db.aql is None:
            return None
        aql = """
        FOR doc IN user_tasks
            FILTER doc.user_id == @user_id AND doc.title == @title
            LIMIT 1
            RETURN doc.task_id
        """
        cursor = client.db.aql.execute(
            aql, bind_vars={"user_id": user_id, "title": task_title}
        )
        for row in cursor:
            return str(row) if row else None
    except Exception as e:
        print(f"  [查詢 task_id 失敗] {e}")
    return None


async def main() -> None:
    parser = argparse.ArgumentParser(description="追蹤文件列表查詢流程")
    parser.add_argument(
        "--user-id",
        default="systemAdmin",
        help="用戶 ID（預設 systemAdmin）",
    )
    parser.add_argument(
        "--task-title",
        default="MM-Agent",
        help="任務標題（預設 MM-Agent）",
    )
    parser.add_argument(
        "--full-flow",
        action="store_true",
        help="執行完整 Chat 流程（Task Analyzer + Memory + LLM）並測量各節點耗時",
    )
    parsed = parser.parse_args()

    query = "你能檢查你能查看的文件列表嗎"
    user_id = parsed.user_id
    task_title = parsed.task_title
    session_id = str(uuid.uuid4())

    # 依 title 查詢 task_id
    task_id = _find_task_id_by_title(user_id, task_title)
    if not task_id:
        # 備用：MM-Agent 常用 task_id（來自 datalake-system kg_service）
        task_id = "1769909074960"
        print(f"\n⚠️ 未找到 user_id={user_id} 且 title={task_title!r} 的任務，使用備用 task_id={task_id}")

    print("=" * 70)
    print("追蹤：「你能檢查你能查看的文件列表嗎」查詢流程")
    print("=" * 70)
    print(f"\n輸入: {query}")
    print(f"user_id: {user_id}")
    print(f"task_title: {task_title}")
    print(f"task_id: {task_id}")
    print(f"session_id: {session_id[:8]}...")

    timings: dict[str, float] = {}

    # ========== Step 1: _is_file_list_query 檢測 ==========
    print("\n" + "-" * 70)
    print("Step 1: 文件列表查詢檢測 (_is_file_list_query)")
    print("-" * 70)
    try:
        t1 = time.perf_counter()
        from services.api.services.chat_memory_service import ChatMemoryService

        is_match = ChatMemoryService._is_file_list_query(query)
        elapsed = (time.perf_counter() - t1) * 1000
        timings["1_is_file_list_query"] = elapsed
        _step(
            "關鍵詞匹配",
            "匹配" if is_match else "未匹配",
            f"查詢應觸發文件元數據檢索: {is_match}",
            elapsed_ms=elapsed,
        )
        if not is_match:
            print("\n  ⚠️ 未匹配！可能原因：關鍵詞列表缺少「檢查」等口語")
            print("  現有關鍵詞: 知識庫.*有多少, 查看.*文件, 文件列表, ...")
    except Exception as e:
        _step("檢測", "失敗", str(e))
        return

    # ========== Step 2: FileMetadataService.list 查詢 ==========
    print("\n" + "-" * 70)
    print("Step 2: 文件元數據查詢 (FileMetadataService.list)")
    print("-" * 70)
    files: list = []
    try:
        t2 = time.perf_counter()
        from services.api.services.file_metadata_service import get_metadata_service

        meta_svc = get_metadata_service()
        files = meta_svc.list(
            user_id=user_id,
            task_id=task_id,
            limit=100,
        )
        elapsed = (time.perf_counter() - t2) * 1000
        timings["2_file_metadata_list"] = elapsed
        _step(
            "查詢結果",
            f"共 {len(files)} 個文件",
            "\n".join(
                [f"- {f.filename} (file_id={f.file_id}, task_id={f.task_id})" for f in files[:10]]
            )
            if files
            else "（無文件，可能 task_id 或 user_id 不匹配）",
            elapsed_ms=elapsed,
        )
        if not files:
            # 嘗試不帶 task_id 查詢（僅 user_id）
            files_all = meta_svc.list(user_id=user_id, task_id=None, limit=100)
            _step(
                "僅 user_id 查詢",
                f"共 {len(files_all)} 個文件",
                "（task_id=None 時返回該用戶所有任務的文件）"
                if files_all
                else "（該用戶無任何文件）",
            )
    except Exception as e:
        _step("查詢", "失敗", str(e))
        import traceback

        traceback.print_exc()
        return

    # ========== Step 3: Memory Retrieval 完整流程 ==========
    print("\n" + "-" * 70)
    print("Step 3: Memory Retrieval (retrieve_for_prompt)")
    print("-" * 70)
    memory_result = None
    try:
        t3 = time.perf_counter()
        from services.api.services.chat_memory_service import get_chat_memory_service

        memory_service = get_chat_memory_service()
        memory_result = await memory_service.retrieve_for_prompt(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            request_id=str(uuid.uuid4()),
            query=query,
            attachments=None,
        )
        elapsed = (time.perf_counter() - t3) * 1000
        timings["3_memory_retrieve"] = elapsed
        _step(
            "檢索結果",
            f"memory_hit_count={memory_result.memory_hit_count}, "
            f"sources={memory_result.memory_sources}, "
            f"retrieval_latency_ms={memory_result.retrieval_latency_ms:.0f}",
            "",
            elapsed_ms=elapsed,
        )
        _step(
            "injection_messages",
            f"共 {len(memory_result.injection_messages)} 條",
            "",
        )
        if memory_result.injection_messages:
            content = memory_result.injection_messages[0].get("content", "")
            preview = content[:500] + "..." if len(content) > 500 else content
            _step("注入內容預覽", "", preview.replace("\n", "\n      "))
        else:
            _step("注入內容", "空", "（LLM 不會收到文件列表）")
    except Exception as e:
        _step("Memory Retrieval", "失敗", str(e))
        import traceback

        traceback.print_exc()
        return

    # ========== Step 4: 完整 Chat 流程（含 Task Analyzer + LLM）==========
    full_flow = parsed.full_flow
    ta_result: object | None = None

    if full_flow:
        print("\n" + "-" * 70)
        print("Step 4: 完整 Chat 流程（Task Analyzer + Memory + LLM）")
        print("-" * 70)
        # Task Analyzer
        t_ta = time.perf_counter()
        try:
            from agents.task_analyzer.analyzer import TaskAnalyzer
            from agents.task_analyzer.models import TaskAnalysisRequest

            analyzer = TaskAnalyzer()
            ta_request = TaskAnalysisRequest(
                task=query,
                context={
                    "user_id": user_id,
                    "session_id": session_id,
                    "task_id": task_id,
                    "request_id": str(uuid.uuid4()),
                    "model_selector": {"mode": "manual", "model_id": "qwen3:32b"},
                },
                user_id=user_id,
                session_id=session_id,
            )
            ta_result = await analyzer.analyze(ta_request)
            elapsed_ta = (time.perf_counter() - t_ta) * 1000
            timings["4_task_analyzer"] = elapsed_ta
            _step(
                "Task Analyzer",
                f"chosen_agent={ta_result.decision_result.chosen_agent if ta_result.decision_result else None}",
                "",
                elapsed_ms=elapsed_ta,
            )
        except Exception as e:
            elapsed_ta = (time.perf_counter() - t_ta) * 1000
            timings["4_task_analyzer"] = elapsed_ta
            _step("Task Analyzer", f"失敗: {e}", "", elapsed_ms=elapsed_ta)

        # LLM 生成（若需要）
        if not (ta_result and ta_result.analysis_details and ta_result.analysis_details.get("direct_answer")):
            t_llm = time.perf_counter()
            try:
                from llm.clients.factory import LLMClientFactory
                from services.api.models.llm_model import LLMProvider

                client = LLMClientFactory.create_client(LLMProvider.OLLAMA, use_cache=True)
                messages = [
                    {"role": "system", "content": "你是一個友善的 AI 助手。"},
                    {"role": "user", "content": query},
                ]
                if memory_result and memory_result.injection_messages:
                    sys_msg = memory_result.injection_messages[0].get("content", "")
                    messages[0]["content"] = messages[0]["content"] + "\n\n" + sys_msg
                resp = await client.chat(messages=messages, model="qwen3:32b")
                elapsed_llm = (time.perf_counter() - t_llm) * 1000
                timings["5_llm_generate"] = elapsed_llm
                content = resp.get("content", "") or resp.get("text", "")
                _step(
                    "LLM 生成",
                    f"回應長度 {len(content)} 字元",
                    "",
                    elapsed_ms=elapsed_llm,
                )
            except Exception as e:
                elapsed_llm = (time.perf_counter() - t_llm) * 1000
                timings["5_llm_generate"] = elapsed_llm
                _step("LLM 生成", f"失敗: {e}", "", elapsed_ms=elapsed_llm)

    # ========== Step 5: 工作節點耗時匯總 ==========
    print("\n" + "=" * 70)
    print("工作節點耗時匯總（「你能檢查你能查看的文件列表嗎」）")
    print("=" * 70)
    node_labels = {
        "1_is_file_list_query": "1. _is_file_list_query 檢測",
        "2_file_metadata_list": "2. FileMetadataService.list",
        "3_memory_retrieve": "3. Memory retrieve_for_prompt",
        "4_task_analyzer": "4. Task Analyzer",
        "5_llm_generate": "5. LLM 生成",
    }
    total_ms = 0
    for key, label in node_labels.items():
        if key in timings:
            ms = timings[key]
            total_ms += ms
            print(f"  {label}: {ms:.0f}ms")
    print(f"  ─────────────────")
    print(f"  總計: {total_ms:.0f}ms ({total_ms/1000:.2f}s)")
    print()
    print("完整 Chat 流程工作節點（依執行順序）：")
    full_nodes = [
        ("G5", "chat.request_received", "請求進入"),
        ("Task Analyzer", "L1 Router LLM / L2 Intent / L3 Task Planner", "意圖分析"),
        ("G6", "Data consent gate", "AI 處理同意檢查"),
        ("Memory", "retrieve_for_prompt", "記憶檢索（含文件列表查詢）"),
        ("Agent?", "若 chosen_agent 非空", "可能調用 Agent（如 KA-Agent）"),
        ("LLM", "MoE 選擇模型生成", "最終回答"),
    ]
    for node, desc, note in full_nodes:
        print(f"  {node}: {desc} — {note}")
    print()
    if memory_result and memory_result.memory_hit_count > 0:
        print("✅ 文件列表已檢索並注入，LLM 應能回答")
    elif memory_result and memory_result.memory_hit_count == 0 and not files:
        print("⚠️ 診斷：未檢索到文件，可能原因：task_id/user_id 不匹配或該任務無文件")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
