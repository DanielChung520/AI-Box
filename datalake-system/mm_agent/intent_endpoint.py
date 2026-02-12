"""
LLM Intent Classification Endpoint - 意圖分類端點

使用 LLM 快速判斷用戶意圖，替代硬編碼關鍵字匹配

意圖類型：
- GREETING: 問候/打招呼
- KNOWLEDGE_QUERY: 業務知識問題
- SIMPLE_QUERY: 簡單數據查詢
- COMPLEX_TASK: 複雜任務/操作指引
- CLARIFICATION: 需要澄清

使用方式：
- POST /api/v1/chat/intent
"""

import json
import logging
from typing import AsyncGenerator
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MODELS = [
    {"name": "gpt-oss:120b", "timeout": 120.0},
]


class IntentType(str, Enum):
    """意圖類型枚舉"""

    GREETING = "GREETING"
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
    SIMPLE_QUERY = "SIMPLE_QUERY"
    COMPLEX_TASK = "COMPLEX_TASK"
    CLARIFICATION = "CLARIFICATION"


class KnowledgeSourceType(str, Enum):
    """知識來源類型"""

    INTERNAL = "internal"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class IntentClassificationResult(BaseModel):
    """意圖分類結果"""

    intent: IntentType
    confidence: float
    is_simple_query: bool
    needs_clarification: bool
    missing_fields: list = []
    clarification_prompts: dict = {}
    thought_process: str = ""
    knowledge_source_type: KnowledgeSourceType = KnowledgeSourceType.UNKNOWN


