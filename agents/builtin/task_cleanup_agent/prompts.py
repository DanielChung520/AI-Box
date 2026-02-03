# 代碼功能說明: Task Cleanup Agent LLM Prompt 模板
# 創建日期: 2026-01-23
# 創建人: Daniel Chung

"""LLM Prompt 模板，用於 Task Cleanup Agent 的分析和驗證。"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class CleanupAnalysis:
    """清理分析結果"""
    urgency: str  # "high" / "medium" / "low",
    risk_level: str  # "high" / "medium" / "low",
    analysis: str
    recommendation: str


@dataclass
class CleanupPlan:
    """清理計劃"""
    steps: List[str] 
    estimated_impact: str
    warnings: List[str]


@dataclass
class CleanupVerification:
    """清理驗證結果"""
    is_complete: bool
    findings: str
    suggestions: List[str]


class CleanupPrompts:
    """清理任務的 Prompt 模板集合"""
    # ========== 分析階段 Prompt ==========
    @staticmethod
    def analyze(user_id: str, task_id: str | None, stats: Dict[str, int]) -> str:
        """生成數據分析 Prompt

        Args:
            user_id: 用戶 ID
            task_id: 任務 ID (可選) 
            stats: 掃描統計結果

        Returns:
            LLM 分析 Prompt
        """
        task_scope = f"任務 {task_id}" if task_id else f"用戶 {user_id} 的所有任務"

        return f"""你是一個數據清理分析專家。請分析以下數據狀況：

## 清理範圍
- 用戶: {user_id}
- 範圍: {task_scope}

## 數據統計
- user_tasks: {stats.get("user_tasks", 0)} 個任務記錄
- file_metadata: {stats.get("file_metadata", 0)} 個文件元數據
- entities: {stats.get("entities", 0)} 個知識圖譜實體
- relations: {stats.get("relations", 0)} 個知識圖譜關係
- qdrant_collections: {stats.get("qdrant_collections", 0)} 個向量集合
- seaweedfs_directories: {stats.get("seaweedfs_directories", 0)} 個存儲目錄

請分析並返回 JSON 格式：
{{
    "urgency": "high/medium/low",
    "risk_level": "high/medium/low",
    "analysis": "數據規模和複雜度的分析描述",
    "recommendation": "是否建議清理的建議"
}}

只返回 JSON，不要有其他內容。"""
    # ========== 計劃階段 Prompt ==========
    @staticmethod
    def generate_plan(
        user_id: str, task_id: str | None, stats: Dict[str, int], analysis: Dict[str, str]
    ) -> str:
        """生成清理計劃 Prompt

        Args:
            user_id: 用戶 ID
            task_id: 任務 ID (可選) 
            stats: 掃描統計結果
            analysis: LLM 分析結果

        Returns:
            清理計劃 Prompt
        """
        task_scope = f"任務 {task_id}" if task_id else f"用戶 {user_id} 的所有數據"

        return f"""基於以下分析結果,請生成清理計劃:

## 清理範圍
- 用戶: {user_id}
- 範圍: {task_scope}

## 數據統計
- {stats.get("user_tasks", 0)} 個任務
- {stats.get("file_metadata", 0)} 個文件元數據
- {stats.get("entities", 0)} 個實體
- {stats.get("relations", 0)} 個關係

## 分析結果
- 緊急性: {analysis.get("urgency", "unknown")}
- 風險等級: {analysis.get("risk_level", "unknown")}
- 分析: {analysis.get("analysis", "")}
- 建議: {analysis.get("recommendation", "")}

請生成清理計劃,返回 JSON 格式:
{{
    "steps": [
        "步驟1: 刪除 ArangoDB 中的 X 個任務記錄",
        "步驟2: 刪除 X 個文件元數據",
        "步驟3: 刪除 Y 個知識圖譜實體和關係",
        "步驟4: 清理 Z 個 Qdrant 向量集合"
    ],
    "estimated_impact": "預估影響描述",
    "warnings": ["警告1", "警告2"]
}}

只返回 JSON,不要有其他內容。"""
    # ========== 驗證階段 Prompt ==========
    @staticmethod
    def verify(
        user_id: str, task_id: str | None, stats: Dict[str, int], result: Dict[str, int]
    ) -> str:
        """生成清理驗證 Prompt

        Args:
            user_id: 用戶 ID
            task_id: 任務 ID (可選) 
            stats: 預期清理數量
            result: 實際清理結果

        Returns:
            驗證 Prompt
        """
        return f"""請驗證清理結果：

## 清理範圍
- 用戶: {user_id}
- 任務: {task_id or "所有任務"}

## 預期清理
- user_tasks: {stats.get("user_tasks", 0)} 個
- file_metadata: {stats.get("file_metadata", 0)} 個
- entities: {stats.get("entities", 0)} 個
- relations: {stats.get("relations", 0)} 個

## 實際清理結果
- user_tasks: {result.get("user_tasks", 0)} 個
- file_metadata: {result.get("file_metadata", 0)} 個
- entities: {result.get("entities", 0)} 個
- relations: {result.get("relations", 0)} 個

請驗證並返回 JSON 格式：
{{
    "is_complete": true/false,
    "findings": "驗證發現描述",
    "suggestions": ["建議1", "建議2"]
}}

只返回 JSON，不要有其他內容。"""
# 便捷函數
def analyze_prompt(user_id: str, task_id: str | None, stats: Dict[str, int]) -> str:
    return CleanupPrompts.analyze(user_id, task_id, stats)


def plan_prompt(
    user_id: str, task_id: str | None, stats: Dict[str, int], analysis: Dict[str, str]
) -> str:
    return CleanupPrompts.generate_plan(user_id, task_id, stats, analysis)


def verify_prompt(
    user_id: str, task_id: str | None, stats: Dict[str, int], result: Dict[str, int]
) -> str:
    return CleanupPrompts.verify(user_id, task_id, stats, result)