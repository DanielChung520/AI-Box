# 代碼功能說明: 配置定義加載器
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""配置定義加載器 - 從 JSON 文件加載配置定義到內存緩存"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class DefinitionLoader:
    """配置定義加載器"""

    def __init__(self, definitions_dir: Optional[Path] = None):
        """
        初始化定義加載器

        Args:
            definitions_dir: 定義文件目錄（默認：services/api/core/config/definitions）
        """
        if definitions_dir is None:
            # 默認路徑：相對於當前文件位置
            base_dir = Path(__file__).parent
            definitions_dir = base_dir / "definitions"

        self.definitions_dir = Path(definitions_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}  # 內存緩存

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """
        加載所有定義文件到內存

        Returns:
            所有配置定義的字典（key: scope, value: 定義內容）
        """
        if not self.definitions_dir.exists():
            logger.warning(
                "定義目錄不存在",
                directory=str(self.definitions_dir),
            )
            return {}

        definitions = {}

        # 遍歷所有 JSON 文件
        for json_file in self.definitions_dir.glob("*.json"):
            try:
                scope = json_file.stem  # 文件名（不含擴展名）作為 scope
                definition = self._load_file(json_file)
                definitions[scope] = definition
                logger.info(
                    "已加載配置定義",
                    scope=scope,
                    file=str(json_file),
                )
            except Exception as e:
                logger.error(
                    "加載定義文件失敗",
                    file=str(json_file),
                    error=str(e),
                )

        # 更新內存緩存
        self._cache = definitions

        logger.info(
            "配置定義加載完成",
            count=len(definitions),
            scopes=list(definitions.keys()),
        )

        return definitions

    def _load_file(self, file_path: Path) -> Dict[str, Any]:
        """
        加載單個定義文件

        Args:
            file_path: JSON 文件路徑

        Returns:
            解析後的 JSON 字典

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 格式錯誤
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("定義文件不存在", file=str(file_path))
            raise
        except json.JSONDecodeError as e:
            logger.error("JSON 解析失敗", file=str(file_path), error=str(e))
            raise

    def get_definition(self, scope: str) -> Optional[Dict[str, Any]]:
        """
        從內存緩存獲取定義

        Args:
            scope: 配置範圍

        Returns:
            配置定義（如果存在），否則返回 None
        """
        return self._cache.get(scope)

    def reload(self) -> Dict[str, Dict[str, Any]]:
        """
        重新加載所有定義文件

        Returns:
            所有配置定義的字典
        """
        logger.info("重新加載配置定義")
        return self.load_all()


# 全局定義加載器實例
_definition_loader: Optional[DefinitionLoader] = None


def get_definition_loader() -> DefinitionLoader:
    """
    獲取定義加載器實例（單例模式）

    Returns:
        DefinitionLoader: 定義加載器實例
    """
    global _definition_loader
    if _definition_loader is None:
        _definition_loader = DefinitionLoader()
    return _definition_loader
