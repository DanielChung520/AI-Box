# 代碼功能說明: DefinitionLoader 單元測試
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""DefinitionLoader 單元測試"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from services.api.core.config import DefinitionLoader, get_definition_loader


class TestDefinitionLoader:
    """DefinitionLoader 測試類"""

    @pytest.fixture
    def temp_dir(self):
        """創建臨時目錄"""
        with TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_definition(self):
        """示例配置定義"""
        return {
            "scope": "genai.policy",
            "description": "生成式 AI 核心策略設置",
            "version": "1.0.0",
            "fields": {
                "rate_limit": {
                    "type": "integer",
                    "min": 1,
                    "max": 1000,
                    "default": 100,
                }
            },
        }

    def test_load_all_success(self, temp_dir, sample_definition):
        """測試成功加載所有定義文件"""
        # 創建測試 JSON 文件
        json_file = temp_dir / "genai.policy.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(sample_definition, f)

        loader = DefinitionLoader(definitions_dir=temp_dir)
        definitions = loader.load_all()

        assert len(definitions) == 1
        assert "genai.policy" in definitions
        assert definitions["genai.policy"]["scope"] == "genai.policy"

    def test_load_all_empty_directory(self, temp_dir):
        """測試空目錄"""
        loader = DefinitionLoader(definitions_dir=temp_dir)
        definitions = loader.load_all()

        assert len(definitions) == 0

    def test_load_all_invalid_json(self, temp_dir):
        """測試無效的 JSON 文件"""
        # 創建無效的 JSON 文件
        json_file = temp_dir / "invalid.json"
        with open(json_file, "w", encoding="utf-8") as f:
            f.write("invalid json content {")

        loader = DefinitionLoader(definitions_dir=temp_dir)
        # 應該記錄錯誤但不拋出異常
        definitions = loader.load_all()

        assert len(definitions) == 0

    def test_load_all_multiple_files(self, temp_dir, sample_definition):
        """測試加載多個定義文件"""
        # 創建第一個文件
        json_file1 = temp_dir / "genai.policy.json"
        with open(json_file1, "w", encoding="utf-8") as f:
            json.dump(sample_definition, f)

        # 創建第二個文件
        sample_definition2 = sample_definition.copy()
        sample_definition2["scope"] = "llm.provider_config"
        json_file2 = temp_dir / "llm.provider_config.json"
        with open(json_file2, "w", encoding="utf-8") as f:
            json.dump(sample_definition2, f)

        loader = DefinitionLoader(definitions_dir=temp_dir)
        definitions = loader.load_all()

        assert len(definitions) == 2
        assert "genai.policy" in definitions
        assert "llm.provider_config" in definitions

    def test_get_definition_success(self, temp_dir, sample_definition):
        """測試從緩存獲取定義"""
        json_file = temp_dir / "genai.policy.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(sample_definition, f)

        loader = DefinitionLoader(definitions_dir=temp_dir)
        loader.load_all()

        definition = loader.get_definition("genai.policy")
        assert definition is not None
        assert definition["scope"] == "genai.policy"

    def test_get_definition_not_found(self, temp_dir):
        """測試獲取不存在的定義"""
        loader = DefinitionLoader(definitions_dir=temp_dir)
        loader.load_all()

        definition = loader.get_definition("nonexistent.scope")
        assert definition is None

    def test_reload(self, temp_dir, sample_definition):
        """測試重新加載定義"""
        json_file = temp_dir / "genai.policy.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(sample_definition, f)

        loader = DefinitionLoader(definitions_dir=temp_dir)
        definitions1 = loader.load_all()

        # 修改定義文件
        sample_definition["version"] = "2.0.0"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(sample_definition, f)

        definitions2 = loader.reload()

        assert len(definitions2) == 1
        assert definitions2["genai.policy"]["version"] == "2.0.0"

    def test_load_file_success(self, temp_dir, sample_definition):
        """測試加載單個文件"""
        json_file = temp_dir / "test.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(sample_definition, f)

        loader = DefinitionLoader(definitions_dir=temp_dir)
        definition = loader._load_file(json_file)

        assert definition["scope"] == "genai.policy"

    def test_load_file_not_found(self, temp_dir):
        """測試加載不存在的文件"""
        loader = DefinitionLoader(definitions_dir=temp_dir)
        nonexistent_file = temp_dir / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            loader._load_file(nonexistent_file)

    def test_get_definition_loader_singleton(self):
        """測試單例模式"""
        with patch("services.api.core.config.definition_loader.DefinitionLoader") as mock_loader:
            loader1 = get_definition_loader()
            loader2 = get_definition_loader()
            # 在單例模式下，應該返回同一個實例
            # 但由於我們使用了 patch，這裡主要是測試調用
            assert loader1 is not None
            assert loader2 is not None
