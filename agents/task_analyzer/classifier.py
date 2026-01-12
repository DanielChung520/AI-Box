# 代碼功能說明: 任務分類器實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-09

"""任務分類器 - 實現任務類型分類邏輯"""

import logging
import re
from typing import Any, Dict, Optional

from agents.task_analyzer.models import TaskClassificationResult, TaskType

logger = logging.getLogger(__name__)


class TaskClassifier:
    """任務分類器"""

    def __init__(self):
        """初始化任務分類器"""
        # 定義關鍵詞模式
        self.patterns = {
            TaskType.QUERY: [
                r"查詢|查詢|搜索|查找|獲取|顯示|列出|告訴我|什麼是|如何|為什麼",
                r"query|search|find|get|show|list|tell|what|how|why",
            ],
            TaskType.EXECUTION: [
                # 基本操作動詞
                r"執行|運行|操作|創建|刪除|更新|修改|發送|調用|執行",
                r"execute|run|perform|create|delete|update|modify|send|call|do",
                # 文件編輯相關動詞
                r"編輯|產生|生成|寫|建立|製作|添加|替換|重寫|格式化",
                r"edit|generate|write|make|build|add|replace|rewrite|format",
                # 隱含編輯意圖動詞
                r"加入|整理|優化|改成|改成|把.*改成",
                r"add.*to|organize|optimize|change.*to|modify.*to",
                # 文件相關名詞（結合動詞時才匹配）
                r"(編輯|產生|創建|生成|寫|建立|製作|修改|更新|刪除|添加|替換|重寫|格式化).*(文件|檔案|文檔)",
                r"(edit|generate|create|write|make|build|modify|update|delete|add|replace|rewrite|format).*(file|document)",
                # 隱含編輯意圖模式（結合文件相關詞）
                r"(幫我在|在).*(文件|檔案|文檔|這個文件|這個檔案|這個文檔).*(加入|添加|添加|改成|整理|優化)",
                r"(幫我整理|幫我優化|把這個).*(文件|檔案|文檔|代碼文件)",
                r"(在文件裡|在文件中|在檔案裡|在檔案中).*(添加|加入|改成)",
            ],
            TaskType.REVIEW: [
                r"審查|檢查|驗證|評估|審核|校對|確認|審批",
                r"review|check|verify|validate|audit|proofread|confirm|approve",
            ],
            TaskType.PLANNING: [
                r"計劃|規劃|設計|安排|制定|準備|組織",
                r"plan|design|arrange|schedule|prepare|organize",
            ],
            TaskType.COMPLEX: [
                r"複雜|多步驟|綜合|整合|協作|多任務",
                r"complex|multi-step|comprehensive|integrate|collaborate|multi-task",
            ],
            TaskType.LOG_QUERY: [
                r"日誌|審計|安全日誌|任務日誌|查看日誌|查詢日誌|顯示日誌|列出日誌|log|audit|security.*log|task.*log",
                r"log|audit|security.*log|task.*log|view.*log|query.*log|show.*log|list.*log",
            ],
        }

    def classify(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskClassificationResult:
        """
        分類任務類型

        Args:
            task: 任務描述
            context: 上下文信息

        Returns:
            任務分類結果
        """
        logger.info(f"Classifying task: {task[:100]}...")

        # 計算每個類型的匹配分數
        scores: Dict[TaskType, float] = {}
        task_lower = task.lower()

        for task_type, patterns in self.patterns.items():
            score = 0.0
            matches = 0

            for pattern in patterns:
                if re.search(pattern, task_lower, re.IGNORECASE):
                    matches += 1
                    score += 0.3

            # 正規化分數
            if matches > 0:
                score = min(score, 1.0)
            else:
                score = 0.1  # 默認最低分數

            scores[task_type] = score

        # 檢查複雜任務標記
        if any(
            keyword in task_lower
            for keyword in [
                "多個",
                "多個步驟",
                "多步驟",
                "綜合",
                "multiple",
                "multi-step",
            ]
        ):
            scores[TaskType.COMPLEX] = max(scores.get(TaskType.COMPLEX, 0.0), 0.8)

        # 選擇得分最高的類型
        if not scores:
            # 默認分類為查詢
            best_type = TaskType.QUERY
            confidence = 0.5
            reasoning = "未找到明確分類模式，默認分類為查詢任務"
        else:
            best_type = max(scores.items(), key=lambda x: x[1])[0]
            confidence = scores[best_type]
            reasoning = f"根據關鍵詞匹配，分類為 {best_type.value} 類型，匹配度 {confidence:.2f}"

        # 考慮上下文信息
        if context:
            if context.get("previous_task_type"):
                # 如果上下文中有之前的任務類型，可能會影響當前分類
                prev_type = context.get("previous_task_type")
                if prev_type in scores:
                    scores[prev_type] += 0.2
                    if scores[prev_type] > confidence:
                        best_type = TaskType(prev_type)
                        confidence = min(scores[prev_type], 1.0)
                        reasoning += f"；考慮上下文，調整為 {best_type.value}"

        logger.info(f"Task classified as {best_type.value} with confidence {confidence:.2f}")

        return TaskClassificationResult(
            task_type=best_type,
            confidence=confidence,
            reasoning=reasoning,
        )
