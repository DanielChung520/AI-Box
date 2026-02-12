"""
SSE Stream Endpoint - 真正串流顯示

使用方式：
- GET /api/v1/chat/stream?sid=xxx&instruction=yyy
- POST /api/v1/chat/stream (JSON body: {"session_id": "xxx", "instruction": "yyy"})
- 從 Ollama 獲取串流響應
- 即時轉發為 SSE 格式
"""

import json
import logging
import asyncio
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

MODELS = [
    {"name": "gpt-oss:120b", "timeout": 180.0},
]


async def generate_stream(instruction: str, session_id: str) -> AsyncGenerator[str, None]:
    """生成 SSE 串流"""
    from sse_starlette.sse import EventSourceResponse
    import httpx

    async def stream_generator():
        try:
            # 1. 發送工作流開始，顯示客戶的問題
            yield {"event": "message", "data": json.dumps({'type': 'workflow_started', 'message': f'客戶要求：{instruction}', 'session_id': session_id})}

            used_model = None

            for model_config in MODELS:
                model_name = model_config["name"]
                timeout = model_config["timeout"]

                yield {"event": "message", "data": json.dumps({'type': 'workflow_started', 'message': f'正在使用 {model_name}...', 'session_id': session_id})}

                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        async with client.stream(
                            "POST",
                            "http://localhost:11434/api/generate",
                            json={
                                "model": model_name,
                                "prompt": f"""你是一位專業的庫存管理 AI Agent。

用戶指令：{instruction}

請嚴格按照以下格式輸出，每個步驟必須換行：

<thinking>
你的思考過程（用完整段落描述）
</thinking>

<plan>
Step 1: [動作] 描述（第一步驟）
Step 2: [動作] 描述（第二步驟）
Step 3: [動作] 描述（第三步驟）
...
</plan>

<ready>
yes
</ready>

重要：每個 Step 必須獨立一行，換行輸出。""",
                                "stream": True,
                            },
                        ) as response:
                            response.raise_for_status()

                            # 狀態機解析
                            in_thinking = False
                            in_plan = False
                            pending = ""
                            thinking_content = ""
                            plan_content = ""

                            async for chunk in response.aiter_lines():
                                if not chunk.strip():
                                    continue

                                try:
                                    data = json.loads(chunk)
                                    # Ollama gpt-oss:120b 返回 thinking 和 response 兩個字段
                                    # thinking: 模型的思考過程（純文字說明）
                                    # response: 包含 <thinking>...</thinking> 等標籤格式
                                    # 優先使用 response，因為它包含結構化標籤供狀態機解析
                                    response = data.get('response', '') or ''
                                    thinking = data.get('thinking', '') or ''
                                    raw_char = response if response.strip() else thinking
                                    if not raw_char:
                                        continue

                                    pending += raw_char

                                    while True:
                                        changed = False

                                        # 檢測 <thinking>
                                        if not in_thinking and not in_plan:
                                            tag_start = pending.find('<thinking>')
                                            if tag_start != -1:
                                                pending = pending[tag_start + 10:]
                                                in_thinking = True
                                                changed = True
                                                continue

                                        # 檢測 </thinking>
                                        if in_thinking:
                                            tag_end = pending.find('</thinking>')
                                            if tag_end != -1:
                                                content = pending[:tag_end].strip()
                                                if content:
                                                    thinking_content += content + '\n'
                                                    yield {"event": "message", "data": json.dumps({'type': 'thinking', 'content': content, 'session_id': session_id})}
                                                    await asyncio.sleep(0.05)
                                                pending = pending[tag_end + 11:]
                                                in_thinking = False
                                                changed = True
                                                continue

                                        # 檢測 <plan>
                                        if not in_thinking and not in_plan:
                                            tag_start = pending.find('<plan>')
                                            if tag_start != -1:
                                                pending = pending[tag_start + 6:]
                                                in_plan = True
                                                changed = True
                                                continue

                                        # 檢測 </plan>
                                        if in_plan:
                                            tag_end = pending.find('</plan>')
                                            if tag_end != -1:
                                                content = pending[:tag_end].strip()
                                                if content:
                                                    plan_content += content + '\n'
                                                pending = pending[tag_end + 7:]
                                                in_plan = False
                                                changed = True
                                                continue

                                        # 檢測 <ready>
                                        if not in_thinking and not in_plan:
                                            tag_start = pending.find('<ready>')
                                            if tag_start != -1:
                                                pending = pending[tag_start + 7:]
                                                tag_end = pending.find('</ready>')
                                                if tag_end != -1:
                                                    pending = pending[tag_end + 8:]
                                                break

                                        if not changed:
                                            break

                                except json.JSONDecodeError:
                                    continue

                            # 思考完成
                            yield {"event": "message", "data": json.dumps({'type': 'thinking_complete', 'message': '思考過程完成', 'session_id': session_id})}

                            # 發送計劃
                            if plan_content.strip():
                                yield {"event": "message", "data": json.dumps({'type': 'plan_started', 'message': '工作計劃已生成', 'session_id': session_id})}

                                for line in plan_content.strip().split('\n'):
                                    line = line.strip()
                                    if line:
                                        yield {"event": "message", "data": json.dumps({'type': 'plan', 'content': line, 'session_id': session_id})}
                                        await asyncio.sleep(0.03)

                            # Ready
                            yield {"event": "message", "data": json.dumps({'type': 'ready', 'message': 'yes', 'session_id': session_id})}

                            # 存儲待執行的工作流
                            logger.info(f"[SSE] 準備存儲工作流: session={session_id}, instruction={instruction[:50]}...")
                            try:
                                from mm_agent.main import PENDING_WORKFLOWS
                                PENDING_WORKFLOWS[session_id] = {
                                    "instruction": instruction,
                                    "plan": plan_content,
                                    "thinking": thinking_content,
                                    "created_at": "now"
                                }
                                logger.info(f"[SSE] 已存儲待執行工作流: session={session_id}, keys={list(PENDING_WORKFLOWS.keys())}")
                            except Exception as e:
                                logger.warning(f"[SSE] 存儲工作流失敗: {e}", exc_info=True)

                            used_model = model_name
                            logger.info(f"[SSE] 完成: {model_name}")
                            break

                except Exception as e:
                    logger.warning(f"[SSE] 模型 {model_name} 失敗: {e}")
                    continue

            if not used_model:
                yield {"event": "message", "data": json.dumps({'type': 'error', 'message': '所有模型都失敗', 'session_id': session_id})}
                return

            # 完成
            yield {"event": "message", "data": json.dumps({'type': 'complete', 'message': '完成', 'session_id': session_id})}

        except Exception as e:
            logger.error(f"[SSE] Error: {e}")
            yield {"event": "message", "data": json.dumps({'type': 'error', 'message': str(e), 'session_id': session_id})}

    return EventSourceResponse(stream_generator(), media_type="text/event-stream")
