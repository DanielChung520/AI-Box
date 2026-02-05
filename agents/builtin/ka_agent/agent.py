# 代碼功能說明: KA-Agent (Knowledge Architect Agent) 核心實現
# 創建日期: 2026-01-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28 11:00 UTC+8

import logging
import time
import json
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from agents.services.orchestrator.task_tracker import TaskTracker, TaskStatus
from agents.builtin.knowledge_ontology_agent.agent import KnowledgeOntologyAgent
from agents.task_analyzer.policy_service import PolicyService
from .models import KARequest, KAResult, KAResponse
from .storage_adapter import KAStorageAdapter
from .error_handler import KAAgentErrorHandler


# 延遲導入以避免循環依賴
def get_llm_dependencies():
    from llm.clients.factory import get_client
    from services.api.models.llm_model import LLMProvider

    return get_client, LLMProvider


def _get_audit_log_service():
    from services.api.services.audit_log_service import AuditLogService

    return AuditLogService()


def _get_file_metadata_service():
    from services.api.services.file_metadata_service import get_metadata_service

    return get_metadata_service()


def _get_encoding_service():
    from services.api.services.knowledge_asset_encoding_service import (
        KnowledgeAssetEncodingService,
    )

    return KnowledgeAssetEncodingService()


def _get_embedding_and_vector_services():
    from services.api.services.embedding_service import get_embedding_service
    from services.api.services.qdrant_vector_store_service import (
        get_qdrant_vector_store_service,
    )

    return get_embedding_service(), get_qdrant_vector_store_service()


logger = logging.getLogger(__name__)


