# 代碼功能說明: MM-Agent 對話鏈 - LangChain 編排 + 多輪對話
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-03

"""MM-Agent 對話鏈 - 意圖語義分析 + 多輪對話支持"""

import logging
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel

from mm_agent.translator import Translator, TranslationResult
from mm_agent.negative_list import NegativeListChecker
from mm_agent.coreference_resolver import CoreferenceResolver
from mm_agent.chain.context_manager import get_context_manager
from mm_agent.semantic_translator import SemanticTranslatorAgent
from mm_agent.translation_models import SemanticTranslationResult

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
        self._last_intent_result = None  # 最後一次 LLM 意圖分類結果

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

    async def _execute_data_agent_query(self, semantic_result) -> dict:
        """執行 Data-Agent 查詢

        MM-Agent 只負責發送完整的自然語言查詢，
        SQL 生成由 Data-Agent 負責（使用 SchemaRAG）。

        Args:
            semantic_result: 語義分析結果

        Returns:
            查詢結果字典
        """
        try:
            import httpx

            # 構建 params（語義概念，而非 Schema）
            params = {}
            if semantic_result.constraints:
                if semantic_result.constraints.material_id:
                    params["material_id"] = semantic_result.constraints.material_id
                if semantic_result.constraints.inventory_location:
                    params["inventory_location"] = semantic_result.constraints.inventory_location
                if semantic_result.constraints.time_range:
                    params["time_range"] = semantic_result.constraints.time_range
                if semantic_result.constraints.material_category:
                    params["material_category"] = semantic_result.constraints.material_category
                if semantic_result.constraints.quantity:
                    params["quantity"] = semantic_result.constraints.quantity

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "http://localhost:8004/api/v1/data-agent/v4/execute",
                    json={
                        "task_id": f"mm_query_{int(time.time())}",
                        "task_type": "schema_driven_query",
                        "task_data": {
                            "nlq": semantic_result.raw_text,
                            "intent": semantic_result.intent,
                            "params": params,
                        },
                    },
                )

            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    data_result = result.get("result", {})
                    return {
                        "status": "success",
                        "sql": data_result.get("sql", "N/A"),  # SQL 由 Data-Agent 生成
                        "data": data_result.get("data", [])[:10],  # 只取前 10 筆
                        "row_count": data_result.get("row_count", 0),
                        "columns": data_result.get("columns", []),
                        "execution_time_ms": data_result.get("execution_time_ms", 0),
                    }
                else:
                    return {
                        "status": "error",
                        "sql": "N/A",
                        "error": result.get("message", "Unknown error"),
                    }
            else:
                return {
                    "status": "error",
                    "sql": "N/A",
                    "error": f"HTTP {response.status_code}",
                }

        except Exception as e:
            logger.error(f"MM-Agent: Data-Agent 查詢失敗: {e}", exc_info=True)
            return {
                "status": "error",
                "sql": "N/A",
                "error": str(e),
            }

    def _get_ka_client(self):
        """獲取 KA-Agent 客戶端（懶加載）"""
        if self._ka_client is None:
            try:
                from agents.services.protocol.http_client import HTTPAgentServiceClient

                self._ka_client = HTTPAgentServiceClient(
                    base_url="http://localhost:8000",  # AI-Box 主服務地址
                    timeout=30,
                )
                logger.info("MM-Agent: KA-Agent 客戶端已初始化")
            except Exception as e:
                logger.warning(f"MM-Agent: 無法初始化 KA-Agent 客戶端: {e}")
        return self._ka_client

    async def _needs_knowledge_retrieval(self, instruction: str) -> bool:
        """判斷是否需要知識庫檢索

        使用 LLM 語義判斷，而非關鍵詞匹配。

        Args:
            instruction: 用戶查詢

        Returns:
            是否需要知識庫檢索
        """
        try:
            from mm_agent.intent_endpoint import classify_intent, IntentType

            # 調用 LLM 語義分類
            result = await classify_intent(instruction)

            # 保存意圖分類結果供後續使用
            self._last_intent_result = result

            # 如果是知識查詢意圖，觸發知識庫檢索
            needs_retrieval = result.intent == IntentType.KNOWLEDGE_QUERY

            # 備用檢測：如果 LLM 沒有正確識別 is_list_files_query，根據關鍵詞判斷
            is_list_files = result.is_list_files_query
            if not is_list_files:
                # 檢查指令是否包含「列出文件」相關關鍵詞
                list_keywords = ["列出", "列表", "有哪些文件", "文件有哪些", "知識庫有", "查看文件"]
                instruction_lower = instruction.lower()
                is_list_files = any(kw in instruction_lower for kw in list_keywords)

            # 保存供後續使用
            result.is_list_files_query = is_list_files

            logger.info(
                f"MM-Agent: 知識庫檢索判斷 (LLM) - "
                f"intent={result.intent.value}, confidence={result.confidence}, "
                f"needs_retrieval={needs_retrieval}, is_list_files={is_list_files}"
            )

            return needs_retrieval

        except Exception as e:
            # 如果 LLM 分類失敗，回退到關鍵詞匹配（兜底策略）
            logger.warning(f"MM-Agent: LLM 語義判斷失敗，回退到關鍵詞匹配: {e}")
            knowledge_keywords = [
                "職責",
                "職能",
                "功能",
                "介紹",
                "說明",
                "技能",
                "能力",
                "可以做",
                "擅長",
                "流程",
                "步驟",
                "怎麼",
                "如何",
                "方法",
                "操作",
                "指引",
                "教學",
                "規則",
                "規定",
                "標準",
                "注意事項",
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
        try:
            import httpx

            # 直接調用 KA-Agent API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/knowledge/query",
                    json={
                        "request_id": f"mm_knowledge_{id(instruction)}",
                        "query": instruction,
                        "agent_id": "ka-agent",
                        "user_id": "mm-agent",
                        "metadata": {
                            "caller_agent_id": "mm-agent",
                            "caller_agent_key": "-h0tjyh",
                        },
                        "options": {
                            "query_type": "hybrid",
                            "top_k": 5,
                            "include_graph": True,
                        },
                    },
                )

            if response.status_code == 200:
                result = response.json()
                if result.get("success") and result.get("results"):
                    # 提取知識內容
                    knowledge = ""
                    for r in result.get("results", [])[:3]:
                        content = r.get("content", "")
                        if content:
                            knowledge += content + "\n\n"

                    if knowledge:
                        logger.info(
                            f"MM-Agent: 知識庫檢索成功, instruction='{instruction[:50]}...', "
                            f"knowledge_length={len(knowledge)}"
                        )
                        return knowledge

            logger.warning(
                f"MM-Agent: 知識庫檢索失敗, instruction='{instruction[:50]}...', "
                f"status={response.status_code}"
            )
            return None

        except Exception as e:
            logger.error(
                f"MM-Agent: 調用 KA-Agent 檢索知識庫失敗: {e}",
                exc_info=True,
            )
            return None

    async def _list_knowledge_files(self) -> str:
        """列出知識庫中的所有文件

        Returns:
            文件列表字符串
        """
        try:
            import httpx

            # 調用 API 獲取知識庫文件列表
            # MM-Agent 的知識庫 ID: root_Material_Management_1770989092
            kb_id = "root_Material_Management_1770989092"

            async with httpx.AsyncClient(timeout=30.0) as client:
                # 獲取知識庫的資料夾
                kb_response = await client.get(
                    f"http://localhost:8000/api/v1/knowledge-bases/{kb_id}/folders"
                )

                if kb_response.status_code != 200:
                    logger.warning(f"MM-Agent: 獲取知識庫資料夾失敗: {kb_response.status_code}")
                    return None

                kb_data = kb_response.json()
                folders = kb_data.get("data", {}).get("items", [])

                # 收集所有有向量的文件
                all_files = []
                for folder in folders:
                    folder_id = folder.get("id")
                    folder_name = folder.get("name", "未知資料夾")

                    files_response = await client.get(
                        f"http://localhost:8000/api/v1/knowledge-bases/folders/{folder_id}/files"
                    )

                    if files_response.status_code == 200:
                        files_data = files_response.json()
                        files = files_data.get("data", {}).get("items", [])

                        for f in files:
                            if f.get("vector_count", 0) > 0:  # 只包含有向量的文件
                                all_files.append(
                                    {
                                        "name": f.get("filename", "未知文件名"),
                                        "folder": folder_name,
                                        "vector_count": f.get("vector_count", 0),
                                    }
                                )

                # 生成文件列表
                if all_files:
                    file_list_text = "根據目前的向量檢索結果，系統的知識庫（即您上傳並已向量化的文件）包含以下文件：\n\n"
                    file_list_text += "| 編號 | 文件名稱 | 所在資料夾 | 向量數 |\n"
                    file_list_text += "|-------|----------|------------|--------|\n"

                    for i, f in enumerate(all_files, 1):
                        file_list_text += (
                            f"| {i} | **{f['name']}** | {f['folder']} | {f['vector_count']} |\n"
                        )

                    file_list_text += f"\n**文件總數：{len(all_files)} 個**\n"
                    file_list_text += (
                        "\n> 注意：這裡所說的「知識庫」指的是您上傳的文件，而非本模型的訓練資料。"
                    )

                    return file_list_text
                else:
                    return "目前知識庫中沒有已向量化的文件。"

        except Exception as e:
            logger.error(f"MM-Agent: 列出知識庫文件失敗: {e}", exc_info=True)
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

        # 【重要】重置 _last_intent_result，確保每次請求都進行新的意圖分類
        self._last_intent_result = None

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

        # Step 3: 知識庫檢索（僅當明確是知識查詢時）
        knowledge_result = None
        is_list_files_query = False

        # 【關鍵】先檢查 _last_intent_result 意圖
        has_data_query_intent = False
        has_knowledge_intent = False

        # 初始意圖判斷
        if self._last_intent_result:
            intent = self._last_intent_result.intent
            # 數據查詢意圖
            if intent in [
                "SIMPLE_QUERY",
                "QUERY_STOCK",
                "QUERY_INVENTORY",
                "QUERY_WORK_ORDER",
                "QUERY_SHIPPING",
            ]:
                has_data_query_intent = True
            elif intent == "COMPLEX_TASK":
                has_data_query_intent = True
            # 知識查詢意圖（只有當不是數據查詢時才設置）
            elif intent == "KNOWLEDGE_QUERY":
                has_knowledge_intent = True

        # 執行翻譯（用於數據查詢）
        translation = await self._translate(working_query)

        # 執行語義分析（獲取意圖和約束）
        semantic_result = None
        if self._semantic_translator:
            try:
                semantic_result = await self._semantic_translator.translate(working_query)
                if semantic_result:
                    # 從 semantic_result 更新意圖判斷（覆蓋 _last_intent_result）
                    intent = semantic_result.intent
                    if intent in [
                        "QUERY_STOCK",
                        "QUERY_INVENTORY",
                        "QUERY_WORK_ORDER",
                        "QUERY_SHIPPING",
                        "SIMPLE_QUERY",
                    ]:
                        has_data_query_intent = True
                        has_knowledge_intent = False  # 覆蓋知識查詢意圖
                        logger.info(f"MM-Agent: semantic_result 意圖={intent}，設置為數據查詢")
                    elif intent == "COMPLEX_TASK":
                        has_data_query_intent = True
                        has_knowledge_intent = False  # 覆蓋知識查詢意圖
                        logger.info(f"MM-Agent: semantic_result 意圖={intent}，設置為數據查詢")
                    elif intent == "KNOWLEDGE_QUERY":
                        # semantic_result 也認為是知識查詢
                        logger.info(f"MM-Agent: semantic_result 意圖={intent}，保持知識查詢")

                    # 如果需要澄清
                    if semantic_result.validation.requires_confirmation:
                        clarification_msg = self._build_clarification_message(
                            intent,
                            semantic_result.validation,
                            semantic_result.constraints,
                        )
                        return MMChainOutput(
                            success=False,
                            response="",
                            needs_clarification=True,
                            clarification_message=clarification_msg,
                            session_id=session_id,
                            resolved_query=resolved_query
                            if resolved_query != instruction
                            else None,
                            translation=translation,
                            debug_info={
                                "step": "semantic_translation",
                                "intent": intent,
                                # 只保留意圖，不包含 schema 相關信息
                                "semantic_result": {
                                    "intent": semantic_result.intent,
                                    "raw_text": semantic_result.raw_text,
                                },
                                "requires_confirmation": True,
                            },
                        )

            except Exception as e:
                logger.warning(f"MM-Agent: 語義翻譯失敗: {e}")

        # 執行 Data-Agent 查詢（數據查詢意圖）
        # MM-Agent 只負責意圖識別，SQL 生成交給 Data-Agent（使用 SchemaRAG）
        data_result = None
        if has_data_query_intent and semantic_result:
            try:
                logger.info(f"MM-Agent: 執行 Data-Agent 查詢（意圖：{semantic_result.intent}）")
                # 直接發送完整自然語言給 Data-Agent，讓 Data-Agent 負責 SQL 生成
                data_result = await self._execute_data_agent_query(semantic_result)
                logger.info(
                    f"MM-Agent: Data-Agent 查詢完成, status={data_result.get('status') if data_result else 'None'}"
                )
            except Exception as e:
                logger.warning(f"MM-Agent: Data-Agent 查詢失敗: {e}")

        # 知識庫檢索（僅當明確是知識查詢且沒有數據查詢時）
        if has_knowledge_intent and not data_result:
            if self._last_intent_result and hasattr(
                self._last_intent_result, "is_list_files_query"
            ):
                is_list_files_query = self._last_intent_result.is_list_files_query

            if is_list_files_query:
                knowledge_result = await self._list_knowledge_files()
            else:
                # 嘗試從多個知識庫類型檢索
                for major in ["responsibilities", "skills", "workflows"]:
                    result = await self._retrieve_knowledge(
                        working_query, domain="mm_agent", major=major
                    )
                    if result:
                        knowledge_result = result
                        logger.info(f"MM-Agent: 從 {major} 知識庫檢索到結果")
                        break
                semantic_result = None

        # 【重要】數據查詢意圖優先，不執行知識庫檢索
        # 如果已經有 semantic_result 識別為數據查詢意圖，直接跳過知識庫檢索判斷
        if has_data_query_intent:
            logger.info(f"MM-Agent: 檢測到數據查詢意圖（semantic_result），跳過知識庫檢索")
        elif await self._needs_knowledge_retrieval(working_query):
            has_knowledge_intent = True  # LLM 判斷為知識查詢
            logger.info(
                f"MM-Agent: 檢測到知識庫查詢需求, instruction='{working_query[:50]}...', is_list_files_query={is_list_files_query}"
            )

            # 如果是「列出知識庫文件」查詢，直接返回文件列表
            if is_list_files_query:
                knowledge_result = await self._list_knowledge_files()
                logger.info(
                    f"MM-Agent: 返回知識庫文件列表, count={len(knowledge_result) if knowledge_result else 0}"
                )
            else:
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

        # Step 4: 使用上下文豐富轉譯結果（對於省略的實體）
        translation = self._enrich_with_context(translation, context_entities)

        # Step 5: 意圖分析
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
        response = ""
        used_knowledge = False
        used_data_query = False

        # 情況 1: 只有知識意圖 → 返回知識庫內容
        if knowledge_result and not data_result:
            response = knowledge_result
            used_knowledge = True
            logger.info(f"MM-Agent: 使用知識庫結果回復, response_length={len(response)}")

        # 情況 2: 只有數據意圖 → 返回 Data-Agent 查詢結果
        elif data_result and data_result.get("status") == "success" and not knowledge_result:
            response = self._format_data_response(data_result)
            used_data_query = True
            logger.info(f"MM-Agent: 使用 Data-Agent 結果回復")

        # 情況 3: 兩者都有 → 由 LLM 整合回覆
        elif knowledge_result and data_result and data_result.get("status") == "success":
            response = await self._generate_integrated_response(
                working_query, knowledge_result, data_result
            )
            used_knowledge = True
            used_data_query = True
            logger.info(f"MM-Agent: 使用整合回覆（知識+數據）")

        # 情況 4: 沒有結果 → 默認回覆
        else:
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
            "used_knowledge_retrieval": used_knowledge,
            "used_data_query": used_data_query,
        }

        # 如果有語義分析結果，添加到 debug_info（只保留意圖，不包含 schema 相關信息）
        if semantic_result:
            # 只保留意圖和約束條件，不包含 schema_binding
            debug_info["semantic_result"] = {
                "intent": semantic_result.intent,
                "raw_text": semantic_result.raw_text,
                "constraints": {
                    "material_id": semantic_result.constraints.material_id,
                    "inventory_location": semantic_result.constraints.inventory_location,
                    "time_range": semantic_result.constraints.time_range,
                }
                if semantic_result.constraints
                else {},
            }
            # 設置意圖
            if has_knowledge_intent and has_data_query_intent:
                debug_info["intent"] = "INTEGRATED"
            elif has_knowledge_intent:
                debug_info["intent"] = "KNOWLEDGE_QUERY"
            elif has_data_query_intent:
                debug_info["intent"] = semantic_result.intent
            else:
                debug_info["intent"] = semantic_result.intent

        # 如果有知識庫查詢意圖但沒有 semantic_result，也設置 intent
        if has_knowledge_intent and not semantic_result:
            debug_info["intent"] = "KNOWLEDGE_QUERY"

        return MMChainOutput(
            success=True,
            response=response,
            translation=translation,
            session_id=session_id,
            resolved_query=resolved_query if resolved_query != instruction else None,
            debug_info=debug_info,
        )

    def _format_data_response(self, data_result: dict) -> str:
        """格式化 Data-Agent 查詢結果"""
        sql = data_result.get("sql", "")
        data = data_result.get("data", [])
        row_count = data_result.get("row_count", 0)
        execution_time = data_result.get("execution_time_ms", 0)

        response = f"**查詢結果**（耗時 {execution_time:.0f} ms）\n\n"

        if sql:
            response += f"**SQL**:\n```sql\n{sql}\n```\n\n"

        if row_count == 0:
            response += "**結果**: 查無資料"
        else:
            response += f"**資料筆數**: {row_count}\n\n"

            if data:
                response += "**前 5 筆資料**:\n"
                response += "| " + " | ".join(data[0].keys()) + " |\n"
                response += "| " + " | ".join(["---"] * len(data[0])) + " |\n"
                for row in data[:5]:
                    response += "| " + " | ".join(str(v) for v in row.values()) + " |\n"

        return response

    async def _generate_integrated_response(
        self, query: str, knowledge_result: str, data_result: dict
    ) -> str:
        """由 LLM 生成整合回覆（知識+數據）"""
        try:
            # 構建整合提示
            data_summary = ""
            if data_result.get("data"):
                data = data_result["data"][:5]
                data_summary = f"**查詢結果**（{data_result.get('row_count', 0)} 筆資料）\n"
                if data:
                    data_summary += "| " + " | ".join(data[0].keys()) + " |\n"
                    data_summary += "| " + " | ".join(["---"] * len(data[0])) + " |\n"
                    for row in data[:5]:
                        data_summary += "| " + " | ".join(str(v) for v in row.values()) + " |\n"

            prompt = f"""用戶問題: {query}

知識庫內容:
{knowledge_result}

數據查詢結果:
{data_summary}

請根據用戶問題，整合知識庫內容和數據查詢結果，生成一個完整、有意義的回答。

要求：
1. 先回答用戶的核心問題
2. 結合知識庫的專業說明
3. 解釋數據查詢結果的業務意義
4. 提供建議或後續行動

回答:"""

            if self._llm_client:
                response = await self._llm_client.generate(
                    prompt=prompt,
                    temperature=0.5,
                    max_tokens=2000,
                )
                text = response.get("text", "") or response.get("content", "")
                return text.strip()

            # 如果沒有 LLM，回退到簡單整合
            return f"**知識庫內容**:\n{knowledge_result}\n\n**數據查詢結果**:\n{data_summary if data_summary else '無數據'}"

        except Exception as e:
            logger.error(f"MM-Agent: 整合回覆生成失敗: {e}")
            return f"**知識庫內容**:\n{knowledge_result}\n\n**數據查詢結果**:\n{data_summary if data_summary else '查詢失敗'}"


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
