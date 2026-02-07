# 代碼功能說明: MM-Agent 對話鏈 - LangChain 編排 + 多輪對話
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-03

"""MM-Agent 對話鏈 - 意圖語義分析 + 多輪對話支持"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

from mm_agent.translator import Translator, TranslationResult
from mm_agent.negative_list import NegativeListChecker
from mm_agent.coreference_resolver import CoreferenceResolver
from mm_agent.chain.context_manager import get_context_manager
from mm_agent.semantic_translator import SemanticTranslatorAgent
from mm_agent.translation_models import SemanticTranslationResult
from mm_agent.services.schema_registry import get_schema_registry

logger = logging.getLogger(__name__)


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
3. 檢查是否需要查詢知識庫（職責、技能、流程等）
4. 進行語義分析，提取意圖和參數
5. 專業轉譯（tlf19 碼、時間表達式）
6. 保存對話歷史和提取的實體
7. 生成自然語言回復

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
- 優先使用知識庫信息回答職責、技能、流程類問題

當無法理解查詢時，請求用戶澄清。"""

    def __init__(self, storage_backend: str = "memory", use_semantic_translator: bool = False):
        """初始化對話鏈

        Args:
            storage_backend: 存儲後端（memory/redis）
            use_semantic_translator: 是否使用語義轉譯 Agent（LLM）
        """
        self._translator = Translator(use_semantic_translator=use_semantic_translator)
        self._negative_list = NegativeListChecker()
        self._context_manager = get_context_manager(storage_backend)
        self._coreference_resolver = CoreferenceResolver(model="qwen3:32b")
        self._ka_client = None  # KA-Agent 客戶端
        self._use_semantic_translator = use_semantic_translator

        # 初始化 LLM client（用於複雜 SQL 生成）
        try:
            from llm.clients.factory import LLMClientFactory
            from services.api.models.llm_model import LLMProvider

            self._llm_client = LLMClientFactory.create_client(
                provider=LLMProvider.OLLAMA, use_cache=True
            )
            logger.info("MM-Agent: LLM client 已初始化")
        except Exception as e:
            logger.warning(f"MM-Agent: 無法初始化 LLM client: {e}")
            self._llm_client = None

        # 初始化 Schema Registry（用於 SQL 生成）
        self._schema_registry = get_schema_registry()

        # 初始化語義轉譯器（當使用新架構時）
        self._semantic_translator = None
        if use_semantic_translator:
            try:
                self._semantic_translator = SemanticTranslatorAgent(use_rules_engine=True)
                logger.info("MM-Agent: 語義轉譯器已初始化")
            except Exception as e:
                logger.warning(f"MM-Agent: 無法初始化語義轉譯器: {e}")

    def _build_clarification_message(self, intent: str, validation, constraints) -> str:
        """構建澄清消息"""
        messages = ["為了更準確地回答您的問題，請提供以下信息："]

        for field in validation.missing_fields:
            prompt = validation.notes or f"請提供 {field}"
            messages.append(f"\n• {prompt}")

        messages.append("\n謝謝您的配合！")
        return "\n".join(messages)

    async def _generate_sql_from_semantic(
        self, semantic_result: SemanticTranslationResult
    ) -> Optional[str]:
        """根據語義分析結果生成 SQL"""
        if not semantic_result:
            return None

        intent = semantic_result.intent
        if intent == "CLARIFICATION":
            return None

        user_input = semantic_result.raw_text.lower()

        # 複雜查詢關鍵詞
        complex_keywords = [
            "每月",
            "每個月",
            "每月份",
            "每日",
            "每天",
            "每季",
            "每季度",
            "每供應商",
            "每客戶",
            "每筆",
            "按月",
            "按日",
            "按季",
            "各月份",
            "各供應商",
            "各客戶",
            "統計",
            "分析",
            "趨勢",
        ]
        is_complex = any(kw in user_input for kw in complex_keywords)

        # 轉換約束條件為字典
        constraints = {}
        if semantic_result.constraints.material_id:
            constraints["material_id"] = semantic_result.constraints.material_id
        if semantic_result.constraints.inventory_location:
            constraints["inventory_location"] = semantic_result.constraints.inventory_location
        if semantic_result.constraints.material_category:
            constraints["material_category"] = semantic_result.constraints.material_category
        if semantic_result.constraints.transaction_type:
            constraints["transaction_type"] = semantic_result.constraints.transaction_type
        if semantic_result.constraints.time_range:
            time_range = semantic_result.constraints.time_range
            if isinstance(time_range, dict):
                constraints["time_range"] = time_range
            else:
                constraints["time_type"] = time_range
        if semantic_result.constraints.quantity:
            constraints["quantity"] = semantic_result.constraints.quantity

        # 複雜查詢：使用 LLM 生成 SQL
        if is_complex:
            logger.info(f"[SQL] 複雜查詢，使用 LLM 生成: {user_input[:50]}...")
            return await self._generate_sql_by_llm(semantic_result)

        # 簡單查詢：使用模板
        try:
            sql = self._schema_registry.generate_sql(intent, constraints)
            logger.info(f"SQL 生成成功（模板）: {sql[:100] if sql else 'None'}...")
            return sql
        except Exception as e:
            logger.warning(f"SQL 生成失敗: {e}")
            return None

    async def _generate_sql_by_llm(
        self, semantic_result: SemanticTranslationResult
    ) -> Optional[str]:
        """使用 LLM 生成複雜 SQL"""
        if not self._llm_client:
            logger.warning("LLM client 未初始化，回退到模板")
            return self._generate_sql_by_template_fallback(semantic_result)

        try:
            user_input = semantic_result.raw_text

            # 構建 Schema 提示
            schema_hint = """你可使用的表格結構：
- img_file: 庫存表 (img01=料號, img02=倉庫, img03=庫位, img10=庫存數量)
- pmn_file: 採購單身 (pmn01=採購單號, pmn02=項次, pmn04=料號, pmn20=數量)
- pmm_file: 採購單頭 (pmm01=單號, pmm02=日期, pmm04=供應商)
- ima_file: 物料主檔 (ima01=料號, ima02=品名)
- coptd_file: 訂單身 (coptd04=料號, coptd02=日期)

SQL 要求：
1. **日期欄位類型是 VARCHAR，必須使用 CAST 轉換**
   - 錯誤写法：DATE_TRUNC('month', pmm02) (❌)
   - 正確写法：DATE_TRUNC('month', CAST(pmm02 AS DATE)) (✅)
   - 錯誤写法：pmm02 >= DATE '2024-01-01' (❌)
   - 正確写法：CAST(pmm02 AS DATE) >= DATE '2024-01-01' (✅)
2. 使用 DuckDB Parquet 語法：read_parquet('s3://bucket/path/year=*/month=*/data.parquet', hive_partitioning=true)
3. 表格路徑前綴：s3://tiptop-raw/raw/v1/
4. 保持格式整齊，適合展示
5. 如果用戶說"每月"，使用 DATE_TRUNC('month', CAST(日期 AS DATE)) AS month
6. 如果用戶說"每日"，使用 DATE_TRUNC('day', CAST(日期 AS DATE)) AS day
7. 只返回 SQL，不要其他說明
8. 禁止使用：*/*/data.parquet 或 */*/*/data.parquet
"""

            prompt = f"""{schema_hint}

用戶輸入：{user_input}

約束條件：
- 料號: {semantic_result.constraints.material_id or "未指定"}
- 倉庫: {semantic_result.constraints.inventory_location or "未指定"}
- 時間: {semantic_result.constraints.time_range or "未指定"}
- 物料類別: {semantic_result.constraints.material_category or "未指定"}

SQL：
"""

            # 調用 LLM
            response = await self._llm_client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=1000,
            )

            # 提取 SQL
            text = response.get("text", "") or response.get("content", "")
            sql = text.strip()

            # 清理 SQL（移除可能的 markdown 格式）
            sql = sql.replace("```sql", "").replace("```", "").strip()

            logger.info(f"LLM SQL 生成成功: {sql[:100]}...")
            return sql

        except Exception as e:
            logger.error(f"LLM SQL 生成失敗: {e}")
            # 回退到模板
            logger.warning("回退到模板生成")
            return self._generate_sql_by_template_fallback(semantic_result)

    def _generate_sql_by_template_fallback(
        self, semantic_result: SemanticTranslationResult
    ) -> Optional[str]:
        """模板回退"""
        intent = semantic_result.intent
        constraints = {}
        if semantic_result.constraints.material_id:
            constraints["material_id"] = semantic_result.constraints.material_id
        if semantic_result.constraints.inventory_location:
            constraints["inventory_location"] = semantic_result.constraints.inventory_location
        if semantic_result.constraints.time_range:
            constraints["time_range"] = semantic_result.constraints.time_range

        try:
            return self._schema_registry.generate_sql(intent, constraints)
        except Exception:
            return None

    def _get_ka_client(self):
        """獲取 KA-Agent 客戶端（懶加載）"""
        if self._ka_client is None:
            try:
                from agents.services.protocol.http_client import HTTPAgentClient

                self._ka_client = HTTPAgentClient(
                    base_url="http://localhost:8000",  # AI-Box 主服務地址
                    timeout=30,
                )
                logger.info("MM-Agent: KA-Agent 客戶端已初始化")
            except Exception as e:
                logger.warning(f"MM-Agent: 無法初始化 KA-Agent 客戶端: {e}")
        return self._ka_client

    def _needs_knowledge_retrieval(self, instruction: str) -> bool:
        """判斷是否需要知識庫檢索

        Args:
            instruction: 用戶查詢

        Returns:
            是否需要知識庫檢索
        """
        knowledge_keywords = [
            # 職責相關
            "職責",
            "職能",
            "功能",
            "介紹",
            "說明",
            "你是誰",
            "你是什麼",
            "你做什麼",
            # 技能相關
            "技能",
            "能力",
            "可以做",
            "擅長",
            "會做",
            "能做",
            # 流程相關
            "流程",
            "步驟",
            "怎麼",
            "如何",
            "方法",
            "操作",
            "指引",
            "教學",
            # 其他知識相關
            "規則",
            "規定",
            "標準",
            "注意事項",
            "注意",
            "提醒",
            "注意點",
        ]

        instruction_lower = instruction.lower()
        return any(keyword in instruction_lower for keyword in knowledge_keywords)

    async def _retrieve_knowledge(
        self, instruction: str, domain: str = "mm_agent", major: str = "responsibilities"
    ) -> Optional[str]:
        """調用 KA-Agent 檢索知識

        Args:
            instruction: 用戶查詢
            domain: 知識庫域名（mm_agent）
            major: 知識庫類型（responsibilities/skills/workflows）

        Returns:
            檢索結果，失敗返回 None
        """
        ka_client = self._get_ka_client()
        if ka_client is None:
            logger.warning("MM-Agent: KA-Agent 客戶端未初始化，無法檢索知識庫")
            return None

        try:
            from agents.services.protocol.base import AgentServiceRequest

            # 構建 KA-Agent 請求
            ka_request = AgentServiceRequest(
                task_id=f"mm_knowledge_{id(instruction)}",
                task_type="knowledge_query",
                task_data={
                    "instruction": instruction,
                    "domain": domain,
                    "major": major,
                },
                metadata={
                    "caller_agent_id": "mm-agent",  # 標記調用方為 mm-agent
                    "knowledge_via_authorized_agent": True,
                },
            )

            # 調用 KA-Agent
            response = await ka_client.execute_agent(
                agent_id="ka-agent",
                request=ka_request,
            )

            if response.success and response.result:
                knowledge = response.result.get("knowledge") or response.result.get("response")
                logger.info(
                    f"MM-Agent: 知識庫檢索成功, instruction='{instruction[:50]}...', "
                    f"knowledge_length={len(knowledge) if knowledge else 0}"
                )
                return knowledge
            else:
                logger.warning(
                    f"MM-Agent: 知識庫檢索失敗, instruction='{instruction[:50]}...', "
                    f"error={response.error if hasattr(response, 'error') else 'Unknown'}"
                )
                return None

        except Exception as e:
            logger.error(
                f"MM-Agent: 調用 KA-Agent 檢索知識庫失敗: {e}",
                exc_info=True,
            )
            return None

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
        elif "庫存" in instruction or translation.material_category:
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

    async def run(self, input_data: MMChainInput) -> MMChainOutput:
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

        # Step 3: 檢查是否需要知識庫檢索
        knowledge_result = None
        if self._needs_knowledge_retrieval(working_query):
            logger.info(f"MM-Agent: 檢測到知識庫查詢需求, instruction='{working_query[:50]}...'")

            # 嘗試從多個知識庫類型檢索
            for major in ["responsibilities", "skills", "workflows"]:
                result = await self._retrieve_knowledge(
                    working_query, domain="mm_agent", major=major
                )
                if result:
                    knowledge_result = result
                    logger.info(f"MM-Agent: 從 {major} 知識庫檢索到結果")
                    break

            if not knowledge_result:
                logger.warning("MM-Agent: 知識庫檢索未返回結果")

        # Step 4: 專業轉譯 + 語義分析（使用新架構）
        semantic_result = None
        translation = await self._translate(working_query)

        # 如果啟用語義轉譯器，使用新架構進行語義分析
        if self._semantic_translator and not knowledge_result:
            try:
                logger.info(f"MM-Agent: 使用語義轉譯器, instruction='{working_query[:50]}...'")
                semantic_result = await self._semantic_translator.translate(working_query)

                # 如果需要澄清，優先返回澄清請求
                if semantic_result.validation.requires_confirmation:
                    clarification_msg = self._build_clarification_message(
                        semantic_result.intent,
                        semantic_result.validation,
                        semantic_result.constraints,
                    )
                    return MMChainOutput(
                        success=False,
                        response="",
                        needs_clarification=True,
                        clarification_message=clarification_msg,
                        session_id=session_id,
                        resolved_query=resolved_query if resolved_query != instruction else None,
                        translation=translation,
                        debug_info={
                            "step": "semantic_translation",
                            "intent": semantic_result.intent,
                            "semantic_result": semantic_result.model_dump(),
                            "requires_confirmation": True,
                        },
                    )
            except Exception as e:
                logger.warning(f"MM-Agent: 語義轉譯失敗，回退到原有邏輯: {e}")

        # Step 5: 使用上下文豐富轉譯結果（對於省略的實體）
        translation = self._enrich_with_context(translation, context_entities)

        # Step 6: 意圖分析
        intent = self._analyze_intent(working_query, translation)

        # Step 6.5: 檢查是否需要澄清（針對模糊的時間表達）
        needs_clarification = False
        clarification_message = None
        ambiguous_time_keywords = ["最近", "這幾天", "近來", "近期"]
        has_ambiguous_time = any(kw in working_query for kw in ambiguous_time_keywords)

        if has_ambiguous_time and intent in ["purchase", "sales", "material_issue"]:
            needs_clarification = True
            clarification_message = """「最近」是指什麼時間範圍？
• 今天
• 最近一週
• 最近一個月
• 最近三個月
• 其他時間範圍"""

        if needs_clarification:
            return MMChainOutput(
                success=False,
                response="",
                needs_clarification=True,
                clarification_message=clarification_message,
                session_id=session_id,
                resolved_query=resolved_query if resolved_query != instruction else None,
                debug_info={
                    "step": "clarification",
                    "intent": intent,
                    "reason": "模糊的時間表達",
                    "translation": translation.model_dump()
                    if hasattr(translation, "model_dump")
                    else dict(translation),
                },
            )

        # Step 7: 生成回復（如果有知識庫結果，優先使用）
        metadata = {
            "part_number": translation.part_number,
            "tlf19": translation.tlf19,
            "intent": intent,
            "table_name": translation.table_name,
        }

        # 保存用戶消息
        self._context_manager.add_message(session_id, "user", instruction, metadata)

        # 生成回復
        if knowledge_result:
            # 使用知識庫結果生成回復
            response = knowledge_result
            logger.info(f"MM-Agent: 使用知識庫結果回復, response_length={len(response)}")
        else:
            # 默認回復
            response = f"已收到指令：{instruction}"
            if resolved_query != instruction:
                response += f"\n（指代消解：{resolved_query}）"

        # 保存助手回覆
        self._context_manager.add_message(session_id, "assistant", response)

        # 構建 debug_info
        debug_info = {
            "step": "analyzed",
            "intent": intent,
            "has_context_entities": len(context_entities) > 0,
            "context_entities": context_entities,
            "translation": translation.model_dump()
            if hasattr(translation, "model_dump")
            else dict(translation),
            "used_knowledge_retrieval": knowledge_result is not None,
            "knowledge_used": knowledge_result is not None,
        }

        # 如果有語義分析結果，添加到 debug_info
        if semantic_result:
            debug_info["semantic_result"] = semantic_result.model_dump()
            debug_info["intent"] = semantic_result.intent

            # 生成 SQL
            generated_sql = await self._generate_sql_from_semantic(semantic_result)
            if generated_sql:
                debug_info["generated_sql"] = generated_sql

        return MMChainOutput(
            success=True,
            response=response,
            translation=translation,
            session_id=session_id,
            resolved_query=resolved_query if resolved_query != instruction else None,
            debug_info=debug_info,
        )


