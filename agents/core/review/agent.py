# 代碼功能說明: Review Agent 核心實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Review Agent - 實現結果驗證和反饋生成"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from agents.core.review.models import ReviewRequest, ReviewResult, ReviewStatus
from agents.infra.memory import MemoryManager
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from genai.prompt import PromptManager

logger = logging.getLogger(__name__)


class ReviewAgent(AgentServiceProtocol):
    """Review Agent - 審查代理"""

    def __init__(
        self,
        prompt_manager: Optional[PromptManager] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        """
        初始化 Review Agent

        Args:
            prompt_manager: 提示管理器
            memory_manager: 記憶管理器
        """
        self.prompt_manager = prompt_manager or PromptManager()
        self.memory_manager = memory_manager

    def review(self, request: ReviewRequest) -> ReviewResult:
        """
        審查執行結果

        Args:
            request: 審查請求

        Returns:
            審查結果
        """
        logger.info("Reviewing execution result...")

        review_id = str(uuid.uuid4())

        # 步驟1: 驗證結果
        validation_result = self._validate_result(request)

        # 步驟2: 計算質量評分
        quality_score = self._calculate_quality_score(request, validation_result)

        # 步驟3: 生成反饋
        feedback = self._generate_feedback(request, validation_result, quality_score)

        # 步驟4: 生成改進建議
        suggestions = self._generate_suggestions(request, validation_result)

        # 步驟5: 識別問題
        issues = self._identify_issues(request, validation_result)

        # 步驟6: 確定審查狀態
        status = self._determine_status(quality_score, issues)

        # 構建審查結果
        review_result = ReviewResult(
            review_id=review_id,
            status=status,
            quality_score=quality_score,
            feedback=feedback,
            suggestions=suggestions,
            issues=issues,
            metadata=request.metadata,
        )

        # 存儲審查結果到記憶（如果可用）
        if self.memory_manager:
            self.memory_manager.store_short_term(
                key=f"review:{review_id}",
                value=review_result.model_dump(),
                ttl=3600,  # 1小時
            )

        logger.info(
            f"Review completed: review_id={review_id}, "
            f"status={status.value}, "
            f"quality_score={quality_score:.2f}"
        )

        return review_result

    def _validate_result(self, request: ReviewRequest) -> Dict[str, Any]:
        """
        驗證執行結果

        Args:
            request: 審查請求

        Returns:
            驗證結果
        """
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
        }

        result = request.result

        # 基本驗證
        errors: List[str] = validation["errors"]  # type: ignore[assignment]
        if not result:
            validation["is_valid"] = False
            errors.append("結果為空")
            return validation

        # 檢查是否有錯誤字段
        if "error" in result:
            validation["is_valid"] = False
            errors.append(f"執行錯誤: {result['error']}")

        # 檢查成功標記
        if "success" in result and not result["success"]:
            validation["is_valid"] = False
            errors.append("執行未成功")

        # 與預期結果比較（如果提供）
        if request.expected:
            comparison = self._compare_with_expected(result, request.expected)
            validation.update(comparison)

        return validation

    def _compare_with_expected(
        self,
        result: Dict[str, Any],
        expected: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        與預期結果比較

        Args:
            result: 實際結果
            expected: 預期結果

        Returns:
            比較結果
        """
        comparison = {
            "matches_expected": True,
            "differences": [],
        }

        # 簡單的比較邏輯
        differences: List[str] = comparison["differences"]  # type: ignore[assignment]
        for key, expected_value in expected.items():
            if key not in result:
                comparison["matches_expected"] = False
                differences.append(f"缺少字段: {key}")
            elif result[key] != expected_value:
                comparison["matches_expected"] = False
                differences.append(f"字段 {key} 不匹配: 期望 {expected_value}, 實際 {result[key]}")

        return comparison

    def _calculate_quality_score(
        self,
        request: ReviewRequest,
        validation_result: Dict[str, Any],
    ) -> float:
        """
        計算質量評分

        Args:
            request: 審查請求
            validation_result: 驗證結果

        Returns:
            質量評分（0.0-1.0）
        """
        base_score = 1.0

        # 根據驗證結果扣分
        if not validation_result.get("is_valid", True):
            base_score -= 0.5

        error_count = len(validation_result.get("errors", []))
        base_score -= error_count * 0.2

        warning_count = len(validation_result.get("warnings", []))
        base_score -= warning_count * 0.1

        # 根據差異扣分
        if not validation_result.get("matches_expected", True):
            diff_count = len(validation_result.get("differences", []))
            base_score -= diff_count * 0.1

        return max(0.0, min(1.0, base_score))

    def _generate_feedback(
        self,
        request: ReviewRequest,
        validation_result: Dict[str, Any],
        quality_score: float,
    ) -> str:
        """
        生成審查反饋

        Args:
            request: 審查請求
            validation_result: 驗證結果
            quality_score: 質量評分

        Returns:
            反饋文本
        """
        feedback_parts = []

        if quality_score >= 0.8:
            feedback_parts.append("執行結果質量良好。")
        elif quality_score >= 0.6:
            feedback_parts.append("執行結果基本符合要求，但仍有改進空間。")
        else:
            feedback_parts.append("執行結果存在問題，需要改進。")

        # 添加錯誤信息
        errors = validation_result.get("errors", [])
        if errors:
            feedback_parts.append(f"發現 {len(errors)} 個錯誤：")
            feedback_parts.extend([f"- {error}" for error in errors[:3]])

        # 添加警告信息
        warnings = validation_result.get("warnings", [])
        if warnings:
            feedback_parts.append(f"發現 {len(warnings)} 個警告：")
            feedback_parts.extend([f"- {warning}" for warning in warnings[:3]])

        return "\n".join(feedback_parts)

    def _generate_suggestions(
        self,
        request: ReviewRequest,
        validation_result: Dict[str, Any],
    ) -> List[str]:
        """
        生成改進建議

        Args:
            request: 審查請求
            validation_result: 驗證結果

        Returns:
            建議列表
        """
        suggestions = []

        # 根據錯誤生成建議
        errors = validation_result.get("errors", [])
        if errors:
            suggestions.append("檢查並修復發現的錯誤")
            suggestions.append("增強錯誤處理機制")

        # 根據差異生成建議
        differences = validation_result.get("differences", [])
        if differences:
            suggestions.append("確保結果與預期一致")
            suggestions.append("檢查數據格式和內容")

        # 根據審查標準生成建議
        if request.criteria:
            suggestions.append("確保滿足所有審查標準")

        return suggestions

    def _identify_issues(
        self,
        request: ReviewRequest,
        validation_result: Dict[str, Any],
    ) -> List[str]:
        """
        識別問題

        Args:
            request: 審查請求
            validation_result: 驗證結果

        Returns:
            問題列表
        """
        issues = []

        # 添加驗證錯誤作為問題
        issues.extend(validation_result.get("errors", []))

        # 添加差異作為問題
        differences = validation_result.get("differences", [])
        issues.extend(differences)

        # 添加警告作為問題
        warnings = validation_result.get("warnings", [])
        issues.extend([f"警告: {w}" for w in warnings])

        return issues

    def _determine_status(
        self,
        quality_score: float,
        issues: List[str],
    ) -> ReviewStatus:
        """
        確定審查狀態

        Args:
            quality_score: 質量評分
            issues: 問題列表

        Returns:
            審查狀態
        """
        if quality_score >= 0.8 and not issues:
            return ReviewStatus.APPROVED
        elif quality_score >= 0.6:
            return ReviewStatus.NEEDS_REVISION
        else:
            return ReviewStatus.REJECTED

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行審查任務（實現 AgentServiceProtocol 接口）

        Args:
            request: Agent 服務請求

        Returns:
            Agent 服務響應
        """
        try:
            # 從 task_data 中提取 ReviewRequest 數據
            task_data = request.task_data
            review_request = ReviewRequest(**task_data)

            # 調用原有的 review 方法
            review_result = self.review(review_request)

            # 轉換為 AgentServiceResponse
            return AgentServiceResponse(
                task_id=request.task_id,
                status=review_result.status.value,
                result=review_result.model_dump(),
                error=None,
                metadata=request.metadata,
            )

        except Exception as e:
            logger.error(f"Review Agent execution failed: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=str(e),
                metadata=request.metadata,
            )

    async def health_check(self) -> AgentServiceStatus:
        """
        健康檢查（實現 AgentServiceProtocol 接口）

        Returns:
            服務狀態
        """
        try:
            # 檢查 prompt_manager 和 memory_manager 是否可用
            if self.prompt_manager:
                return AgentServiceStatus.AVAILABLE
            return AgentServiceStatus.UNAVAILABLE
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return AgentServiceStatus.ERROR

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        獲取服務能力（實現 AgentServiceProtocol 接口）

        Returns:
            服務能力描述
        """
        return {
            "name": "Review Agent",
            "description": "結果驗證和反饋生成服務",
            "capabilities": [
                "result_validation",  # 結果驗證
                "quality_scoring",  # 質量評分
                "feedback_generation",  # 反饋生成
                "issue_identification",  # 問題識別
            ],
            "version": "1.0.0",
        }
