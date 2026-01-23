# 代碼功能說明: 視覺元素處理整合模組
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""視覺元素處理整合模組 - 將 VisualParser 整合到文件處理流程

功能：
1. 處理從文檔中提取的圖片
2. 批量處理多個視覺元素
3. 將視覺描述合併到文檔內容
"""

import os
from typing import Any, Dict, List, Optional

import structlog

from .parsers.visual_parser import VisualParser, get_visual_parser

logger = structlog.get_logger(__name__)


class VisualElementProcessor:
    """視覺元素處理器 - 整合 Prompt B 到文件處理流程"""

    def __init__(self, visual_parser: Optional[VisualParser] = None):
        """
        初始化視覺元素處理器

        Args:
            visual_parser: VisualParser 實例（可選）
        """
        self.visual_parser = visual_parser or get_visual_parser()

    async def process_document_images(
        self,
        images: List[Dict[str, Any]],
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        處理文檔中的多個圖片

        Args:
            images: 圖片信息列表，每個包含 image_content 或 image_path
            file_id: 文件ID
            user_id: 用戶ID

        Returns:
            處理後的圖片信息列表，包含描述文本
        """
        processed_images = []

        for img_info in images:
            try:
                image_content = img_info.get("image_content")

                if image_content is None and "image_path" in img_info:
                    image_path = img_info["image_path"]
                    if os.path.exists(image_path):
                        with open(image_path, "rb") as f:
                            image_content = f.read()

                if image_content is None:
                    logger.warning(
                        "圖片內容為空",
                        file_id=file_id,
                        img_info=img_info,
                    )
                    continue

                element_type = img_info.get("element_type")

                result = await self.visual_parser.parse_visual_element(
                    image_content=image_content,
                    element_type=element_type,
                    file_id=file_id,
                    user_id=user_id,
                )

                processed_images.append(
                    {
                        **img_info,
                        "description": result["text"],
                        "element_type": result["metadata"]["element_type"],
                        "metadata": {
                            **img_info.get("metadata", {}),
                            **result["metadata"],
                        },
                    }
                )

            except Exception as e:
                logger.error(
                    "圖片處理失敗",
                    file_id=file_id,
                    error=str(e),
                    exc_info=True,
                )
                processed_images.append(
                    {
                        **img_info,
                        "description": f"[圖片處理失敗: {str(e)}]",
                        "error": str(e),
                    }
                )

        return processed_images

    def merge_descriptions_to_text(
        self,
        original_text: str,
        processed_images: List[Dict[str, Any]],
        image_placeholder: str = "\n\n[圖片: {description}]\n\n",
    ) -> str:
        """
        將圖片描述合併到原始文本

        Args:
            original_text: 原始文本
            processed_images: 處理後的圖片信息列表
            image_placeholder: 圖片佔位符模板

        Returns:
            合併後的文本
        """
        if not processed_images:
            return original_text

        merged_text = original_text

        for img_info in processed_images:
            description = img_info.get("description", "")
            if description and description not in merged_text:
                placeholder = image_placeholder.format(description=description)
                merged_text += placeholder

        return merged_text

    async def process_table_image(
        self,
        image_content: bytes,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        專門處理表格圖片

        Args:
            image_content: 表格圖片內容
            file_id: 文件ID
            user_id: 用戶ID

        Returns:
            Markdown 格式的表格字符串
        """
        result = await self.visual_parser.parse_table(
            image_content=image_content,
            file_id=file_id,
            user_id=user_id,
        )

        return result["text"]

    async def process_chart_image(
        self,
        image_content: bytes,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        專門處理技術圖表

        Args:
            image_content: 圖表圖片內容
            file_id: 文件ID
            user_id: 用戶ID

        Returns:
            圖表描述字典
        """
        return await self.visual_parser.parse_chart(
            image_content=image_content,
            file_id=file_id,
            user_id=user_id,
        )


def get_visual_element_processor() -> VisualElementProcessor:
    """獲取視覺元素處理器實例"""
    return VisualElementProcessor()
