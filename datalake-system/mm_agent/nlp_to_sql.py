# 代碼功能說明: NLP → SQL 整合流程
# 創建日期: 2026-02-06
# 創建人: AI-Box 開發團隊

"""NLP to SQL Integration - 整合 Router → Extractor → SQLGenerator

流程：
1. Router 判斷任務類型
2. Extractor 提取查詢參數
3. SQLGenerator 生成 SQL
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from mm_agent.router import Router
from mm_agent.extractor import Extractor
from mm_agent.sql_generator import SQLGenerator
from mm_agent.models.query_spec import TaskType

logger = logging.getLogger(__name__)


@dataclass
class NLPToSQLResult:
    """NLP → SQL 結果"""

    success: bool
    task_type: Optional[str] = None
    response: Optional[str] = None
    query_spec: Optional[Dict[str, Any]] = None
    sql: Optional[str] = None
    error: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None


class NLPToSQL:
    """NLP → SQL 整合引擎"""

    def __init__(self):
        """初始化整合引擎"""
        self.router = Router()
        self.extractor = Extractor()
        self.sql_generator = SQLGenerator()

    def classify(self, user_input: str) -> NLPToSQLResult:
        """分類用戶輸入（同步版本）

        Args:
            user_input: 用戶輸入

        Returns:
            NLPToSQLResult: 分類結果
        """
        try:
            result = self.router.classify(user_input)

            if result.task_type == TaskType.GREETING:
                return NLPToSQLResult(
                    success=True,
                    task_type="greeting",
                    response=result.response,
                )

            elif result.task_type == TaskType.ERROR_INPUT:
                return NLPToSQLResult(
                    success=True,
                    task_type="error_input",
                    response=result.response,
                )

            elif result.task_type == TaskType.COMPLEX:
                return NLPToSQLResult(
                    success=True,
                    task_type="complex",
                    debug_info={"message": "Complex task - Todo planning needed"},
                )

            # QUERY - 繼續處理
            return NLPToSQLResult(
                success=True,
                task_type="query",
                debug_info={"needs_extraction": True},
            )

        except Exception as e:
            logger.error(f"分類失敗: {e}", exc_info=True)
            return NLPToSQLResult(
                success=False,
                error=str(e),
            )

    async def process(self, user_input: str) -> NLPToSQLResult:
        """完整處理流程（異步版本）

        Args:
            user_input: 用戶輸入

        Returns:
            NLPToSQLResult: 處理結果
        """
        try:
            # 步驟 1：Router 分類
            classify_result = self.router.classify(user_input)

            logger.info(f"[NLP→SQL] Router 分類: {classify_result.task_type.value}")

            # 步驟 2：根據類型處理
            if classify_result.task_type == TaskType.GREETING:
                return NLPToSQLResult(
                    success=True,
                    task_type="greeting",
                    response=classify_result.response,
                )

            elif classify_result.task_type == TaskType.ERROR_INPUT:
                return NLPToSQLResult(
                    success=True,
                    task_type="error_input",
                    response=classify_result.response,
                )

            elif classify_result.task_type == TaskType.COMPLEX:
                return NLPToSQLResult(
                    success=True,
                    task_type="complex",
                    debug_info={"message": "Complex task - Todo planning needed"},
                )

            # QUERY 類型：繼續提取和生成
            # 步驟 3：Extractor 提取參數
            logger.info(f"[NLP→SQL] Extractor 提取參數...")
            query_spec = await self.extractor.extract(user_input)

            logger.info(f"[NLP→SQL] 提取結果: {query_spec}")

            # 步驟 4：SQLGenerator 生成 SQL
            logger.info(f"[NLP→SQL] SQLGenerator 生成 SQL...")
            sql = self.sql_generator.generate(query_spec)

            logger.info(f"[NLP→SQL] SQL 生成成功")

            return NLPToSQLResult(
                success=True,
                task_type="query",
                query_spec=query_spec,
                sql=sql,
                debug_info={
                    "router_confidence": getattr(classify_result, "confidence", None),
                    "extractor_confidence": query_spec.get("confidence"),
                },
            )

        except Exception as e:
            logger.error(f"處理失敗: {e}", exc_info=True)
            return NLPToSQLResult(
                success=False,
                error=str(e),
            )

    def process_sync(self, user_input: str) -> NLPToSQLResult:
        """同步處理流程

        Args:
            user_input: 用戶輸入

        Returns:
            NLPToSQLResult: 處理結果
        """
        return asyncio.run(self.process(user_input))


# 便捷函數
_nlp_to_sql_engine: Optional[NLPToSQL] = None


def get_nlp_to_sql_engine() -> NLPToSQL:
    """獲取 NLP→SQL 引擎實例"""
    global _nlp_to_sql_engine
    if _nlp_to_sql_engine is None:
        _nlp_to_sql_engine = NLPToSQL()
    return _nlp_to_sql_engine


def nlp_to_sql(user_input: str) -> NLPToSQLResult:
    """便捷函數：NLP → SQL

    Args:
        user_input: 用戶輸入

    Returns:
        NLPToSQLResult: 處理結果
    """
    engine = get_nlp_to_sql_engine()
    return engine.process_sync(user_input)


def nlp_classify(user_input: str) -> NLPToSQLResult:
    """便捷函數：分類用戶輸入

    Args:
        user_input: 用戶輸入

    Returns:
        NLPToSQLResult: 分類結果
    """
    engine = get_nlp_to_sql_engine()
    return engine.classify(user_input)