INTENT_CLASSIFICATION_PROMPT = """你是一位專業的庫存管理 AI Assistant，負責分析用戶查詢意圖。

## 任務
分析以下用戶輸入，判斷其意圖類型。

## 用戶輸入
{instruction}

## 意圖類型定義

1. **GREETING** - 問候/打招呼
   - 例如：「你好」、「Hi」、「早安」、「在嗎」
   - 不需要執行任何操作
   - **關鍵詞**：你好、早安、午安、晚安、嗨、在嗎

2. **KNOWLEDGE_QUERY** - 業務知識問題
   - 例如：「如何做好ABC庫存管理」、「ERP操作步驟」、「公司規定」
   - 特點：需要專業知識解答，可能是內部知識或外部專業知識
   - 子類型：
     - internal: 公司內部知識（ERP操作、公司規定、業務流程）
     - external: 外部專業知識（產業最佳實踐，法規遵循）
   - 需要執行的操作：KA-Agent 或 LLM + 上網搜尋

3. **SIMPLE_QUERY** - 簡單數據查詢
   - 例如：「查詢 W01 倉庫的庫存」、「料號 10-0001 的品名」、「統計 2024 年採購筆數」
   - 特點：
     - 明確的查詢目標
     - 單一數據查詢
     - 不需要多步驟執行
     - 不需要比較、排名、分析
   - 查詢類型：庫存查詢、採購查詢、銷售查詢
   - 需要執行的操作：Text-to-SQL
   - **以下情況應判斷為 SIMPLE_QUERY**：
     - 「查詢 W03 倉庫庫存」
     - 「料號 10-0001 的品名」
     - 「各倉庫的總庫存量」

4. **COMPLEX_TASK** - 複雜任務/操作指引
   - **核心特點**：需要多步驟執行、需要比較分析、需要生成計劃
   - **以下情況應判斷為 COMPLEX_TASK**：
     a. **比較分析類**：包含「比較」、「對比」、「排名」、「排行」
        - 例如：「比較近三個月採購金額」、「各倉庫庫存金額排行」
        - 例如：「成品倉與原料倉庫存對比」
     b. **多維度總覽類**：包含「總覽」、「概述」、「完整」
        - 例如：「料號 10-0001 的採購與庫存總覽」
     c. **業務規則類**：包含「未交」、「未出」、「未交貨」、「未完成」
        - 例如：「本月採購單未交貨明細」
     d. **操作步驟類**：包含「如何」、「怎麼建立」、「操作步驟」
        - 例如：「如何建立採購單」
     e. **分類分析類**：包含「ABC」、「分類分析」
        - 例如：「ABC 庫存分類分析」
   - 需要執行的操作：ReAct 工作流程

5. **CLARIFICATION** - 需要澄清
   - 用戶意圖不明確，缺乏必要信息
   - 例如：「倉庫的庫存」（未指定哪個倉庫）、「那個料號」（未指定料號）
   - **以下情況應判斷為 CLARIFICATION**：
     - 輸入過短（少於 5 個字）
     - 缺少關鍵查詢對象
     - 指代不明确（「那個」、「它」）
   - 需要回問用戶補充信息

## 判斷優先順序

1. 首先檢查是否為 GREETING
2. 然後檢查是否為 CLARIFICATION（輸入過短或缺少關鍵信息）
3. 然後檢查是否為 KNOWLEDGE_QUERY（純知識問題）
4. 然後檢查是否為 COMPLEX_TASK（包含比較、分析、多步驟關鍵詞）
5. 最後判斷為 SIMPLE_QUERY

## 輸出格式
請嚴格按照以下 JSON 格式輸出：

```json
{{
  "intent": "意圖類型",
  "confidence": 0.0-1.0 的置信度,
  "is_simple_query": true/false,
  "needs_clarification": true/false,
  "missing_fields": ["缺失的字段列表"],
  "clarification_prompts": {{"字段名": "詢問方式"}},
  "knowledge_source_type": "internal/external/unknown",
  "thought_process": "你的分析思路"
}}
```

## 範例

**範例 1**
用戶輸入：「你好」
```json
{{
  "intent": "GREETING",
  "confidence": 0.98,
  "is_simple_query": false,
  "needs_clarification": false,
  "missing_fields": [],
  "clarification_prompts": {{}},
  "knowledge_source_type": "unknown",
  "thought_process": "用戶輸入'你好'是典型的問候語，不需要執行任何操作"
}}
```

**範例 2**
用戶輸入：「比較近三個月採購金額」
```json
{{
  "intent": "COMPLEX_TASK",
  "confidence": 0.95,
  "is_simple_query": false,
  "needs_clarification": false,
  "missing_fields": [],
  "clarification_prompts": {{}},
  "knowledge_source_type": "unknown",
  "thought_process": "用戶要求'比較'近三個月採購金額，這是比較分析類的複雜任務，需要多步驟執行：查詢三個月數據→彙總→比較分析→生成回覆"
}}
```

**範例 3**
用戶輸入：「本月採購單未交貨明細」
```json
{{
  "intent": "COMPLEX_TASK",
  "confidence": 0.95,
  "is_simple_query": false,
  "needs_clarification": false,
  "missing_fields": [],
  "clarification_prompts": {{}},
  "knowledge_source_type": "unknown",
  "thought_process": "用戶要求'未交貨'明細，這是業務規則類的複雜任務，需要過濾未完成交貨的採購單，涉及業務邏輯判斷"
}}
```

**範例 4**
用戶輸入：「料號 10-0001 的採購與庫存總覽」
```json
{{
  "intent": "COMPLEX_TASK",
  "confidence": 0.95,
  "is_simple_query": false,
  "needs_clarification": false,
  "missing_fields": [],
  "clarification_prompts": {{}},
  "knowledge_source_type": "unknown",
  "thought_process": "用戶要求'採購與庫存總覽'，這是多維度總覽類的複雜任務，需要查詢採購明細和庫存明細，然後合併回覆"
}}
```

**範例 5**
用戶輸入：「如何做好ABC庫存管理」
```json
{{
  "intent": "KNOWLEDGE_QUERY",
  "confidence": 0.95,
  "is_simple_query": false,
  "needs_clarification": false,
  "missing_fields": [],
  "clarification_prompts": {{}},
  "knowledge_source_type": "external",
  "thought_process": "用戶詢問ABC庫存管理的專業知識，這是業務知識問題，需要檢索相關專業知識"
}}
```

**範例 6**
用戶輸入：「ERP 收料操作步驟」
```json
{{
  "intent": "KNOWLEDGE_QUERY",
  "confidence": 0.95,
  "is_simple_query": false,
  "needs_clarification": false,
  "missing_fields": [],
  "clarification_prompts": {{}},
  "knowledge_source_type": "internal",
  "thought_process": "用戶詢問ERP收料操作，這是公司內部知識，需要查詢KA-Agent"
}}
```

**範例 7**
用戶輸入：「查詢 W03 倉庫的庫存總量」
```json
{{
  "intent": "SIMPLE_QUERY",
  "confidence": 0.95,
  "is_simple_query": true,
  "needs_clarification": false,
  "missing_fields": [],
  "clarification_prompts": {{}},
  "knowledge_source_type": "unknown",
  "thought_process": "用戶想要查詢特定倉庫的庫存總量，這是明確的庫存查詢需求，單一查詢目標"
}}
```

**範例 8**
用戶輸入：「W03」
```json
{{
  "intent": "CLARIFICATION",
  "confidence": 0.9,
  "is_simple_query": true,
  "needs_clarification": true,
  "missing_fields": ["完整查詢需求"],
  "clarification_prompts": {{
    "完整需求": "您說的'W03'是指要查詢什麼？是 W03 倉庫的庫存嗎？"
  }},
  "knowledge_source_type": "unknown",
  "thought_process": "用戶只輸入'W03'，信息過於簡略，無法確定是要查詢庫存、採購還是其他"
}}
```

**範例 9**
用戶輸入：「如何建立採購單」
```json
{{
  "intent": "COMPLEX_TASK",
  "confidence": 0.95,
  "is_simple_query": false,
  "needs_clarification": false,
  "missing_fields": [],
  "clarification_prompts": {{}},
  "knowledge_source_type": "unknown",
  "thought_process": "用戶詢問操作步驟，需要提供詳細的操作指引，這是複雜任務"
}}
```

 **範例 10**
用戶輸入：「各倉庫庫存金額排行」
```json
{{"intent": "COMPLEX_TASK", "confidence": 0.95, "is_simple_query": false, "needs_clarification": false, "missing_fields": [], "clarification_prompts": {{}}, "knowledge_source_type": "unknown", "thought_process": "用戶要求'排行'，這是比較分析類的複雜任務，需要查詢各倉庫庫存×單價→計算金額→排序"}}
```

## 輸出格式範例

**思考過程格式範例：**
```
要完成 ABC 分類，需要先取得每個 SKU 的相關數據...

**1. 必要欄位**
- 商品代號 / SKU
- 商品名稱（可選）
- 年度使用量（或年度銷售量）
- 單位成本（或單位售價）

**2. 計算步驟**
- 計算每項商品的「年消耗金額」＝ 年度使用量 × 單位成本
- 依年消耗金額由高到低排序
- 計算累積金額百分比與累積項目百分比
- 依常用的門檻（如 A佔前70% 金額、B佔70%~90%、C佔90%~100%）劃分類別

**3. 使用者可能的回覆**
- 若使用者直接提供完整的表格，我即可立即執行分類
- 若使用者只提供部分資訊，我需要請他補足缺少的欄位
```

**任務計劃格式範例：**
```
**Step1**: [資料蒐集] 從 ERP/WMS 匯出 SKU、單價、年度使用量等欄位

**Step2**: [資料清理] 檢查缺失值、重複項與單位一致性

**Step3**: [計算金額] 以「單價 × 年度使用量」得到年度消耗金額

**Step4**: [排序累積] 依消耗金額遞減排序，計算累積百分比

**Step5**: [設定門檻] 依 80%/15%/5% 比例設定 A/B/C 分類

 **Step6**: [產出結果] 產出包含 SKU、消耗金額、累積%、分類的表格
```

**回問格式範例：**
```json
{{
  "intent": "CLARIFICATION",
  "confidence": 0.9,
  "is_simple_query": true,
  "needs_clarification": true,
  "missing_fields": ["SKU資料"],
  "clarification_prompts": {{
    "資料來源": "請問您要分析的 SKU 資料是從 ERP 系統匯出，還是提供 Excel 檔案？"
  }},
  "thought_process": "使用者未提供 SKU 資料，需要請他補充"
}}
```

## 重要規則

1. **只返回 JSON**：嚴格只輸出 JSON 格式，不要輸出任何其他文字、標籤或說明
2. **不要使用 <thinking> 標籤**：不要輸出 `<thinking>`、`</thinking>`、`<plan>`、`</plan>` 等標籤
3. **思考過程格式**：使用完整句子，主要標題用 **加粗**（如 **1. 必要欄位**），每項之間要有空行分隔
4. **回問格式**：clarification_prompts 的 key 用簡短標題（如 "資料來源"），value 是完整問句，不需要加粗
5. **優先識別 GREETING**：問候語直接返回
6. **輸入過短判斷 CLARIFICATION**：少於 5 個字或缺少關鍵對象
7. **知識問題優先 KNOWLEDGE_QUERY**：純知識查詢不涉及數據
8. **包含比較/排名/總覽/未交 → COMPLEX_TASK**：這些關鍵詞表示複雜任務
9. **簡單數據查詢 → SIMPLE_QUERY**：單一查詢目標
10. **confidence 應反映判斷確定程度**

請分析用戶輸入並直接輸出 JSON 格式結果，不要有任何額外說明：
"""


