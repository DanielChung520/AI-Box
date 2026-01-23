# 代碼功能說明: 視覺元素解析器 (Prompt B 視覺解析員)
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""視覺元素解析器 - 實現 Prompt B 視覺解析員規格

功能：
1. 表格識別和 Markdown 轉換
2. 技術圖表識別和描述生成
3. 產品圖片描述生成
4. 關聯技術術語輸出

符合規格書 Prompt B 規格：
- 表格：精確還原為 Markdown 格式，確保行列對齊
- 技術圖表：描述 X/Y 軸含義、趨勢變化以及關鍵數據點
- 產品圖片：描述主體特徵、組成零件以及潛在功能
"""

from io import BytesIO
from typing import Any, Dict, List, Optional

import structlog

from .base_parser import BaseParser

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = structlog.get_logger(__name__)


class VisualParser(BaseParser):
    """視覺元素解析器（實現 Prompt B 視覺解析員）"""

    def __init__(self, vision_model: Optional[str] = None):
        """
        初始化視覺解析器

        Args:
            vision_model: 視覺模型名稱（可選，使用默認模型 qwen3-vl:8b）
        """
        super().__init__()

        if not PIL_AVAILABLE:
            raise ImportError("Pillow 未安裝，請運行: pip install Pillow")

        try:
            from llm.clients.ollama_vision import get_ollama_vision_client

            self.vision_client = get_ollama_vision_client()
            self.vision_model = vision_model or self.vision_client.default_model
        except Exception as e:
            logger.error("無法初始化視覺客戶端", error=str(e))
            raise RuntimeError(f"無法初始化視覺客戶端: {str(e)}") from e

    def _get_table_prompt(self) -> str:
        """獲取表格識別的 Prompt"""
        return """你現在是一名視覺數據解析專家。請分析這張圖片並判斷其類型：

**若為表格**：請精確還原為 Markdown 格式，確保行列對齊，不要遺漏任何數據。
輸出格式應為標準 Markdown 表格，例如：
| 欄位1 | 欄位2 | 欄位3 |
|-------|-------|-------|
| 數據1 | 數據2 | 數據3 |

**重要要求**：
1. 保持所有行列對齊
2. 不要遺漏任何數據
3. 如果有表頭，請確保表頭正確
4. 如果數據包含特殊字符，請完整保留"""

    def _get_chart_prompt(self) -> str:
        """獲取技術圖表識別的 Prompt"""
        return """你現在是一名視覺數據解析專家。請分析這張圖片（技術圖表）：

**任務**：描述 X/Y 軸含義、趨勢變化（上升/下降/平穩）以及關鍵數據點。

**輸出格式**：
```
【圖表類型】：折線圖/柱狀圖/圓餅圖/散點圖等

【座標軸說明】：
- X軸：描述X軸代表的意義
- Y軸：描述Y軸代表的意義

【趨勢分析】：
- 整體趨勢：上升/下降/平穩/波動
- 具體變化：描述關鍵轉折點

【關鍵數據點】：
- 列出最重要的3-5個數據點

【圖表標題】（如果可見）："""

    def _get_product_image_prompt(self) -> str:
        """獲取產品圖片描述的 Prompt"""
        return """你現在是一名視覺數據解析專家。請分析這張產品圖片：

**任務**：描述主體特徵、組成零件以及其在文件中的潛在功能。

**輸出格式**：
```
【產品名稱】（如果可識別）：描述

【主要特徵】：
- 列出產品的主要外觀特徵

【組成零件】：
- 列出可識別的零件或組件
- 標註每個零件的位置或功能

【潛在功能】：描述產品在文件上下文中可能的用途

【技術規格】（如果可識別）：描述尺寸、材質等"""

    def _get_visual_element_prompt(self, element_type: Optional[str] = None) -> str:
        """
        獲取通用視覺元素識別 Prompt

        Args:
            element_type: 元素類型（table/chart/image/product），可選

        Returns:
            完整的 Prompt 字符串
        """
        base_prompt = """你現在是一名視覺數據解析專家。請分析這張圖片並判斷其類型：

"""
        type_specific_prompt = ""

        if element_type == "table":
            type_specific_prompt = self._get_table_prompt()
        elif element_type == "chart":
            type_specific_prompt = self._get_chart_prompt()
        elif element_type == "product":
            type_specific_prompt = self._get_product_image_prompt()
        else:
            type_specific_prompt = """請根據圖片類型進行分析和描述：

* **若為表格**：請精確還原為 Markdown 格式，確保行列對齊，不要遺漏任何數據。
* **若為技術圖表 (如曲線、流程圖)**：請描述 X/Y 軸含義、趨勢變化（上升/下降/平穩）以及關鍵數據點。
* **若為產品圖片**：請描述主體特徵、組成零件以及其在文件中的潛在功能。

