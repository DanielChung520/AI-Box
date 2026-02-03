# 代碼功能說明: 内建 Agent 模組
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""内建 Agent 模組

提供 AI-Box 核心内建 Agent：
- Document Editing Agent: 文件編輯服務
- Registry Manager: 注册管理员
- Security Manager: 安全管理员
- Orchestrator Manager: 协调管理员
- Storage Manager: 数据存储员
- System Config Agent: 系统配置代理

这些 Agent 是 AI 驱动的任务导向服务，需要注册到 Registry 以便被 Agent Discovery 發現。
"""

import logging
from typing import Dict, Optional

from agents.services.protocol.base import AgentServiceProtocol
from agents.services.registry.registry import get_agent_registry
from services.api.services.system_agent_registry_store_service import (
    get_system_agent_registry_store_service,
)

from .document_editing.agent import DocumentEditingAgent
from .orchestrator_manager.agent import OrchestratorManagerAgent
from .registry_manager.agent import RegistryManagerAgent
from .security_manager.agent import SecurityManagerAgent
from .storage_manager.agent import StorageManagerAgent
from .system_config_agent.agent import SystemConfigAgent

logger = logging.getLogger(__name__)

__all__ = [
    "DocumentEditingAgent",
    "RegistryManagerAgent",
    "SecurityManagerAgent",
    "OrchestratorManagerAgent",
    "StorageManagerAgent",
    "SystemConfigAgent",
    "initialize_builtin_agents",
    "register_builtin_agents",
    "get_builtin_agent",
]

# 全局内建 Agent 实例字典
_builtin_agents: Dict[str, AgentServiceProtocol] = {}


def initialize_builtin_agents() -> Dict[str, AgentServiceProtocol]:
    """
    初始化所有内建 Agent

    Returns:
        内建 Agent 实例字典
    """
    global _builtin_agents

    if _builtin_agents:
        # 已经初始化，直接返回
        return _builtin_agents

    # 初始化各个内建 Agent（單個失敗不影響其他）
    # Document Editing Agent（優先，測試重點）
    try:
        _builtin_agents["document_editing"] = DocumentEditingAgent()
        logger.info("Document Editing Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Document Editing Agent: {e}", exc_info=True)

    # 其他 Agent（允許失敗，不影響 Document Editing Agent）
    try:
        _builtin_agents["registry_manager"] = RegistryManagerAgent()
    except Exception as e:
        logger.warning(f"Failed to initialize Registry Manager Agent: {e}", exc_info=True)

    try:
        _builtin_agents["security_manager"] = SecurityManagerAgent()
    except Exception as e:
        logger.warning(f"Failed to initialize Security Manager Agent: {e}", exc_info=True)

    try:
        _builtin_agents["orchestrator_manager"] = OrchestratorManagerAgent()
    except Exception as e:
        logger.warning(f"Failed to initialize Orchestrator Manager Agent: {e}", exc_info=True)

    try:
        _builtin_agents["storage_manager"] = StorageManagerAgent()
    except Exception as e:
        logger.warning(f"Failed to initialize Storage Manager Agent: {e}", exc_info=True)

    try:
        _builtin_agents["system_config"] = SystemConfigAgent()
    except Exception as e:
        logger.warning(f"Failed to initialize System Config Agent: {e}", exc_info=True)

    # Document Editing Agent v2.0 (md-editor)
    try:
        from .document_editing_v2.agent import DocumentEditingAgentV2

        _builtin_agents["md_editor"] = DocumentEditingAgentV2()
        logger.info("Document Editing Agent v2.0 (md-editor) initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Document Editing Agent v2.0: {e}", exc_info=True)

    # Excel Editor Agent (xls-editor)
    try:
        from .xls_editor.agent import XlsEditingAgent

        _builtin_agents["xls_editor"] = XlsEditingAgent()
        logger.info("Excel Editor Agent (xls-editor) initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Excel Editor Agent: {e}", exc_info=True)

    # Markdown to PDF Agent (md-to-pdf)
    try:
        from .md_to_pdf.agent import MdToPdfAgent

        _builtin_agents["md_to_pdf"] = MdToPdfAgent()
        logger.info("Markdown to PDF Agent (md-to-pdf) initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Markdown to PDF Agent: {e}", exc_info=True)

    # Excel to PDF Agent (xls-to-pdf)
    try:
        from .xls_to_pdf.agent import XlsToPdfAgent

        _builtin_agents["xls_to_pdf"] = XlsToPdfAgent()
        logger.info("Excel to PDF Agent (xls-to-pdf) initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Excel to PDF Agent: {e}", exc_info=True)

    # PDF to Markdown Agent (pdf-to-md)
    try:
        from .pdf_to_md.agent import PdfToMdAgent

        _builtin_agents["pdf_to_md"] = PdfToMdAgent()
        logger.info("PDF to Markdown Agent (pdf-to-md) initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize PDF to Markdown Agent: {e}", exc_info=True)

    # Knowledge Architect Agent (ka-agent)
    try:
        from .ka_agent.agent import KnowledgeArchitectAgent

        _builtin_agents["ka_agent"] = KnowledgeArchitectAgent()
        logger.info("Knowledge Architect Agent initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Knowledge Architect Agent: {e}", exc_info=True)

    logger.info(
        f"Initialized {len(_builtin_agents)} builtin agents: {list(_builtin_agents.keys())}"
    )
    return _builtin_agents


def _register_agent_helper(
    agent_key: str,
    agent_id: str,
    agent_type: str,
    name: str,
    description: str,
    default_capabilities: list,
    version: str,
    category: str,
    registry,
    system_agent_store,
    agents_dict: dict,
):
    """注册 Agent 的辅助函数"""
    agent = agents_dict.get(agent_key)
    # 修改時間：2026-01-28 - 支持沒有 agent_id 屬性的 Agent（使用傳入的 agent_id）
    # 修改時間：2026-01-28 - 添加實例檢查和驗證日誌
    if not agent:
        logger.error(
            f"Agent '{agent_key}' not found in agents_dict. Cannot register {agent_id} ({name})."
        )
        return

    logger.info(
        f"Registering {name} ({agent_id}) with instance: {type(agent).__name__}"
    )

    if agent:
        try:
            capabilities = default_capabilities.copy()
            if hasattr(agent, "get_capabilities"):
                try:
                    import asyncio
                    import inspect

                    if inspect.iscoroutinefunction(agent.get_capabilities):
                        try:
                            loop = asyncio.get_event_loop()
                            if not loop.is_running():
                                caps = asyncio.run(agent.get_capabilities())
                                if isinstance(caps, dict) and "capabilities" in caps:
                                    capabilities = caps.get("capabilities", capabilities)
                        except RuntimeError:
                            pass
                    else:
                        caps = agent.get_capabilities()
                        if isinstance(caps, dict) and "capabilities" in caps:
                            capabilities = caps.get("capabilities", capabilities)
                except Exception as e:
                    logger.warning(
                        f"Failed to get capabilities for {agent_id}: {e}",
                        exc_info=True,
                    )

            # 注册到 System Agent Registry
            system_agent_store.register_system_agent(
                agent_id=agent_id,
                agent_type=agent_type,
                name=name,
                description=description,
                capabilities=capabilities,
                version=version,
                metadata={
                    "is_system_agent": True,
                    "is_internal": True,
                    "category": category,
                },
            )
            logger.info(f"{name} ({agent_id}) registered to System Agent Registry (ArangoDB)")

            # 注册到 Agent Registry
            from agents.services.protocol.base import AgentServiceProtocolType
            from agents.services.registry.models import (
                AgentEndpoints,
                AgentMetadata,
                AgentPermissionConfig,
                AgentRegistrationRequest,
                AgentStatus,
            )

            request = AgentRegistrationRequest(
                agent_id=agent_id,
                agent_type=agent_type,
                name=name,
                endpoints=AgentEndpoints(
                    http=None,
                    mcp=None,
                    protocol=AgentServiceProtocolType.HTTP,
                    is_internal=True,
                ),
                capabilities=capabilities,
                metadata=AgentMetadata(
                    version=version,
                    description=description,
                    author="AI-Box Team",
                    tags=[agent_type, "builtin", "v2.0"],
                ),
                permissions=AgentPermissionConfig(),
            )

            success = registry.register_agent(request, instance=agent)
            if success:
                agent_info = registry.get_agent_info(agent_id)
                if agent_info:
                    agent_info.status = AgentStatus.ONLINE
                    logger.info(f"{name} ({agent_id}) registered successfully (status: ONLINE)")

                    # 驗證實例是否被存儲
                    stored_instance = registry.get_agent(agent_id)
                    if stored_instance:
                        logger.info(
                            f"✅ {name} ({agent_id}) instance stored successfully: "
                            f"{type(stored_instance).__name__}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ {name} ({agent_id}) registered but instance not found in registry. "
                            f"This may cause 'instance not found' errors."
                        )
                else:
                    logger.warning(f"{name} ({agent_id}) registered but not found in registry")
            else:
                logger.error(f"Failed to register {name} ({agent_id})")
        except Exception as e:
            logger.warning(f"Failed to register {name}: {e}", exc_info=True)


def _do_register_all_agents(
    agents_dict: Optional[Dict[str, AgentServiceProtocol]] = None,
) -> Dict[str, AgentServiceProtocol]:
    """
    實際執行所有 Agent 註冊邏輯的內部函數

    Args:
        agents_dict: Agent 實例字典（如果為 None，使用全局 _builtin_agents）

    Returns:
        內建 Agent 實例字典
    """
    global _builtin_agents

    if agents_dict is None:
        agents_dict = _builtin_agents

    if not agents_dict:
        # 如果未初始化，先初始化
        initialize_builtin_agents()
        agents_dict = _builtin_agents
    else:
        # 如果傳入了 agents_dict，使用它
        _builtin_agents = agents_dict

    registry = get_agent_registry()  # 初始化 registry

    # 導入需要的類（用於 Agent 註冊）
    from agents.services.protocol.base import AgentServiceProtocolType
    from agents.services.registry.models import (
        AgentEndpoints,
        AgentMetadata,
        AgentPermissionConfig,
        AgentRegistrationRequest,
        AgentStatus,
    )

    # 註冊 Document Editing Agent
    document_editing_agent = agents_dict.get("document_editing")
    if document_editing_agent and hasattr(document_editing_agent, "agent_id"):
        # 使用 agent 實例的 agent_id（"document-editing-agent"），而不是字典的 key
        agent_id = document_editing_agent.agent_id
        # 獲取 agent 的能力描述（如果有）
        capabilities = [
            "document_editing",
            "file_editing",
            "markdown_editing",
            "streaming_editing",
            "execution",
            "action",
        ]
        # 嘗試獲取 agent 的能力描述（如果可用且是同步方法）
        if hasattr(document_editing_agent, "get_capabilities"):
            try:
                import inspect

                # 檢查是否是協程函數
                if inspect.iscoroutinefunction(document_editing_agent.get_capabilities):
                    # 如果是異步方法，嘗試使用當前事件循環（如果存在）
                    try:
                        import asyncio

                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # 如果事件循環正在運行，使用默認能力
                            logger.debug(
                                f"Event loop is running, using default capabilities for {agent_id}"
                            )
                        else:
                            # 如果事件循環未運行，可以使用 asyncio.run
                            caps = asyncio.run(document_editing_agent.get_capabilities())
                            if isinstance(caps, dict) and "capabilities" in caps:
                                capabilities = caps.get("capabilities", capabilities)
                    except RuntimeError:
                        # 無法獲取事件循環，使用默認能力
                        logger.debug(
                            f"Failed to get event loop, using default capabilities for {agent_id}"
                        )
                else:
                    # 同步方法，直接調用
                    caps = document_editing_agent.get_capabilities()
                    if isinstance(caps, dict) and "capabilities" in caps:
                        capabilities = caps.get("capabilities", capabilities)
            except Exception as e:
                logger.warning(
                    f"Failed to get capabilities for {agent_id}: {e}, using default capabilities"
                )

        # 先註冊到 System Agent Registry（ArangoDB），確保 System Agent 標記正確
        # ⚠️ 注意：document-editing-agent 已標記為 inactive，因為不夠精確，應使用更具體的 md-editor
        try:
            system_agent_store = get_system_agent_registry_store_service()
            # 先註冊，然後更新為 inactive
            system_agent_store.register_system_agent(
                agent_id=agent_id,
                agent_type="document_editing",
                name="Document Editing Agent",
                description="文件編輯服務，支持 Markdown 文件的 AI 驅動編輯（已停用，請使用 md-editor）",
                capabilities=(
                    capabilities
                    if capabilities
                    else [
                        "document_editing",
                        "file_editing",
                        "markdown_editing",
                        "streaming_editing",
                        "execution",
                        "action",
                    ]
                ),
                version="1.0.0",
                metadata={
                    "is_system_agent": True,
                    "is_internal": True,
                    "category": "system_support",
                    "deprecated": True,
                    "replacement": "md-editor",
                    "reason": "不夠精確，應使用更具體的 md-editor",
                },
            )
            # 更新為 inactive 和 offline
            system_agent_store.update_system_agent(
                agent_id=agent_id,
                status="offline",  # 標記為 offline，避免被調用
                is_active=False,  # 標記為 inactive
            )
            logger.info(
                f"Document Editing Agent ({agent_id}) registered to System Agent Registry (ArangoDB)"
            )
        except Exception as e:
            logger.warning(
                f"Failed to register Document Editing Agent ({agent_id}) to System Agent Registry: {e}",
                exc_info=True,
            )

        # 然後註冊到 Agent Registry（內存），此時會自動檢查 System Agent Registry 標記為 is_system_agent=True
        document_editing_request = AgentRegistrationRequest(
            agent_id=agent_id,  # 使用 "document-editing-agent"
            agent_type="document_editing",
            name="Document Editing Agent",
            endpoints=AgentEndpoints(
                http=None,
                mcp=None,
                protocol=AgentServiceProtocolType.HTTP,
                is_internal=True,  # 標記為內部 Agent
            ),
            capabilities=(
                capabilities
                if capabilities
                else [
                    "document_editing",
                    "file_editing",
                    "markdown_editing",
                    "streaming_editing",
                    "execution",
                    "action",
                ]
            ),
            metadata=AgentMetadata(
                version="1.0.0",
                description="文件編輯服務，支持 Markdown 文件的 AI 驅動編輯",
                author="AI-Box Team",
                tags=["document_editing", "file_editing", "builtin"],
            ),  # type: ignore[call-arg]  # icon 有默認值
            permissions=AgentPermissionConfig(),  # type: ignore[call-arg]  # 所有參數都有默認值
        )

        success = registry.register_agent(document_editing_request, instance=document_editing_agent)
        if success:
            # 確保 Agent 狀態為 ONLINE（內部 Agent 應該自動在線）
            agent_info = registry.get_agent_info(agent_id)
            if agent_info:
                # 內部 Agent 應該直接設置為 ONLINE
                agent_info.status = AgentStatus.ONLINE  # type: ignore[assignment]
                logger.info(
                    f"Document Editing Agent ({agent_id}) registered successfully (status: ONLINE)"
                )
            else:
                logger.warning(
                    f"Document Editing Agent ({agent_id}) registered but not found in registry"
                )
        else:
            logger.error(f"Failed to register Document Editing Agent ({agent_id})")

    # 註冊其他 System Agents（安全審計 Agent、Report Agent 等）
    # Security Manager Agent (安全審計 Agent)
    security_manager_agent = agents_dict.get("security_manager")
    if security_manager_agent:
        security_agent_id = "security-manager-agent"  # 使用標準命名格式
        try:
            # 註冊到 Agent Registry（內存）
            security_request = AgentRegistrationRequest(
                agent_id=security_agent_id,
                agent_type="security_audit",
                name="Security Manager Agent",
                endpoints=AgentEndpoints(
                    http=None,
                    mcp=None,
                    protocol=AgentServiceProtocolType.HTTP,
                    is_internal=True,  # 標記為內部 Agent
                ),
                capabilities=["security_audit", "risk_assessment", "permission_check"],
                metadata=AgentMetadata(
                    version="1.0.0",
                    description="安全審計和管理服務，提供智能風險評估、權限檢查和驗證",
                    author="AI-Box Team",
                    tags=["security", "audit", "builtin"],
                ),  # type: ignore[call-arg]  # icon 有默認值
                permissions=AgentPermissionConfig(),  # type: ignore[call-arg]  # 所有參數都有默認值
            )
            # 先註冊到 System Agent Registry（ArangoDB）
            system_agent_store = get_system_agent_registry_store_service()
            system_agent_store.register_system_agent(
                agent_id=security_agent_id,
                agent_type="security_audit",
                name="Security Manager Agent",
                description="安全審計和管理服務，提供智能風險評估、權限檢查和驗證",
                capabilities=["security_audit", "risk_assessment", "permission_check"],
                version="1.0.0",
                metadata={
                    "is_system_agent": True,
                    "is_internal": True,
                    "category": "system_support",
                },
            )
            logger.info(
                f"Security Manager Agent ({security_agent_id}) registered to System Agent Registry (ArangoDB)"
            )

            # 然後註冊到 Agent Registry（內存），此時會自動檢查 System Agent Registry 標記為 is_system_agent=True
            registry.register_agent(security_request, instance=security_manager_agent)
            logger.info(
                f"Security Manager Agent ({security_agent_id}) registered to Agent Registry"
            )
        except Exception as e:
            logger.warning(f"Failed to register Security Manager Agent: {e}", exc_info=True)

    # Document Editing Agent v2.0 (md-editor)
    try:
        from .document_editing_v2.agent import DocumentEditingAgentV2  # noqa: F401
    except ImportError:
        pass

    md_editor_agent = agents_dict.get("md_editor")
    if md_editor_agent and hasattr(md_editor_agent, "agent_id"):
        md_editor_id = md_editor_agent.agent_id  # "md-editor"
        try:
            capabilities = [
                "document_editing",
                "markdown_editing",
                "structured_editing",
                "block_patch",
                "execution",
                "action",
            ]
            if hasattr(md_editor_agent, "get_capabilities"):
                try:
                    import inspect

                    if inspect.iscoroutinefunction(md_editor_agent.get_capabilities):
                        try:
                            import asyncio

                            loop = asyncio.get_event_loop()
                            if not loop.is_running():
                                caps = asyncio.run(md_editor_agent.get_capabilities())
                                if isinstance(caps, dict) and "capabilities" in caps:
                                    capabilities = caps.get("capabilities", capabilities)
                        except RuntimeError:
                            pass
                    else:
                        caps = md_editor_agent.get_capabilities()
                        if isinstance(caps, dict) and "capabilities" in caps:
                            capabilities = caps.get("capabilities", capabilities)
                except Exception as e:
                    logger.warning(
                        f"Failed to get capabilities for {md_editor_id}: {e}",
                        exc_info=True,
                    )

            # 先註冊到 System Agent Registry（ArangoDB）
            system_agent_store = get_system_agent_registry_store_service()
            system_agent_store.register_system_agent(
                agent_id=md_editor_id,
                agent_type="document_editing",
                name="Markdown Editor Agent (v2.0)",
                description="基於 Intent DSL 和 Block Patch 的結構化 Markdown 文件編輯服務",
                capabilities=capabilities,
                version="2.0.0",
                metadata={
                    "is_system_agent": True,
                    "is_internal": True,
                    "category": "document_editing",
                },
            )
            logger.info(
                f"Markdown Editor Agent v2.0 ({md_editor_id}) registered to System Agent Registry (ArangoDB)"
            )

            # 然後註冊到 Agent Registry（內存）
            md_editor_request = AgentRegistrationRequest(
                agent_id=md_editor_id,
                agent_type="document_editing",
                name="Markdown Editor Agent (v2.0)",
                endpoints=AgentEndpoints(
                    http=None,
                    mcp=None,
                    protocol=AgentServiceProtocolType.HTTP,
                    is_internal=True,
                ),
                capabilities=capabilities,
                metadata=AgentMetadata(
                    version="2.0.0",
                    description="基於 Intent DSL 和 Block Patch 的結構化 Markdown 文件編輯服務",
                    author="AI-Box Team",
                    tags=["document_editing", "markdown_editing", "builtin", "v2.0"],
                ),
                permissions=AgentPermissionConfig(),
            )

            success = registry.register_agent(md_editor_request, instance=md_editor_agent)
            if success:
                agent_info = registry.get_agent_info(md_editor_id)
                if agent_info:
                    from agents.services.registry.models import AgentStatus

                    agent_info.status = AgentStatus.ONLINE
                    logger.info(
                        f"Markdown Editor Agent v2.0 ({md_editor_id}) registered successfully (status: ONLINE)"
                    )
                else:
                    logger.warning(
                        f"Markdown Editor Agent v2.0 ({md_editor_id}) registered but not found in registry"
                    )
            else:
                logger.error(f"Failed to register Markdown Editor Agent v2.0 ({md_editor_id})")
        except Exception as e:
            logger.warning(f"Failed to register Markdown Editor Agent v2.0: {e}", exc_info=True)

    # Excel Editor Agent (xls-editor)
    _register_agent_helper(
        agent_key="xls_editor",
        agent_id="xls-editor",
        agent_type="document_editing",
        name="Excel Editor Agent (v2.0)",
        description="基於 Intent DSL 和 Structured Patch 的結構化 Excel 文件編輯服務",
        default_capabilities=[
            "document_editing",
            "excel_editing",
            "structured_editing",
            "structured_patch",
        ],
        version="2.0.0",
        category="document_editing",
        registry=registry,
        system_agent_store=get_system_agent_registry_store_service(),
        agents_dict=_builtin_agents,
    )

    # Markdown to PDF Agent (md-to-pdf)
    _register_agent_helper(
        agent_key="md_to_pdf",
        agent_id="md-to-pdf",
        agent_type="document_conversion",
        name="Markdown to PDF Agent (v2.0)",
        description="將 Markdown 文件轉換為 PDF 文件",
        default_capabilities=[
            "document_conversion",
            "markdown_to_pdf",
            "pdf_generation",
        ],
        version="2.0.0",
        category="document_conversion",
        registry=registry,
        system_agent_store=get_system_agent_registry_store_service(),
        agents_dict=_builtin_agents,
    )

    # Excel to PDF Agent (xls-to-pdf)
    _register_agent_helper(
        agent_key="xls_to_pdf",
        agent_id="xls-to-pdf",
        agent_type="document_conversion",
        name="Excel to PDF Agent (v2.0)",
        description="將 Excel 文件轉換為 PDF 文件",
        default_capabilities=[
            "document_conversion",
            "excel_to_pdf",
            "pdf_generation",
        ],
        version="2.0.0",
        category="document_conversion",
        registry=registry,
        system_agent_store=get_system_agent_registry_store_service(),
        agents_dict=_builtin_agents,
    )

    # PDF to Markdown Agent (pdf-to-md)
    _register_agent_helper(
        agent_key="pdf_to_md",
        agent_id="pdf-to-md",
        agent_type="document_conversion",
        name="PDF to Markdown Agent (v2.0)",
        description="將 PDF 文件轉換為 Markdown 文件",
        default_capabilities=[
            "document_conversion",
            "pdf_to_markdown",
            "text_extraction",
        ],
        version="2.0.0",
        category="document_conversion",
        registry=registry,
        system_agent_store=get_system_agent_registry_store_service(),
        agents_dict=_builtin_agents,
    )

    # Knowledge Architect Agent (ka-agent)
    # 修改時間：2026-01-28 - 添加診斷日誌
    ka_agent = agents_dict.get("ka_agent")
    if ka_agent:
        logger.info(
            f"✅ KA-Agent instance found: {type(ka_agent).__name__}, "
            f"agent_id={ka_agent.agent_id if hasattr(ka_agent, 'agent_id') else 'N/A'}"
        )
    else:
        logger.error("❌ KA-Agent instance not found in agents_dict!")

    _register_agent_helper(
        agent_key="ka_agent",
        agent_id="ka-agent",
        agent_type="knowledge_service",
        name="Knowledge Architect Agent (v1.5)",
        description="知識資產總建築師，負責知識資產化、生命週期管理與混合檢索",
        default_capabilities=[
            "knowledge.query",
            "ka.lifecycle",
            "ka.list",
            "ka.retrieve",
        ],
        version="1.5.0",
        category="knowledge_service",
        registry=registry,
        system_agent_store=get_system_agent_registry_store_service(),
        agents_dict=_builtin_agents,
    )

    # Report Agent（未來添加）
    # 當 Report Agent 實現後，可以在這裡註冊
    # report_agent = agents_dict.get("report_agent")
    # if report_agent:
    #     report_agent_id = "report-agent"
    #     # 註冊邏輯...

    return _builtin_agents


def register_builtin_agents() -> Dict[str, AgentServiceProtocol]:
    """
    註冊所有內建 Agent 到 Registry

    Returns:
        內建 Agent 實例字典
    """
    global _builtin_agents

    if not _builtin_agents:
        # 如果未初始化，先初始化
        initialize_builtin_agents()

    # 調用實際的註冊邏輯
    return _do_register_all_agents()


def get_builtin_agent(agent_id: str) -> Optional[AgentServiceProtocol]:
    """
    獲取內建 Agent 實例

    Args:
        agent_id: Agent ID（document_editing, registry_manager, security_manager, orchestrator_manager, storage_manager, system_config）
                  注意：字典的 key 是下劃線格式，但 Agent 實例的 agent_id 可能是連字符格式

    Returns:
        內建 Agent 實例，如果不存在返回 None
    """
    if not _builtin_agents:
        # 如果未初始化，先初始化
        initialize_builtin_agents()

    # 先嘗試直接使用 agent_id 作為 key
    if agent_id in _builtin_agents:
        return _builtin_agents[agent_id]

    # 如果找不到，嘗試查找所有 agent 實例，使用它們的 agent_id 屬性
    for key, agent in _builtin_agents.items():
        if hasattr(agent, "agent_id") and agent.agent_id == agent_id:
            return agent

    return None

    # Excel Editor Agent (xls-editor)
    try:
        from .xls_editor.agent import XlsEditingAgent

        _builtin_agents["xls_editor"] = XlsEditingAgent()
        logger.info("Excel Editor Agent (xls-editor) initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Excel Editor Agent: {e}", exc_info=True)

    # Markdown to PDF Agent (md-to-pdf)
    try:
        from .md_to_pdf.agent import MdToPdfAgent

        _builtin_agents["md_to_pdf"] = MdToPdfAgent()
        logger.info("Markdown to PDF Agent (md-to-pdf) initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Markdown to PDF Agent: {e}", exc_info=True)

    # Excel to PDF Agent (xls-to-pdf)
    try:
        from .xls_to_pdf.agent import XlsToPdfAgent

        _builtin_agents["xls_to_pdf"] = XlsToPdfAgent()
        logger.info("Excel to PDF Agent (xls-to-pdf) initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Excel to PDF Agent: {e}", exc_info=True)

    # PDF to Markdown Agent (pdf-to-md)
    try:
        from .pdf_to_md.agent import PdfToMdAgent

        _builtin_agents["pdf_to_md"] = PdfToMdAgent()
        logger.info("PDF to Markdown Agent (pdf-to-md) initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize PDF to Markdown Agent: {e}", exc_info=True)
