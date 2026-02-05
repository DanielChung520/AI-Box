# 代碼功能說明: 新增經寶PoC分類到代理展示區
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-03

"""新增經寶PoC分類到代理展示區

前置條件:
    - ArangoDB 已啟動且 .env 已配置
    - 請先啟用虛擬環境: source venv/bin/activate (或 uv run)

使用方式:
    python add_jingbao_poc_category.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 確保專案根目錄在 sys.path
project_root = Path(__file__).resolve().parent  # scripts 目錄
project_root = project_root.parent  # ai-box 專案根目錄
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(dotenv_path=project_root / ".env")

import logging

from services.api.models.agent_display_config import (
    AgentConfig,
    CategoryConfig,
    MultilingualText,
)
from services.api.services.agent_display_config_store_service import (
    AgentDisplayConfigStoreService,
)

logger = logging.getLogger(__name__)


def _ml(en: str, zh_cn: str, zh_tw: str) -> MultilingualText:
    """建立多語言文本"""
    return MultilingualText(en=en, zh_CN=zh_cn, zh_TW=zh_tw)


def add_jingbao_poc_category() -> bool:
    """新增經寶PoC分類到代理展示區

    Returns:
        是否成功
    """
    try:
        store = AgentDisplayConfigStoreService()
    except RuntimeError as e:
        logger.error(f"ArangoDB 連線失敗: {e}")
        return False

    tenant_id: str | None = None  # 系統級配置

    # 檢查分類是否已存在
    existing = store.get_category_config("jingbao-poc", tenant_id)
    if existing:
        logger.info("經寶PoC分類已存在，跳過建立")
        return True

    # 建立經寶PoC分類
    jingbao_poc_category = CategoryConfig(
        id="jingbao-poc",
        display_order=4,  # 放在最後
        is_visible=True,
        name=_ml("Jingbao PoC", "经宝PoC", "經寶PoC"),
        icon="fa-flask",
        description=_ml(
            "Jingbao proof of concept demos",
            "经宝概念验证演示",
            "經寶概念驗證演示",
        ),
    )

    try:
        store.create_category(
            jingbao_poc_category, tenant_id=tenant_id, created_by="add_jingbao_poc_script"
        )
        logger.info("✅ 已建立經寶PoC分類: jingbao-poc")
        return True
    except Exception as e:
        logger.error(f"建立經寶PoC分類失敗: {e}")
        return False


def main() -> int:
    """主程式"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("開始新增經寶PoC分類...")
    success = add_jingbao_poc_category()
    if success:
        logger.info("經寶PoC分類建立完成")
        return 0
    logger.error("經寶PoC分類建立失敗")
    return 1


if __name__ == "__main__":
    sys.exit(main())
