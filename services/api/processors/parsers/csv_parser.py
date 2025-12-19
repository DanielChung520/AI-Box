# 代碼功能說明: CSV 文件解析器
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""CSV 文件解析器"""

import csv
from io import StringIO
from typing import Any, Dict

from .base_parser import BaseParser


class CsvParser(BaseParser):
    """CSV 文件解析器"""

    def parse(self, file_path: str) -> Dict[str, Any]:
        """解析 CSV 文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

            # 將 CSV 轉換為文本
            text_parts = []
            for row in rows:
                text_parts.append(", ".join(row))

            full_text = "\n".join(text_parts)

            return {
                "text": full_text,
                "metadata": {
                    "num_rows": len(rows),
                    "num_columns": len(rows[0]) if rows else 0,
                    "char_count": len(full_text),
                },
            }
        except Exception as e:
            self.logger.error("CSV 文件解析失敗", file_path=file_path, error=str(e))
            raise

    def parse_from_bytes(self, file_content: bytes, **kwargs: Any) -> Dict[str, Any]:
        """從字節內容解析 CSV"""
        encoding: str = kwargs.get("encoding", "utf-8")
        try:
            text = file_content.decode(encoding)
            reader = csv.reader(StringIO(text))
            rows = list(reader)

            text_parts = []
            for row in rows:
                text_parts.append(", ".join(row))

            full_text = "\n".join(text_parts)

            return {
                "text": full_text,
                "metadata": {
                    "num_rows": len(rows),
                    "num_columns": len(rows[0]) if rows else 0,
                    "char_count": len(full_text),
                },
            }
        except Exception as e:
            self.logger.error("CSV 解析失敗", error=str(e))
            raise

    def get_supported_extensions(self) -> list:
        return [".csv"]
