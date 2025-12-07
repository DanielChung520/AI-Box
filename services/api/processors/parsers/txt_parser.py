# 代碼功能說明: 純文本文件解析器
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""純文本文件解析器"""

from typing import Dict, Any
from .base_parser import BaseParser


class TxtParser(BaseParser):
    """純文本文件解析器"""

    def __init__(self):
        super().__init__()

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析文本文件

        Args:
            file_path: 文件路徑

        Returns:
            解析結果，包含文本內容和元數據
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            return {
                "text": content,
                "metadata": {
                    "encoding": "utf-8",
                    "line_count": len(content.splitlines()),
                    "char_count": len(content),
                },
            }
        except UnicodeDecodeError:
            # 嘗試其他編碼
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    content = f.read()
                return {
                    "text": content,
                    "metadata": {
                        "encoding": "gbk",
                        "line_count": len(content.splitlines()),
                        "char_count": len(content),
                    },
                }
            except Exception as e:
                self.logger.error("文本文件解析失敗", file_path=file_path, error=str(e))
                raise
        except Exception as e:
            self.logger.error("文本文件解析失敗", file_path=file_path, error=str(e))
            raise

    def parse_from_bytes(
        self, file_content: bytes, encoding: str = "utf-8", **kwargs
    ) -> Dict[str, Any]:
        """
        從字節內容解析文本

        Args:
            file_content: 文件內容（字節）
            encoding: 編碼格式
            **kwargs: 其他參數

        Returns:
            解析結果
        """
        try:
            text = file_content.decode(encoding)
            return {
                "text": text,
                "metadata": {
                    "encoding": encoding,
                    "line_count": len(text.splitlines()),
                    "char_count": len(text),
                },
            }
        except UnicodeDecodeError:
            # 嘗試其他編碼
            try:
                text = file_content.decode("gbk")
                return {
                    "text": text,
                    "metadata": {
                        "encoding": "gbk",
                        "line_count": len(text.splitlines()),
                        "char_count": len(text),
                    },
                }
            except Exception as e:
                self.logger.error("文本解析失敗", error=str(e))
                raise
        except Exception as e:
            self.logger.error("文本解析失敗", error=str(e))
            raise

    def get_supported_extensions(self) -> list:
        return [".txt"]
