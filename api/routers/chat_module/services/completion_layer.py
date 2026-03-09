# 代碼功能說明: CompletionLayer - 最終補全層（結果格式化 + Metadata 注入）
# 創建日期: 2026-03-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-09

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class FinalResponse:
    """最終回應數據結構"""

    content: str
    status: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    total_latency_ms: float = 0.0


class CompletionLayer:
    """
    最終補全層 - 負責格式化 BPA 動作結果並注入 perception metadata

    職責：
    1. 從 action_result 提取回覆內容
    2. 處理成功/錯誤情況
    3. 注入 perception 和 intent metadata
    4. 返回統一的 FinalResponse 結構
    """

    def __init__(self) -> None:
        """初始化補全層"""
        self.logger = logger

    async def complete(
        self,
        action_result: Optional[Dict[str, Any]] = None,
        perception_result: Optional[Any] = None,
        intent_result: Optional[Any] = None,
    ) -> FinalResponse:
        """
        完成回應格式化並注入 metadata

        Args:
            action_result: BPA 動作執行結果
            perception_result: 感知層結果（可能包含 perception_metadata）
            intent_result: 意圖分類結果（可能包含 intent_name）

        Returns:
            FinalResponse: 統一的最終回應結構
        """
        start_time = time.time()
        self.logger.info(
            "完成層開始處理",
            has_action_result=action_result is not None,
            has_perception_result=perception_result is not None,
            has_intent_result=intent_result is not None,
        )

        # 初始化元數據
        metadata: Dict[str, Any] = {}
        content = ""
        status = "success"

        # === 情況 1: action_result 不為 None 且無錯誤 ===
        if action_result is not None:
            # 檢查是否有錯誤狀態
            has_error = action_result.get("status") == "error" or "error" in action_result

            if not has_error:
                # 嘗試按順序提取內容
                content = self._extract_content(action_result)
                if content:
                    status = "success"
                    self.logger.info(
                        "成功提取行動結果內容",
                        content_length=len(content),
                    )
                else:
                    # 沒有找到內容，視為錯誤
                    status = "error"
                    content = self._get_error_message()
                    actual_error = action_result
                    metadata["actual_error"] = str(actual_error)
                    self.logger.warning(
                        "無法從行動結果提取內容",
                        action_result=actual_error,
                    )
            else:
                # 發生錯誤
                status = "error"
                content = self._get_error_message()
                actual_error = action_result.get("error", action_result)
                metadata["actual_error"] = str(actual_error)
                self.logger.warning(
                    "行動結果包含錯誤",
                    error=actual_error,
                )
        else:
            # === 情況 2: action_result 為 None ===
            status = "error"
            content = self._get_error_message()
            self.logger.warning("行動結果為空")

        # === 注入 Perception Metadata ===
        if perception_result is not None and hasattr(perception_result, "perception_metadata"):
            metadata["perception"] = perception_result.perception_metadata
            self.logger.info(
                "注入感知元數據",
                perception_keys=list(perception_result.perception_metadata.keys()),
            )

        # === 注入 Intent 信息 ===
        if intent_result is not None and hasattr(intent_result, "intent_name"):
            metadata["intent"] = {
                "name": intent_result.intent_name,
            }
            if hasattr(intent_result, "confidence"):
                metadata["intent"]["confidence"] = intent_result.confidence
            self.logger.info(
                "注入意圖信息",
                intent_name=intent_result.intent_name,
            )

        # === 計算總延遲 ===
        total_latency_ms = (time.time() - start_time) * 1000
        metadata["completed_at"] = time.time()

        response = FinalResponse(
            content=content,
            status=status,
            metadata=metadata,
            total_latency_ms=total_latency_ms,
        )

        self.logger.info(
            "完成層處理完成",
            status=status,
            latency_ms=total_latency_ms,
        )

        return response

    def _extract_content(self, action_result: Dict[str, Any]) -> str:
        """
        按優先級順序從 action_result 提取內容

        嘗試順序:
        1. content
        2. reply
        3. data.content
        4. data.answer
        5. message
        6. result.response

        Args:
            action_result: BPA 動作結果字典

        Returns:
            提取的內容字符串，如果未找到則返回空字符串
        """
        # 直接鍵
        if "content" in action_result and action_result["content"]:
            return str(action_result["content"])

        if "reply" in action_result and action_result["reply"]:
            return str(action_result["reply"])

        if "message" in action_result and action_result["message"]:
            return str(action_result["message"])

        # 嵌套鍵 - data
        data = action_result.get("data")
        if isinstance(data, dict):
            if "content" in data and data["content"]:
                return str(data["content"])
            if "answer" in data and data["answer"]:
                return str(data["answer"])

        # 嵌套鍵 - result
        result = action_result.get("result")
        if isinstance(result, dict):
            if "response" in result and result["response"]:
                return str(result["response"])

        return ""

    def _get_error_message(self) -> str:
        """
        獲取用戶友好的錯誤消息（繁體中文）

        Returns:
            錯誤消息
        """
        return "抱歉，處理您的請求時發生錯誤，請稍後再試。"

    def to_dict(self, response: FinalResponse) -> Dict[str, Any]:
        """
        將 FinalResponse 轉換為字典格式，與現有 OrchestratorService 返回格式相容

        Args:
            response: FinalResponse 物件

        Returns:
            字典格式的回應
        """
        return {
            "content": response.content,
            "status": response.status,
            "metadata": response.metadata,
        }
