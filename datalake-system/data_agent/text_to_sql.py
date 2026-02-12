# 代碼功能說明: Text-to-SQL 轉換服務
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10
#
# 架構說明:
# - 使用 RAG 檢索相關表格
# - 使用 metadata/services/ 生成 Prompt
# - 完整的 Token 使用統計（用於計費）

"""Text-to-SQL 轉換服務 - 使用 RAG + Metadata Services"""

import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from agents.task_analyzer.models import LLMProvider
from llm.clients.factory import get_client

logger = logging.getLogger(__name__)

# Token 統計服務（全局）
_token_stats_service = None


def _get_token_stats_service():
    """獲取 Token 統計服務（延遲導入）"""
    global _token_stats_service
    if _token_stats_service is None:
        try:
            from services.api.services.token_stats_service import get_token_stats_service

            _token_stats_service = get_token_stats_service()
        except Exception:
            return None
    return _token_stats_service


class TokenStats:
    """Token 使用統計"""

    def __init__(
        self,
        task_id: str = "",
        user_id: str = "",
        operation: str = "text_to_sql",
    ):
        self.task_id = task_id
        self.user_id = user_id
        self.operation = operation
        self.start_time = time.time()

        # Prompt 相關
        self.prompt_length = 0
        self.prompt_tokens = 0

        # LLM 回應相關
        self.completion_tokens = 0
        self.response_length = 0
        self.response_text = ""

        # 回送數據相關
        self.output_data_size = 0
        self.output_rows = 0

        # 錯誤統計
        self._error = None
        self.success = True

    @property
    def error(self) -> Optional[str]:
        return self._error

    @error.setter
    def error(self, value: str):
        self._error = value

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        elapsed_ms = int((time.time() - self.start_time) * 1000)
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "operation": self.operation,
            "prompt": {
                "length": self.prompt_length,
                "tokens": self.prompt_tokens,
            },
            "response": {
                "length": self.response_length,
                "tokens": self.completion_tokens,
            },
            "output": {
                "data_size_bytes": self.output_data_size,
                "rows": self.output_rows,
            },
            "latency_ms": elapsed_ms,
            "success": self.success,
            "error": self.error,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
        }


# SQL 注入檢測模式
SQL_INJECTION_PATTERNS = [
    r"\bOR\b.*=.*",
    r"'.*UNION.*",
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bTRUNCATE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\b--\b",
    r"\b;\s*\w",
    r"'\s*OR\s+'1'\s*=\s*'1'",
]


def sanitize_natural_language_query(query: str) -> Tuple[bool, str]:
    """
    檢測並清理自然語言查詢，防止 SQL 注入攻擊
    """
    if not query:
        return True, ""

    query_upper = query.upper()

    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, query_upper):
            return False, "檢測到潛在 SQL 注入攻擊，請重新輸入查詢"

    return True, ""


def estimate_tokens(text: str) -> int:
    """
    估算 Token 數量（中英文混合）

    估算方法：
    - 英文：平均 4 字符 = 1 token
    - 中文：平均 1-2 字符 = 1 token
    - 混合：使用簡化估算
    """
    if not text:
        return 0

    # 簡化估算：中文字符約 2 字符/token，英文字符約 4 字符/token
    chinese_chars = sum(1 for c in text if ord(c) > 127)
    english_chars = len(text) - chinese_chars

    # 中文按 1.5 字符/token 估算，英文按 4 字符/token 估算
    return int(chinese_chars / 1.5 + english_chars / 4)


