# 代碼功能說明: Pandoc 轉換器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Pandoc 轉換器

實現通過 Pandoc 將 Markdown 轉換為 PDF。
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PandocConverter:
    """Pandoc 轉換器

    提供 Markdown 到 PDF 的轉換功能。
    """

    def __init__(self):
        """初始化 Pandoc 轉換器"""
        self.logger = logger

    def convert(
        self,
        markdown_content: str,
        output_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        將 Markdown 轉換為 PDF

        Args:
            markdown_content: Markdown 內容
            output_path: 輸出 PDF 文件路徑
            options: 轉換選項

        Returns:
            轉換是否成功
        """
        try:
            # 創建臨時 Markdown 文件
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as tmp_file:
                tmp_file.write(markdown_content)
                tmp_md_path = tmp_file.name

            try:
                # 構建 Pandoc 命令
                cmd = ["pandoc", tmp_md_path, "-o", output_path]

                # 添加選項
                if options:
                    if options.get("page_size"):
                        cmd.extend(["--pdf-engine-opt", f"-V papersize={options['page_size']}"])
                    if options.get("margin"):
                        margin = options["margin"]
                        cmd.extend(
                            [
                                "--pdf-engine-opt",
                                f"-V geometry:margin={margin.get('top', '2cm')}",
                            ]
                        )

                # 執行轉換
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode != 0:
                    self.logger.error(f"Pandoc conversion failed: {result.stderr}")
                    return False

                self.logger.info(f"PDF converted successfully: {output_path}")
                return True

            finally:
                # 清理臨時文件
                Path(tmp_md_path).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            self.logger.error("Pandoc conversion timeout")
            return False
        except Exception as e:
            self.logger.error(f"Pandoc conversion error: {e}", exc_info=True)
            return False

    def is_available(self) -> bool:
        """
        檢查 Pandoc 是否可用

        Returns:
            Pandoc 是否可用
        """
        try:
            result = subprocess.run(
                ["pandoc", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