async def classify_intent(instruction: str, session_id: str = "") -> IntentClassificationResult:
    """使用 LLM 進行意圖分類"""

    import httpx

    prompt = INTENT_CLASSIFICATION_PROMPT.format(instruction=instruction)
    used_model = None

    for model_config in MODELS:
        model_name = model_config["name"]
        timeout = model_config["timeout"]

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()

                data = response.json()
                content = data.get("response", "") or data.get("thinking", "")

                logger.info(f"[Intent] LLM 返回: {content[:200]}...")

                result = parse_llm_response(content)
                used_model = model_name
                logger.info(f"[Intent] 分類完成: {result.intent.value}, 模型: {model_name}")
                return result

        except Exception as e:
            logger.warning(f"[Intent] 模型 {model_name} 失敗: {e}")
            continue

    logger.error("[Intent] 所有模型都失敗")
    return IntentClassificationResult(
        intent=IntentType.SIMPLE_QUERY,
        confidence=0.5,
        is_simple_query=True,
        needs_clarification=False,
        thought_process="模型調用失敗，使用默認分類",
    )


def parse_llm_response(content: str) -> IntentClassificationResult:
    """解析 LLM 返回的內容，提取意圖分類結果"""
    import re

    text = content.strip()

    # 清理 markdown code block
    text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text)

    # 清理 <thinking> 標籤（如果 LLM 錯誤地返回了標籤格式）
    text = re.sub(r"<\/?thinking[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<\/?plan[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<\/?ready[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<\/?response[^>]*>", "", text, flags=re.IGNORECASE)

    # 清理 Markdown 粗體標籤
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)

    # 嘗試提取 JSON
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        json_str = text[start : end + 1]
        
        # 清理 JSON 中的轉義字符和多余字符
        # 處理中文引號
        json_str = json_str.replace("「", '"').replace("」", '"')
        json_str = json_str.replace("『", '"').replace("』", '"')
        
        # 處理轉義的換行
        json_str = re.sub(r'\\n\s*', ' ', json_str)
        
        try:
            data = json.loads(json_str)
            intent_str = data.get("intent", "SIMPLE_QUERY")

            try:
                intent = IntentType(intent_str)
            except ValueError:
                intent = IntentType.SIMPLE_QUERY

            knowledge_source_str = data.get("knowledge_source_type", "unknown")
            try:
                knowledge_source_type = KnowledgeSourceType(knowledge_source_str)
            except ValueError:
                knowledge_source_type = KnowledgeSourceType.UNKNOWN

            return IntentClassificationResult(
                intent=intent,
                confidence=data.get("confidence", 0.8),
                is_simple_query=data.get("is_simple_query", intent == IntentType.SIMPLE_QUERY),
                needs_clarification=data.get("needs_clarification", False),
                missing_fields=data.get("missing_fields", []),
                clarification_prompts=data.get("clarification_prompts", {}),
                thought_process=data.get("thought_process", ""),
                knowledge_source_type=knowledge_source_type,
            )
        except json.JSONDecodeError as e:
            logger.warning(f"[Intent] JSON 解析失敗: {e}, 原始內容: {json_str[:200]}...")
    
    # 如果無法解析 JSON，使用備用解析方法
    return fallback_parse(content)