class KnowledgeArchitectAgent(AgentServiceProtocol):
    """KA-Agent: 知識資產總建築師"""

    def __init__(self, ko_agent: Optional[KnowledgeOntologyAgent] = None):
        self._logger = logger
        self._config = self._load_local_config()
        self._task_tracker = TaskTracker(use_arangodb=True)
        self._ko_agent = ko_agent or KnowledgeOntologyAgent()
        self._policy = PolicyService()
        self._storage = KAStorageAdapter(
            endpoint=self._config.get("storage", {}).get(
                "seaweedfs_endpoint", "http://localhost:8334"
            ),
            bucket=self._config.get("storage", {}).get("asset_bucket", "knowledge-assets"),
        )
        # 修改時間：2026-01-28 - 使用 agent_id 屬性（而非 _agent_id）以符合註冊檢查要求
        self.agent_id = "ka-agent"  # 使用標準命名格式，與註冊代碼一致
        self._agent_id = self._config.get("agent_id", "ka_agent")  # 保留向後兼容
        # 這裡的 chain 目前是字串列表，調用時需處理
        # 修改時間：2026-01-28 - 優先使用 gpt-oss:120b-cloud（Cloud 模型，不佔本地記憶體）
        self._model_chain = self._config.get("model_routing", {}).get(
            "planning_chain", ["gpt-oss:120b-cloud", "gpt-oss:20b", "qwen3-next:latest"]
        )
        self._system_prompt = self._get_orchestration_prompt()
        # 修改時間：2026-01-28 - 新增錯誤處理器
        self._error_handler = KAAgentErrorHandler()
        # 修改時間：2026-01-28 - 啟動 heartbeat 機制（保持 agent 狀態為 online）
        self._start_heartbeat()

    def _load_local_config(self) -> Dict[str, Any]:
        config_path = Path(__file__).parent / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self._logger.error(f"Failed to load KA-Agent config: {e}")
                return {}
        return {}

    def _start_heartbeat(self) -> None:
        """啟動 heartbeat 機制（保持 agent 狀態為 online）"""
        try:
            from agents.services.registry.health_monitor import HealthMonitor

            health_monitor = HealthMonitor.get_instance()
            health_monitor.register_agent(
                agent_id=self.agent_id,
                agent_instance=None,  # 內部 agent 不需要實例
                heartbeat_interval=60,  # 每 60 秒發送一次 heartbeat
            )
            self._logger.debug(
                f"[KA-Agent] 💓 Heartbeat 機制啟動: agent_id={self.agent_id}, interval=60s"
            )
        except Exception as e:
            self._logger.warning(f"Failed to start heartbeat: {e}")

    def _get_orchestration_prompt(self) -> str:
        return """
# 角色：知識建築師 (Knowledge Architect)
你負責 AI-Box 核心知識資產的治理與管理。

## 執行規範
1. **意圖識別**：
   - MANAGEMENT: 上架、更版、刪除、生命週期變更。
   - RETRIEVAL: 查詢、搜索、知識提取。

2. **管理指令協議 (MANAGEMENT)**：
   - 必須產出 JSON 格式對象，包含 `todo_list`。
   - 結尾要求確認：「請確認以上任務清單，點擊執行後我將開始自動化處理。」
"""

    async def _call_llm_chain(self, prompt: str) -> str:
        get_client, LLMProvider = get_llm_dependencies()

        for model_name in self._model_chain:
            try:
                # 修改時間：2026-01-28 - 修復 Provider 識別邏輯
                # 參考 chat.py 的 _infer_provider_from_model_id 函數
                # gpt-oss:120b-cloud 和 gpt-oss:20b 是 Ollama 模型，不是 OpenAI
                provider = LLMProvider.OLLAMA  # 默認使用 Ollama
                model_lower = model_name.lower()

                # Ollama 模型識別：包含 ":" 或是指定的 Ollama 模型
                if ":" in model_name or model_lower in {
                    "llama2",
                    "gpt-oss:20b",
                    "gpt-oss:120b-cloud",
                    "qwen3-coder:30b",
                }:
                    provider = LLMProvider.OLLAMA
                # OpenAI 模型：以 "gpt-" 開頭但不包含 ":"（如 gpt-4, gpt-4-turbo）
                elif model_lower.startswith("gpt-") and ":" not in model_name:
                    provider = LLMProvider.OPENAI
                elif "gemini" in model_lower:
                    provider = LLMProvider.GOOGLE  # 修改：LLMProvider.GOOGLE (不是 GEMINI)
                # 其他情況默認使用 Ollama

                self._logger.debug(
                    f"[KA-Agent] Provider 識別: model={model_name}, "
                    f"provider={provider.value}, model_lower={model_lower}"
                )

                client = get_client(provider)
                response = await client.generate(
                    prompt=prompt,
                    model=model_name,  # 指定具體型號
                    system_prompt=self._system_prompt,
                    temperature=0.2,
                )
                if response and "text" in response:
                    return str(response["text"])
            except Exception as e:
                self._logger.warning(f"模型 {model_name} 調用失敗: {e}")
                continue
        raise RuntimeError("模型鏈路全部失效")

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        start_time = time.time()
        execution_start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))

        try:
            self._logger.info(
                f"[KA-Agent] 🚀 請求接收: task_id={request.task_id}, "
                f"task_type={request.task_type}, execution_start={execution_start}, "
                f"has_context={request.context is not None}, "
                f"has_metadata={request.metadata is not None}"
            )

            task_data = request.task_data or {}
            instruction = str(task_data.get("instruction", ""))

            # 修改時間：2026-01-28 - 添加參數驗證
            if not instruction or instruction.strip() == "":
                self._logger.warning(
                    f"[KA-Agent] ⚠️ 缺少必要參數: task_id={request.task_id}, parameter=instruction"
                )
                feedback = self._error_handler.missing_parameter(
                    parameter_name="instruction",
                    context="請提供您想執行的操作或查詢",
                )
                formatted_feedback = self._error_handler.format_feedback_for_llm(feedback)

                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="failed",
                    error=formatted_feedback,
                    result=feedback.model_dump(),
                    metadata=request.metadata or {},
                )

            self._logger.info(
                f"[KA-Agent] 📝 指令解析: task_id={request.task_id}, "
                f"instruction_length={len(instruction)}, "
                f"instruction_preview={instruction[:100]}..."
            )

            # 使用 LLM 進行意圖解析
            llm_start_time = time.time()
            self._logger.info(
                f"[KA-Agent] 🤖 開始 LLM 意圖解析: task_id={request.task_id}, "
                f"model_chain={self._model_chain}"
            )

            llm_output = await self._call_llm_chain(instruction)

            llm_latency_ms = int((time.time() - llm_start_time) * 1000)
            self._logger.info(
                f"[KA-Agent] ✅ LLM 意圖解析完成: task_id={request.task_id}, "
                f"llm_latency_ms={llm_latency_ms}, "
                f"output_length={len(llm_output)}, output_preview={llm_output[:200]}..."
            )

            plan: Dict[str, Any] = {"category": "MANAGEMENT", "todo_list": []}
            try:
                json_start = llm_output.find("{")
                json_end = llm_output.rfind("}") + 1
                if json_start >= 0:
                    plan = json.loads(llm_output[json_start:json_end])
                    self._logger.info(
                        f"[KA-Agent] 📋 計劃解析成功: task_id={request.task_id}, "
                        f"category={plan.get('category')}, "
                        f"todo_list_count={len(plan.get('todo_list', []))}"
                    )
            except Exception as parse_error:
                self._logger.warning(
                    f"[KA-Agent] ⚠️ 計劃解析失敗，使用默認分類: task_id={request.task_id}, "
                    f"error={str(parse_error)}"
                )
                if "query" in instruction.lower() or "search" in instruction.lower():
                    plan = {"category": "RETRIEVAL"}
                    self._logger.info(
                        f"[KA-Agent] 🔍 檢測到檢索意圖: task_id={request.task_id}, "
                        f"category=RETRIEVAL"
                    )

            ka_req = KARequest(**task_data)
            flow_start_time = time.time()

            # 修改時間：2026-01-28 - 優先使用 action 字段判斷流程，而非 LLM 意圖解析
            # action 字段由調用方明確指定，比 LLM 解析更可靠
            is_retrieval_action = ka_req.action in [
                "knowledge.query",
                "ka.list",
                "ka.retrieve",
            ]

            # 如果 action 明確指示檢索，強制使用 RETRIEVAL 流程
            if is_retrieval_action:
                plan["category"] = "RETRIEVAL"
                self._logger.info(
                    f"[KA-Agent] 🔍 根據 action 字段強制進入檢索流程: "
                    f"task_id={request.task_id}, action={ka_req.action}"
                )

            if plan.get("category") == "MANAGEMENT":
                self._logger.info(
                    f"[KA-Agent] 🔧 進入管理流程: task_id={request.task_id}, "
                    f"action={ka_req.action}, todo_list_count={len(plan.get('todo_list', []))}"
                )
                result = await self._handle_management_flow(
                    ka_req, request, plan.get("todo_list", [])
                )
            else:
                self._logger.info(
                    f"[KA-Agent] 🔍 進入檢索流程: task_id={request.task_id}, "
                    f"query={ka_req.query}, query_type={ka_req.query_type}, "
                    f"file_id={ka_req.file_id}, domain={ka_req.domain}, major={ka_req.major}"
                )
                result = await self._handle_retrieval_flow(ka_req, request)

            flow_latency_ms = int((time.time() - flow_start_time) * 1000)
            total_latency_ms = int((time.time() - start_time) * 1000)
            result.query_time_ms = total_latency_ms

            self._logger.info(
                f"[KA-Agent] ✅ 流程執行完成: task_id={request.task_id}, "
                f"category={plan.get('category')}, success={result.success}, "
                f"flow_latency_ms={flow_latency_ms}, total_latency_ms={total_latency_ms}, "
                f"result_count={len(result.results) if hasattr(result, 'results') else 0}"
            )

            if not result.success and result.error:
                self._logger.warning(
                    f"[KA-Agent] ⚠️ 流程執行失敗: task_id={request.task_id}, error={result.error}"
                )

            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed" if result.success else "failed",
                result=result.model_dump(),
                error=result.error,
                metadata=request.metadata or {},
            )
        except Exception as e:
            total_latency_ms = int((time.time() - start_time) * 1000)
            self._logger.error(
                f"[KA-Agent] ❌ 執行異常: task_id={request.task_id}, "
                f"error={str(e)}, error_type={type(e).__name__}, "
                f"total_latency_ms={total_latency_ms}",
                exc_info=True,
            )

            # 修改時間：2026-01-28 - 使用用戶友好的錯誤反饋
            feedback = self._error_handler.system_error(
                error_message=str(e),
                error_type=type(e).__name__,
                retry_possible=True,
            )

            formatted_feedback = self._error_handler.format_feedback_for_llm(feedback)

            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                error=formatted_feedback,  # 用戶友好的錯誤消息
                result=feedback.model_dump(),  # 完整的反饋結構
                metadata=request.metadata or {},
            )

    async def _handle_management_flow(
        self, req: KARequest, raw_req: AgentServiceRequest, llm_todo: List[Dict[str, Any]]
    ) -> KAResponse:
        management_start_time = time.time()
        task_id = raw_req.task_id

        self._logger.info(
            f"[KA-Agent] 🔧 管理流程開始: task_id={task_id}, "
            f"action={req.action}, llm_todo_count={len(llm_todo)}"
        )

        user_confirmed = False
        if raw_req.metadata:
            user_confirmed = raw_req.metadata.get("user_confirmed", False)

        if not user_confirmed:
            self._logger.info(f"[KA-Agent] ⏸️ 等待用戶確認: task_id={task_id}, action={req.action}")

            todo_list = llm_todo if llm_todo else self._generate_default_todo_list()
            tracked_task_id = self._task_tracker.create_task(
                instruction=str(raw_req.task_data.get("instruction", "KA Task")),
                target_agent_id=self.agent_id,  # 修改時間：2026-01-28 - 使用 agent_id 屬性
                user_id=str(
                    raw_req.metadata.get("user_id", "unknown") if raw_req.metadata else "unknown"
                ),
                intent={"action": req.action, "todo": todo_list},
            )

            self._logger.info(
                f"[KA-Agent] ✅ 任務創建完成，等待確認: task_id={task_id}, "
                f"tracked_task_id={tracked_task_id}, todo_list_count={len(todo_list)}"
            )

            return KAResponse(
                success=True,
                message="[ACTION_REQUIRED] 請確認任務清單。",
                metadata={
                    "status": "AWAITING_CONFIRMATION",
                    "task_id": tracked_task_id,
                    "todo_list": todo_list,
                },
            )

        self._logger.info(
            f"[KA-Agent] ▶️ 用戶已確認，開始執行管理步驟: task_id={task_id}, action={req.action}"
        )

        target_task_id = raw_req.metadata.get("task_id") if raw_req.metadata else raw_req.task_id
        result = await self._execute_management_steps(req, str(target_task_id))

        management_latency_ms = int((time.time() - management_start_time) * 1000)
        self._logger.info(
            f"[KA-Agent] ✅ 管理流程完成: task_id={task_id}, "
            f"target_task_id={target_task_id}, success={result.success}, "
            f"management_latency_ms={management_latency_ms}"
        )

        return result

    async def _execute_management_steps(self, req: KARequest, task_id: str) -> KAResponse:
        execution_start_time = time.time()
        try:
            self._logger.info(
                f"[KA-Agent] ⚡ 開始執行管理步驟: task_id={task_id}, action={req.action}"
            )

            self._task_tracker.update_task_status(task_id, TaskStatus.RUNNING)
            self._logger.debug(f"[KA-Agent] 📊 任務狀態更新為 RUNNING: task_id={task_id}")

            file_id = req.file_id or (req.metadata.get("file_id") if req.metadata else None)
            if file_id:
                self._logger.info(
                    f"[KA-Agent] 📁 註冊知識資產: task_id={task_id}, file_id={file_id}, "
                    f"domain={req.metadata.get('domain') if req.metadata else None}, "
                    f"major={req.metadata.get('major') if req.metadata else None}"
                )
                registration_start_time = time.time()
                reg = await self._register_knowledge_asset(
                    file_id=file_id,
                    domain=req.metadata.get("domain") if req.metadata else None,
                    major=req.metadata.get("major") if req.metadata else None,
                    vector_refs=req.metadata.get("vector_refs") if req.metadata else None,
                    graph_refs=req.metadata.get("graph_refs") if req.metadata else None,
                )
                registration_latency_ms = int((time.time() - registration_start_time) * 1000)

                ka_id = reg["ka_id"]
                knw_code = reg["knw_code"]

                self._logger.info(
                    f"[KA-Agent] ✅ 知識資產註冊完成: task_id={task_id}, "
                    f"file_id={file_id}, ka_id={ka_id}, knw_code={knw_code}, "
                    f"registration_latency_ms={registration_latency_ms}"
                )
                audit = _get_audit_log_service()
                from services.api.models.audit_log import AuditAction, AuditLogCreate

                audit.log(
                    AuditLogCreate(
                        user_id="systemAdmin",
                        action=AuditAction.KNOWLEDGE_ASSET_CREATED,
                        resource_type="knowledge_asset",
                        resource_id=file_id,
                        ip_address="127.0.0.1",
                        user_agent="KA-Agent",
                        details={
                            "file_id": file_id,
                            "ka_id": ka_id,
                            "knw_code": knw_code,
                            "domain": reg.get("domain"),
                            "major": reg.get("major"),
                        },
                    ),
                    async_mode=True,
                )
            else:
                await asyncio.sleep(0.1)
                ka_id = req.ka_id or f"KA-{int(time.time())}"
                knw_code = None
            execution_latency_ms = int((time.time() - execution_start_time) * 1000)

            self._task_tracker.update_task_status(
                task_id, TaskStatus.COMPLETED, result={"ka_id": ka_id, "knw_code": knw_code}
            )

            self._logger.info(
                f"[KA-Agent] ✅ 管理步驟執行完成: task_id={task_id}, "
                f"ka_id={ka_id}, knw_code={knw_code}, execution_latency_ms={execution_latency_ms}"
            )

            return KAResponse(
                success=True,
                message=f"資產化成功: {ka_id}",
                metadata={"ka_id": ka_id, "knw_code": knw_code},
            )
        except Exception as e:
            execution_latency_ms = int((time.time() - execution_start_time) * 1000)
            self._logger.error(
                f"[KA-Agent] ❌ 管理步驟執行失敗: task_id={task_id}, "
                f"error={str(e)}, error_type={type(e).__name__}, "
                f"execution_latency_ms={execution_latency_ms}",
                exc_info=True,
            )
            self._task_tracker.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
            raise

    async def _register_knowledge_asset(
        self,
        file_id: str,
        domain: Optional[str] = None,
        major: Optional[str] = None,
        vector_refs: Optional[List[str]] = None,
        graph_refs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """註冊知識資產：Ontology 對齊、KNW-Code 生成、寫入 file_metadata（規格 Ch 5.4, 8.1）"""
        meta_svc = _get_file_metadata_service()
        existing = meta_svc.get(file_id)
        if not existing:
            raise ValueError(f"file_metadata 不存在: file_id={file_id}")
        enc_svc = _get_encoding_service()
        filename = existing.filename or ""
        preview: Optional[str] = None
        if hasattr(existing, "custom_metadata") and existing.custom_metadata:
            preview = (existing.custom_metadata.get("preview") or "")[:2000]
        enc = await enc_svc.encode_file(
            file_id=file_id,
            filename=filename,
            file_content_preview=preview,
            file_metadata={"file_type": existing.file_type, "user_id": existing.user_id},
        )
        from services.api.models.file_metadata import FileMetadataUpdate

        update = FileMetadataUpdate(
            task_id="KA-Agent-Tasks",
            knw_code=enc["knw_code"],
            ka_id=enc["ka_id"],
            domain=enc["domain"],
            major=enc.get("major"),
            lifecycle_state=enc["lifecycle_state"],
            version=enc["version"],
            vector_refs=vector_refs,
            graph_refs=graph_refs,
        )
        meta_svc.update(file_id, update)
        return enc

    async def _handle_retrieval_flow(
        self, req: KARequest, raw_req: AgentServiceRequest
    ) -> KAResponse:
        retrieval_start_time = time.time()
        task_id = raw_req.task_id

        self._logger.info(
            f"[KA-Agent] 🔍 檢索流程開始: task_id={task_id}, "
            f"query={req.query}, query_type={req.query_type}, "
            f"domain={req.domain}, major={req.major}, top_k={req.top_k}"
        )

        # 獲取調用 Agent 的 ID（從 metadata 中）
        caller_agent_id = None
        if raw_req.metadata:
            caller_agent_id = raw_req.metadata.get("caller_agent_id")

        self._logger.debug(
            f"[KA-Agent] 📋 調用方信息: task_id={task_id}, caller_agent_id={caller_agent_id}"
        )

        # Agent 權限檢查（檢查是否有 MM-Agent 知識庫訪問權限）
        MM_AGENT_KNOWLEDGE_CAPABILITY = "mm_agent_knowledge"

        if caller_agent_id:
            try:
                from agents.services.registry.registry import get_agent_registry

                registry = get_agent_registry()
                agent_info = registry.get_agent_info(caller_agent_id)

                if agent_info:
                    capabilities = agent_info.capabilities or []
                    has_mm_knowledge = MM_AGENT_KNOWLEDGE_CAPABILITY in capabilities

                    self._logger.info(
                        f"[KA-Agent] 🔐 Agent 權限檢查: task_id={task_id}, "
                        f"caller_agent_id={caller_agent_id}, has_mm_knowledge={has_mm_knowledge}, "
                        f"capabilities={capabilities}"
                    )

                    if not has_mm_knowledge:
                        feedback = self._error_handler.permission_denied(
                            user_id=caller_agent_id,
                            action="知識庫檢索",
                            resource="MM-Agent 知識庫",
                            reason=f"Agent '{caller_agent_id}' 沒有 '{MM_AGENT_KNOWLEDGE_CAPABILITY}' 能力",
                        )

                        formatted_feedback = self._error_handler.format_feedback_for_llm(feedback)

                        return KAResponse(
                            success=False,
                            message=formatted_feedback,
                            results=[],
                            total=0,
                            metadata={"feedback": feedback.model_dump()},
                        )
                else:
                    self._logger.warning(
                        f"[KA-Agent] ⚠️ 未找到 Agent 信息: task_id={task_id}, caller_agent_id={caller_agent_id}"
                    )
            except Exception as e:
                self._logger.error(
                    f"[KA-Agent] ❌ 權限檢查失敗: task_id={task_id}, error={str(e)}", exc_info=True
                )

        user_id = str(raw_req.metadata.get("user_id", "unknown") if raw_req.metadata else "unknown")
        resource = {
            "action": "knowledge_query",
            "query": req.query,
            "resource_type": "knowledge_asset",
        }

        # 檢索安全審計（規格 Ch 7.6, 13.5）
        self._logger.debug(
            f"[KA-Agent] 🔐 權限檢查: task_id={task_id}, user_id={user_id}, action=knowledge_query"
        )

        allowed = self._policy.check_permission(
            user_id=user_id, action="knowledge_query", resource=resource
        )
        if not allowed:
            self._logger.warning(
                f"[KA-Agent] ⚠️ 權限檢查失敗: task_id={task_id}, user_id={user_id}, "
                f"query={req.query}"
            )

            # 修改時間：2026-01-28 - 使用用戶友好的錯誤反饋
            feedback = self._error_handler.permission_denied(
                user_id=user_id,
                action="知識庫查詢",
                resource="知識資產",
                reason="您的帳戶權限不足以執行此操作",
            )

            audit = _get_audit_log_service()
            from services.api.models.audit_log import AuditAction, AuditLogCreate

            audit.log(
                AuditLogCreate(
                    user_id=user_id,
                    action=AuditAction.ACCESS_DENIED,
                    resource_type="knowledge_asset",
                    resource_id=None,
                    ip_address="127.0.0.1",
                    user_agent="KA-Agent",
                    details={
                        "query": req.query,
                        "reason": "permission_denied",
                        "feedback": feedback.model_dump(),
                    },
                ),
                async_mode=True,
            )

            formatted_feedback = self._error_handler.format_feedback_for_llm(feedback)

            return KAResponse(
                success=False,
                message=formatted_feedback,  # 用戶友好的錯誤消息
                results=[],
                total=0,
                metadata={"feedback": feedback.model_dump()},
            )

        # Domain / Major 過濾（規格 Ch 8.3）
        # KA-Agent 為知識管理員：對所有已上架知識文件有權限，不因 user/task 限縮（caller_is_ka_agent=True）
        meta_svc = _get_file_metadata_service()
        ka_files = meta_svc.list(
            knw_code_not_null=True,
            domain=req.domain,
            major=req.major,
            limit=500,
            caller_is_ka_agent=True,
        )
        file_ids = [f.file_id for f in ka_files]

        self._logger.info(
            f"[KA-Agent] 📊 文件過濾結果: task_id={task_id}, "
            f"total_files={len(ka_files)}, domain={req.domain}, major={req.major}"
        )

        vector_results: List[Dict[str, Any]] = []
        graph_results: List[KAResult] = []

        if req.query and file_ids:
            emb_svc, vec_svc = _get_embedding_and_vector_services()
            q_emb = await emb_svc.generate_embedding(text=req.query or "")
            for fid in file_ids[:50]:  # 限制並發
                hits = vec_svc.query_vectors(
                    query_embedding=q_emb,
                    file_id=fid,
                    limit=min(5, req.top_k),
                )
                for h in hits:
                    h["file_id"] = fid
                    vector_results.append(h)

        if req.query_type in ["graph", "hybrid"]:
            sub_request = AgentServiceRequest(
                task_id=f"{raw_req.task_id}_sub",
                task_type="graph_query",
                task_data={"action": "entity_retrieval", "entity_name": req.query},
                metadata={},
            )
            graph_resp = await self._ko_agent.execute(sub_request)
            if graph_resp.status == "completed":
                graph_results.append(
                    KAResult(
                        content=str(graph_resp.result),
                        ka_id="GLOBAL",
                        version="1.0",
                        confidence_hint=0.85,
                        source="graph",
                    )
                )

        # 重排序結果
        rerank_start_time = time.time()
        self._logger.info(
            f"[KA-Agent] 🔄 開始重排序: task_id={task_id}, "
            f"vector_results_count={len(vector_results)}, "
            f"graph_results_count={len(graph_results)}, "
            f"query_type={req.query_type}, top_k={req.top_k}"
        )

        results = self._rerank_results(
            vector_results=vector_results,
            graph_results=graph_results,
            query_type=req.query_type,
            top_k=req.top_k,
        )

        rerank_latency_ms = int((time.time() - rerank_start_time) * 1000)
        retrieval_total_latency_ms = int((time.time() - retrieval_start_time) * 1000)

        self._logger.info(
            f"[KA-Agent] ✅ 檢索流程完成: task_id={task_id}, "
            f"final_results_count={len(results)}, rerank_latency_ms={rerank_latency_ms}, "
            f"retrieval_total_latency_ms={retrieval_total_latency_ms}"
        )

        # 修改時間：2026-01-28 - 添加空結果的用戶友好反饋
        if len(results) == 0:
            self._logger.info(f"[KA-Agent] 📭 查詢結果為空: task_id={task_id}, query={req.query}")

            feedback = self._error_handler.empty_result(
                query=req.query or "",
                search_scope=f"domain={req.domain or '全部'}, major={req.major or '全部'}",
            )

            formatted_feedback = self._error_handler.format_feedback_for_llm(feedback)

            return KAResponse(
                success=True,  # 不是錯誤，只是結果為空
                message=formatted_feedback,
                results=[],
                total=0,
                query_time_ms=retrieval_total_latency_ms,
                metadata={
                    "feedback": feedback.model_dump(),
                    "file_count": len(file_ids),
                    "vector_results_count": len(vector_results),
                    "graph_results_count": len(graph_results),
                },
            )

        return KAResponse(
            success=True,
            message="檢索完成",
            results=results,
            total=len(results),
            query_time_ms=retrieval_total_latency_ms,
            metadata={
                "file_count": len(file_ids),
                "vector_results_count": len(vector_results),
                "graph_results_count": len(graph_results),
            },
        )

    def _rerank_results(
        self,
        vector_results: List[Dict[str, Any]],
        graph_results: List[KAResult],
        query_type: str,
        top_k: int,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4,
    ) -> List[KAResult]:
        """混合檢索重排：向量與圖譜權重融合（規格 Ch 7.6, 10.1）"""
        out: List[KAResult] = []
        seen: set = set()

        def _vec_to_result(h: Dict[str, Any]) -> Optional[KAResult]:
            payload = h.get("payload") or {}
            text = payload.get("chunk_text") or payload.get("text") or str(payload)
            key = (h.get("file_id"), text[:80])
            if key in seen:
                return None
            seen.add(key)
            return KAResult(
                content=text,
                ka_id=payload.get("ka_id") or h.get("file_id") or "UNKNOWN",
                version=payload.get("version") or "1.0",
                confidence_hint=float(h.get("score") or 0.0),
                source="vector",
            )

        vec_converted = []
        for h in vector_results:
            r = _vec_to_result(h)
            if r is not None:
                vec_converted.append((r, float(h.get("score") or 0.0)))

        for g in graph_results:
            out.append(g)

        vec_converted.sort(key=lambda x: x[1], reverse=True)
        for r, _ in vec_converted[: max(0, top_k - len(out))]:
            out.append(r)

        return out[:top_k]

    def _generate_default_todo_list(self) -> List[Dict[str, Any]]:
        return [
            {"id": i, "desc": d, "status": "pending"}
            for i, d in enumerate(["環境檢查", "知識處理", "資產註冊", "數據提交"], 1)
        ]

    async def health_check(self) -> AgentServiceStatus:
        return AgentServiceStatus.AVAILABLE

    async def get_capabilities(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,  # 修改時間：2026-01-28 - 使用 agent_id 屬性
            "capabilities": ["knowledge.query", "ka.lifecycle", "ka.list", "ka.retrieve"],
        }
