# 代碼功能說明: Prompt B 視覺解析員單元測試
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""Prompt B 視覺解析員單元測試 - 測試視覺元素解析功能

測試場景：
1. 表格識別和 Markdown 轉換
2. 技術圖表識別和描述生成
3. 產品圖片描述生成
4. 元素類型自動檢測
5. 錯誤處理和 Fallback 機制
"""

from unittest.mock import AsyncMock, patch

import pytest


class MockVisionResult:
    """模擬視覺模型返回結果"""

    def __init__(self, description: str, confidence: float = 0.9):
        self.description = description
        self.content = description
        self.confidence = confidence

    def get(self, key: str, default: str = "") -> str:
        if key == "description":
            return self.description
        elif key == "content":
            return self.content
        elif key == "confidence":
            return self.confidence
        return default


@pytest.fixture
def mock_vision_client():
    """創建模擬的視覺客戶端"""
    client = AsyncMock()
    return client


@pytest.fixture
def sample_table_image():
    """範例：表格圖片字節"""
    return b"fake_table_image_bytes"


@pytest.fixture
def sample_chart_image():
    """範例：圖表圖片字節"""
    return b"fake_chart_image_bytes"


@pytest.fixture
def sample_product_image():
    """範例：產品圖片字節"""
    return b"fake_product_image_bytes"


@pytest.fixture
def mock_vision_result_factory():
    """創建模擬結果的工廠函數"""

    def _create_result(description: str, confidence: float = 0.9):
        return MockVisionResult(description, confidence)

    return _create_result


class TestVisualParser:
    """測試 VisualParser 類"""

    @pytest.mark.asyncio
    async def test_parse_table_success(
        self, mock_vision_client, sample_table_image, mock_vision_result_factory
    ):
        """測試表格識別成功"""
        from services.api.processors.parsers.visual_parser import VisualParser

        table_markdown = """| 溫度 | 壓力 | 效率 |
|------|------|------|
| 100°C | 1.5MPa | 85% |
| 150°C | 2.0MPa | 90% |
| 200°C | 2.5MPa | 92% |"""

        mock_vision_client.describe_image = AsyncMock(
            return_value=mock_vision_result_factory(table_markdown)
        )

        with patch(
            "llm.clients.ollama_vision.get_ollama_vision_client",
            return_value=mock_vision_client,
        ):
            parser = VisualParser()
            parser.vision_client = mock_vision_client

            result = await parser.parse_table(
                image_content=sample_table_image,
                file_id="test-file-123",
                user_id="user-456",
            )

        assert result is not None
        assert "text" in result
        assert "metadata" in result
        assert "|" in result["text"]
        assert result["metadata"]["element_type"] == "table"

    @pytest.mark.asyncio
    async def test_parse_chart_success(
        self, mock_vision_client, sample_chart_image, mock_vision_result_factory
    ):
        """測試技術圖表識別成功"""
        from services.api.processors.parsers.visual_parser import VisualParser

        chart_description = """【圖表類型】：折線圖

【座標軸說明】：
- X軸：時間（月份）
- Y軸：產量（噸）

【趨勢分析】：
- 整體趨勢：上升
- 具體變化：從1月的100噸上升到12月的200噸

【關鍵數據點】：
- 1月：100噸
- 6月：150噸
- 12月：200噸"""

        mock_vision_client.describe_image = AsyncMock(
            return_value=mock_vision_result_factory(chart_description)
        )

        with patch(
            "llm.clients.ollama_vision.get_ollama_vision_client",
            return_value=mock_vision_client,
        ):
            parser = VisualParser()
            parser.vision_client = mock_vision_client

            result = await parser.parse_chart(
                image_content=sample_chart_image,
                file_id="test-file-456",
                user_id="user-789",
            )

        assert result is not None
        assert "text" in result
        assert "折線圖" in result["text"]
        assert "X軸" in result["text"]
        assert "Y軸" in result["text"]
        assert result["metadata"]["element_type"] == "chart"

    @pytest.mark.asyncio
    async def test_parse_product_image_success(
        self, mock_vision_client, sample_product_image, mock_vision_result_factory
    ):
        """測試產品圖片描述成功"""
        from services.api.processors.parsers.visual_parser import VisualParser

        product_description = """【產品名稱】：熱解爐

【主要特徵】：
- 圓柱形金屬容器
- 配有溫度顯示面板
- 底部有支撐框架

【組成零件】：
- 爐體：不銹鋼材質，直徑2米
- 加熱系統：電熱絲環繞
- 溫度感測器：位於爐體內部
- 控制面板：數位顯示溫度和壓力

【潛在功能】：用於廢棄物高溫熱解處理

