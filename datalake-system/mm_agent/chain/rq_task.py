# 代碼功能說明: RQ 任務處理模組 - 處理 Agent-todo 非同步任務
# 創建日期: 2026-02-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-08

"""RQ 任務處理模組 - 提供 Agent-todo 非同步執行功能

重要：此模組必須能夠被 RQ Worker 正確導入
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# SSE 發布配置
_SSE_API_URL = "http://localhost:8000"


def _publish_sse_sync(
    request_id: str,
    step: str,
    status: str,
    message: str,
    progress: float = 0.0,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """同步發布 SSE 事件（供 RQ Worker 使用）

    Args:
        request_id: 會話 ID
        step: 步驟名稱
        status: 狀態 (processing/completed/error)
        message: 狀態描述
        progress: 進度 0-1
        extra: 額外信息
    """
    import httpx

    data = {
        "request_id": request_id,
        "step": step,
        "status": status,
        "message": message,
        "progress": progress,
        "timestamp": datetime.now().isoformat(),
    }
    if extra:
        data["extra"] = extra

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{_SSE_API_URL}/api/v1/agent-status/event",
                json=data,
            )
            if response.status_code >= 400:
                logger.warning(f"[RQ-SSE] SSE publish failed: {response.status_code}")
    except Exception as e:
        logger.warning(f"[RQ-SSE] SSE publish error: {e}")


def _publish_data_result_sse(
    request_id: str,
    step_id: int,
    sql: str,
    row_count: int,
    sample_data: Optional[List[Dict]] = None,
) -> None:
    """發布數據查詢結果 SSE"""
    _publish_sse_sync(
        request_id=request_id,
        step=f"step_{step_id}_data_query",
        status="completed",
        message=f"查詢完成，返回 {row_count} 行數據",
        progress=1.0,
        extra={
            "type": "data_result",
            "step_id": step_id,
            "sql": sql[:500],
            "row_count": row_count,
            "sample": sample_data[:3] if sample_data else None,
        },
    )


def _publish_knowledge_result_sse(
    request_id: str,
    step_id: int,
    knowledge: str,
    source: str,
) -> None:
    """發布知識檢索結果 SSE"""
    _publish_sse_sync(
        request_id=request_id,
        step=f"step_{step_id}_knowledge_retrieval",
        status="completed",
        message=f"知識檢索成功，來源: {source}",
        progress=1.0,
        extra={
            "type": "knowledge_result",
            "step_id": step_id,
            "knowledge": knowledge[:500] if knowledge else "",
            "source": source,
        },
    )


# 確保 datalake-system 在路徑中
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _get_redis_connection():
    """獲取 Redis 連接（從環境變數）"""
    import os
    import redis

    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        redis_conn = redis.Redis.from_url(
            redis_url,
            decode_responses=False,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    else:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD") or None

        redis_conn = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=False,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return redis_conn


def execute_agent_todo_sync(
    session_id: str,
    step_id: int,
    action_type: str,
    instruction: str,
    parameters: Dict[str, Any],
    total_steps: int,
) -> Dict[str, Any]:
    """執行 Agent-todo 步驟（同步函數，用於 RQ 任務）

    Args:
        session_id: 會話 ID
        step_id: 步驟 ID
        action_type: 行動類型
        instruction: 執行指令
        parameters: 行動參數
        total_steps: 總步驟數

    Returns:
        執行結果字典
    """
    import uuid
    from datetime import datetime
    from shared.agents.todo.schema import Todo, TodoType, TodoState
    from shared.database.arango_client import SharedArangoClient

    logger.info(f"[RQ-Task] 開始執行: session={session_id}, step={step_id}, action={action_type}")

    # 映射 action_type 到 TodoType
    todo_type_map = {
        "knowledge_retrieval": TodoType.KNOWLEDGE_RETRIEVAL,
        "data_query": TodoType.DATA_QUERY,
        "data_cleaning": TodoType.DATA_CLEANING,
        "computation": TodoType.COMPUTATION,
        "visualization": TodoType.VISUALIZATION,
        "response_generation": TodoType.RESPONSE_GENERATION,
    }
    todo_type = todo_type_map.get(action_type, TodoType.COMPUTATION)

    # 初始化 ArangoDB
    arango = SharedArangoClient()

    # 創建 Todo
    todo = Todo(
        type=todo_type,
        owner_agent="MM-Agent",
        instruction=instruction,
        input={
            "session_id": session_id,
            "step_id": step_id,
            "action_type": action_type,
            "total_steps": total_steps,
            "parameters": parameters,
        },
    )

    todo_id = None
    try:
        todo_id = arango.create_todo(todo)

        logger.info(f"[RQ-Task] Todo 已創建: {todo_id}")

        # 根據 action_type 執行相應操作（傳遞 session_id 和 step_id 用於 SSE）
        result = _execute_action(action_type, instruction, parameters, session_id, step_id)

        # 更新 Todo 狀態為完成
        asyncio.run(arango.update_todo(todo_id, state=TodoState.COMPLETED.value))

        logger.info(f"[RQ-Task] 完成: step={step_id}, success={result.get('success', False)}")

        return {
            "success": result.get("success", True),
            "todo_id": todo_id,
            "session_id": session_id,
            "step_id": step_id,
            "action_type": action_type,
            "result": result,
            "observation": result.get("observation", f"步驟 {step_id} 完成"),
        }

    except Exception as e:
        logger.error(f"[RQ-Task] 執行失敗: step={step_id}, error={e}", exc_info=True)

        # 更新 Todo 狀態為失敗
        try:
            if todo_id and arango:
                asyncio.run(
                    arango.update_todo(
                        todo_id,
                        state=TodoState.FAILED.value,
                        error={"code": "EXECUTION_ERROR", "message": str(e)},
                    )
                )
        except Exception:
            pass

        return {
            "success": False,
            "todo_id": todo_id,
            "session_id": session_id,
            "step_id": step_id,
            "action_type": action_type,
            "error": str(e),
            "observation": f"步驟 {step_id} 執行失敗",
        }


def _execute_action(
    action_type: str,
    instruction: str,
    parameters: Dict[str, Any],
    session_id: str,
    step_id: int = 0,
) -> Dict[str, Any]:
    """根據 action_type 執行相應操作

    Args:
        action_type: 行動類型
        instruction: 執行指令
        parameters: 行動參數
        session_id: 會話 ID
        step_id: 步驟 ID（用於 SSE 發布）

    Returns:
        執行結果
    """
    import httpx

    if action_type == "data_query":
        return _execute_data_query(instruction, parameters, session_id, step_id)
    elif action_type == "knowledge_retrieval":
        return _execute_knowledge_retrieval(instruction, parameters, session_id, step_id)
    elif action_type == "response_generation":
        return _execute_response_generation(instruction, parameters, session_id)
    else:
        logger.warning(f"[RQ-Task] 未知的 action_type: {action_type}，返回成功")
        return {
            "success": True,
            "observation": f"行動類型 {action_type} 已跳過（RQ 模式暂不支持）",
        }


def _execute_data_query(
    instruction: str,
    parameters: Dict[str, Any],
    session_id: str = "",
    step_id: int = 0,
) -> Dict[str, Any]:
    """執行數據查詢 - 調用 Data-Agent

    Args:
        instruction: 查詢指令
        parameters: 參數
        session_id: 會話 ID（用於 SSE 發布）
        step_id: 步驟 ID（用於 SSE 發布）

    Returns:
        查詢結果
    """
    import httpx
    import uuid

    logger.info(f"[RQ-Task] 執行數據查詢 (JP): {instruction[:50]}...")

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                "http://localhost:8004/jp/execute",
                json={
                    "task_id": f"rq_data_{uuid.uuid4().hex[:8]}",
                    "task_type": "schema_driven_query",
                    "task_data": {
                        "nlq": instruction,
                    },
                },
            )

            result = response.json()

            if result.get("status") == "success":
                rows = result.get("result", {}).get("data", [])
                sql = result.get("result", {}).get("sql", "")

                logger.info(f"[RQ-Task] 數據查詢完成: {len(rows)} 行")

                # 發布 SSE 事件
                if session_id and step_id > 0:
                    try:
                        _publish_data_result_sse(
                            request_id=session_id,
                            step_id=step_id,
                            sql=sql,
                            row_count=len(rows),
                            sample_data=rows[:3],
                        )
                        logger.info(
                            f"[RQ-Task] SSE 數據結果已發布: session={session_id}, step={step_id}"
                        )
                    except Exception as sse_err:
                        logger.warning(f"[RQ-Task] SSE 發布失敗: {sse_err}")

                return {
                    "success": True,
                    "data": rows,
                    "sql": sql,
                    "row_count": len(rows),
                    "observation": f"數據查詢完成，返回 {len(rows)} 行",
                }
            else:
                error_msg = result.get("error", "未知錯誤")
                logger.error(f"[RQ-Task] 數據查詢失敗: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "observation": f"數據查詢失敗: {error_msg}",
                }

    except Exception as e:
        logger.error(f"[RQ-Task] 調用 Data-Agent 失敗: {e}")
        return {
            "success": False,
            "error": str(e),
            "observation": f"數據查詢異常: {e}",
        }


def _execute_knowledge_retrieval(
    instruction: str,
    parameters: Dict[str, Any],
    session_id: str = "",
    step_id: int = 0,
) -> Dict[str, Any]:
    """執行知識檢索

    Args:
        instruction: 檢索指令
        parameters: 參數
        session_id: 會話 ID（用於 SSE 發布）
        step_id: 步驟 ID（用於 SSE 發布）

    Returns:
        檢索結果
    """
    import httpx
    import uuid

    logger.info(f"[RQ-Task] 執行知識檢索: {instruction[:50]}...")

    source = "none"
    knowledge = ""

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                "http://localhost:8000/api/v1/agents/execute",
                json={
                    "agent_id": "ka-agent",
                    "task": {
                        "type": "knowledge_query",
                        "action": "ka.retrieve",
                        "instruction": instruction,
                        "domain": "mm_agent",
                        "major": "responsibilities",
                        "top_k": 5,
                        "query_type": "hybrid",
                    },
                    "metadata": {
                        "caller_agent_id": "mm-agent",
                        "caller_agent_key": "-h0tjyh",
                    },
                },
            )

            result = response.json()
            if result.get("status") == "success":
                knowledge = result.get("result", {}).get("knowledge", "")
                source = "ka_agent"

    except Exception as e:
        logger.warning(f"[RQ-Task] KA-Agent 調用失敗: {e}，使用 LLM 回退")

        # 回退到 LLM
        try:
            with httpx.Client(timeout=120.0) as client:
                llm_response = client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "gpt-oss:120b",
                        "prompt": f"請用繁體中文回答：{instruction}",
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 2048},
                    },
                )

                if llm_response.status_code == 200:
                    llm_result = llm_response.json()
                    knowledge = llm_result.get("response", "")
                    source = "llm"

        except Exception as e:
            logger.error(f"[RQ-Task] LLM 調用失敗: {e}")

    # 發布 SSE 事件
    if session_id and step_id > 0:
        try:
            _publish_knowledge_result_sse(
                request_id=session_id,
                step_id=step_id,
                knowledge=knowledge,
                source=source,
            )
            logger.info(f"[RQ-Task] SSE 知識結果已發布: session={session_id}, step={step_id}")
        except Exception as sse_err:
            logger.warning(f"[RQ-Task] SSE 發布失敗: {sse_err}")

    return {
        "success": True,
        "knowledge": knowledge,
        "source": source,
        "observation": f"知識檢索成功，來源: {source}",
    }


def _execute_response_generation(
    instruction: str, parameters: Dict[str, Any], session_id: str
) -> Dict[str, Any]:
    """執行回覆生成

    Args:
        instruction: 生成指令
        parameters: 參數
        session_id: 會話 ID

    Returns:
        生成結果
    """
    import httpx

    logger.info(f"[RQ-Task] 執行回覆生成")

    # 收集上下文數據
    context_data = parameters.get("context_data", {})

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "gpt-oss:120b",
                    "prompt": f"根據以下信息生成回覆：\n\n{instruction}\n\n上下文：{context_data}",
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 1024},
                },
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")

                return {
                    "success": True,
                    "response": response_text,
                    "observation": "回覆生成成功",
                }

    except Exception as e:
        logger.error(f"[RQ-Task] 回覆生成失敗: {e}")

    return {
        "success": True,
        "response": instruction,
        "observation": "回覆生成回退到原始指令",
    }


# RQ 任務隊列名稱
AGENT_TODO_QUEUE = "agent_todo"


def enqueue_agent_todo(
    session_id: str,
    step_id: int,
    action_type: str,
    instruction: str,
    parameters: Dict[str, Any],
    total_steps: int,
) -> str:
    """交付 Agent-todo 任務到 RQ 隊列

    Args:
        session_id: 會話 ID
        step_id: 步驟 ID
        action_type: 行動類型
        instruction: 執行指令
        parameters: 行動參數
        total_steps: 總步驟數

    Returns:
        Job ID
    """
    from database.rq.queue import get_task_queue

    queue = get_task_queue(AGENT_TODO_QUEUE)

    # 使用字符串形式的函數引用，讓 RQ 能夠正確解析
    job = queue.enqueue(
        "mm_agent.chain.rq_task.execute_agent_todo_sync",
        session_id,
        step_id,
        action_type,
        instruction,
        parameters,
        total_steps,
        job_timeout="10m",  # 10 分鐘超時
        result_ttl=3600,  # 結果保留 1 小時
    )

    logger.info(f"[RQ-Task] 任務已交付: job_id={job.id}, session={session_id}, step={step_id}")
    return job.id
