# 代碼功能說明: 圖片文件解析器
# 創建日期: 2025-12-06 16:01 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 16:01 (UTC+8)

"""圖片文件解析器 - 使用視覺模型生成圖片描述"""

from typing import Dict, Any, Optional
import structlog
from io import BytesIO

from .base_parser import BaseParser

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = structlog.get_logger(__name__)


class ImageParser(BaseParser):
    """圖片文件解析器 - 使用視覺模型生成描述"""

    def __init__(self, vision_model: Optional[str] = None):
        """
        初始化圖片解析器

        Args:
            vision_model: 視覺模型名稱（可選，使用默認模型）
        """
        super().__init__()

        if not PIL_AVAILABLE:
            raise ImportError("Pillow 未安裝，請運行: pip install Pillow")

        # 延遲導入避免循環依賴
        try:
            from llm.clients.ollama_vision import get_ollama_vision_client

            self.vision_client = get_ollama_vision_client()
            self.vision_model = vision_model or self.vision_client.default_model
        except Exception as e:
            logger.error("無法初始化視覺客戶端", error=str(e))
            raise RuntimeError(f"無法初始化視覺客戶端: {str(e)}") from e

    def _extract_image_metadata(self, image_content: bytes) -> Dict[str, Any]:
        """
        提取圖片元數據

        Args:
            image_content: 圖片內容（字節）

        Returns:
            圖片元數據字典
        """
        try:
            img = Image.open(BytesIO(image_content))
            metadata = {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "size_bytes": len(image_content),
            }

            # 嘗試提取 EXIF 數據（如果可用）
            if hasattr(img, "_getexif") and img._getexif():
                try:
                    metadata["exif"] = dict(img._getexif())
                except Exception:
                    pass

            return metadata
        except Exception as e:
            self.logger.warning("圖片元數據提取失敗", error=str(e))
            return {
                "width": None,
                "height": None,
                "format": None,
                "mode": None,
                "size_bytes": len(image_content),
            }

    async def parse_from_bytes(
        self,
        file_content: bytes,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        從字節內容解析圖片

        Args:
            file_content: 圖片文件內容（字節）
            file_id: 文件ID（用於追蹤）
            user_id: 用戶ID（用於追蹤）
            task_id: 任務ID（用於追蹤）
            **kwargs: 其他參數

        Returns:
            解析結果，包含描述文本和元數據
        """
        if not PIL_AVAILABLE:
            raise ImportError("Pillow 未安裝")

        try:
            # 提取圖片元數據
            image_metadata = self._extract_image_metadata(file_content)

            # 調用視覺模型生成描述
            self.logger.info(
                "開始生成圖片描述",
                file_id=file_id,
                image_format=image_metadata.get("format"),
                image_size=f"{image_metadata.get('width')}x{image_metadata.get('height')}",
            )

            description_result = await self.vision_client.describe_image(
                image_content=file_content,
                model=self.vision_model,
                user_id=user_id,
                file_id=file_id,
                task_id=task_id,
            )

            description_text = description_result.get("description", "")
            confidence = description_result.get("confidence")
            vision_metadata = description_result.get("metadata", {})

            self.logger.info(
                "圖片描述生成完成",
                file_id=file_id,
                description_length=len(description_text),
                model=self.vision_model,
            )

            # 合併元數據
            combined_metadata = {
                **image_metadata,
                "vision_model": self.vision_model,
                "description_confidence": confidence,
                **vision_metadata,
            }

            return {
                "text": description_text,
                "metadata": combined_metadata,
            }

        except Exception as e:
            self.logger.error(
                "圖片解析失敗",
                file_id=file_id,
                error=str(e),
                exc_info=True,
            )
            # 返回空描述，不拋出異常（允許其他文件繼續處理）
            return {
                "text": f"[圖片解析失敗: {str(e)}]",
                "metadata": {
                    "error": str(e),
                    "width": None,
                    "height": None,
                    "format": None,
                    "size_bytes": len(file_content),
                },
            }

    def parse(self, file_path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        解析圖片文件

        Args:
            file_path: 圖片文件路徑
            **kwargs: 其他參數

        Returns:
            解析結果
        """
        if not PIL_AVAILABLE:
            raise ImportError("Pillow 未安裝")

        try:
            # 讀取文件內容
            with open(file_path, "rb") as f:
                file_content = f.read()

            # 使用 parse_from_bytes 處理
            return self.parse_from_bytes(file_content, **kwargs)

        except Exception as e:
            self.logger.error("圖片文件解析失敗", file_path=file_path, error=str(e))
            raise

    def get_supported_extensions(self) -> list:
        """獲取支持的文件擴展名列表"""
        return [".png", ".jpg", ".jpeg", ".bmp", ".svg", ".gif", ".webp"]
