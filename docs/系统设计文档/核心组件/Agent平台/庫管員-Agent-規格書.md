# 庫管員 Agent 規格書

**版本**：2.2
**創建日期**：2026-01-13
**創建人**：Daniel Chung
**最後修改日期**：2026-01-13

> **📋 相關文檔**：
>
> - [AI-Box-Agent-架構規格書.md](./AI-Box-Agent-架構規格書.md) - Agent 架構總體設計
> - [Data-Agent-規格書.md](./Data-Agent-規格書.md) - Data Agent 規格書（**必讀**：了解數據查詢接口）
> - [模擬-Datalake-規劃書.md](./模擬-Datalake-規劃書.md) - 模擬 Datalake 規劃書（**必讀**：了解外部數據源）
> - [Agent-開發規範.md](./Agent-開發規範.md) - Agent 開發指南
> - [Agent-部署方式建議.md](./Agent-部署方式建議.md) - Agent 部署方式建議

---

## 目錄

1. [概述](#1-概述)
2. [工作職責](#2-工作職責)
3. [指令接收與語義分析](#3-指令接收與語義分析)
4. [提示詞管理](#4-提示詞管理)
5. [上下文管理](#5-上下文管理)
6. [職責理解與任務分解](#6-職責理解與任務分解)
7. [Data Agent 調用](#7-data-agent-調用)
8. [數據結果判斷與處理](#8-數據結果判斷與處理)
9. [業務邏輯處理](#9-業務邏輯處理)
10. [交付標準](#10-交付標準)
11. [代碼實現規格](#11-代碼實現規格)
12. [與其他組件的協作](#12-與其他組件的協作)
13. [實現計劃](#13-實現計劃)
14. [測試結果與驗證](#14-測試結果與驗證)

---

## 1. 概述

### 1.1 定位

**庫管員 Agent（Warehouse Manager Agent）**是一個**外部業務 Agent**，作為獨立服務註冊到 AI-Box，負責庫存管理業務邏輯：

- **料號查詢**：查詢物料編號、規格、單位等基本信息
- **庫存查詢**：查詢當前庫存數量、庫存位置、庫存狀態
- **缺料分析**：分析庫存是否缺料，計算缺料數量
- **採購單生成**：當庫存缺料時，生成採購單（虛擬動作，用於測試）
- **庫存管理**：其他庫存相關工作（庫存調整、庫存盤點等）

**重要原則**：

- ✅ **外部服務**：作為獨立服務部署，通過 MCP Protocol 與 AI-Box 通信
- ✅ **業務邏輯層**：專注於庫存管理業務邏輯，不直接訪問數據
- ✅ **數據代理**：通過 Data Agent 訪問 Datalake，不直接訪問 SeaweedFS

### 1.2 設計目標

1. **真實業務場景模擬**：模擬真實的庫存管理業務流程
2. **智能語義理解**：理解用戶指令的語義，識別要履行的職責
3. **數據代理調用**：通過 Data Agent 訪問外部 Datalake（SeaweedFS）
4. **結果智能判斷**：對數據結果進行初步判斷和業務邏輯處理
5. **虛擬動作支持**：支持虛擬的採購單生成動作（不實際執行，僅記錄）

### 1.3 架構位置

```
┌─────────────────────────────────────────────────────────┐
│  AI-Box（AI 操作系統）                                   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  第一層：協調層（Agent Orchestrator）              │   │
│  │  - 接收用戶指令：「查詢料號 ABC-123 的庫存」      │   │
│  │  - 任務分析與路由                                 │   │
│  │  - 通過 MCP Client 調用庫管員 Agent               │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↓ MCP Protocol
┌─────────────────────────────────────────────────────────┐
│  庫管員 Agent（外部服務，端口 8003）                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │  MCP Server                                       │   │
│  │  - 接收來自 AI-Box 的調用                        │   │
│  │  - 語義分析與職責理解                             │   │
│  │  - 通過 Orchestrator 調用 Data Agent              │   │
│  │  - 結果判斷與業務邏輯處理                         │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↓ 通過 AI-Box Orchestrator
┌─────────────────────────────────────────────────────────┐
│  Data Agent（Datalake 外部服務，端口 8004）              │
│  ┌──────────────────────────────────────────────────┐   │
│  │  - 查詢外部 Datalake（SeaweedFS）                │   │
│  │  - 返回料號和庫存數據                             │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 工作職責

### 2.1 核心職責

#### 2.1.1 語義分析與理解

1. **指令語義分析**
   - 解析用戶自然語言指令
   - 識別關鍵詞和意圖
   - 提取業務參數（料號、數量等）

2. **職責識別**
   - 判斷要履行的職責類型
   - 確定需要的數據查詢
   - 規劃執行步驟

#### 2.1.2 數據查詢協調

1. **Data Agent 調用**
   - 通過 AI-Box Orchestrator 調用 Data Agent
   - 構建查詢請求參數
   - 處理查詢響應

2. **數據結果判斷**
   - 驗證數據完整性
   - 判斷數據有效性
   - 識別異常情況

#### 2.1.3 業務邏輯處理

1. **缺料分析**
   - 比較當前庫存與安全庫存
   - 計算缺料數量
   - 判斷缺料狀態

2. **採購單生成**
   - 生成採購單記錄（虛擬）
   - 記錄採購單信息
   - 返回採購單結果

### 2.2 職責邊界

**庫管員 Agent 負責**：

- ✅ 語義分析和職責理解
- ✅ 業務邏輯處理（缺料分析、採購單生成）
- ✅ 數據結果的初步判斷
- ✅ 通過 Orchestrator 調用 Data Agent

**庫管員 Agent 不負責**：

- ❌ 直接訪問 Datalake（由 Data Agent 負責）
- ❌ 數據存儲和管理（由 Datalake 負責）
- ❌ 數據字典和 Schema 管理（由 Data Agent 負責）

---

## 3. 指令接收與語義分析

### 3.1 指令接收流程

庫管員 Agent 通過 MCP Protocol 接收來自 AI-Box Orchestrator 的調用：

```python
async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
    """
    執行庫存管理任務

    Args:
        request: Agent 服務請求，包含：
            - task_id: 任務 ID
            - task_data: 任務數據（用戶指令或結構化請求）
            - metadata: 元數據（用戶信息、租戶信息等）

    Returns:
        Agent 服務響應，包含：
            - task_id: 任務 ID
            - status: 任務狀態（completed/failed/error）
            - result: 執行結果
            - error: 錯誤信息（如果有）
            - metadata: 元數據
    """
    # 1. 接收指令
    user_instruction = request.task_data.get("instruction", "")

    # 2. 語義分析
    semantic_result = await self._analyze_semantics(user_instruction)

    # 3. 職責理解
    responsibility = await self._understand_responsibility(semantic_result)

    # 4. 執行任務
    result = await self._execute_responsibility(responsibility, request)

    return AgentServiceResponse(
        task_id=request.task_id,
        status="completed",
        result=result,
        metadata=request.metadata,
    )
```

### 3.2 語義分析實現

#### 3.2.1 關鍵詞識別

```python
async def _analyze_semantics(self, instruction: str) -> SemanticAnalysisResult:
    """語義分析：識別關鍵詞和意圖"""

    # 定義關鍵詞模式
    patterns = {
        "query_part": [
            r"查詢.*料號",
            r"查詢.*物料",
            r"料號.*信息",
            r"料號.*規格",
            r"料號.*供應商",
            r"供應商.*誰",
            r"物料.*信息",
            r"part.*info",
            r"query.*part",
        ],
        "query_stock": [
            r"查詢.*庫存",
            r"庫存.*數量",
            r"還有.*庫存",
            r"庫存.*多少",
            r"多少.*庫存",
            r"stock.*quantity",
            r"current.*stock",
            r"存放在.*哪裡",
            r"存放.*位置",
        ],
        "analyze_shortage": [
            r"缺料",
            r"補貨",
            r"shortage",
            r"需要.*補",
            r"庫存.*不足",
        ],
        "generate_purchase_order": [
            r"生成.*採購單",
            r"創建.*採購單",
            r"purchase.*order",
            r"採購",
        ],
    }

    # 識別意圖
    detected_intent = None
    confidence = 0.0

    for intent, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, instruction, re.IGNORECASE):
                detected_intent = intent
                confidence = 0.8
                break

    # 提取參數
    part_number = self._extract_part_number(instruction)
    quantity = self._extract_quantity(instruction)

    return SemanticAnalysisResult(
        intent=detected_intent,
        confidence=confidence,
        parameters={
            "part_number": part_number,
            "quantity": quantity,
        },
        original_instruction=instruction,
    )
```

#### 3.2.2 參數提取

```python
def _extract_part_number(self, instruction: str) -> Optional[str]:
    """提取料號"""

    # 模式1：ABC-123 格式
    pattern1 = r"([A-Z]{2,4}-\d{2,6})"
    match = re.search(pattern1, instruction, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # 模式2：料號 ABC-123
    pattern2 = r"料號[：:]\s*([A-Z0-9-]+)"
    match = re.search(pattern2, instruction, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return None

def _extract_quantity(self, instruction: str) -> Optional[int]:
    """提取數量

    注意：避免從料號中提取數量（如ABC-123中的123）
    """

    # 先提取料號，避免從料號中提取數量
    part_number = self._extract_part_number(instruction)

    # 模式：數字 + 單位（件、個、PCS等）
    # 排除料號中的數字（如ABC-123中的123）
    pattern = r"(\d+)\s*(?:件|個|PCS|pcs|unit|units)"
    matches = list(re.finditer(pattern, instruction, re.IGNORECASE))

    for match in matches:
        # 檢查這個數字是否在料號中
        match_start = match.start()
        match_end = match.end()
        matched_text = instruction[max(0, match_start - 10) : match_end + 10]

        # 如果匹配的數字在料號附近（前後10個字符內），跳過
        if part_number and part_number.replace("-", "").replace("_", "") in matched_text:
            continue

        try:
            quantity = int(match.group(1))
            # 數量應該在合理範圍內（1-1000000）
            if 1 <= quantity <= 1000000:
                return quantity
        except ValueError:
            continue

    return None
```

### 3.3 語義分析結果模型

```python
class SemanticAnalysisResult(BaseModel):
    """語義分析結果"""

    intent: Optional[str] = None  # 識別的意圖
    confidence: float = 0.0  # 置信度（0-1）
    parameters: Dict[str, Any] = {}  # 提取的參數
    original_instruction: str  # 原始指令
    clarification_needed: bool = False  # 是否需要澄清
    clarification_questions: List[str] = []  # 澄清問題列表
```

---

## 4. 提示詞管理

### 4.1 為什麼需要提示詞

庫管員 Agent 需要理解用戶的自然語言指令，單純的正則表達式匹配可能無法處理：

1. **複雜指令**：如「幫我看看 ABC-123 的庫存夠不夠，不夠的話生成採購單」
2. **模糊指令**：如「那個料號的庫存怎麼樣了」
3. **多意圖指令**：如「查詢 ABC-123 和 XYZ-456 的庫存，看看哪個缺料」
4. **上下文相關指令**：如「剛才查的那個料號，幫我生成採購單」

**建議**：使用 LLM + 提示詞進行語義分析，正則表達式作為備選方案。

### 4.2 System Prompt 設計

```python
WAREHOUSE_AGENT_SYSTEM_PROMPT = """你是一個庫存管理助手（庫管員 Agent），專門負責處理庫存管理相關的業務邏輯。

你的職責：
1. 理解用戶的庫存管理指令
2. 識別用戶要執行的操作類型（查詢料號、查詢庫存、缺料分析、生成採購單等）
3. 提取業務參數（料號、數量等）
4. 理解上下文中的指代（如「剛才查的那個料號」）

支持的操作類型：
- query_part: 查詢物料基本信息
- query_stock: 查詢庫存信息
- analyze_shortage: 缺料分析
- generate_purchase_order: 生成採購單
- adjust_stock: 調整庫存（虛擬）

輸出要求：
- 必須返回有效的 JSON 格式
- 包含識別的意圖（intent）、置信度（confidence）、提取的參數（parameters）
- 如果指令不明確，標記需要澄清（clarification_needed）並提供澄清問題
"""
```

### 4.3 User Prompt 構建

```python
def _build_semantic_analysis_prompt(
    self,
    instruction: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """構建語義分析提示詞"""

    prompt = f"""分析以下用戶指令，識別意圖並提取參數。

用戶指令：
{instruction}

"""

    # 添加上下文信息（如果提供）
    if context:
        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        prompt += f"""上下文信息：
{context_str}

注意：如果指令中包含指代（如「剛才查的那個料號」），請從上下文中獲取對應的值。

"""

    prompt += """請返回以下 JSON 格式：
{
    "intent": "query_part|query_stock|analyze_shortage|generate_purchase_order|adjust_stock",
    "confidence": 0.0-1.0,
    "parameters": {
        "part_number": "料號（如果可提取）",
        "quantity": 數量（如果可提取）,
        "location": "庫存位置（如果可提取）"
    },
    "clarification_needed": false,
    "clarification_questions": []
}

如果指令不明確，請設置 clarification_needed 為 true，並提供澄清問題。"""

    return prompt
```

### 4.4 LLM 調用實現

```python
async def _analyze_semantics_with_llm(
    self,
    instruction: str,
    context: Optional[Dict[str, Any]] = None,
) -> SemanticAnalysisResult:
    """使用 LLM 進行語義分析"""

    try:
        # 構建提示詞
        system_prompt = WAREHOUSE_AGENT_SYSTEM_PROMPT
        user_prompt = self._build_semantic_analysis_prompt(instruction, context)

        # 調用 LLM（使用 AI-Box 的 LLM 服務或本地 LLM）
        llm_response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,  # 低溫度，提高確定性
        )

        # 解析 LLM 響應
        result = json.loads(llm_response)

        return SemanticAnalysisResult(
            intent=result.get("intent"),
            confidence=result.get("confidence", 0.0),
            parameters=result.get("parameters", {}),
            original_instruction=instruction,
            clarification_needed=result.get("clarification_needed", False),
            clarification_questions=result.get("clarification_questions", []),
        )

    except Exception as e:
        # LLM 調用失敗，回退到正則表達式
        self._logger.warning(f"LLM semantic analysis failed, falling back to regex: {e}")
        return await self._analyze_semantics_with_regex(instruction)
```

### 4.5 混合策略

```python
async def _analyze_semantics(
    self,
    instruction: str,
    context: Optional[Dict[str, Any]] = None,
) -> SemanticAnalysisResult:
    """語義分析（混合策略）"""

    # 策略1：簡單指令使用正則表達式（快速）
    if self._is_simple_instruction(instruction):
        return await self._analyze_semantics_with_regex(instruction)

    # 策略2：複雜指令使用 LLM（智能）
    return await self._analyze_semantics_with_llm(instruction, context)

def _is_simple_instruction(self, instruction: str) -> bool:
    """判斷是否為簡單指令"""

    # 簡單指令特徵：
    # 1. 長度較短（< 50 字符）
    # 2. 包含明確的關鍵詞和料號
    # 3. 不包含指代或上下文依賴

    if len(instruction) > 50:
        return False

    # 檢查是否包含指代
    if any(word in instruction for word in ["剛才", "那個", "這個", "它", "他"]):
        return False

    # 檢查是否包含明確的料號
    if re.search(r"[A-Z]{2,4}-\d{2,6}", instruction, re.IGNORECASE):
        return True

    return False
```

---

## 5. 上下文管理

### 5.1 為什麼需要上下文管理

庫管員 Agent 需要支持多輪對話，記住之前的查詢結果和上下文：

1. **指代理解**：如「剛才查的那個料號，幫我生成採購單」
2. **連續查詢**：如「查詢 ABC-123 的庫存」→「它缺料嗎？」→「生成採購單」
3. **結果引用**：如「剛才查的那個料號，庫存是多少來著？」

### 5.2 上下文數據模型

```python
class ConversationContext(BaseModel):
    """對話上下文"""

    session_id: str  # 會話 ID
    user_id: Optional[str] = None  # 用戶 ID
    tenant_id: Optional[str] = None  # 租戶 ID

    # 歷史記錄
    history: List[Dict[str, Any]] = []  # 歷史對話記錄

    # 當前查詢的上下文
    current_query: Optional[Dict[str, Any]] = None  # 當前查詢信息
    last_result: Optional[Dict[str, Any]] = None  # 上次查詢結果

    # 提取的實體（用於指代解析）
    entities: Dict[str, Any] = {}  # 實體映射，如 {"last_part_number": "ABC-123"}

    # 時間戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

### 5.3 上下文存儲

```python
class ContextManager:
    """上下文管理器"""

    def __init__(self):
        self._contexts: Dict[str, ConversationContext] = {}
        self._max_history_length = 10  # 最大歷史記錄長度

    async def get_context(
        self,
        session_id: str,
    ) -> ConversationContext:
        """獲取上下文"""

        if session_id not in self._contexts:
            self._contexts[session_id] = ConversationContext(
                session_id=session_id,
            )

        return self._contexts[session_id]

    async def update_context(
        self,
        session_id: str,
        instruction: str,
        result: Dict[str, Any],
    ) -> None:
        """更新上下文"""

        context = await self.get_context(session_id)

        # 添加歷史記錄
        context.history.append({
            "instruction": instruction,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        })

        # 限制歷史記錄長度
        if len(context.history) > self._max_history_length:
            context.history = context.history[-self._max_history_length:]

        # 更新當前查詢和結果
        context.current_query = {
            "instruction": instruction,
            "timestamp": datetime.now().isoformat(),
        }
        context.last_result = result

        # 提取實體（用於指代解析）
        self._extract_entities(context, result)

        # 更新時間戳
        context.updated_at = datetime.now()

    def _extract_entities(
        self,
        context: ConversationContext,
        result: Dict[str, Any],
    ) -> None:
        """從結果中提取實體（支持多種結果格式）"""

        # 提取料號（多種可能的字段位置）
        part_number = None

        # 直接字段
        if "part_number" in result:
            part_number = result["part_number"]
        # 從part_info中提取
        elif "part_info" in result and isinstance(result["part_info"], dict):
            part_number = result["part_info"].get("part_number")
        # 從stock_info中提取
        elif "stock_info" in result and isinstance(result["stock_info"], dict):
            part_number = result["stock_info"].get("part_number")
        # 從result嵌套中提取
        elif "result" in result and isinstance(result["result"], dict):
            inner_result = result["result"]
            if "part_number" in inner_result:
                part_number = inner_result["part_number"]
            elif "part_info" in inner_result and isinstance(inner_result["part_info"], dict):
                part_number = inner_result["part_info"].get("part_number")
            elif "stock_info" in inner_result and isinstance(inner_result["stock_info"], dict):
                part_number = inner_result["stock_info"].get("part_number")

        if part_number:
            context.entities["last_part_number"] = part_number

        # 提取庫存信息（支持多種格式）
        stock = None
        if "current_stock" in result:
            stock = result["current_stock"]
        elif "stock_info" in result and isinstance(result["stock_info"], dict):
            stock = result["stock_info"].get("current_stock")
        elif "result" in result and isinstance(result["result"], dict):
            inner_result = result["result"]
            if "current_stock" in inner_result:
                stock = inner_result["current_stock"]
            elif "stock_info" in inner_result and isinstance(inner_result["stock_info"], dict):
                stock = inner_result["stock_info"].get("current_stock")

        if stock is not None:
            context.entities["last_stock"] = stock

        # 提取缺料狀態（支持多種格式）
        is_shortage = None
        if "is_shortage" in result:
            is_shortage = result["is_shortage"]
        elif "analysis" in result and isinstance(result["analysis"], dict):
            is_shortage = result["analysis"].get("is_shortage")
        elif "result" in result and isinstance(result["result"], dict):
            inner_result = result["result"]
            if "is_shortage" in inner_result:
                is_shortage = inner_result["is_shortage"]
            elif "analysis" in inner_result and isinstance(inner_result["analysis"], dict):
                is_shortage = inner_result["analysis"].get("is_shortage")

        if is_shortage is not None:
            context.entities["last_shortage_status"] = is_shortage
```

### 5.4 指代解析

```python
async def _resolve_references(
    self,
    instruction: str,
    context: ConversationContext,
) -> str:
    """解析指代，將指代替換為實際值

    增強功能：
    1. 如果指令中沒有料號，但上下文中有，則自動添加料號
    2. 支持多種指代形式（「它」、「他」、「剛才查的那個料號」等）
    3. 智能判斷是否需要補充料號
    """

    resolved_instruction = instruction

    # 如果指令中沒有料號，但上下文中有，則添加料號
    if "last_part_number" in context.entities:
        part_number = context.entities["last_part_number"]

        # 檢查指令中是否已經包含料號
        if not re.search(r"[A-Z]{2,4}-\d{2,6}", instruction, re.IGNORECASE):
            # 解析「剛才查的那個料號」
            if "剛才" in instruction or "那個" in instruction or "這個" in instruction:
                # 替換「剛才查的那個料號」等模式
                resolved_instruction = re.sub(
                    r"(剛才|那個|這個).*料號",
                    f"料號 {part_number}",
                    resolved_instruction,
                )
            # 解析「它」、「他」
            elif "它" in instruction or "他" in instruction:
                # 在「它」或「他」後面添加料號
                resolved_instruction = re.sub(
                    r"([它他])",
                    f"{part_number}",
                    resolved_instruction,
                )
            # 如果指令中沒有明確的指代，但缺少料號，則在開頭添加
            elif not any(
                keyword in instruction
                for keyword in ["料號", "part", "ABC", "XYZ", "查詢", "query"]
            ):
                # 對於缺少料號的指令，在開頭添加料號
                resolved_instruction = f"料號 {part_number} {resolved_instruction}"

    return resolved_instruction
```

### 5.5 上下文在語義分析中的使用

```python
async def _analyze_semantics(
    self,
    instruction: str,
    session_id: Optional[str] = None,
    request: Optional[AgentServiceRequest] = None,
) -> SemanticAnalysisResult:
    """語義分析（帶上下文）"""

    # 獲取上下文
    context = None
    if session_id:
        context = await self._context_manager.get_context(session_id)

        # 解析指代
        instruction = await self._resolve_references(instruction, context)

    # 構建上下文信息（用於 LLM）
    context_info = None
    if context and context.last_result:
        context_info = {
            "last_query": context.current_query,
            "last_result": context.last_result,
            "entities": context.entities,
        }

    # 進行語義分析
    result = await self._analyze_semantics_with_llm(instruction, context_info)

    return result
```

### 5.6 上下文在執行流程中的使用

```python
async def execute(
    self,
    request: AgentServiceRequest
) -> AgentServiceResponse:
    """執行任務（帶上下文管理）"""

    # 1. 獲取會話 ID
    session_id = request.metadata.get("session_id") or request.task_id

    # 2. 獲取上下文
    context = await self._context_manager.get_context(session_id)

    # 3. 獲取用戶指令
    user_instruction = request.task_data.get("instruction", "")

    # 4. 語義分析（使用上下文）
    semantic_result = await self._analyze_semantics(
        user_instruction,
        session_id=session_id,
        request=request,
    )

    # 5. 職責理解
    responsibility = await self._understand_responsibility(semantic_result)

    # 6. 執行任務
    result = await self._execute_responsibility(responsibility, request)

    # 7. 更新上下文
    await self._context_manager.update_context(
        session_id=session_id,
        instruction=user_instruction,
        result=result,
    )

    return AgentServiceResponse(
        task_id=request.task_id,
        status="completed",
        result=result,
        metadata=request.metadata,
    )
```

---

## 6. 職責理解與任務分解

### 4.1 職責識別

根據語義分析結果，識別要履行的職責：

```python
async def _understand_responsibility(
    self,
    semantic_result: SemanticAnalysisResult
) -> Responsibility:
    """職責理解：根據語義分析結果識別職責"""

    intent = semantic_result.intent

    if intent == "query_part":
        return Responsibility(
            type="query_part",
            description="查詢物料基本信息",
            steps=[
                "調用 Data Agent 查詢物料數據",
                "格式化返回結果",
            ],
            required_data=["part_number"],
        )

    elif intent == "query_stock":
        return Responsibility(
            type="query_stock",
            description="查詢庫存信息",
            steps=[
                "調用 Data Agent 查詢庫存數據",
                "分析庫存狀態",
                "格式化返回結果",
            ],
            required_data=["part_number"],
        )

    elif intent == "analyze_shortage":
        return Responsibility(
            type="analyze_shortage",
            description="缺料分析",
            steps=[
                "調用 Data Agent 查詢當前庫存",
                "調用 Data Agent 查詢安全庫存",
                "計算缺料數量",
                "判斷缺料狀態",
                "生成分析報告",
            ],
            required_data=["part_number"],
        )

    elif intent == "generate_purchase_order":
        return Responsibility(
            type="generate_purchase_order",
            description="生成採購單",
            steps=[
                "驗證缺料狀態（可選）",
                "生成採購單記錄",
                "記錄採購單信息",
                "返回採購單結果",
            ],
            required_data=["part_number", "quantity"],
        )

    else:
        # 未識別意圖，需要澄清
        return Responsibility(
            type="clarification_needed",
            description="需要澄清用戶意圖",
            steps=["生成澄清問題"],
            clarification_questions=[
                "請明確您要執行哪個操作？",
                "1. 查詢料號信息",
                "2. 查詢庫存",
                "3. 缺料分析",
                "4. 生成採購單",
            ],
        )
```

### 4.2 職責模型

```python
class Responsibility(BaseModel):
    """職責定義"""

    type: str  # 職責類型
    description: str  # 職責描述
    steps: List[str]  # 執行步驟
    required_data: List[str]  # 必需的數據
    optional_data: List[str] = []  # 可選的數據
    clarification_questions: List[str] = []  # 澄清問題（如果需要）
```

### 4.3 任務分解示例

**示例 1：查詢庫存**

```
用戶指令：「查詢料號 ABC-123 的庫存」

語義分析：
- 意圖：query_stock
- 參數：part_number = "ABC-123"
- 置信度：0.9

職責理解：
- 職責類型：query_stock
- 執行步驟：
  1. 調用 Data Agent 查詢庫存數據（part_number: ABC-123）
  2. 分析庫存狀態（正常/待補貨/缺料）
  3. 格式化返回結果

任務分解：
- 任務1：查詢庫存數據
  - 調用 Data Agent: query_datalake
  - 參數：bucket="bucket-datalake-assets", key="stock/ABC-123.json"
- 任務2：分析庫存狀態
  - 比較 current_stock 與 safety_stock
  - 判斷狀態：normal/low/shortage
- 任務3：格式化結果
  - 構建響應數據結構
  - 返回給用戶
```

**示例 2：缺料分析**

```
用戶指令：「檢查料號 ABC-123 是否需要補貨」

語義分析：
- 意圖：analyze_shortage
- 參數：part_number = "ABC-123"
- 置信度：0.85

職責理解：
- 職責類型：analyze_shortage
- 執行步驟：
  1. 查詢當前庫存
  2. 查詢安全庫存（從物料信息中獲取）
  3. 計算缺料數量
  4. 判斷缺料狀態
  5. 生成分析報告

任務分解：
- 任務1：查詢庫存數據
  - 調用 Data Agent: query_datalake
  - 參數：bucket="bucket-datalake-assets", key="stock/ABC-123.json"
- 任務2：查詢物料信息（獲取安全庫存）
  - 調用 Data Agent: query_datalake
  - 參數：bucket="bucket-datalake-assets", key="parts/ABC-123.json"
- 任務3：缺料分析
  - 計算：shortage_quantity = safety_stock - current_stock
  - 判斷：is_shortage = current_stock < safety_stock
- 任務4：生成報告
  - 構建分析結果
  - 返回給用戶
```

---

## 7. Data Agent 調用

### 5.1 調用方式

庫管員 Agent 通過 AI-Box Orchestrator 調用 Data Agent：

```python
async def _call_data_agent(
    self,
    action: str,
    parameters: Dict[str, Any],
    request: AgentServiceRequest,
) -> Dict[str, Any]:
    """調用 Data Agent"""

    # 通過 AI-Box Orchestrator 調用 Data Agent
    # 注意：庫管員 Agent 需要能夠訪問 AI-Box 的 Orchestrator API

    import httpx

    AI_BOX_API_URL = os.getenv("AI_BOX_API_URL", "http://localhost:8000")
    API_KEY = os.getenv("AI_BOX_API_KEY", "your-api-key")

    # 構建 Data Agent 請求
    data_agent_request = {
        "action": action,
        **parameters,
        "user_id": request.metadata.get("user_id"),
        "tenant_id": request.metadata.get("tenant_id"),
    }

    # 通過 Orchestrator API 調用 Data Agent
    response = httpx.post(
        f"{AI_BOX_API_URL}/api/v1/agents/execute",
        json={
            "agent_id": "data-agent",  # 外部 Data Agent
            "task": {
                "task_id": f"{request.task_id}-data-query",
                "task_data": data_agent_request,
                "metadata": request.metadata,
            },
        },
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30.0,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Data Agent call failed: {response.text}")

    result = response.json()

    if not result.get("result", {}).get("success"):
        raise RuntimeError(
            f"Data Agent query failed: {result.get('result', {}).get('error')}"
        )

    return result.get("result", {})
```

### 5.2 查詢物料信息

```python
async def _query_part_info(
    self,
    part_number: str,
    request: AgentServiceRequest,
) -> Dict[str, Any]:
    """查詢物料信息"""

    result = await self._call_data_agent(
        action="query_datalake",
        parameters={
            "bucket": "bucket-datalake-assets",
            "key": f"parts/{part_number}.json",
            "query_type": "exact",
        },
        request=request,
    )

    if not result.get("success"):
        raise ValueError(f"Failed to query part info: {result.get('error')}")

    rows = result.get("rows", [])
    if not rows:
        raise ValueError(f"Part not found: {part_number}")

    return rows[0]  # 返回第一個結果
```

### 5.3 查詢庫存信息

```python
async def _query_stock_info(
    self,
    part_number: str,
    request: AgentServiceRequest,
) -> Dict[str, Any]:
    """查詢庫存信息"""

    result = await self._call_data_agent(
        action="query_datalake",
        parameters={
            "bucket": "bucket-datalake-assets",
            "key": f"stock/{part_number}.json",
            "query_type": "exact",
        },
        request=request,
    )

    if not result.get("success"):
        raise ValueError(f"Failed to query stock info: {result.get('error')}")

    rows = result.get("rows", [])
    if not rows:
        raise ValueError(f"Stock not found: {part_number}")

    return rows[0]  # 返回第一個結果
```

### 5.4 錯誤處理

```python
async def _call_data_agent_with_retry(
    self,
    action: str,
    parameters: Dict[str, Any],
    request: AgentServiceRequest,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """調用 Data Agent（帶重試機制）"""

    last_error = None

    for attempt in range(max_retries):
        try:
            return await self._call_data_agent(action, parameters, request)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # 指數退避
                continue
            else:
                raise

    raise last_error
```

---

## 8. 數據結果判斷與處理

### 6.1 結果完整性檢查

```python
def _check_result_completeness(
    self,
    result: Dict[str, Any],
    required_fields: List[str],
) -> ValidationResult:
    """檢查結果完整性"""

    issues = []
    warnings = []

    # 檢查必需字段
    for field in required_fields:
        if field not in result:
            issues.append(f"Missing required field: {field}")
        elif result[field] is None:
            warnings.append(f"Field {field} is None")

    # 檢查數據類型
    if "current_stock" in result:
        if not isinstance(result["current_stock"], int):
            issues.append("current_stock must be an integer")
        elif result["current_stock"] < 0:
            issues.append("current_stock cannot be negative")

    return ValidationResult(
        valid=len(issues) == 0,
        issues=issues,
        warnings=warnings,
    )
```

### 6.2 庫存狀態判斷

```python
def _analyze_stock_status(
    self,
    current_stock: int,
    safety_stock: int,
) -> StockStatus:
    """分析庫存狀態"""

    if current_stock >= safety_stock:
        status = "normal"
        shortage_quantity = 0
    elif current_stock >= safety_stock * 0.5:
        status = "low"
        shortage_quantity = safety_stock - current_stock
    else:
        status = "shortage"
        shortage_quantity = safety_stock - current_stock

    return StockStatus(
        status=status,
        current_stock=current_stock,
        safety_stock=safety_stock,
        shortage_quantity=shortage_quantity,
        is_shortage=(status == "shortage"),
    )
```

### 6.3 數據有效性驗證

```python
def _validate_data(
    self,
    part_info: Dict[str, Any],
    stock_info: Dict[str, Any],
) -> ValidationResult:
    """驗證數據有效性"""

    issues = []
    warnings = []

    # 檢查料號一致性
    if part_info.get("part_number") != stock_info.get("part_number"):
        issues.append(
            f"Part number mismatch: {part_info.get('part_number')} vs {stock_info.get('part_number')}"
        )

    # 檢查安全庫存
    safety_stock = part_info.get("safety_stock")
    if safety_stock is None:
        warnings.append("safety_stock is not defined in part info")
    elif safety_stock <= 0:
        issues.append("safety_stock must be greater than 0")

    # 檢查當前庫存
    current_stock = stock_info.get("current_stock")
    if current_stock is None:
        issues.append("current_stock is missing in stock info")
    elif current_stock < 0:
        issues.append("current_stock cannot be negative")

    return ValidationResult(
        valid=len(issues) == 0,
        issues=issues,
        warnings=warnings,
    )
```

### 6.4 異常情況處理

```python
def _handle_data_anomalies(
    self,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """處理數據異常情況"""

    anomalies = []

    # 檢查異常值
    if "current_stock" in result:
        current_stock = result["current_stock"]
        if current_stock == 0:
            anomalies.append("庫存為零，需要立即補貨")
        elif current_stock < 0:
            anomalies.append("庫存為負數，數據異常")

    # 檢查時間戳
    if "last_updated" in result:
        last_updated = datetime.fromisoformat(result["last_updated"])
        days_since_update = (datetime.now() - last_updated).days
        if days_since_update > 30:
            anomalies.append(f"庫存數據已 {days_since_update} 天未更新")

    result["anomalies"] = anomalies
    result["has_anomalies"] = len(anomalies) > 0

    return result
```

---

## 9. 業務邏輯處理

### 7.1 缺料分析邏輯

```python
async def _analyze_shortage(
    self,
    part_number: str,
    request: AgentServiceRequest,
) -> Dict[str, Any]:
    """缺料分析"""

    # 1. 查詢庫存信息
    stock_info = await self._query_stock_info(part_number, request)

    # 2. 查詢物料信息（獲取安全庫存）
    part_info = await self._query_part_info(part_number, request)

    # 3. 驗證數據
    validation = self._validate_data(part_info, stock_info)
    if not validation.valid:
        raise ValueError(f"Data validation failed: {validation.issues}")

    # 4. 分析庫存狀態
    current_stock = stock_info.get("current_stock", 0)
    safety_stock = part_info.get("safety_stock", 0)

    stock_status = self._analyze_stock_status(current_stock, safety_stock)

    # 5. 生成分析報告
    analysis_result = {
        "part_number": part_number,
        "part_name": part_info.get("name"),
        "current_stock": current_stock,
        "safety_stock": safety_stock,
        "status": stock_status.status,
        "is_shortage": stock_status.is_shortage,
        "shortage_quantity": stock_status.shortage_quantity,
        "location": stock_info.get("location"),
        "recommendation": self._generate_recommendation(stock_status),
        "anomalies": self._handle_data_anomalies(stock_info).get("anomalies", []),
    }

    return analysis_result

def _generate_recommendation(self, stock_status: StockStatus) -> str:
    """生成建議"""

    if stock_status.status == "normal":
        return "庫存充足，無需補貨"
    elif stock_status.status == "low":
        return f"庫存偏低，建議補貨 {stock_status.shortage_quantity} 件"
    else:
        return f"庫存缺料，建議立即補貨 {stock_status.shortage_quantity} 件"
```

### 7.2 採購單生成邏輯

```python
async def _generate_purchase_order(
    self,
    part_number: str,
    quantity: int,
    request: AgentServiceRequest,
) -> Dict[str, Any]:
    """生成採購單（虛擬）"""

    # 1. 驗證參數
    if quantity <= 0:
        raise ValueError("Purchase quantity must be greater than 0")

    # 2. 查詢物料信息（獲取供應商信息）
    part_info = await self._query_part_info(part_number, request)

    # 3. 可選：檢查缺料狀態
    shortage_analysis = await self._analyze_shortage(part_number, request)
    if not shortage_analysis.get("is_shortage"):
        # 雖然不缺料，但用戶明確要求生成採購單，仍然生成
        pass

    # 4. 生成採購單記錄
    purchase_order_id = f"PO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    purchase_order = {
        "purchase_order_id": purchase_order_id,
        "part_number": part_number,
        "part_name": part_info.get("name"),
        "quantity": quantity,
        "supplier": part_info.get("supplier"),
        "unit_price": part_info.get("unit_price"),
        "total_amount": quantity * (part_info.get("unit_price", 0)),
        "status": "虛擬生成",
        "created_at": datetime.now().isoformat(),
        "created_by": "warehouse_manager_agent",
        "note": "此為虛擬採購單，僅用於測試",
    }

    # 5. 記錄採購單（可選：存儲到數據庫或日誌）
    self._logger.info(
        "purchase_order_generated",
        purchase_order_id=purchase_order_id,
        part_number=part_number,
        quantity=quantity,
    )

    return purchase_order
```

---

## 10. 交付標準

### 8.1 響應格式標準

庫管員 Agent 的響應必須遵循統一的格式標準：

```python
class WarehouseAgentResponse(BaseModel):
    """庫管員 Agent 響應模型"""

    success: bool  # 是否成功
    task_type: str  # 任務類型
    result: Optional[Dict[str, Any]] = None  # 執行結果
    error: Optional[str] = None  # 錯誤信息
    metadata: Optional[Dict[str, Any]] = None  # 元數據

    # 語義分析信息
    semantic_analysis: Optional[Dict[str, Any]] = None  # 語義分析結果
    responsibility: Optional[str] = None  # 履行的職責

    # 數據查詢信息
    data_queries: Optional[List[Dict[str, Any]]] = []  # 數據查詢記錄

    # 結果判斷信息
    validation: Optional[Dict[str, Any]] = None  # 數據驗證結果
    anomalies: Optional[List[str]] = []  # 異常情況列表
```

### 8.2 成功響應示例

#### 8.2.1 查詢庫存響應

```json
{
  "success": true,
  "task_type": "query_stock",
  "result": {
    "part_number": "ABC-123",
    "part_name": "電子元件 A",
    "current_stock": 50,
    "safety_stock": 100,
    "location": "倉庫 A-01",
    "status": "shortage",
    "shortage_quantity": 50,
    "last_updated": "2026-01-13T10:00:00Z"
  },
  "semantic_analysis": {
    "intent": "query_stock",
    "confidence": 0.9,
    "parameters": {
      "part_number": "ABC-123"
    }
  },
  "responsibility": "查詢庫存信息",
  "data_queries": [
    {
      "action": "query_datalake",
      "bucket": "bucket-datalake-assets",
      "key": "stock/ABC-123.json",
      "success": true
    }
  ],
  "validation": {
    "valid": true,
    "issues": [],
    "warnings": []
  },
  "anomalies": ["庫存為零，需要立即補貨"]
}
```

#### 8.2.2 缺料分析響應

```json
{
  "success": true,
  "task_type": "analyze_shortage",
  "result": {
    "part_number": "ABC-123",
    "part_name": "電子元件 A",
    "current_stock": 50,
    "safety_stock": 100,
    "status": "shortage",
    "is_shortage": true,
    "shortage_quantity": 50,
    "location": "倉庫 A-01",
    "recommendation": "庫存缺料，建議立即補貨 50 件"
  },
  "semantic_analysis": {
    "intent": "analyze_shortage",
    "confidence": 0.85,
    "parameters": {
      "part_number": "ABC-123"
    }
  },
  "responsibility": "缺料分析",
  "data_queries": [
    {
      "action": "query_datalake",
      "bucket": "bucket-datalake-assets",
      "key": "stock/ABC-123.json",
      "success": true
    },
    {
      "action": "query_datalake",
      "bucket": "bucket-datalake-assets",
      "key": "parts/ABC-123.json",
      "success": true
    }
  ],
  "validation": {
    "valid": true,
    "issues": [],
    "warnings": []
  }
}
```

### 8.3 錯誤響應標準

```json
{
  "success": false,
  "task_type": "query_stock",
  "error": "Part not found: ABC-999",
  "semantic_analysis": {
    "intent": "query_stock",
    "confidence": 0.9,
    "parameters": {
      "part_number": "ABC-999"
    }
  },
  "data_queries": [
    {
      "action": "query_datalake",
      "bucket": "bucket-datalake-assets",
      "key": "stock/ABC-999.json",
      "success": false,
      "error": "File not found: bucket-datalake-assets/stock/ABC-999.json"
    }
  ]
}
```

---

## 11. 代碼實現規格

### 9.1 類結構

```python
class WarehouseManagerAgent(AgentServiceProtocol):
    """庫管員 Agent - 庫存管理業務 Agent"""

    def __init__(self):
        self.agent_id = "warehouse-manager-agent"
        self._logger = logging.getLogger(__name__)
        self._ai_box_api_url = os.getenv("AI_BOX_API_URL", "http://localhost:8000")
        self._api_key = os.getenv("AI_BOX_API_KEY", "your-api-key")

    async def execute(
        self,
        request: AgentServiceRequest
    ) -> AgentServiceResponse:
        """執行任務"""
        # 實現邏輯
        pass

    async def health_check(self) -> AgentServiceStatus:
        """健康檢查"""
        return AgentServiceStatus.AVAILABLE

    async def get_capabilities(self) -> dict:
        """獲取服務能力"""
        return {
            "capabilities": [
                "query_part",
                "query_stock",
                "analyze_shortage",
                "generate_purchase_order",
            ],
            "description": "庫存管理業務 Agent",
        }

    # 語義分析方法
    async def _analyze_semantics(self, instruction: str) -> SemanticAnalysisResult:
        """語義分析"""
        pass

    async def _understand_responsibility(
        self,
        semantic_result: SemanticAnalysisResult
    ) -> Responsibility:
        """職責理解"""
        pass

    # Data Agent 調用方法
    async def _call_data_agent(
        self,
        action: str,
        parameters: Dict[str, Any],
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """調用 Data Agent"""
        pass

    # 業務邏輯方法
    async def _query_part_info(
        self,
        part_number: str,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """查詢物料信息"""
        pass

    async def _analyze_shortage(
        self,
        part_number: str,
        request: AgentServiceRequest,
    ) -> Dict[str, Any]:
        """缺料分析"""
        pass
```

### 9.2 MCP Server 實現

```python
from mcp.server.server import MCPServer
from agents.external.warehouse_manager.agent import WarehouseManagerAgent

# 初始化 Agent
warehouse_agent = WarehouseManagerAgent()

# 創建 MCP Server
mcp_server = MCPServer(
    name="warehouse-manager-agent",
    version="2.0.0",
)

# 註冊工具
@mcp_server.tool()
async def query_part(arguments: dict) -> dict:
    """查詢料號信息"""
    part_number = arguments.get("part_number")
    # 實現邏輯
    pass

@mcp_server.tool()
async def query_stock(arguments: dict) -> dict:
    """查詢庫存"""
    part_number = arguments.get("part_number")
    # 實現邏輯
    pass

@mcp_server.tool()
async def analyze_shortage(arguments: dict) -> dict:
    """缺料分析"""
    part_number = arguments.get("part_number")
    # 實現邏輯
    pass
```

---

## 12. 與其他組件的協作

### 10.1 與 AI-Box Orchestrator 的協作

庫管員 Agent 通過 MCP Protocol 接收來自 AI-Box Orchestrator 的調用：

```python
# AI-Box Orchestrator 通過 MCP Client 調用庫管員 Agent
from agents.services.protocol.mcp_client import MCPAgentServiceClient

mcp_client = MCPAgentServiceClient(
    server_url="http://localhost:8003/mcp",
    server_name="warehouse-manager-agent",
    api_key="your-api-key",
)

response = await mcp_client.execute(
    request=AgentServiceRequest(
        task_id=task_id,
        task_data={
            "instruction": "查詢料號 ABC-123 的庫存",
        },
        metadata={"user_id": user_id, "tenant_id": tenant_id},
    ),
)
```

### 10.2 與 Data Agent 的協作

庫管員 Agent 通過 AI-Box Orchestrator 調用 Data Agent：

```python
# 在庫管員 Agent 中
response = await self._call_data_agent(
    action="query_datalake",
    parameters={
        "bucket": "bucket-datalake-assets",
        "key": "stock/ABC-123.json",
        "query_type": "exact",
    },
    request=request,
)
```

---

## 13. 實現計劃

### 11.1 開發階段

#### 階段一：基礎框架搭建（2-3 天）

**任務**：

1. 創建 Agent 項目結構
2. 實現 MCP Server
3. 實現 AgentServiceProtocol 接口
4. 實現基本的 HTTP API 端點
5. 實現健康檢查和服務能力查詢

**交付物**：

- Agent 基礎框架
- MCP Server 實現
- HTTP API 端點
- 基本測試用例

#### 階段二：語義分析與職責理解（3-4 天）

**任務**：

1. 實現語義分析功能（正則表達式版本）
2. 實現 LLM 語義分析功能
3. 實現提示詞管理
4. 實現職責識別功能
5. 實現參數提取功能
6. 實現任務分解功能

**交付物**：

- 語義分析模塊（正則 + LLM）
- 提示詞管理模塊
- 職責理解模塊
- 單元測試

#### 階段二點五：上下文管理（2-3 天）

**任務**：

1. 實現上下文數據模型
2. 實現上下文管理器
3. 實現指代解析功能
4. 實現上下文在語義分析中的使用
5. 實現上下文在執行流程中的使用

**交付物**：

- 上下文管理模塊
- 指代解析模塊
- 單元測試

#### 階段三：Data Agent 調用（1-2 天）

**任務**：

1. 實現 Data Agent 調用邏輯
2. 實現錯誤處理和重試機制
3. 實現查詢結果緩存（可選）

**交付物**：

- Data Agent 調用模塊
- 錯誤處理模塊
- 集成測試

#### 階段四：業務邏輯實現（2-3 天）

**任務**：

1. 實現料號查詢功能
2. 實現庫存查詢功能
3. 實現缺料分析功能
4. 實現採購單生成功能（虛擬）

**交付物**：

- 業務邏輯模塊
- 單元測試

#### 階段五：結果判斷與處理（1-2 天）

**任務**：

1. 實現結果完整性檢查
2. 實現庫存狀態判斷
3. 實現數據有效性驗證
4. 實現異常情況處理

**交付物**：

- 結果判斷模塊
- 驗證模塊
- 單元測試

#### 階段六：Agent 註冊與測試（1-2 天）

**任務**：

1. 註冊 Agent 到 AI-Box Platform
2. 端到端測試
3. 性能測試

**交付物**：

- 註冊配置
- 測試報告

### 11.2 技術棧

**開發語言**：Python 3.11+

**框架**：

- FastAPI：HTTP API 框架
- MCP Server：MCP Protocol 服務器
- Pydantic：數據驗證
- httpx：HTTP 客戶端（調用 AI-Box API）

**依賴**：

```python
fastapi>=0.104.0
mcp>=0.1.0
pydantic>=2.0.0
httpx>=0.25.0
python-dotenv>=1.0.0
```

### 11.3 項目結構

```
warehouse-manager-agent/
├── main.py                      # FastAPI 入口
├── agent.py                     # Agent 實現
├── mcp_server.py                # MCP Server 實現
├── models.py                    # 數據模型
├── services/                    # 業務邏輯服務
│   ├── semantic_analyzer.py     # 語義分析服務（正則 + LLM）
│   ├── prompt_manager.py        # 提示詞管理服務
│   ├── context_manager.py       # 上下文管理服務
│   ├── responsibility_analyzer.py # 職責理解服務
│   ├── part_service.py         # 料號服務
│   ├── stock_service.py        # 庫存服務
│   └── purchase_service.py     # 採購服務
├── handlers/                    # API 處理器
│   ├── query_handler.py        # 查詢處理器
│   └── purchase_handler.py     # 採購處理器
├── validators/                  # 驗證器
│   ├── result_validator.py     # 結果驗證器
│   └── data_validator.py       # 數據驗證器
├── config.py                    # 配置管理
├── requirements.txt             # 依賴
├── Dockerfile                   # Docker 配置
└── README.md                    # 文檔
```

---

---

## 14. 測試結果與驗證

### 14.1 獨立測試結果

**測試日期**：2026-01-13
**測試版本**：1.0.0
**測試模式**：獨立測試（直接調用Data-Agent，不通過AI-Box Orchestrator）

#### 14.1.1 測試統計

- **總測試數**：29
- **通過數**：29 ✅
- **失敗數**：0 ❌
- **通過率**：**100.0%** 🎉

#### 14.1.2 測試改進歷程

| 階段 | 通過率 | 通過數 | 主要改進 |
|------|--------|--------|----------|
| 初始測試（無測試數據） | 6.9% | 2/29 | - |
| 準備測試數據 | 72.4% | 21/29 | ✅ +65.5% |
| 修復數據格式解析 | 89.7% | 26/29 | ✅ +17.3% |
| 改進語義分析和上下文管理 | 96.6% | 28/29 | ✅ +6.9% |
| **最終版本** | **100.0%** | **29/29** | ✅ **+3.4%** |

**總提升**：**+93.1%** ⬆️

#### 14.1.3 測試場景覆蓋

**基礎查詢場景（場景1-6）** ✅ 全部通過

- 查詢料號信息
- 查詢庫存
- 查詢庫存數量（「還有多少庫存」）
- 查詢庫存位置（「存放在哪裡」）
- 查詢物料規格
- 查詢物料供應商

**缺料分析場景（場景7-9）** ✅ 全部通過

- 缺料檢查
- 缺料分析
- 缺料建議生成

**採購單生成場景（場景10-11）** ✅ 全部通過

- 基本採購單生成
- 條件式採購單生成

**上下文和多輪對話場景（場景12-14）** ✅ 全部通過

- 指代解析（「剛才查的那個料號」）
- 多輪對話（「它缺料嗎？」→「生成採購單」）
- 連續查詢不同料號

**複雜場景（場景15-17）** ✅ 全部通過

- 複雜指令理解
- 錯誤處理（料號不存在）
- 參數驗證（缺少數量參數）

**邊界情況（場景18-19）** ✅ 全部通過

- 不同格式的指令解析
- 英文指令支持

**完整工作流程（場景20）** ✅ 全部通過

- 多步驟完整流程

#### 14.1.4 已驗證的功能

1. **獨立測試模式**：
   - ✅ 直接客戶端切換正常
   - ✅ HTTP API調用正常
   - ✅ 數據格式解析正確

2. **語義分析**：
   - ✅ 正則表達式模式匹配正確
   - ✅ 料號和數量提取準確
   - ✅ 上下文補充功能正常
   - ✅ 避免從料號中提取數量

3. **上下文管理**：
   - ✅ 實體提取功能正常（支持多種結果格式）
   - ✅ 指代解析功能正常
   - ✅ 多輪對話支持完整

4. **業務邏輯**：
   - ✅ 料號查詢正常
   - ✅ 庫存查詢正常
   - ✅ 缺料分析正常
   - ✅ 採購單生成正常

#### 14.1.5 測試文件

- **test_integration_scenarios.py** (506行) - 29個工作應用場景
- **prepare_test_data.py** (204行) - 測試數據準備腳本
- **generate_test_report.py** (78行) - 測試報告生成工具

詳細測試報告請參閱：

- `datalake-system/tests/warehouse_manager_agent/INTEGRATION_TEST_REPORT.md`
- `datalake-system/tests/warehouse_manager_agent/TEST_FINAL_REPORT.md`

### 14.2 代碼改進總結

#### 14.2.1 語義分析改進

**改進內容**：

1. 增強正則表達式模式，支持更多指令格式：
   - `query_stock`: 添加"還有.*庫存"、"存放在.*哪裡"等模式
   - `query_part`: 添加"料號.*規格"、"供應商.*誰"等模式
2. 改進數量提取邏輯，避免從料號中提取數量（如ABC-123中的123）
3. 支持上下文補充：如果指令中沒有料號，但上下文中有，則自動使用上下文的料號

**代碼位置**：

- `warehouse_manager_agent/services/semantic_analyzer.py`

#### 14.2.2 上下文管理改進

**改進內容**：

1. 增強實體提取，支持多種結果格式：
   - 直接字段（`part_number`）
   - 嵌套字段（`part_info.part_number`、`stock_info.part_number`）
   - 雙層嵌套（`result.part_info.part_number`）
2. 改進指代解析邏輯：
   - 支持「它」、「他」、「剛才查的那個料號」等多種指代形式
   - 自動從上下文補充料號到缺少料號的指令中
   - 智能判斷是否需要補充料號

**代碼位置**：

- `warehouse_manager_agent/services/context_manager.py`

#### 14.2.3 數據格式解析改進

**改進內容**：

1. 修復直接客戶端返回的數據格式與服務類期望的格式不匹配問題
2. 正確提取嵌套的 `result` 字段
3. 處理 DataAgentResponse 的雙層結構

**代碼位置**：

- `warehouse_manager_agent/data_agent_direct_client.py`

### 14.3 下一步計劃

#### 階段1：獨立測試 ✅ 完成

- [x] 創建直接客戶端
- [x] 修改服務類支持直接客戶端
- [x] 更新測試腳本
- [x] 執行測試並驗證功能
- [x] 修復發現的問題
- [x] **通過率達到100%**

#### 階段2：註冊到AI-Box（待執行）

獨立測試通過後：

- [ ] 註冊庫管員Agent到AI-Box Orchestrator
- [ ] 配置Agent Registry
- [ ] 驗證註冊成功

#### 階段3：E2E測試（待執行）

註冊完成後：

- [ ] 切換到E2E測試模式
- [ ] 執行完整E2E測試
- [ ] 驗證AI-Box → 庫管員Agent → Data Agent → Datalake完整流程

---

**版本**: 2.2
**最後更新日期**: 2026-01-13
**維護人**: Daniel Chung
**主要變更**:

- v2.0: 從規劃書升級為規格書，新增語義分析、職責理解、Data Agent 調用、結果判斷等詳細規格
- v2.1: 新增提示詞管理和上下文管理章節，支持 LLM 語義分析和多輪對話
- v2.2: 更新語義分析和上下文管理的實際實現細節，新增測試結果章節，記錄100%通過率的獨立測試結果
