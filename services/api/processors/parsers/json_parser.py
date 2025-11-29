# 代碼功能說明: JSON 文件解析器
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""JSON 文件解析器"""

import json
from typing import Dict, Any
from .base_parser import BaseParser


class JsonParser(BaseParser):
    """JSON 文件解析器"""

    def parse(self, file_path: str) -> Dict[str, Any]:
        """解析 JSON 文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 將 JSON 轉換為文本
            text = json.dumps(data, ensure_ascii=False, indent=2)

            return {
                "text": text,
                "metadata": {
                    "data_type": type(data).__name__,
                    "char_count": len(text),
                },
            }
        except Exception as e:
            self.logger.error("JSON 文件解析失敗", file_path=file_path, error=str(e))
            raise

    def parse_from_bytes(self, file_content: bytes, **kwargs: Any) -> Dict[str, Any]:
        """從字節內容解析 JSON"""
        encoding: str = kwargs.get("encoding", "utf-8")
        try:
            text = file_content.decode(encoding)
            data = json.loads(text)

            formatted_text = json.dumps(data, ensure_ascii=False, indent=2)

            return {
                "text": formatted_text,
                "metadata": {
                    "data_type": type(data).__name__,
                    "char_count": len(formatted_text),
                },
            }
        except Exception as e:
            self.logger.error("JSON 解析失敗", error=str(e))
            raise

    def get_supported_extensions(self) -> list:
        return [".json"]
