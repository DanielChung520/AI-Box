# 代碼功能說明: Execution Agent MCP Server 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""Execution Agent MCP Server"""


import structlog

from agents.core.execution.agent import ExecutionAgent
from agents.core.execution.models import ExecutionRequest
from mcp.server.server import MCPServer

logger = structlog.get_logger(__name__)

# 初始化 Execution Agent
execution_agent = ExecutionAgent()

# 創建 MCP Server
mcp_server = MCPServer(
    name="execution-agent",
    version="1.0.0",
)


# 註冊工具：執行任務
async def execute_task_handler(arguments: dict) -> dict:
    """執行任務工具處理器"""
    request = ExecutionRequest(**arguments)
    result = execution_agent.execute_task(request)  # 使用 execute_task 方法
    return result.model_dump()


mcp_server.register_tool(
    name="execute_task",
    description="執行任務或工具調用",
    input_schema={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "任務描述",
            },
            "tool_name": {
                "type": "string",
                "description": "工具名稱（可選）",
            },
            "tool_args": {
                "type": "object",
                "description": "工具參數（可選）",
            },
            "plan_step_id": {
                "type": "string",
                "description": "計劃步驟ID（可選）",
            },
            "context": {
                "type": "object",
                "description": "上下文信息（可選）",
            },
        },
        "required": ["task"],
    },
    handler=execute_task_handler,
)