def fallback_parse(content: str) -> IntentClassificationResult:
    """備用解析方法"""
    text_lower = content.lower()

    greeting_keywords = ["你好", "hi", "hello", "早安", "晚安", "在嗎", "嗨"]
    if any(kw in text_lower for kw in greeting_keywords):
        return IntentClassificationResult(
            intent=IntentType.GREETING,
            confidence=0.9,
            is_simple_query=False,
            needs_clarification=False,
            thought_process="通過關鍵詞判斷為問候語",
        )

    knowledge_keywords = ["如何", "什麼是", "說明", "定義", "步驟", "操作", "ERP", "規定", "流程"]
    if any(kw in text_lower for kw in knowledge_keywords):
        return IntentClassificationResult(
            intent=IntentType.KNOWLEDGE_QUERY,
            confidence=0.85,
            is_simple_query=False,
            needs_clarification=False,
            knowledge_source_type=KnowledgeSourceType.EXTERNAL,
            thought_process="通過關鍵詞判斷為業務知識問題",
        )

    complex_keywords = ["分析", "比較", "排名", "ABC", "分類", "趨勢", "預測", "統計", "報告"]
    if any(kw in text_lower for kw in complex_keywords):
        return IntentClassificationResult(
            intent=IntentType.COMPLEX_TASK,
            confidence=0.85,
            is_simple_query=False,
            needs_clarification=False,
            thought_process="通過關鍵詞判斷為複雜任務",
        )

    if len(content.strip()) < 5:
        return IntentClassificationResult(
            intent=IntentType.CLARIFICATION,
            confidence=0.8,
            is_simple_query=True,
            needs_clarification=True,
            missing_fields=["完整查詢需求"],
            clarification_prompts={"完整查詢需求": "請提供更詳細的查詢需求"},
            thought_process="輸入過短，需要澄清",
        )

    return IntentClassificationResult(
        intent=IntentType.SIMPLE_QUERY,
        confidence=0.7,
        is_simple_query=True,
        needs_clarification=False,
        thought_process="默認為簡單查詢",
    )


