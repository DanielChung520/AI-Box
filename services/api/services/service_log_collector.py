# 代碼功能說明: 服務日誌收集器
# 創建日期: 2026-01-17 18:48 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 18:48 UTC+8

"""服務日誌收集器 - 從各種來源收集服務日誌並存儲到 ArangoDB"""

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.api.services.service_log_store_service import get_service_log_store_service

logger = logging.getLogger(__name__)


class ServiceLogCollector:
    """服務日誌收集器"""

    def __init__(self):
        """初始化服務日誌收集器"""
        self.log_store_service = get_service_log_store_service()

        # 定義服務日誌文件路徑映射
        self.service_log_paths = {
            "fastapi": [
                "/Users/daniel/GitHub/AI-Box/logs/api.log",
                "/Users/daniel/GitHub/AI-Box/logs/fastapi.log",
            ],
            "rq_worker": [
                "/Users/daniel/GitHub/AI-Box/logs/rq_worker.log",
            ],
            # ChromaDB 日志收集已移除（已迁移到 Qdrant）
            "redis": [
                "/var/log/redis/redis-server.log",
                "/usr/local/var/log/redis.log",
            ],
            "arangodb": [
                "/var/log/arangodb3/arangodb.log",
                "/usr/local/var/log/arangodb3/arangodb.log",
            ],
        }

        # 日誌級別正則表達式
        self.log_level_pattern = re.compile(
            r"\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b", re.IGNORECASE
        )

        # 時間戳正則表達式（多種格式）
        self.timestamp_patterns = [
            re.compile(
                r"(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)"
            ),  # ISO 8601
            re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"),  # YYYY-MM-DD HH:MM:SS
            re.compile(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})"),  # MM/DD/YYYY HH:MM:SS
        ]

    async def collect_service_logs(
        self,
        service_name: str,
        max_lines: int = 1000,
        since_timestamp: Optional[datetime] = None,
    ) -> int:
        """
        收集特定服務的日誌

        Args:
            service_name: 服務名稱
            max_lines: 最多讀取的行數
            since_timestamp: 僅收集此時間之後的日誌

        Returns:
            收集的日誌數量
        """
        try:
            log_paths = self.service_log_paths.get(service_name, [])
            if not log_paths:
                logger.warning(f"No log paths configured for service: {service_name}")
                return 0

            collected_logs = []

            for log_path in log_paths:
                if not os.path.exists(log_path):
                    logger.debug(f"Log file not found: {log_path}")
                    continue

                try:
                    logs_from_file = self._read_log_file(
                        log_path, service_name, max_lines, since_timestamp
                    )
                    collected_logs.extend(logs_from_file)
                except Exception as e:
                    logger.error(
                        f"Failed to read log file: path={log_path}, error={str(e)}",
                        exc_info=True,
                    )

            if collected_logs:
                # 批量插入日誌
                count = self.log_store_service.batch_create_logs(collected_logs)
                logger.info(f"Collected service logs: service_name={service_name}, count={count}")
                return count

            return 0

        except Exception as e:
            logger.error(
                f"Failed to collect service logs: service_name={service_name}, error={str(e)}",
                exc_info=True,
            )
            raise RuntimeError(f"Failed to collect service logs: {e}") from e

    def _read_log_file(
        self,
        log_path: str,
        service_name: str,
        max_lines: int,
        since_timestamp: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        """
        讀取日誌文件

        Args:
            log_path: 日誌文件路徑
            service_name: 服務名稱
            max_lines: 最多讀取的行數
            since_timestamp: 僅收集此時間之後的日誌

        Returns:
            日誌列表
        """
        logs = []

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                # 讀取最後 max_lines 行
                lines = f.readlines()
                lines = lines[-max_lines:] if len(lines) > max_lines else lines

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # 解析日誌行
                    log_entry = self._parse_log_line(line, service_name)

                    if log_entry:
                        # 如果指定了 since_timestamp，則過濾早於該時間的日誌
                        if since_timestamp and log_entry["timestamp"] < since_timestamp:
                            continue

                        logs.append(log_entry)

        except Exception as e:
            logger.error(f"Failed to read log file: path={log_path}, error={str(e)}", exc_info=True)

        return logs

    def _parse_log_line(self, line: str, service_name: str) -> Optional[Dict[str, Any]]:
        """
        解析日誌行

        Args:
            line: 日誌行
            service_name: 服務名稱

        Returns:
            日誌條目字典，如果解析失敗則返回 None
        """
        try:
            # 提取日誌級別
            log_level = "INFO"
            level_match = self.log_level_pattern.search(line)
            if level_match:
                log_level = level_match.group(1).upper()

            # 提取時間戳
            timestamp = datetime.utcnow()
            for pattern in self.timestamp_patterns:
                ts_match = pattern.search(line)
                if ts_match:
                    ts_str = ts_match.group(1)
                    try:
                        # 嘗試多種時間格式
                        timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        break
                    except ValueError:
                        try:
                            timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            try:
                                timestamp = datetime.strptime(ts_str, "%m/%d/%Y %H:%M:%S")
                            except ValueError:
                                pass

            return {
                "service_name": service_name,
                "log_level": log_level,
                "message": line,
                "timestamp": timestamp,
                "metadata": {
                    "source": "file",
                    "raw_line": line,
                },
            }

        except Exception as e:
            logger.debug(f"Failed to parse log line: error={str(e)}")
            return None

    async def collect_all_services(self) -> Dict[str, int]:
        """
        收集所有服務的日誌

        Returns:
            每個服務收集的日誌數量字典
        """
        results = {}

        for service_name in self.service_log_paths.keys():
            try:
                count = await self.collect_service_logs(service_name)
                results[service_name] = count
            except Exception as e:
                logger.error(
                    f"Failed to collect logs for service: service_name={service_name}, error={str(e)}",
                    exc_info=True,
                )
                results[service_name] = 0

        return results


# 單例服務
_collector: Optional[ServiceLogCollector] = None


def get_service_log_collector() -> ServiceLogCollector:
    """獲取服務日誌收集器單例"""
    global _collector
    if _collector is None:
        _collector = ServiceLogCollector()
    return _collector
