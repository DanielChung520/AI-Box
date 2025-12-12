# 代碼功能說明: 圖片文件解析器
# 創建日期: 2025-12-06 16:01 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

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

            # 對於 GIF 文件（特別是動畫 GIF），需要特殊處理
            is_gif = img.format == "GIF"
            is_animated = False
            frame_count = 1

            if is_gif:
                try:
                    # 檢查是否為動畫 GIF
                    img.seek(0)  # 確保在第一幀

                    # 首先嘗試使用 PIL 的內置屬性（如果可用）
                    if hasattr(img, "is_animated") and img.is_animated:
                        is_animated = True
                        frame_count = 0
                        try:
                            while True:
                                frame_count += 1
                                img.seek(
                                    frame_count
                                )  # 使用 frame_count 而不是 img.tell() + 1
                        except EOFError:
                            pass
                        img.seek(0)  # 重置到第一幀
                    else:
                        # 如果沒有 is_animated 屬性，手動檢查
                        frame_count = 1
                        try:
                            # 嘗試讀取第二幀
                            img.seek(1)
                            is_animated = True
                            frame_count = 2
                            # 繼續計數剩餘的幀
                            try:
                                while True:
                                    frame_count += 1
                                    img.seek(frame_count)
                            except EOFError:
                                pass
                            img.seek(0)  # 重置到第一幀
                        except EOFError:
                            # 只有一幀，不是動畫
                            is_animated = False
                            frame_count = 1
                            img.seek(0)  # 確保在第一幀
                except Exception as e:
                    # 如果無法讀取多幀，可能是靜態 GIF 或文件損壞
                    self.logger.debug("無法讀取 GIF 幀數", error=str(e))
                    is_animated = False
                    frame_count = 1
                    img.seek(0)  # 確保在第一幀

            # 安全地獲取尺寸（對於某些格式可能需要特殊處理）
            try:
                width = img.width
                height = img.height
            except Exception as e:
                # 如果無法獲取尺寸，嘗試使用 size 屬性
                self.logger.debug(
                    "無法通過 width/height 獲取尺寸，使用 size 屬性", error=str(e)
                )
                try:
                    width, height = img.size
                except Exception:
                    width = None
                    height = None

            metadata = {
                "width": width,
                "height": height,
                "format": img.format,
                "mode": img.mode,
                "size_bytes": len(image_content),
            }

            # 對於 GIF，添加動畫相關信息
            if is_gif:
                metadata["is_animated"] = is_animated
                metadata["frame_count"] = frame_count if is_animated else 1

            # 嘗試提取 EXIF 數據（如果可用）
            # 注意：GIF 不支持 EXIF，但其他格式可能支持
            if not is_gif and hasattr(img, "_getexif") and img._getexif():
                try:
                    metadata["exif"] = dict(img._getexif())
                except Exception:
                    pass
            elif hasattr(img, "getexif"):
                # PIL 10.0+ 使用 getexif() 方法
                try:
                    exif_data = img.getexif()
                    if exif_data:
                        metadata["exif"] = dict(exif_data)
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

            # 對於動畫 GIF，提取第一幀用於描述生成
            image_format = image_metadata.get("format")
            is_animated_gif = image_format == "GIF" and image_metadata.get(
                "is_animated", False
            )
            image_content_for_vision = file_content

            if is_animated_gif:
                try:
                    # 提取 GIF 第一幀作為靜態圖像用於視覺模型
                    img = Image.open(BytesIO(file_content))
                    img.seek(0)  # 確保在第一幀

                    # 將第一幀轉換為 PNG 格式（視覺模型通常更好地支持 PNG）
                    frame_buffer = BytesIO()
                    img.save(frame_buffer, format="PNG")
                    image_content_for_vision = frame_buffer.getvalue()

                    self.logger.info(
                        "動畫 GIF 檢測到，使用第一幀生成描述",
                        file_id=file_id,
                        frame_count=image_metadata.get("frame_count", 1),
                    )
                except Exception as e:
                    self.logger.warning(
                        "無法提取 GIF 第一幀，使用原始文件",
                        file_id=file_id,
                        error=str(e),
                    )
                    # 如果提取失敗，使用原始文件內容
                    image_content_for_vision = file_content

            # 調用視覺模型生成描述
            self.logger.info(
                "開始生成圖片描述",
                file_id=file_id,
                image_format=image_format,
                image_size=f"{image_metadata.get('width')}x{image_metadata.get('height')}",
                is_animated_gif=is_animated_gif,
            )

            description_result = await self.vision_client.describe_image(
                image_content=image_content_for_vision,
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
