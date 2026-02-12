"""
WebSocket Stream Endpoint - 真正的流式響應

Ollama 返回 NDJSON，一行一行數據
我們即時讀取、即時發送到前端
"""

import json
import logging
import html
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

MODELS = [
    {"name": "gpt-oss:120b", "timeout": 180.0},
]


def sync_ollama_stream(model_name: str, instruction: str, timeout: float):
    """同步讀取 Ollama 流，返回文本"""
    import httpx
    
    try:
        with httpx.Client(timeout=timeout) as client:
            with client.stream(
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
                
                all_bytes = b''
                for chunk in response.iter_bytes():
                    all_bytes += chunk
                
                return all_bytes.decode('utf-8'), None
                
    except Exception as e:
        logger.error(f"[Sync Ollama] Error: {e}")
        return None, str(e)


async def websocket_generate_stream(websocket):
    """WebSocket 串流生成器"""
    from concurrent.futures import ThreadPoolExecutor
    
    executor = ThreadPoolExecutor(max_workers=1)
    loop = asyncio.get_event_loop()
    
    try:
        data = await websocket.receive_text()
        request_data = json.loads(data)
        instruction = request_data.get("instruction", "")
        session_id = request_data.get("session_id", f"ws-{id(websocket)}")

        await websocket.send_json({
            "type": "workflow_started",
            "message": f"客戶要求：{instruction}",
            "session_id": session_id
        })

        used_model = None
        text = None
        
        for model_config in MODELS:
            model_name = model_config["name"]
            timeout = model_config["timeout"]
            
            await websocket.send_json({
                "type": "workflow_started",
                "message": f"正在使用 {model_name}...",
                "session_id": session_id
            })
            
            # 在執行器中運行
            text, error = await loop.run_in_executor(
                executor, 
                sync_ollama_stream, 
                model_name, 
                instruction, 
                timeout
            )
            
            if text and not error:
                used_model = model_name
                logger.info(f"[WebSocket] 完成: {model_name}")
                break
            else:
                logger.warning(f"[WebSocket] 模型 {model_name} 失敗: {error}")
                continue

        if not used_model or not text:
            await websocket.send_json({
                "type": "error",
                "message": "所有模型都失敗",
                "session_id": session_id
            })
            return

        # 狀態機解析 - 只提取標籤內的內容
        in_thinking = False
        in_plan = False
        pending_content = ""
        thinking_content = ""
        plan_content = ""

        for line in text.strip().split('\n'):
            if not line.strip():
                continue
            try:
                data_obj = json.loads(line)
                # Ollama gpt-oss:120b 返回 thinking 和 response 兩個字段
                # thinking: 模型的思考過程（純文字說明）
                # response: 包含 <thinking>...</thinking> 等標籤格式
                # 優先使用 response，因為它包含結構化標籤供狀態機解析
                response = data_obj.get('response', '') or ''
                thinking = data_obj.get('thinking', '') or ''
                raw_char = response if response.strip() else thinking
                if not raw_char:
                    continue

                pending_content += raw_char

                while True:
                    changed = False

                    if not in_thinking and not in_plan:
                        tag_start = pending_content.find('<thinking>')
                        if tag_start != -1:
                            pending_content = pending_content[tag_start + 10:]
                            in_thinking = True
                            changed = True
                            continue

                    if in_thinking:
                        tag_end = pending_content.find('</thinking>')
                        if tag_end != -1:
                            content = pending_content[:tag_end].strip()
                            if content:
                                thinking_content += content + '\n'
                                await websocket.send_json({
                                    "type": "thinking",
                                    "content": content,
                                    "session_id": session_id
                                })
                                await asyncio.sleep(0.05)
                            pending_content = pending_content[tag_end + 11:]
                            in_thinking = False
                            changed = True
                            continue

                    if not in_thinking and not in_plan:
                        tag_start = pending_content.find('<plan>')
                        if tag_start != -1:
                            pending_content = pending_content[tag_start + 6:]
                            in_plan = True
                            changed = True
                            continue

                    if in_plan:
                        tag_end = pending_content.find('</plan>')
                        if tag_end != -1:
                            content = pending_content[:tag_end].strip()
                            if content:
                                plan_content += content + '\n'
                            pending_content = pending_content[tag_end + 7:]
                            in_plan = False
                            changed = True
                            continue

                    if not in_thinking and not in_plan:
                        tag_start = pending_content.find('<ready>')
                        if tag_start != -1:
                            pending_content = pending_content[tag_start + 7:]
                            tag_end = pending_content.find('</ready>')
                            if tag_end != -1:
                                pending_content = pending_content[tag_end + 8:]
                            break

                    if not changed:
                        break

                if data_obj.get('done', False):
                    break
            except json.JSONDecodeError:
                continue

        # 發送 thinking_complete
        await websocket.send_json({
            "type": "thinking_complete",
            "message": "思考過程完成",
            "session_id": session_id
        })

        # 發送 plan_started
        if plan_content.strip():
            await websocket.send_json({
                "type": "plan_started",
                "message": "工作計劃已生成",
                "session_id": session_id
            })

            for line in plan_content.strip().split('\n'):
                line = line.strip()
                if line:
                    await websocket.send_json({
                        "type": "plan",
                        "content": line,
                        "session_id": session_id
                    })
                    await asyncio.sleep(0.03)

        # 發送 ready
        await websocket.send_json({
            "type": "ready",
            "message": "yes",
            "session_id": session_id
        })

        # 發送 plan sections
        if plan_content:
            await websocket.send_json({
                "type": "plan_started",
                "message": "工作計劃已生成",
                "session_id": session_id
            })

            for line in plan_content.split('\n'):
                line = line.strip()
                if line:
                    await websocket.send_json({
                        "type": "plan",
                        "content": line,
                        "session_id": session_id
                    })
                    await asyncio.sleep(0.03)

        # 發送 ready
        await websocket.send_json({
            "type": "ready",
            "message": "yes",
            "session_id": session_id
        })

        # 存儲待執行的工作流（用戶確認後在意圖端點啟動）
        try:
            from mm_agent.main import PENDING_WORKFLOWS
            PENDING_WORKFLOWS[session_id] = {
                "instruction": instruction,
                "plan": plan_content,
                "thinking": thinking_content,
                "created_at": "now"
            }
            logger.info(f"[WebSocket] 已存儲待執行工作流: session={session_id}")
        except Exception as e:
            logger.warning(f"[WebSocket] 存儲工作流失敗: {e}")

        await websocket.send_json({
            "type": "complete",
            "message": "完成",
            "session_id": session_id
        })

    except Exception as e:
        logger.error(f"[WebSocket] Error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "session_id": "error"
            })
        except:
            pass
