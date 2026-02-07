# -*- coding: utf-8 -*-
# 代碼功能說明: Data-Agent 整合層
# 創建日期: 2026-02-06
# 創建人: AI-Box 開發團隊

"""Data-Agent - 數據查詢代理

職責：
1. 接收 SemanticAnalysis（語義分析結果）
2. 生成 SQL 語句
3. 透過 DuckDB 查詢 SeaweedFS 的 Parquet 文件
4. 返回結果

架構：
SeaweedFS (S3) → DuckDB → Parquet Files → Query Results

支持的表：
- img_file: 庫存檔
- ima_file: 品名檔
- tlf_file: 交易檔
- pmn_file: 採購單明細檔
- pmm_file: 採購單頭檔
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

import duckdb

from mm_agent.bpa.semantic_analyzer import BPASemanticAnalyzer, SemanticAnalysis
from mm_agent.sql_generator import SQLGenerator

logger = logging.getLogger(__name__)


class QueryStatus(str, Enum):
    """查詢狀態"""

    SUCCESS = "success"
    CLARIFICATION_NEEDED = "clarification_needed"
    NO_MATCH = "no_match"
    ERROR = "error"


@dataclass
class QueryResult:
    """查詢結果"""

    status: QueryStatus
    sql: Optional[str] = None
    data: Optional[List[Dict]] = None
    row_count: int = 0
    clarification_question: Optional[str] = None
    error: Optional[str] = None
    semantic_analysis: Optional[Dict] = None


class DataAgentConfig:
    """Data-Agent 配置"""

    # S3 / SeaweedFS 配置
    S3_ENDPOINT = "localhost:8334"
    S3_ACCESS_KEY = "admin"
    S3_SECRET_KEY = "admin123"
    S3_USE_SSL = False
    S3_URL_STYLE = "path"

    # Bucket 配置
    BUCKET_NAME = "tiptop-raw"

    # 表路徑映射
    TABLE_PATHS = {
        "img_file": "s3://{bucket}/raw/v1/img_file/year=*/*/data.parquet",
        "ima_file": "s3://{bucket}/raw/v1/ima_file/year=*/*/data.parquet",
        "tlf_file": "s3://{bucket}/raw/v1/tlf_file/year=*/*/data.parquet",
        "pmn_file": "s3://{bucket}/raw/v1/pmn_file/year=*/*/data.parquet",
        "pmm_file": "s3://{bucket}/raw/v1/pmm_file/year=*/*/data.parquet",
    }


class DataAgent:
    """Data-Agent 數據查詢代理

    整合 BPA SemanticAnalyzer、SQLGenerator 和 DuckDB
    實現 NLP → 語義分析 → SQL → DuckDB(S3) → 結果
    """

    def __init__(self, config: Optional[DataAgentConfig] = None, mock: bool = True):
        """初始化 Data-Agent

        Args:
            config: 配置（可選）
            mock: 是否使用 Mock 模式（默認 True）
        """
        self.config = config or DataAgentConfig()
        self.semantic_analyzer = BPASemanticAnalyzer()
        self.sql_generator = SQLGenerator()
        self.mock = mock
        self._duckdb_conn = None
        self._mock_data = self._get_mock_data()

    def _get_mock_data(self) -> Dict[str, List[Dict]]:
        """獲取 Mock 數據"""
        return {
            "QUERY_PURCHASE": [
                {"tlf01": "RM05-008", "ima02": "塑料原料 A", "total_qty": 1000, "tx_count": 5},
                {"tlf01": "RM05-009", "ima02": "塑料原料 B", "total_qty": 2500, "tx_count": 8},
            ],
            "QUERY_STOCK": [
                {"img01": "RM05-008", "ima02": "塑料原料 A", "img02": "RAW01", "total_qty": 5000},
                {"img01": "RM05-009", "ima02": "塑料原料 B", "img02": "RAW01", "total_qty": 3000},
            ],
            "QUERY_SALES": [
                {"tlf01": "FG01-001", "ima02": "成品 A", "total_qty": 200, "tx_count": 3},
            ],
            "ANALYZE_SHORTAGE": [
                {"img01": "RM05-010", "ima02": "塑料原料 C", "img02": "RAW01", "img10": 50},
            ],
            "GENERATE_ORDER": [
                {
                    "pmn01": "PO-2024-001",
                    "pmn02": "1",
                    "pmn04": "RM05-008",
                    "ima02": "塑料原料 A",
                    "pmn20": 1000,
                },
            ],
        }

    def _get_duckdb_connection(self):
        """獲取 DuckDB 連接"""
        if self._duckdb_conn is None:
            self._duckdb_conn = duckdb.connect(":memory:")

            # 配置 S3 連接
            self._duckdb_conn.execute(f"""
                SET s3_endpoint = '{self.config.S3_ENDPOINT}';
                SET s3_access_key_id = '{self.config.S3_ACCESS_KEY}';
                SET s3_secret_access_key = '{self.config.S3_SECRET_KEY}';
                SET s3_use_ssl = {str(self.config.S3_USE_SSL).lower()};
                SET s3_url_style = '{self.config.S3_URL_STYLE}';
            """)

            logger.info("[Data-Agent] DuckDB S3 配置完成")

        return self._duckdb_conn

    def _get_table_path(self, table_name: str) -> str:
        """獲取表的路徑"""
        path_template = self.config.TABLE_PATHS.get(table_name, "")
        return path_template.format(bucket=self.config.BUCKET_NAME)

    def query(self, user_input: str) -> QueryResult:
        """執行查詢

        Args:
            user_input: 用戶輸入

        Returns:
            QueryResult: 查詢結果
        """
        # 步驟 1: 語義分析
        logger.info(f"[Data-Agent] 開始語義分析: {user_input}")
        semantic = self.semantic_analyzer.analyze(user_input)

        # 步驟 2: 檢查是否需要澄清
        if semantic.needs_clarification:
            logger.info(f"[Data-Agent] 需要澄清: {semantic.clarification_issues}")
            return QueryResult(
                status=QueryStatus.CLARIFICATION_NEEDED,
                clarification_question=self._generate_clarification_question(semantic),
                semantic_analysis=self._serialize_semantic(semantic),
            )

        # 步驟 3: 生成 SQL
        logger.info(f"[Data-Agent] 生成 SQL...")
        sql = self._generate_sql(semantic)

        if not sql:
            logger.warning(f"[Data-Agent] 無法生成 SQL")
            return QueryResult(
                status=QueryStatus.NO_MATCH,
                error="無法識別的查詢意圖",
                semantic_analysis=self._serialize_semantic(semantic),
            )

        logger.info(f"[Data-Agent] SQL 生成成功: {sql[:100]}...")

        # 步驟 4: 執行查詢
        if self.mock:
            # Mock 模式
            intent = (
                semantic.intent.value if hasattr(semantic.intent, "value") else str(semantic.intent)
            )
            data = self._mock_data.get(intent, [])
            logger.info(f"[Data-Agent] Mock 模式，返回 {len(data)} 行")
        else:
            # 真實 DuckDB 模式
            try:
                con = self._get_duckdb_connection()
                data = self._execute_sql(con, sql)
                logger.info(f"[Data-Agent] DuckDB 查詢成功，返回 {len(data)} 行")
            except Exception as e:
                logger.error(f"[Data-Agent] DuckDB 查詢失敗: {e}")
                return QueryResult(
                    status=QueryStatus.ERROR,
                    error=str(e),
                    sql=sql,
                    semantic_analysis=self._serialize_semantic(semantic),
                )

        return QueryResult(
            status=QueryStatus.SUCCESS,
            sql=sql,
            data=data,
            row_count=len(data) if data else 0,
            semantic_analysis=self._serialize_semantic(semantic),
        )

    def _generate_sql(self, semantic: SemanticAnalysis) -> Optional[str]:
        """生成 SQL"""
        try:
            # 轉換為 SQLGenerator 格式
            spec_dict = {
                "intent": semantic.intent.value
                if hasattr(semantic.intent, "value")
                else str(semantic.intent),
                "complexity": semantic.complexity.value
                if hasattr(semantic.complexity, "value")
                else str(semantic.complexity),
                "material_id": semantic.material_id,
                "warehouse": semantic.warehouse,
                "time_type": semantic.time_type,
                "time_value": semantic.time_value,
                "transaction_type": semantic.transaction_type,
                "material_category": semantic.material_category,
            }

            sql = self.sql_generator.generate(spec_dict)

            # 將 FROM table 替換為 FROM read_parquet(...)
            sql = self._adapt_sql_for_parquet(sql)

            return sql
        except Exception as e:
            logger.error(f"SQL 生成失敗: {e}")
            return None

    def _adapt_sql_for_parquet(self, sql: str) -> str:
        """適配 SQL 為 Parquet 查詢"""
        # 替換表名為 Parquet 路徑
        table_mappings = {
            # FROM 語句
            "FROM img_file": f"FROM read_parquet('{self._get_table_path('img_file')}', hive_partitioning=true) AS img_file",
            "FROM ima_file": f"FROM read_parquet('{self._get_table_path('ima_file')}', hive_partitioning=true) AS ima_file",
            "FROM tlf_file": f"FROM read_parquet('{self._get_table_path('tlf_file')}', hive_partitioning=true) AS tlf_file",
            "FROM pmn_file": f"FROM read_parquet('{self._get_table_path('pmn_file')}', hive_partitioning=true) AS pmn_file",
            "FROM pmm_file": f"FROM read_parquet('{self._get_table_path('pmm_file')}', hive_partitioning=true) AS pmm_file",
            # LEFT JOIN 語句
            "LEFT JOIN ima_file ON": f"LEFT JOIN read_parquet('{self._get_table_path('ima_file')}', hive_partitioning=true) AS ima_file ON",
            "LEFT JOIN tlf_file ON": f"LEFT JOIN read_parquet('{self._get_table_path('tlf_file')}', hive_partitioning=true) AS tlf_file ON",
            "LEFT JOIN pmm_file ON": f"LEFT JOIN read_parquet('{self._get_table_path('pmm_file')}', hive_partitioning=true) AS pmm_file ON",
        }

        adapted_sql = sql
        for old, new in table_mappings.items():
            adapted_sql = adapted_sql.replace(old, new)

        return adapted_sql

    def _execute_sql(self, con, sql: str) -> List[Dict]:
        """執行 SQL 並返回結果"""
        try:
            # 執行查詢
            result = con.execute(sql)

            # 獲取列名
            columns = [desc[0] for desc in result.description]

            # 獲取所有行
            rows = result.fetchall()

            # 轉換為字典列表
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # 處理 Decimal 類型
                    if hasattr(value, "quantize"):
                        value = float(value)
                    row_dict[col] = value
                data.append(row_dict)

            return data

        except Exception as e:
            logger.error(f"SQL 執行失敗: {e}")
            raise

    def _generate_clarification_question(self, semantic: SemanticAnalysis) -> str:
        """生成澄清問題"""
        issues = semantic.clarification_issues

        if not issues:
            return "請提供更多資訊"

        issue = issues[0]

        if issue.get("type") == "extraction_clarification":
            return issue.get("question", "請提供更多資訊")

        return issue.get("question", "請提供更多資訊")

    def _serialize_semantic(self, semantic: SemanticAnalysis) -> Dict[str, Any]:
        """序列化語義分析結果"""
        return {
            "intent": semantic.intent.value
            if hasattr(semantic.intent, "value")
            else str(semantic.intent),
            "complexity": semantic.complexity.value
            if hasattr(semantic.complexity, "value")
            else str(semantic.complexity),
            "material_id": semantic.material_id,
            "warehouse": semantic.warehouse,
            "time_type": semantic.time_type,
            "time_value": semantic.time_value,
            "transaction_type": semantic.transaction_type,
            "material_category": semantic.material_category,
            "confidence": semantic.confidence,
            "needs_clarification": semantic.needs_clarification,
            "clarification_issues": semantic.clarification_issues,
        }

    def close(self):
        """關閉連接"""
        if self._duckdb_conn:
            self._duckdb_conn.close()
            self._duckdb_conn = None


# 便捷函數
_data_agent: Optional[DataAgent] = None


def get_data_agent() -> DataAgent:
    """獲取 Data-Agent 實例"""
    global _data_agent
    if _data_agent is None:
        _data_agent = DataAgent()
    return _data_agent


def query(user_input: str) -> QueryResult:
    """便捷函數：執行查詢

    Args:
        user_input: 用戶輸入

    Returns:
        QueryResult: 查詢結果
    """
    agent = get_data_agent()
    return agent.query(user_input)