class TextToSQLService:
    """Text-to-SQL 轉換服務 - 使用 RAG + Metadata Services"""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        system_id: str = "tiptop_erp",
        metadata_root: Optional[Path] = None,
    ):
        self._llm_provider = llm_provider or LLMProvider.OLLAMA
        self._llm_client = None
        self._logger = logger
        self._system_id = system_id

        from datalake_system.metadata.services import PromptBuilder, SmartSchemaLoader
        from datalake_system.data_agent.schema_rag import SchemaRAGService

        if metadata_root is None:
            metadata_root = ai_box_root / "datalake-system" / "metadata"

        self._loader = SmartSchemaLoader(metadata_root)
        self._builder = PromptBuilder(self._loader)
        self._rag = SchemaRAGService(metadata_root)

        logger.info(f"TextToSQLService 初始化完成，系統: {system_id}")

    def _get_llm_client(self):
        """獲取 LLM client"""
        if self._llm_client is None:
            self._llm_client = get_client(self._llm_provider)
        return self._llm_client

    async def generate_sql(
        self,
        instruction: str,
        task_id: str = "",
        user_id: str = "",
    ) -> Dict[str, Any]:
        """
        從自然語言生成 SQL

        Args:
            instruction: 用戶輸入（自然語言）
            task_id: 任務 ID（用於 Token 統計）
            user_id: 用戶 ID（用於 Token 統計）

        Returns:
            {
                'success': bool,
                'sql': str,
                'error': str,
                'tokens': {
                    'prompt_tokens': int,
                    'completion_tokens': int,
                    'total_tokens': int,
                },
                'latency_ms': int,
            }
        """
        stats = TokenStats(task_id=task_id, user_id=user_id, operation="text_to_sql")

        try:
            # 1. RAG 檢索相關表格（必選！）
            rag_results = self._rag.retrieve(
                query=instruction,
                system_id=self._system_id,
                top_k=7,
            )
            relevant_tables = self._rag.get_table_names(rag_results)

            logger.info(f"RAG 檢索結果: {relevant_tables}")

            # 2. 生成 Prompt（只包含相關表）
            from datalake_system.metadata.services import SQLDialect

            prompt = self._builder.build_schema_prompt(
                system_id=self._system_id,
                table_names=relevant_tables,
                user_query=instruction,
                dialect=SQLDialect.DUCKDB,
            )

            # 統計 Prompt
            stats.prompt_length = len(prompt)
            stats.prompt_tokens = estimate_tokens(prompt)

            # 3. 調用 LLM
            client = self._get_llm_client()
            start_time = time.time()
            response = await client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=800,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            sql = response.get("text", "") or response.get("content", "")
            sql = sql.strip()
            sql = sql.replace("```sql", "").replace("```", "").strip()

            # 統計回應
            stats.response_length = len(sql)
            stats.response_text = sql

            # 從 LLM 回應提取 Token 使用量
            if "usage" in response:
                stats.prompt_tokens = response["usage"].get("prompt_tokens", stats.prompt_tokens)
                stats.completion_tokens = response["usage"].get("completion_tokens", 0)
            else:
                stats.completion_tokens = estimate_tokens(sql)

            # 4. 記錄 Token 統計
            self._log_token_stats(stats, latency_ms)

            return {
                "success": True,
                "sql": sql,
                "error": None,
                "tokens": {
                    "prompt_tokens": stats.prompt_tokens,
                    "completion_tokens": stats.completion_tokens,
                    "total_tokens": stats.prompt_tokens + stats.completion_tokens,
                },
                "latency_ms": latency_ms,
            }

        except Exception as e:
            stats.success = False
            stats.error = str(e)
            self._logger.error(f"Text-to-SQL 失敗: {e}")

            # 記錄錯誤統計
            self._log_token_stats(stats, int((time.time() - stats.start_time) * 1000))

            return {
                "success": False,
                "sql": None,
                "error": str(e),
                "tokens": {
                    "prompt_tokens": stats.prompt_tokens,
                    "completion_tokens": stats.completion_tokens,
                    "total_tokens": stats.prompt_tokens + stats.completion_tokens,
                },
                "latency_ms": int((time.time() - stats.start_time) * 1000),
            }

    def _log_token_stats(self, stats: TokenStats, latency_ms: int):
        """記錄 Token 統計"""
        try:
            service = _get_token_stats_service()
            if service is None:
                return

            # 記錄到服務
            stats_data = stats.to_dict()
            stats_data["latency_ms"] = latency_ms

            # 異步記錄（不阻塞）
            import threading

            threading.Thread(
                target=service.record_usage,
                args=(stats_data,),
                daemon=True,
            ).start()

            # 同時記錄到日誌
            total_tokens = stats.prompt_tokens + stats.completion_tokens
            self._logger.info(
                f"Token 統計: "
                f"prompt={stats.prompt_tokens}, "
                f"completion={stats.completion_tokens}, "
                f"total={total_tokens}, "
                f"latency={latency_ms}ms, "
                f"success={stats.success}"
            )

        except Exception as e:
            self._logger.warning(f"記錄 Token 統計失敗: {e}")

    def update_output_stats(self, task_id: str, rows: int, data_size: int):
        """更新輸出數據統計（SQL 執行完成後調用）"""
        try:
            service = _get_token_stats_service()
            if service is None:
                return

            # 異步更新
            import threading

            threading.Thread(
                target=service.update_output,
                args=(task_id, rows, data_size),
                daemon=True,
            ).start()

        except Exception as e:
            self._logger.warning(f"更新輸出統計失敗: {e}")

    async def convert(self, natural_language: str, **kwargs) -> Dict[str, Any]:
        """轉換自然語言為 SQL（兼容舊接口）"""
        return await self.generate_sql(natural_language)


TextToSQLServiceWithRAG = TextToSQLService