# 註冊工具：生成並應用文檔編輯（Agent 編輯指令交互）
async def generate_and_edit_document_handler(arguments: dict) -> dict:
    """
    生成並應用文檔編輯工具處理器
    根據用戶指令生成 patches 並應用到文件

    Args:
        arguments: 包含 file_id、instruction 等參數的字典

    Returns:
        編輯結果字典
    """
    try:
        from agents.core.execution.document_editing_service import DocumentEditingService
        from services.api.services.doc_patch_service import apply_search_replace_patches
        from services.api.services.file_metadata_service import FileMetadataService
        from storage.file_storage import create_storage_from_config
        from system.infra.config.config import get_config_section

        file_id = arguments.get("file_id")
        instruction = arguments.get("instruction")
        doc_format = arguments.get("doc_format", "md")
        cursor_position = arguments.get("cursor_position")

        if not file_id:
            return {
                "success": False,
                "error": "file_id is required",
            }

        if not instruction:
            return {
                "success": False,
                "error": "instruction is required",
            }

        # 獲取文件內容
        config = get_config_section("file_upload", default={}) or {}
        storage = create_storage_from_config(config)
        metadata_service = FileMetadataService()
        file_metadata = metadata_service.get(file_id)
        if not file_metadata or not file_metadata.storage_path:
            return {
                "success": False,
                "error": f"File not found: {file_id}",
            }

        # 讀取原始文件內容
        original_content = storage.read(file_metadata.storage_path)
        if original_content is None:
            return {
                "success": False,
                "error": f"Failed to read file: {file_metadata.storage_path}",
            }

        file_content = original_content.decode("utf-8")

        # 使用 DocumentEditingService 生成 patches
        editing_service = DocumentEditingService()
        patch_kind, patch_payload, summary = await editing_service.generate_editing_patches(
            instruction=instruction,
            file_content=file_content,
            doc_format=doc_format,
            cursor_position=cursor_position,
        )

        # 轉換為 Search-and-Replace patches（如果需要）
        if patch_kind == "search_replace":
            patches = editing_service.convert_to_search_replace_patches(patch_kind, patch_payload)
        else:
            # 對於其他格式，目前不支持自動轉換
            # 可以後續實現 unified_diff 到 search_replace 的轉換
            return {
                "success": False,
                "error": f"Unsupported patch format: {patch_kind}. Only search_replace is supported.",
            }

        if not patches:
            return {
                "success": False,
                "error": "Failed to generate patches from instruction",
            }

        # 應用 Search-and-Replace patches
        modified_content = apply_search_replace_patches(
            original=file_content,
            patches=patches,
            cursor_position=cursor_position,
        )

        logger.info(
            "Document edited successfully via generate_and_edit_document",
            file_id=file_id,
            patch_count=len(patches),
            summary=summary[:100] if summary else "",
        )

        return {
            "success": True,
            "file_id": file_id,
            "modified_content": modified_content,
            "patches_applied": len(patches),
            "summary": summary,
            "patch_kind": patch_kind,
        }

    except Exception as e:
        logger.error(f"generate_and_edit_document failed: {e}", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


mcp_server.register_tool(
    name="generate_and_edit_document",
    description="根據用戶指令生成並應用文檔編輯 patches（Agent 編輯指令交互）",
    input_schema={
        "type": "object",
        "properties": {
            "file_id": {
                "type": "string",
                "description": "文件 ID",
            },
            "instruction": {
                "type": "string",
                "description": "用戶的編輯指令（自然語言）",
            },
            "doc_format": {
                "type": "string",
                "description": "文檔格式（md/txt/json）",
                "default": "md",
            },
            "cursor_position": {
                "type": "integer",
                "description": "游標位置（可選，用於上下文匹配）",
            },
        },
        "required": ["file_id", "instruction"],
    },
    handler=generate_and_edit_document_handler,
)


# 註冊工具：文檔編輯（直接應用 patches）
async def edit_document_handler(arguments: dict) -> dict:
    """
    文檔編輯工具處理器

    Args:
        arguments: 包含 file_id 和 patches 的參數字典

    Returns:
        編輯結果字典
    """
    try:
        from services.api.services.doc_patch_service import apply_search_replace_patches
        from storage.file_storage import create_storage_from_config
        from system.infra.config.config import get_config_section

        file_id = arguments.get("file_id")
        patches = arguments.get("patches", [])

        if not file_id:
            return {
                "success": False,
                "error": "file_id is required",
            }

        if not patches:
            return {
                "success": False,
                "error": "patches list cannot be empty",
            }

        # 獲取文件內容
        config = get_config_section("file_upload", default={}) or {}
        storage = create_storage_from_config(config)

        # 從文件元數據獲取文件路徑
        from services.api.services.file_metadata_service import FileMetadataService

        metadata_service = FileMetadataService()
        file_metadata = metadata_service.get(file_id)
        if not file_metadata or not file_metadata.storage_path:
            return {
                "success": False,
                "error": f"File not found: {file_id}",
            }

        # 讀取原始文件內容
        original_content = storage.read(file_metadata.storage_path)
        if original_content is None:
            return {
                "success": False,
                "error": f"Failed to read file: {file_metadata.storage_path}",
            }

        # 應用 Search-and-Replace patches
        modified_content = apply_search_replace_patches(
            original=original_content.decode("utf-8"),
            patches=patches,
        )

        # 保存修改後的文件（注意：這裡只是預覽，實際保存應該通過 API 進行）
        # 為了安全，我們只返回修改後的內容，不直接寫入文件
        logger.info(
            "Document edited successfully",
            file_id=file_id,
            patch_count=len(patches),
        )

        return {
            "success": True,
            "file_id": file_id,
            "modified_content": modified_content,
            "patches_applied": len(patches),
        }

    except Exception as e:
        logger.error(f"Document editing failed: {e}", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


mcp_server.register_tool(
    name="edit_document",
    description="Apply search-and-replace patches to a document",
    input_schema={
        "type": "object",
        "properties": {
            "file_id": {
                "type": "string",
                "description": "文件 ID",
            },
            "patches": {
                "type": "array",
                "description": "Search-and-Replace patches 列表",
                "items": {
                    "type": "object",
                    "properties": {
                        "search_block": {
                            "type": "string",
                            "description": "要搜索的文本塊",
                        },
                        "replace_block": {
                            "type": "string",
                            "description": "替換後的文本塊",
                        },
                        "confidence": {
                            "type": "number",
                            "description": "置信度（0.0-1.0）",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": ["search_block", "replace_block"],
                },
            },
            "cursor_position": {
                "type": "integer",
                "description": "游標位置（可選，用於上下文匹配）",
            },
        },
        "required": ["file_id", "patches"],
    },
    handler=edit_document_handler,
)
