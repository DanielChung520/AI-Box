# 代碼功能說明: 雙軌 RAG 處理器
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""雙軌 RAG 處理器 - 實現 Stage 1 快速軌和 Stage 2 深度軌

架構說明：
- Stage 1（快速軌）：立即完成基礎向量索引，提供即時檢索能力
- Stage 2（深度軌）：背景任務，使用 LLM + VLM 進行深度理解

功能：
1. 階段分離：Stage 1 和 Stage 2 完全分離
2. 非阻塞：Stage 2 在背景執行，不影響用戶體驗
3. 漸進式更新：Stage 2 完成後使用 Qdrant upsert 更新 Payload
4. 向後兼容：保留現有功能，Stage 2 失敗不影響 Stage 1
"""

import time
from typing import Any, Dict, List, Optional

import structlog

from services.api.processors.contextual_header_generator import (
    ContextualHeaderGenerator,
    get_contextual_header_generator,
)
from services.api.processors.visual_element_processor import (
    VisualElementProcessor,
    get_visual_element_processor,
)

logger = structlog.get_logger(__name__)


class DualTrackProcessor:
    """雙軌 RAG 處理器"""

    def __init__(
        self,
        contextual_header_generator: Optional[ContextualHeaderGenerator] = None,
        visual_element_processor: Optional[VisualElementProcessor] = None,
    ):
        """
        初始化雙軌處理器

        Args:
            contextual_header_generator: ContextualHeaderGenerator 實例
            visual_element_processor: VisualElementProcessor 實例
        """
        self.contextual_header_generator = (
            contextual_header_generator or get_contextual_header_generator()
        )
        self.visual_element_processor = visual_element_processor or get_visual_element_processor()

    def update_stage1_status(
        self,
        file_id: str,
        stage: str,
        progress: int,
        message: str,
        **kwargs,
    ):
        """
        更新 Stage 1 處理狀態

        Args:
            file_id: 文件 ID
            stage: 當前階段
            progress: 進度 (0-100)
            message: 狀態消息
            **kwargs: 額外狀態數據
        """
        from api.routers.file_upload import _update_processing_status

        status_data = {
            "stage": "stage1",
            "sub_stage": stage,
            "progress": progress,
            "message": message,
            **kwargs,
        }
        _update_processing_status(
            file_id=file_id,
            dual_track=status_data,
        )

    def update_stage2_status(
        self,
        file_id: str,
        stage: str,
        progress: int,
        message: str,
        **kwargs,
    ):
        """
        更新 Stage 2 處理狀態

        Args:
            file_id: 文件 ID
            stage: 當前階段
            progress: 進度 (0-100)
            message: 狀態消息
            **kwargs: 額外狀態數據
        """
        from api.routers.file_upload import _update_processing_status

        status_data = {
            "stage": "stage2",
            "sub_stage": stage,
            "progress": progress,
            "message": message,
            **kwargs,
        }
        _update_processing_status(
            file_id=file_id,
            dual_track=status_data,
        )

    async def process_stage2_background(
        self,
        file_id: str,
        file_name: str,
        file_path: str,
        file_type: Optional[str],
        full_text: str,
        chunks: List[Dict[str, Any]],
        images: List[Dict[str, Any]],
        global_summary: Optional[Dict[str, Any]],
        user_id: str,
    ) -> bool:
        """
        Stage 2 背景處理任務

        執行 Prompt A、B、C，然後更新 Qdrant Payload

        Args:
            file_id: 文件 ID
            file_name: 文件名
            file_path: 文件路徑
            file_type: 文件類型
            full_text: 完整文本
            chunks: 已分塊的數據
            images: 從文檔中提取的圖片
            global_summary: 已有摘要（可選）
            user_id: 用戶 ID

        Returns:
            是否成功完成
        """
        stage2_start_time = time.time()

        try:
            logger.info(
                "開始 Stage 2 深度軌處理",
                file_id=file_id,
                chunk_count=len(chunks),
                image_count=len(images),
            )

            # ========== Stage 2.1: Prompt A 語意摘要員 ==========
            if not global_summary:
                self.update_stage2_status(
                    file_id=file_id,
                    stage="prompt_a",
                    progress=0,
                    message="生成文件摘要",
                )

                from api.routers.file_upload import _generate_file_summary_for_metadata

                global_summary = await _generate_file_summary_for_metadata(
                    file_id=file_id,
                    file_name=file_name,
                    full_text=full_text,
                    user_id=user_id,
                )

                if global_summary:
                    logger.info(
                        "Stage 2 Prompt A 完成",
                        file_id=file_id,
                        theme=global_summary.get("theme", "N/A"),
                    )

            self.update_stage2_status(
                file_id=file_id,
                stage="prompt_a",
                progress=100,
                message="文件摘要生成完成",
                global_summary_theme=global_summary.get("theme") if global_summary else None,
            )

            # ========== Stage 2.2: Prompt B 視覺解析員 ==========
            processed_images: List[Dict[str, Any]] = []

            if images:
                self.update_stage2_status(
                    file_id=file_id,
                    stage="prompt_b",
                    progress=0,
                    message=f"處理 {len(images)} 個視覺元素",
                )

                processed_images = await self.visual_element_processor.process_document_images(
                    images=images,
                    file_id=file_id,
                    user_id=user_id,
                )

                for i, img in enumerate(processed_images):
                    if i < len(chunks):
                        chunks[i]["metadata"]["image_description"] = img.get("description", "")
                        chunks[i]["metadata"]["element_type"] = img.get("element_type", "image")

                logger.info(
                    "Stage 2 Prompt B 完成",
                    file_id=file_id,
                    processed_count=len(processed_images),
                )

            self.update_stage2_status(
                file_id=file_id,
                stage="prompt_b",
                progress=100,
                message=f"視覺元素處理完成 ({len(processed_images) if images else 0} 個)",
                image_count=len(processed_images) if images else 0,
            )

            # ========== Stage 2.3: Prompt C Contextual Header 整合員 ==========
            self.update_stage2_status(
                file_id=file_id,
                stage="prompt_c",
                progress=0,
                message="生成 Contextual Headers",
            )

            updated_chunks = await self.contextual_header_generator.generate_headers_batch(
                chunks=chunks,
                global_context=global_summary,
                file_id=file_id,
                user_id=user_id,
                concurrency=5,
            )

            logger.info(
                "Stage 2 Prompt C 完成",
                file_id=file_id,
                header_count=len(updated_chunks),
            )

            # ========== Stage 2.4: 更新 Qdrant Payload ==========
            self.update_stage2_status(
                file_id=file_id,
                stage="payload_update",
                progress=0,
                message="更新向量存儲 Payload",
            )

            from services.api.services.qdrant_vector_store_service import (
                get_qdrant_vector_store_service,
            )

            vector_store_service = get_qdrant_vector_store_service()

            update_success = vector_store_service.update_vectors_payload(
                file_id=file_id,
                chunks=updated_chunks,
                user_id=user_id,
            )

            if update_success:
                logger.info(
                    "Stage 2 Payload 更新完成",
                    file_id=file_id,
                    chunk_count=len(updated_chunks),
                )

            self.update_stage2_status(
                file_id=file_id,
                stage="payload_update",
                progress=100,
                message="Payload 更新完成",
                update_success=update_success,
            )

            stage2_duration = time.time() - stage2_start_time
            logger.info(
                "Stage 2 深度軌處理完成",
                file_id=file_id,
                duration_seconds=stage2_duration,
                success=True,
            )

            return True

        except Exception as e:
            stage2_duration = time.time() - stage2_start_time
            logger.error(
                "Stage 2 深度軌處理失敗",
                file_id=file_id,
                error=str(e),
                duration_seconds=stage2_duration,
                exc_info=True,
            )

            self.update_stage2_status(
                file_id=file_id,
                stage="error",
                progress=0,
                message=f"處理失敗: {str(e)}",
                error=str(e),
            )

            return False

    def should_enable_dual_track(self) -> bool:
        """
        檢查是否啟用雙軌處理

        從配置讀取雙軌處理設置

        Returns:
            是否啟用雙軌處理
        """
        try:
            from system.infra.config.config import get_config_section

            config = get_config_section("chunk_processing", default={}) or {}
            dual_track_config = config.get("dual_track", {})

            return dual_track_config.get("enabled", False)
        except Exception:
            return False


def get_dual_track_processor() -> DualTrackProcessor:
    """獲取雙軌處理器實例"""
    return DualTrackProcessor()
