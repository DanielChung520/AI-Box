# 代碼功能說明: Resolver 狀態機
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10

"""Resolver 狀態機

職責：
- 執行狀態機流程
- 解析 NLQ、匹配概念、解析綁定
- 生成 Physical Query AST

狀態流程：
INIT → PARSE_NLQ → MATCH_CONCEPTS → RESOLVE_BINDINGS
→ VALIDATE → BUILD_AST → EMIT_SQL → EXECUTE
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

from .config import get_config, SchemaDrivenQueryConfig
from .models import (
    ParsedIntent,
    MatchedConcept,
    ResolvedBinding,
    QueryAST,
    IntentDefinition,
    ConceptDefinition,
    BindingColumn,
    IntentsContainer,
    ConceptsContainer,
    BindingsContainer,
    OperatorType,
)

logger = logging.getLogger(__name__)


class ResolverState(str, Enum):
    """Resolver 狀態"""

    INIT = "INIT"
    PARSE_NLQ = "PARSE_NLQ"
    MATCH_CONCEPTS = "MATCH_CONCEPTS"
    RESOLVE_BINDINGS = "RESOLVE_BINDINGS"
    VALIDATE = "VALIDATE"
    BUILD_AST = "BUILD_AST"
    EMIT_SQL = "EMIT_SQL"
    EXECUTE = "EXECUTE"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class ResolverError(Exception):
    """Resolver 錯誤"""

    def __init__(self, state: ResolverState, message: str, details: Optional[Dict] = None):
        self.state = state
        self.message = message
        self.details = details or {}
        super().__init__(f"[{state.value}] {message}")


class ResolverContext:
    """Resolver 上下文"""

    def __init__(self, nlq: str):
        self.nlq = nlq
        self.state = ResolverState.INIT
        self.state_history: List[ResolverState] = []
        self.parsed: Optional[ParsedIntent] = None
        self.matched_concepts: Dict[str, MatchedConcept] = {}
        self.resolved_bindings: List[ResolvedBinding] = []
        self.intent: Optional[IntentDefinition] = None
        self.ast: Optional[QueryAST] = None
        self.sql: str = ""
        self.error: Optional[str] = None

    def transition_to(self, new_state: ResolverState):
        """狀態轉換"""
        self.state = new_state
        self.state_history.append(new_state)
        logger.debug(f"State transition: {new_state.value}")


class Resolver:
    """
    Schema Driven Query Resolver

    狀態機實現：
    1. INIT - 初始化
    2. PARSE_NLQ - 解析 NLQ
    3. MATCH_CONCEPTS - 匹配概念
    4. RESOLVE_BINDINGS - 解析綁定
    5. VALIDATE - 驗證
    6. BUILD_AST - 生成 AST
    7. EMIT_SQL - 生成 SQL
    8. EXECUTE - 執行
    """

    def __init__(
        self,
        config: Optional[SchemaDrivenQueryConfig] = None,
        intents: Optional[IntentsContainer] = None,
        concepts: Optional[ConceptsContainer] = None,
        bindings: Optional[BindingsContainer] = None,
    ):
        self.config = config or get_config()
        self._intents = intents
        self._concepts = concepts
        self._bindings = bindings

        # 延遲載入 loader
        self._loader = None

    def load_schemas(self):
        """載入 Schema 定義"""
        from .loaders import get_schema_loader

        self._loader = get_schema_loader(self.config)
        self._intents = self._loader.load_intents()
        self._concepts = self._loader.load_concepts()
        self._bindings = self._loader.load_bindings()

    def _get_intent(self, name: str) -> Optional[IntentDefinition]:
        """獲取意圖定義"""
        if self._intents:
            return self._intents.intents.get(name)
        return None

    def _get_concept(self, name: str) -> Optional[ConceptDefinition]:
        """獲取概念定義"""
        if self._concepts:
            return self._concepts.concepts.get(name)
        return None

    def _get_binding(self, concept: str, datasource: str = "ORACLE") -> Optional[BindingColumn]:
        """獲取綁定定義"""
        if self._bindings:
            return self._bindings.bindings.get(concept, {}).get(datasource)
        return None

    def resolve(self, nlq: str) -> Dict[str, Any]:
        """
        執行狀態機

        Args:
            nlq: 自然語言查詢

        Returns:
            Dict: 查詢結果
        """
        context = ResolverContext(nlq)

        try:
            # State 0: INIT
            context.transition_to(ResolverState.INIT)
            logger.info(f"Start resolving NLQ: {nlq[:50]}...")

            # State 1: PARSE_NLQ
            context = self._parse_nlq(context)

            # State 2: MATCH_CONCEPTS
            context = self._match_concepts(context)

            # State 3: RESOLVE_BINDINGS
            context = self._resolve_bindings(context)

            # State 4: VALIDATE
            context = self._validate(context)

            # State 5: BUILD_AST
            context = self._build_ast(context)

            # State 6: EMIT_SQL
            context = self._emit_sql(context)

            # State 7: COMPLETED
            context.transition_to(ResolverState.COMPLETED)

            logger.info(f"Resolved successfully: {context.sql[:50]}...")

            return {
                "status": "success",
                "sql": context.sql,
                "state_history": [s.value for s in context.state_history],
            }

        except ResolverError as e:
            logger.error(f"Resolver error: {e}")
            context.transition_to(ResolverState.ERROR)
            return {
                "status": "error",
                "error_code": e.state.value,
                "message": e.message,
                "details": e.details,
                "state_history": [s.value for s in context.state_history],
            }

    def _parse_nlq(self, context: ResolverContext) -> ResolverContext:
        """State 1: 解析 NLQ"""
        from .parser import SimpleNLQParser, LLMNLQParser

        context.transition_to(ResolverState.PARSE_NLQ)

        # 使用 LLM 作為主要解析器
        llm_parser = LLMNLQParser(skip_validation=True)
        llm_parser.load_intents(self._intents)

        parsed = llm_parser.parse(context.nlq)

        # 如果 LLM 解析失敗或信心度低，嘗試簡單解析器
        if parsed.confidence < 0.3:
            logger.warning(
                f"LLM parsing confidence too low ({parsed.confidence}), falling back to simple parser"
            )
            simple_parser = SimpleNLQParser(skip_validation=True)
            simple_parser.load_intents(self._intents)
            parsed = simple_parser.parse(context.nlq)

        if parsed.confidence < 0.3:
            raise ResolverError(
                ResolverState.PARSE_NLQ,
                f"無法識別查詢意圖 (confidence: {parsed.confidence})",
                {"nlq": context.nlq},
            )

        context.parsed = parsed
        logger.info(
            f"Parsed intent: {parsed.intent}, params: {parsed.params}, confidence: {parsed.confidence}"
        )

        return context

    def _match_concepts(self, context: ResolverContext) -> ResolverContext:
        """State 2: 匹配概念"""
        context.transition_to(ResolverState.MATCH_CONCEPTS)

        if not context.parsed:
            raise ResolverError(ResolverState.MATCH_CONCEPTS, "No parsed intent")

        # 意圖映射：將未知意圖映射到已知的庫存查詢
        intent_name = context.parsed.intent
        intent_mapping = {
            "QUERY_STATS": "QUERY_INVENTORY",
            "QUERY_COMPLEX": "QUERY_INVENTORY",
        }
        if intent_name in intent_mapping:
            mapped_intent = intent_mapping[intent_name]
            logger.info(f"Mapping intent '{intent_name}' -> '{mapped_intent}'")
            intent_name = mapped_intent

        # 獲取意圖定義
        intent_def = self._get_intent(intent_name)
        if not intent_def:
            raise ResolverError(ResolverState.MATCH_CONCEPTS, f"Intent not found: {intent_name}")

        context.intent = intent_def

        # 匹配參數到概念
        for param_name, param_value in context.parsed.params.items():
            concept_def = self._get_concept(param_name)
            if not concept_def:
                logger.warning(f"Concept not found: {param_name}")
                continue

            context.matched_concepts[param_name] = MatchedConcept(
                concept=param_name, value=param_value, source="parsed"
            )

        logger.info(f"Matched {len(context.matched_concepts)} concepts")

        return context

    def _resolve_bindings(self, context: ResolverContext) -> ResolverContext:
        """State 3: 解析綁定"""
        import re
        from datetime import datetime

        context.transition_to(ResolverState.RESOLVE_BINDINGS)

        if not context.intent:
            raise ResolverError(ResolverState.RESOLVE_BINDINGS, "No intent definition")

        datasource = self.config.datasource.upper()

        def parse_time_range_value(value: Any) -> tuple[Optional[str], Optional[str]]:
            """解析時間範圍值，返回 (start_date, end_date)"""
            # 處理 dict 格式 {"type": "YEAR", "year": 2026}
            if isinstance(value, dict):
                year = value.get("year")
                if not year:
                    return None, None
                month = value.get("month", 1)
                start_date = f"{year}-{month:02d}-01"
                if month == 12:
                    end_date = f"{int(year) + 1}-01-01"
                else:
                    end_date = f"{year}-{month + 1:02d}-01"
                return start_date, end_date

            # 處理字串格式 "2026年1月" 或 "2026-01"
            if not isinstance(value, str):
                return None, None

            # 匹配 "2026年1月" 格式
            match = re.search(r"(\d{4})年(\d{1,2})月?", value)
            if match:
                year = match.group(1)
                month = int(match.group(2))
                start_date = f"{year}-{month:02d}-01"
                # 下個月的第一天
                if month == 12:
                    end_date = f"{int(year) + 1}-01-01"
                else:
                    end_date = f"{year}-{month + 1:02d}-01"
                return start_date, end_date

            # 匹配 "2026-01" 格式
            match = re.search(r"(\d{4})-(\d{1,2})", value)
            if match:
                year = match.group(1)
                month = int(match.group(2))
                start_date = f"{year}-{month:02d}-01"
                if month == 12:
                    end_date = f"{int(year) + 1}-01-01"
                else:
                    end_date = f"{year}-{month + 1:02d}-01"
                return start_date, end_date

            return None, None

        # 解析所有需要輸出的維度和指標
        for dim in context.intent.output.dimensions:
            binding = self._get_binding(dim, datasource)
            if not binding:
                raise ResolverError(
                    ResolverState.RESOLVE_BINDINGS, f"Binding not found for dimension: {dim}"
                )

            context.resolved_bindings.append(
                ResolvedBinding(
                    concept=dim,
                    table=binding.table,
                    column=binding.column,
                    aggregation=None,
                    operator=binding.operator or "=",
                )
            )

        for metric in context.intent.output.metrics:
            binding = self._get_binding(metric, datasource)
            if not binding:
                raise ResolverError(
                    ResolverState.RESOLVE_BINDINGS, f"Binding not found for metric: {metric}"
                )

            context.resolved_bindings.append(
                ResolvedBinding(
                    concept=metric,
                    table=binding.table,
                    column=binding.column,
                    aggregation=binding.aggregation,
                    operator=binding.operator or "=",
                )
            )

        # 解析過濾器
        for filter_name, matched in context.matched_concepts.items():
            binding = self._get_binding(filter_name, datasource)
            if not binding:
                logger.warning(f"No binding for filter: {filter_name}")
                continue

            # 處理 TIME_RANGE
            if filter_name == "TIME_RANGE" and matched.value:
                # 對於簡單統計查詢（只有 COUNT），跳過時間過濾
                # 因為 S3 path 已經按 year/month 分區
                is_simple_count = (
                    len(context.intent.output.metrics) == 1
                    and len(context.intent.output.dimensions) == 0
                )
                if is_simple_count:
                    logger.info("Skipping TIME_RANGE for simple COUNT query")
                    continue

                start_date, end_date = parse_time_range_value(matched.value)
                if start_date and end_date:
                    logger.info(f"TIME_RANGE parsed: {start_date} to {end_date}")
                    context.resolved_bindings.append(
                        ResolvedBinding(
                            concept=filter_name,
                            table=binding.table,
                            column=binding.column,
                            aggregation=None,
                            operator=OperatorType.BETWEEN,
                            value={
                                "type": "BETWEEN",
                                "start": f"'{start_date}'",
                                "end": f"'{end_date}'",
                            },
                        )
                    )
                    continue

            context.resolved_bindings.append(
                ResolvedBinding(
                    concept=filter_name,
                    table=binding.table,
                    column=binding.column,
                    aggregation=None,
                    operator=binding.operator or "=",
                    value=matched.value,
                )
            )

        logger.info(f"Resolved {len(context.resolved_bindings)} bindings")

        return context

    def _validate(self, context: ResolverContext) -> ResolverContext:
        """State 4: 驗證"""
        context.transition_to(ResolverState.VALIDATE)

        if not context.resolved_bindings:
            raise ResolverError(ResolverState.VALIDATE, "No bindings resolved")

        # 檢查必需的過濾器
        if context.intent:
            for required in context.intent.input.required_filters:
                if required not in context.matched_concepts:
                    raise ResolverError(
                        ResolverState.VALIDATE,
                        f"Required filter missing: {required}",
                        {"required": required},
                    )

        logger.info("Validation passed")

        return context

    def _build_ast(self, context: ResolverContext) -> ResolverContext:
        """State 5: 生成 AST"""
        context.transition_to(ResolverState.BUILD_AST)

        ast = QueryAST()

        # 收集表格
        tables = set()
        for binding in context.resolved_bindings:
            tables.add(binding.table)

        ast.from_tables = list(tables)

        # SELECT 子句
        for binding in context.resolved_bindings:
            expr = binding.column
            if binding.aggregation and binding.aggregation.value.upper() != "NONE":
                expr = f"{binding.aggregation.value}({binding.column})"

            ast.select.append({"expr": expr, "alias": binding.concept.lower()})

        # WHERE 子句
        for binding in context.resolved_bindings:
            if binding.value is not None:
                ast.where_conditions.append(
                    {
                        "column": binding.column,
                        "operator": binding.operator.value
                        if hasattr(binding.operator, "value")
                        else str(binding.operator),
                        "value": binding.value,
                    }
                )

        # GROUP BY 子句（如果有聚合）
        has_aggregation = any(b.aggregation for b in context.resolved_bindings)
        if has_aggregation:
            for binding in context.resolved_bindings:
                if not binding.aggregation:
                    ast.group_by.append(binding.column)

        # 分頁參數 (LIMIT / OFFSET)
        if context.parsed:
            if context.parsed.limit:
                ast.limit = context.parsed.limit
            elif ast.limit is None:
                # 預設 LIMIT，防止全表掃描
                ast.limit = 100
                logger.info("Added default LIMIT=100 to prevent full table scan")
            if context.parsed.offset:
                ast.offset = context.parsed.offset
        elif ast.limit is None:
            # 預設 LIMIT，防止全表掃描
            ast.limit = 100
            logger.info("Added default LIMIT=100 to prevent full table scan")

        context.ast = ast

        logger.info(
            f"AST built: select={len(ast.select)}, from={ast.from_tables}, limit={ast.limit}, offset={ast.offset}"
        )

        return context

    def _emit_sql(self, context: ResolverContext) -> ResolverContext:
        """State 6: 生成 SQL"""
        context.transition_to(ResolverState.EMIT_SQL)

        if not context.ast:
            raise ResolverError(ResolverState.EMIT_SQL, "No AST built")

        datasource = self.config.datasource.upper()

        from .sql_generator import DuckDBSQLGenerator, get_sql_generator

        # 獲取 bindings
        bindings_data = {}
        if self._bindings:
            bindings_data = self._bindings.bindings

        # 根據資料源創建生成器
        if datasource == "DUCKDB":
            generator = DuckDBSQLGenerator(
                bucket="tiptop-raw",
                dialect=datasource,
                bindings=bindings_data,
            )
        else:
            generator = get_sql_generator(datasource)

        context.sql = generator.generate(context.ast)

        logger.info(f"SQL generated (dialect={datasource}): {context.sql[:100]}...")

        return context

    def execute(self, sql: str) -> Dict[str, Any]:
        """
        執行 SQL

        Args:
            sql: SQL 語句

        Returns:
            Dict: 查詢結果
        """
        from .executor import SQLExecutor

        executor = SQLExecutor(self.config)
        return executor.execute(sql)
