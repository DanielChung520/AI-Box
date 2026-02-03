# 代碼功能說明: MM-Agent 對話鏈 - LangChain 編排 + 多輪對話
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31

"""MM-Agent 對話鏈 - 意圖語義分析 + 多輪對話支持"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel

from mm_agent.translator import Translator, TranslationResult
from mm_agent.negative_list import NegativeListChecker
from mm_agent.coreference_resolver import CoreferenceResolver
from mm_agent.chain.context_manager import ContextManager, get_context_manager


class MMChainInput(BaseModel):
    """對話鏈輸入"""

    instruction: str
    session_id: Optional[str] = None  # 對話會話 ID
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class MMChainOutput(BaseModel):
    """對話鏈輸出"""

    success: bool
    response: str
    translation: Optional[TranslationResult] = None
    needs_clarification: bool = False
    clarification_message: Optional[str] = None
    session_id: Optional[str] = None  # 返回會話 ID
    resolved_query: Optional[str] = None  # 指代消解後的查詢
    debug_info: Optional[Dict[str, Any]] = None


class MMAgentChain:
    """MM-Agent 對話鏈 - 意圖語義分析 + 多輪對話支持"""

    SYSTEM_PROMPT = """你是一個專業的物料管理助手（MM-Agent）。

你的職責是：
1. 理解用戶關於庫存、採購、銷售的查詢
2. 將自然語言轉換為專業術語
3. 維護多輪對話上下文，理解指代和省略
4. 提供準確、專業的回覆

工作流程：
1. 嘗試指代消解（從上下文提取省略信息）
2. 負面表列檢查（權限控制）
3. 進行語義分析，提取意圖和參數
4. 專業轉譯（tlf19 碼、時間表達式）
5. 保存對話歷史和提取的實體
6. 生成自然語言回復

多輪對話示例：
用戶：RM05-008 上月買進多少
助手：RM05-008 上月採購進貨共 5,000 KG
用戶：這個料號庫存還有多少（"這個料號"指代 RM05-008）
助手：RM05-008 當前庫存 3,200 KG

回覆要求：
- 使用繁體中文
- 專業但易於理解的語言
- 包含關鍵數據和專業術語說明
- 多輪對話時保持上下文一致

