# SSE Event Emitter for Data-Agent
# 用于发送阶段性成果汇报

import asyncio
import json
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class StageEvent:
    """阶段事件"""

    stage: str  # 阶段名称
    message: str  # 人类可读的消息
    data: Dict[str, Any] = field(default_factory=dict)  # 实际数据
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    task_id: str = ""


class SSEEventEmitter:
    """SSE 事件发射器

    用于在各阶段发出成果汇报，
    替代簡單的狀態通知。
    """

    # 阶段定义
    STAGE_REQUEST_RECEIVED = "request_received"
    STAGE_SCHEMA_CONFIRMED = "schema_confirmed"
    STAGE_SQL_GENERATED = "sql_generated"
    STAGE_QUERY_EXECUTING = "query_executing"
    STAGE_QUERY_COMPLETED = "query_completed"
    STAGE_RESULT_VALIDATING = "result_validating"
    STAGE_RESULT_READY = "result_ready"
    STAGE_ERROR = "error"

    def __init__(self):
        self._callbacks: List[Callable] = []

    def add_callback(self, callback: Callable):
        """添加回调函数"""
        self._callbacks.append(callback)

    async def emit(self, event: StageEvent):
        """发出事件"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.warning(f"SSE callback error: {e}")

    # 便捷方法

    async def request_received(self, task_id: str, nlq: str):
        """階段 1: 接收到請求"""
        await self.emit(
            StageEvent(
                stage=self.STAGE_REQUEST_RECEIVED,
                message=f"已接收到請求：{nlq}",
                data={"nlq": nlq},
                task_id=task_id,
            )
        )

    async def schema_confirmed(
        self, task_id: str, schema_used: str, tables: List[str], columns: List[str]
    ):
        """階段 2: 確認找到 Schema"""
        table_str = ", ".join(tables) if tables else schema_used
        column_str = ", ".join(columns[:5]) + ("..." if len(columns) > 5 else "")

        await self.emit(
            StageEvent(
                stage=self.STAGE_SCHEMA_CONFIRMED,
                message=f"已確認找到對應的表格：{table_str}，相關欄位：{column_str}",
                data={"schema_used": schema_used, "tables": tables, "columns": columns},
                task_id=task_id,
            )
        )

    async def sql_generated(self, task_id: str, sql: str, intent: str):
        """階段 3: 產生 SQL"""
        # 截断 SQL 显示
        sql_preview = sql[:100] + "..." if len(sql) > 100 else sql

        await self.emit(
            StageEvent(
                stage=self.STAGE_SQL_GENERATED,
                message=f"已產生 SQL：{sql_preview}",
                data={"sql": sql, "intent": intent},
                task_id=task_id,
            )
        )

    async def query_executing(self, task_id: str, timeout: int):
        """階段 4: 執行查詢"""
        await self.emit(
            StageEvent(
                stage=self.STAGE_QUERY_EXECUTING,
                message=f"正在執行查詢中...（超時設定：{timeout}秒）",
                data={"timeout": timeout},
                task_id=task_id,
            )
        )

    async def query_completed(self, task_id: str, row_count: int, execution_time_ms: float):
        """階段 5: 查詢完成"""
        await self.emit(
            StageEvent(
                stage=self.STAGE_QUERY_COMPLETED,
                message=f"已查詢完成，正在檢查結果...（耗時：{execution_time_ms}ms，返回 {row_count} 筆資料）",
                data={"row_count": row_count, "execution_time_ms": execution_time_ms},
                task_id=task_id,
            )
        )

    async def result_validating(self, task_id: str):
        """階段 5.5: 結果驗證中"""
        await self.emit(
            StageEvent(
                stage=self.STAGE_RESULT_VALIDATING,
                message="正在驗證結果...",
                data={},
                task_id=task_id,
            )
        )

    async def result_ready(self, task_id: str, status: str, row_count: int):
        """階段 6: 返回結果"""
        status_msg = (
            "成功" if status == "success" else "部分成功" if status == "partial" else "失敗"
        )

        await self.emit(
            StageEvent(
                stage=self.STAGE_RESULT_READY,
                message=f"已返回結果：{status_msg}（{row_count} 筆資料）",
                data={"status": status, "row_count": row_count},
                task_id=task_id,
            )
        )

    async def error(self, task_id: str, error_code: str, message: str):
        """錯誤"""
        await self.emit(
            StageEvent(
                stage=self.STAGE_ERROR,
                message=f"發生錯誤：{message}",
                data={"error_code": error_code, "message": message},
                task_id=task_id,
            )
        )


# 全局实例
_event_emitter = SSEEventEmitter()


def get_event_emitter() -> SSEEventEmitter:
    """获取全局事件发射器"""
    return _event_emitter