**注意**：輸出必須包含該圖片在文件中可能關聯的技術術語。"""

        return base_prompt + type_specific_prompt

    async def parse_visual_element(
        self,
        image_content: bytes,
        element_type: Optional[str] = None,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        解析視覺元素（表格、圖表、圖片）

        Args:
            image_content: 圖片內容（字節）
            element_type: 元素類型（table/chart/image/product），可選
            file_id: 文件ID（用於追蹤）
            user_id: 用戶ID（用於追蹤）
            task_id: 任務ID（用於追蹤）
            **kwargs: 其他參數

        Returns:
            解析結果，包含：
            - text: 描述文本
            - metadata: 元數據（包含 element_type, confidence 等）
        """
        try:
            prompt = self._get_visual_element_prompt(element_type)

            self.logger.info(
                "開始解析視覺元素",
                file_id=file_id,
                element_type=element_type or "auto-detect",
                model=self.vision_model,
            )

            result = await self.vision_client.describe_image(
                image_content=image_content,
                prompt=prompt,
                model=self.vision_model,
                user_id=user_id,
                file_id=file_id,
                task_id=task_id,
            )

            description_text = result.get("description", "")
            confidence = result.get("confidence")
            vision_metadata = result.get("metadata", {})

            self.logger.info(
                "視覺元素解析完成",
                file_id=file_id,
                element_type=element_type or "unknown",
                description_length=len(description_text),
            )

            return {
                "text": description_text,
                "metadata": {
                    "element_type": element_type or self._detect_element_type(description_text),
                    "description_confidence": confidence,
                    "vision_model": self.vision_model,
                    **vision_metadata,
                },
            }

        except Exception as e:
            self.logger.error(
                "視覺元素解析失敗",
                file_id=file_id,
                element_type=element_type,
                error=str(e),
                exc_info=True,
            )
            return {
                "text": f"[視覺元素解析失敗: {str(e)}]",
                "metadata": {
                    "error": str(e),
                    "element_type": element_type or "unknown",
                },
            }

    def _detect_element_type(self, description: str) -> str:
        """
        根據描述文本檢測元素類型

        Args:
            description: 描述文本

        Returns:
            元素類型（table/chart/image）
        """
        description_lower = description.lower()

        if "表格" in description or "markdown" in description_lower or "|" in description:
            return "table"
        elif (
            "圖表" in description or "趨勢" in description or "軸" in description or "數據點" in description
        ):
            return "chart"
        elif "產品" in description or "零件" in description or "特徵" in description:
            return "product"
        else:
            return "image"

    async def parse_table(
        self,
        image_content: bytes,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        專門解析表格圖片

        Args:
            image_content: 圖片內容（字節）
            file_id: 文件ID
            user_id: 用戶ID
            **kwargs: 其他參數

        Returns:
            Markdown 格式的表格字符串
        """
        return await self.parse_visual_element(
            image_content=image_content,
            element_type="table",
            file_id=file_id,
            user_id=user_id,
            **kwargs,
        )

    async def parse_chart(
        self,
        image_content: bytes,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        專門解析技術圖表

        Args:
            image_content: 圖片內容（字節）
            file_id: 文件ID
            user_id: 用戶ID
            **kwargs: 其他參數

        Returns:
            圖表描述
        """
        return await self.parse_visual_element(
            image_content=image_content,
            element_type="chart",
            file_id=file_id,
            user_id=user_id,
            **kwargs,
        )

    async def parse_product_image(
        self,
        image_content: bytes,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        專門解析產品圖片

        Args:
            image_content: 圖片內容（字節）
            file_id: 文件ID
            user_id: 用戶ID
            **kwargs: 其他參數

        Returns:
            產品描述
        """
        return await self.parse_visual_element(
            image_content=image_content,
            element_type="product",
            file_id=file_id,
            user_id=user_id,
            **kwargs,
        )

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

            try:
                width = img.width
                height = img.height
            except Exception:
                width, height = img.size

            return {
                "width": width,
                "height": height,
                "format": img.format,
                "mode": img.mode,
                "size_bytes": len(image_content),
            }
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
        element_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        從字節內容解析視覺元素

        Args:
            file_content: 圖片內容（字節）
            file_id: 文件ID
            user_id: 用戶ID
            task_id: 任務ID
            element_type: 元素類型（可選）
            **kwargs: 其他參數

        Returns:
            解析結果
        """
        if not PIL_AVAILABLE:
            raise ImportError("Pillow 未安裝")

        image_metadata = self._extract_image_metadata(file_content)

        result = await self.parse_visual_element(
            image_content=file_content,
            element_type=element_type,
            file_id=file_id,
            user_id=user_id,
            task_id=task_id,
            **kwargs,
        )

        result["metadata"]["image_metadata"] = image_metadata
        return result

    def parse(self, file_path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        解析視覺元素文件

        Args:
            file_path: 文件路徑
            **kwargs: 其他參數

        Returns:
            解析結果
        """
        if not PIL_AVAILABLE:
            raise ImportError("Pillow 未安裝")

        try:
            with open(file_path, "rb") as f:
                file_content = f.read()

            import asyncio

            return asyncio.run(self.parse_from_bytes(file_content, **kwargs))

        except Exception as e:
            self.logger.error("視覺元素文件解析失敗", file_path=file_path, error=str(e))
            raise

    def get_supported_extensions(self) -> List[str]:
        """獲取支持的文件擴展名列表"""
        return [".png", ".jpg", ".jpeg", ".bmp", ".svg", ".gif", ".webp", ".tiff", ".tif"]


def get_visual_parser() -> VisualParser:
    """獲取視覺解析器實例"""
    return VisualParser()