當無法理解查詢時，請求用戶澄清。"""

    def __init__(self, storage_backend: str = "memory"):
        self._translator = Translator()
        self._negative_list = NegativeListChecker()
        self._context_manager = get_context_manager(storage_backend)
        self._coreference_resolver = CoreferenceResolver(model="qwen3:32b")

    def _check_negative_list(self, instruction: str) -> tuple[bool, str]:
        """L4: 負面表列檢查（權限控制）"""
        return self._negative_list.is_denied(instruction)

    def _translate(self, instruction: str) -> TranslationResult:
        """L2: 專業轉譯"""
        return self._translator.translate(instruction)

    def _analyze_intent(self, instruction: str, translation: TranslationResult) -> str:
        """L1: 意圖分析"""
        if translation.tlf19:
            if translation.tlf19 in ["101", "102"]:
                return "purchase"
            elif translation.tlf19 in ["201"]:
                return "material_issue"
            elif translation.tlf19 in ["202"]:
                return "sales"
            elif translation.tlf19 in ["301"]:
                return "scrapping"
        elif "庫存" in instruction:
            return "inventory"
        return "unknown"

    def _resolve_references(
        self,
        instruction: str,
        session_id: str,
    ) -> tuple[str, Dict[str, Any]]:
        """指代消解（使用 CoreferenceResolver）

        Args:
            instruction: 當前查詢
            session_id: 會話 ID

        Returns:
            (消解後的查詢, 使用的實體)
        """
        # 獲取上下文
        context = self._context_manager.get_context(session_id)
        if not context:
            return instruction, {}

        # 獲取對話歷史
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in self._context_manager.get_recent_messages(session_id, limit=3)
        ]

        # 使用 CoreferenceResolver 進行消解
        result = self._coreference_resolver.resolve(
            current_query=instruction,
            context_entities=context.extracted_entities,
            conversation_history=conversation_history,
        )

        return result.resolved_query, result.entities

    def _enrich_with_context(
        self,
        translation: TranslationResult,
        context_entities: Dict[str, Any],
    ) -> TranslationResult:
        """使用上下文實體豐富轉譯結果"""
        # 如果當前沒有提取到料號，但上下文有，則使用上下文的
        if not translation.part_number and context_entities.get("part_number"):
            translation.part_number = context_entities["part_number"]

        # 類似處理其他實體
        if not translation.tlf19 and context_entities.get("tlf19"):
            translation.tlf19 = context_entities["tlf19"]

        if not translation.table_name and context_entities.get("table_name"):
            translation.table_name = context_entities["table_name"]

        return translation

    def run(self, input_data: MMChainInput) -> MMChainOutput:
        """執行對話鏈（同步版本 - 支持多輪對話）"""
        instruction = input_data.instruction
        user_id = input_data.user_id
        session_id = input_data.session_id

        # 如果沒有提供 session_id，創建新會話
        if not session_id:
            session_id = self._context_manager.create_session(user_id=user_id)

        # 確保會話存在
        context = self._context_manager.get_context(session_id)
        if not context:
            session_id = self._context_manager.create_session(
                user_id=user_id, session_id=session_id
            )

        # Step 1: 嘗試指代消解
        resolved_query, context_entities = self._resolve_references(instruction, session_id)

        # 使用消解後的查詢進行後續處理
        working_query = resolved_query if resolved_query != instruction else instruction

        # Step 2: 負面表列檢查（權限控制）
        is_denied, denied_msg = self._check_negative_list(working_query)
        if is_denied:
            self._context_manager.add_message(session_id, "user", instruction)

            return MMChainOutput(
                success=False,
                response="",
                needs_clarification=False,
                clarification_message=None,
                session_id=session_id,
                resolved_query=resolved_query if resolved_query != instruction else None,
                debug_info={
                    "step": "negative_list_check",
                    "denied": True,
                    "denied_message": denied_msg,
                },
            )

        # Step 3: 專業轉譯
        translation = self._translate(working_query)

        # Step 4: 使用上下文豐富轉譯結果（對於省略的實體）
        translation = self._enrich_with_context(translation, context_entities)

        # Step 5: 意圖分析
        intent = self._analyze_intent(working_query, translation)

        # Step 6: 保存對話歷史和實體
        metadata = {
            "part_number": translation.part_number,
            "tlf19": translation.tlf19,
            "intent": intent,
            "table_name": translation.table_name,
        }

        # 保存用戶消息
        self._context_manager.add_message(session_id, "user", instruction, metadata)

        # 生成回復
        response = f"已收到指令：{instruction}"
        if resolved_query != instruction:
            response += f"\n（指代消解：{resolved_query}）"

        # 保存助手回覆
        self._context_manager.add_message(session_id, "assistant", response)

        return MMChainOutput(
            success=True,
            response=response,
            translation=translation,
            session_id=session_id,
            resolved_query=resolved_query if resolved_query != instruction else None,
            debug_info={
                "step": "analyzed",
                "intent": intent,
                "has_context_entities": len(context_entities) > 0,
                "context_entities": context_entities,
                "translation": translation.model_dump(),
            },
        )


if __name__ == "__main__":
    import asyncio

    chain = MMAgentChain()

    print("=" * 70)
    print("MM-Agent 多輪對話測試")
    print("=" * 70)

    # 模擬多輪對話
    conversation = [
        ("RM05-008 上月買進多少", "第一輪：初始查詢"),
        ("這個料號庫存還有多少", "第二輪：指代消解測試"),
        ("上月賣出多少", "第三輪：進一步省略"),
        ("今天天氣如何", "第四輪：無關查詢"),
    ]

    session_id = None

    for instruction, desc in conversation:
        print(f"\n{'=' * 70}")
        print(f"{desc}")
        print(f"用戶: {instruction}")

        result = chain.run(MMChainInput(instruction=instruction, session_id=session_id))

        # 保存 session_id 用於下一輪
        session_id = result.session_id

        if result.needs_clarification:
            print(f"助手: ❌ 需要澄清")
            print(f"訊息: {result.clarification_message[:60]}...")
        else:
            trans = result.translation
            print(f"助手: ✅ 理解成功")

            if result.resolved_query:
                print(f"   指代消解: {result.resolved_query}")

            print(f"   - 料號: {trans.part_number}")
            print(f"   - tlf19: {trans.tlf19}")
            print(f"   - 意圖: {result.debug_info.get('intent')}")

            # 顯示是否使用了上下文
            if result.debug_info.get("has_context_entities"):
                print(f"   - 使用了上下文實體: {result.debug_info.get('context_entities')}")

    # 顯示完整對話歷史
    print(f"\n{'=' * 70}")
    print("完整對話歷史:")
    print(f"{'=' * 70}")
    context = chain._context_manager.get_context(session_id)
    if context:
        for i, msg in enumerate(context.messages, 1):
            role = "用戶" if msg.role == "user" else "助手"
            print(f"{i}. [{role}] {msg.content}")

    print(f"\n{'=' * 70}")
    print("測試完成")