if __name__ == "__main__":
    import asyncio

    async def main():
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
            ("告訴我你的職責", "第五輪：知識庫查詢測試"),
        ]

        session_id = None

        for instruction, desc in conversation:
            print(f"\n{'=' * 70}")
            print(f"{desc}")
            print(f"用戶: {instruction}")

            result = await chain.run(MMChainInput(instruction=instruction, session_id=session_id))

            # 保存 session_id 用於下一輪
            session_id = result.session_id

            if result.needs_clarification:
                print("助手: ❌ 需要澄清")
                print(f"訊息: {result.clarification_message[:60]}...")
            else:
                trans = result.translation
                print("助手: ✅ 理解成功")

                if result.resolved_query:
                    print(f"   指代消解: {result.resolved_query}")

                print(f"   - 料號: {trans.part_number}")
                print(f"   - tlf19: {trans.tlf19}")
                print(f"   - 意圖: {result.debug_info.get('intent')}")

                # 顯示是否使用了上下文
                if result.debug_info.get("has_context_entities"):
                    print(f"   - 使用了上下文實體: {result.debug_info.get('context_entities')}")

                # 顯示是否使用了知識庫
                if result.debug_info.get("used_knowledge_retrieval"):
                    print(f"   - 使用知識庫檢索: {result.debug_info.get('knowledge_used', False)}")

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

    asyncio.run(main())
