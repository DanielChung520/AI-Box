from __future__ import annotations
# 代碼功能說明: VisionAgent實現
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""VisionAgent實現 - 視覺數據解析和處理LangGraph節點"""
import logging
from typing import Any, Dict, List

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState
from llm.clients.ollama_vision import get_ollama_vision_client

logger = logging.getLogger(__name__)


class VisionAgent(BaseAgentNode):
    """視覺分析Agent - 負責圖片和圖表的深度解析"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        self.vision_client = get_ollama_vision_client()

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行視覺分析
        """
        try:
            # 1. 檢查是否有需要處理的圖片
            image_files = self._get_image_files(state)
            if not image_files:
                return NodeResult.success(data={"message": "No images to process"})

            # 2. 執行並行視覺解析
            analysis_results = []
            for file_info in image_files:
                result = await self._process_image(file_info, state)
                analysis_results.append(result)

            # 3. 更新狀態
            state.vision_analysis.extend(analysis_results)

            # 4. 記錄觀察
            state.add_observation(
                "vision_analysis_completed",
                {
                    "processed_count": len(analysis_results),
                    "file_ids": [r["file_id"] for r in analysis_results],
                },
            )

            logger.info(f"Vision analysis completed for {len(analysis_results)} images")

            return NodeResult.success(
                data={
                    "vision_results": analysis_results,
                    "summary": f"Successfully processed {len(analysis_results)} images",
                }
            )

        except Exception as e:
            logger.error(f"VisionAgent execution error: {e}", exc_info=True)
            return NodeResult.failure(f"Vision analysis failed: {str(e)}")

    def _get_image_files(self, state: AIBoxState) -> List[Dict[str, Any]]:
        """從狀態中提取圖片文件信息"""
        images = []
        if state.injected_context and "images" in state.injected_context:
            images = state.injected_context["images"]
        return images

    async def _process_image(self, file_info: Dict[str, Any], state: AIBoxState) -> Dict[str, Any]:
        """處理單個圖片""",
        file_id = file_info.get("file_id")
        content = file_info.get("content", b"")

        analysis = await self.vision_client.describe_image(
            image_content=content, user_id=state.user_id, file_id=file_id, task_id=state.task_id,
        )

        return {
            "file_id": file_id,
            "description": analysis.get("description"),
            "metadata": analysis.get("metadata", {}),
        }


def create_vision_agent_config() -> NodeConfig:
    """創建VisionAgent配置""",
    return NodeConfig(
        name="VisionAgent",
        description="視覺分析Agent - 負責圖片和圖表的深度解析",
        max_retries=2,
        timeout=60.0,
        required_inputs=["user_id"],
        optional_inputs=["task_id", "injected_context"],
        output_keys=["vision_analysis"]
    )


def create_vision_agent() -> VisionAgent:
    """創建VisionAgent實例""",
    config = create_vision_agent_config()
    return VisionAgent(config)