async def generate_intent_stream(
    instruction: str, session_id: str
) -> AsyncGenerator[str, None]:
    """生成意圖分類的 SSE 串流"""
    from sse_starlette.sse import EventSourceResponse
    import httpx

    async def stream_generator():
        try:
            yield {"event": "message", "data": json.dumps({"type": "intent_started", "message": "正在分析意圖...", "session_id": session_id})}

            prompt = INTENT_CLASSIFICATION_PROMPT.format(instruction=instruction)
            used_model = None

            for model_config in MODELS:
                model_name = model_config["name"]
                timeout = model_config["timeout"]

                yield {"event": "message", "data": json.dumps({"type": "intent_started", "message": f"正在使用 {model_name} 分析...", "session_id": session_id})}

                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        async with client.stream(
                            "POST",
                            "http://localhost:11434/api/generate",
                            json={
                                "model": model_name,
                                "prompt": prompt,
                                "stream": True,
                            },
                        ) as response:
                            response.raise_for_status()

                            thinking_content = ""

                            async for chunk in response.aiter_lines():
                                if chunk.strip():
                                    try:
                                        data = json.loads(chunk)
                                        # Ollama gpt-oss:120b 返回 thinking 和 response 兩個字段
                                        # thinking: 模型的思考過程（純文字說明）
                                        # response: 包含 <thinking>...</thinking> 等標籤格式
                                        # 優先使用 response，因為它包含結構化標籤
                                        response_text = data.get("response", "") or ""
                                        thinking_text = data.get("thinking", "") or ""
                                        raw_char = response_text if response_text.strip() else thinking_text
                                        if raw_char:
                                            thinking_content += raw_char
                                            yield {"event": "message", "data": json.dumps({"type": "intent_thinking", "content": raw_char, "session_id": session_id})}
                                    except json.JSONDecodeError:
                                        pass

                            yield {"event": "message", "data": json.dumps({"type": "intent_thinking_complete", "message": "思考完成", "session_id": session_id})}

                            result = parse_llm_response(thinking_content)

                            yield {
                                "event": "message",
                                "data": json.dumps(
                                    {
                                        "type": "intent_classified",
                                        "intent": result.intent.value,
                                        "confidence": result.confidence,
                                        "is_simple_query": result.is_simple_query,
                                        "needs_clarification": result.needs_clarification,
                                        "missing_fields": result.missing_fields,
                                        "clarification_prompts": result.clarification_prompts,
                                        "knowledge_source_type": result.knowledge_source_type.value,
                                        "thought_process": result.thought_process,
                                        "session_id": session_id,
                                    }
                                ),
                            }

                            used_model = model_name
                            logger.info(f"[Intent Stream] 分類完成: {result.intent.value}, 模型: {model_name}")
                            break

                except Exception as e:
                    logger.warning(f"[Intent Stream] 模型 {model_name} 失敗: {e}")
                    continue

            if not used_model:
                yield {"event": "message", "data": json.dumps({"type": "error", "message": "所有模型都失敗", "session_id": session_id})}

            yield {"event": "message", "data": json.dumps({"type": "intent_complete", "message": "完成", "session_id": session_id})}

        except Exception as e:
            logger.error(f"[Intent Stream] Error: {e}")
            yield {"event": "message", "data": json.dumps({"type": "error", "message": str(e), "session_id": session_id})}

    return EventSourceResponse(stream_generator(), media_type="text/event-stream")
