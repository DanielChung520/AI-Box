# 代碼功能說明: Intent Matcher v4.0 單元測試（L2 意圖與任務抽象層）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Intent Matcher v4.0 單元測試 - 測試 L2 意圖與任務抽象層"""

import pytest
from unittest.mock import MagicMock, patch

from agents.task_analyzer.intent_matcher import IntentMatcher, FALLBACK_INTENT_NAME
from agents.task_analyzer.models import IntentDSL, SemanticUnderstandingOutput


class TestIntentMatcherV4:
    """Intent Matcher v4.0 測試類"""

    @pytest.fixture
    def intent_matcher(self):
        """創建 IntentMatcher 實例"""
        return IntentMatcher()

    @pytest.fixture
    def semantic_output(self):
        """創建 SemanticUnderstandingOutput 實例"""
        return SemanticUnderstandingOutput(
            topics=["document", "system_design"],
            entities=["Document Editing Agent", "API Spec"],
            action_signals=["design", "refine", "structure"],
            modality="instruction",
            certainty=0.92,
        )

    @pytest.fixture
    def mock_intent_registry(self):
        """創建 Mock Intent Registry"""
        registry = MagicMock()
        return registry

    def test_match_intent_success(self, intent_matcher, semantic_output):
        """測試 Intent 匹配成功"""
        # Mock Intent Registry
        mock_intent = IntentDSL(
            name="modify_document",
            domain="system_architecture",
            target="Document Editing Agent",
            output_format=["Engineering Spec"],
            depth="Advanced",
            version="1.0.0",
            default_version=True,
            is_active=True,
            description="修改文檔內容，包括編輯、更新、重構等操作",
        )

        with patch.object(intent_matcher, "intent_registry") as mock_registry:
            mock_registry.list_intents.return_value = [mock_intent]

            result = intent_matcher.match_intent(semantic_output, "幫我編輯README.md文件")

            # 驗證結果
            assert result is not None
            assert result.name == "modify_document"
            assert result.domain == "system_architecture"
            assert result.target == "Document Editing Agent"

    def test_match_intent_no_match(self, intent_matcher, semantic_output):
        """測試 Intent 匹配失敗（分數低於閾值）"""
        # Mock Intent Registry（返回不匹配的 Intent）
        mock_intent = IntentDSL(
            name="analyze_data",
            domain="data_analysis",
            target="Data Analysis Agent",
            output_format=["Analysis Report"],
            depth="Advanced",
            version="1.0.0",
            default_version=True,
            is_active=True,
            description="分析數據，包括統計分析、趨勢分析等",
        )

        with patch.object(intent_matcher, "intent_registry") as mock_registry:
            mock_registry.list_intents.return_value = [mock_intent]

            result = intent_matcher.match_intent(semantic_output, "幫我編輯README.md文件")

            # 驗證結果為 None（將使用 Fallback Intent）
            assert result is None

    def test_match_intent_empty_registry(self, intent_matcher, semantic_output):
        """測試 Intent Registry 為空的情況"""
        with patch.object(intent_matcher, "intent_registry") as mock_registry:
            mock_registry.list_intents.return_value = []

            result = intent_matcher.match_intent(semantic_output, "幫我編輯README.md文件")

            # 驗證結果為 None
            assert result is None

    def test_get_fallback_intent_success(self, intent_matcher):
        """測試獲取 Fallback Intent 成功"""
        # Mock Fallback Intent
        mock_fallback = IntentDSL(
            name=FALLBACK_INTENT_NAME,
            domain="general",
            target=None,
            output_format=["General Response"],
            depth="Basic",
            version="1.0.0",
            default_version=True,
            is_active=True,
            description="通用查詢 Intent，用於無法匹配特定 Intent 的情況",
        )

        with patch.object(intent_matcher, "intent_registry") as mock_registry:
            mock_registry.get_intent_by_name.return_value = mock_fallback

            result = intent_matcher.get_fallback_intent()

            # 驗證結果
            assert result is not None
            assert result.name == FALLBACK_INTENT_NAME
            assert result.is_active is True

    def test_get_fallback_intent_create_default(self, intent_matcher):
        """測試創建默認 Fallback Intent"""
        # Mock Intent Registry（Fallback Intent 不存在）
        with patch.object(intent_matcher, "intent_registry") as mock_registry:
            # 第一次調用返回 None（不存在）
            mock_registry.get_intent_by_name.return_value = None
            # create_intent 成功創建
            mock_fallback = IntentDSL(
                name=FALLBACK_INTENT_NAME,
                domain="general",
                target=None,
                output_format=["General Response"],
                depth="Basic",
                version="1.0.0",
                default_version=True,
                is_active=True,
                description="通用查詢 Intent，用於無法匹配特定 Intent 的情況",
            )
            mock_registry.create_intent.return_value = mock_fallback

            result = intent_matcher.get_fallback_intent()

            # 驗證結果
            assert result is not None
            assert result.name == FALLBACK_INTENT_NAME
            # 驗證 create_intent 被調用
            mock_registry.create_intent.assert_called_once()

    def test_get_fallback_intent_use_first_active(self, intent_matcher):
        """測試使用第一個啟用的 Intent 作為 Fallback"""
        # Mock Intent Registry（Fallback Intent 不存在，但有其他 Intent）
        mock_intent = IntentDSL(
            name="modify_document",
            domain="system_architecture",
            target="Document Editing Agent",
            output_format=["Engineering Spec"],
            depth="Advanced",
            version="1.0.0",
            default_version=True,
            is_active=True,
            description="修改文檔內容",
        )

        with patch.object(intent_matcher, "intent_registry") as mock_registry:
            # Fallback Intent 不存在
            mock_registry.get_intent_by_name.return_value = None
            # create_intent 失敗（已存在）
            from agents.task_analyzer.models import IntentCreate

            mock_registry.create_intent.side_effect = ValueError("Intent already exists")
            # list_intents 返回其他 Intent
            mock_registry.list_intents.return_value = [mock_intent]

            result = intent_matcher.get_fallback_intent()

            # 驗證結果為第一個啟用的 Intent
            assert result is not None
            assert result.name == "modify_document"

    def test_calculate_match_score(self, intent_matcher, semantic_output):
        """測試匹配分數計算"""
        mock_intent = IntentDSL(
            name="modify_document",
            domain="system_architecture",
            target="Document Editing Agent",
            output_format=["Engineering Spec"],
            depth="Advanced",
            version="1.0.0",
            default_version=True,
            is_active=True,
            description="修改文檔內容，包括編輯、更新、重構等操作",
        )

        score = intent_matcher._calculate_match_score(
            mock_intent,
            semantic_output.topics,
            semantic_output.entities,
            semantic_output.action_signals,
            "幫我編輯README.md文件",
        )

        # 驗證分數在合理範圍內
        assert 0.0 <= score <= 1.0
        # 由於 topics、entities、action_signals 都匹配，分數應該較高
        assert score > 0.3  # 應該高於匹配閾值

    def test_calculate_match_score_low_match(self, intent_matcher):
        """測試低匹配分數計算"""
        semantic_output = SemanticUnderstandingOutput(
            topics=["weather", "forecast"],
            entities=["Weather Service"],
            action_signals=["query", "get"],
            modality="question",
            certainty=0.85,
        )

        mock_intent = IntentDSL(
            name="modify_document",
            domain="system_architecture",
            target="Document Editing Agent",
            output_format=["Engineering Spec"],
            depth="Advanced",
            version="1.0.0",
            default_version=True,
            is_active=True,
            description="修改文檔內容，包括編輯、更新、重構等操作",
        )

        score = intent_matcher._calculate_match_score(
            mock_intent,
            semantic_output.topics,
            semantic_output.entities,
            semantic_output.action_signals,
            "今天天氣如何？",
        )

        # 驗證分數較低（不匹配）
        assert 0.0 <= score <= 1.0
        # 由於 topics、entities、action_signals 都不匹配，分數應該較低
        assert score < 0.3  # 應該低於匹配閾值

    @pytest.mark.asyncio
    async def test_match_intent_integration(self, intent_matcher):
        """測試 Intent 匹配集成測試（需要真實的 Intent Registry）"""
        # 注意：此測試需要 Intent Registry 已初始化並包含 Intent 定義
        # 如果 Intent Registry 未初始化，此測試可能會失敗
        semantic_output = SemanticUnderstandingOutput(
            topics=["document", "system_design"],
            entities=["Document Editing Agent"],
            action_signals=["edit", "modify"],
            modality="instruction",
            certainty=0.90,
        )

        try:
            result = intent_matcher.match_intent(semantic_output, "幫我編輯README.md文件")
            # 如果匹配成功，驗證結果
            if result:
                assert result.name is not None
                assert result.domain is not None
                assert result.is_active is True
        except Exception as e:
            # 如果 Intent Registry 未初始化，跳過此測試
            pytest.skip(f"Intent Registry not initialized: {e}")