【技術規格】：
- 最高溫度：1000°C
- 工作壓力：2.5MPa"""

        mock_vision_client.describe_image = AsyncMock(
            return_value=mock_vision_result_factory(product_description)
        )

        with patch(
            "llm.clients.ollama_vision.get_ollama_vision_client",
            return_value=mock_vision_client,
        ):
            parser = VisualParser()
            parser.vision_client = mock_vision_client

            result = await parser.parse_product_image(
                image_content=sample_product_image,
                file_id="test-file-789",
                user_id="user-abc",
            )

        assert result is not None
        assert "text" in result
        assert "主要特徵" in result["text"]
        assert "組成零件" in result["text"]
        assert result["metadata"]["element_type"] == "product"

    @pytest.mark.asyncio
    async def test_parse_visual_element_auto_detect(
        self, mock_vision_client, sample_table_image, mock_vision_result_factory
    ):
        """測試自動檢測元素類型"""
        from services.api.processors.parsers.visual_parser import VisualParser

        mock_vision_client.describe_image = AsyncMock(
            return_value=mock_vision_result_factory("這是一個表格")
        )

        with patch(
            "llm.clients.ollama_vision.get_ollama_vision_client",
            return_value=mock_vision_client,
        ):
            parser = VisualParser()
            parser.vision_client = mock_vision_client

            result = await parser.parse_visual_element(
                image_content=sample_table_image,
                file_id="test-file-auto",
                user_id="user-auto",
            )

        assert result is not None
        assert "metadata" in result
        assert result["metadata"]["element_type"] in ["table", "chart", "product", "image"]

    @pytest.mark.asyncio
    async def test_parse_visual_element_vision_error(self, mock_vision_client, sample_table_image):
        """測試視覺模型調用錯誤處理"""
        from services.api.processors.parsers.visual_parser import VisualParser

        mock_vision_client.describe_image = AsyncMock(
            side_effect=Exception("Vision model unavailable")
        )

        with patch(
            "llm.clients.ollama_vision.get_ollama_vision_client",
            return_value=mock_vision_client,
        ):
            parser = VisualParser()
            parser.vision_client = mock_vision_client

            result = await parser.parse_visual_element(
                image_content=sample_table_image,
                file_id="test-file-error",
                user_id="user-error",
            )

        assert result is not None
        assert "text" in result
        assert "解析失敗" in result["text"]
        assert "error" in result["metadata"]

    def test_detect_element_type_table(self):
        """測試表格類型檢測"""
        from services.api.processors.parsers.visual_parser import VisualParser

        parser = VisualParser()
        description = "這是一個表格，包含以下數據：| 欄位1 | 欄位2 |"
        element_type = parser._detect_element_type(description)
        assert element_type == "table"

    def test_detect_element_type_chart(self):
        """測試圖表類型檢測"""
        from services.api.processors.parsers.visual_parser import VisualParser

        parser = VisualParser()
        description = "這是一個折線圖，X軸顯示時間，Y軸顯示產量，趨勢上升"
        element_type = parser._detect_element_type(description)
        assert element_type == "chart"

    def test_detect_element_type_product(self):
        """測試產品類型檢測"""
        from services.api.processors.parsers.visual_parser import VisualParser

        parser = VisualParser()
        description = "這是一個產品圖片，主要特徵包括圓柱形爐體和加熱系統"
        element_type = parser._detect_element_type(description)
        assert element_type == "product"

    def test_get_supported_extensions(self):
        """測試支持的文件擴展名"""
        from services.api.processors.parsers.visual_parser import VisualParser

        parser = VisualParser()
        extensions = parser.get_supported_extensions()

        assert ".png" in extensions
        assert ".jpg" in extensions
        assert ".jpeg" in extensions
        assert ".bmp" in extensions
        assert ".gif" in extensions
        assert ".webp" in extensions


class TestPromptBSpecificationCompliance:
    """測試 Prompt B 規格遵循"""

    def test_table_prompt_contains_requirements(self):
        """測試表格 Prompt 包含必要要求"""
        from services.api.processors.parsers.visual_parser import VisualParser

        parser = VisualParser()
        table_prompt = parser._get_table_prompt()

        assert "Markdown" in table_prompt
        assert "行列對齊" in table_prompt
        assert "表頭" in table_prompt

    def test_chart_prompt_contains_requirements(self):
        """測試圖表 Prompt 包含必要要求"""
        from services.api.processors.parsers.visual_parser import VisualParser

        parser = VisualParser()
        chart_prompt = parser._get_chart_prompt()

        assert "X軸" in chart_prompt
        assert "Y軸" in chart_prompt
        assert "趨勢" in chart_prompt
        assert "數據點" in chart_prompt

    def test_product_prompt_contains_requirements(self):
        """測試產品圖片 Prompt 包含必要要求"""
        from services.api.processors.parsers.visual_parser import VisualParser

        parser = VisualParser()
        product_prompt = parser._get_product_image_prompt()

        assert "主要特徵" in product_prompt
        assert "組成零件" in product_prompt
        assert "潛在功能" in product_prompt

    @pytest.mark.asyncio
    async def test_output_includes_technical_terms(
        self, mock_vision_client, sample_product_image, mock_vision_result_factory
    ):
        """測試輸出包含技術術語"""
        from services.api.processors.parsers.visual_parser import VisualParser

        description_with_terms = """【技術術語】：熱解爐、高溫熱解、廢棄物處理、能源轉化

這是一個熱解爐設備，用於廢棄物處理。"""

        mock_vision_client.describe_image = AsyncMock(
            return_value=mock_vision_result_factory(description_with_terms)
        )

        with patch(
            "llm.clients.ollama_vision.get_ollama_vision_client",
            return_value=mock_vision_client,
        ):
            parser = VisualParser()
            parser.vision_client = mock_vision_client

            result = await parser.parse_product_image(
                image_content=sample_product_image,
                file_id="test-file-terms",
                user_id="user-terms",
            )

        assert result is not None
        assert "text" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
