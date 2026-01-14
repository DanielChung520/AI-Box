# 代碼功能說明: 添加「經寶PoC」分類配置
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""添加「經寶PoC」分類配置腳本

用於測試前端代理展示區功能，添加一個新的分類 tab。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(base_dir))

from dotenv import load_dotenv

# 顯式加載 .env 文件
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

from services.api.models.agent_display_config import CategoryConfig, MultilingualText
from services.api.services.agent_display_config_store_service import AgentDisplayConfigStoreService


def add_jingbao_poc_category() -> None:
    """添加「經寶PoC」分類配置"""
    print("開始添加「經寶PoC」分類配置...")

    # 創建 Store Service
    store_service = AgentDisplayConfigStoreService()

    # 檢查是否已存在
    category_id = "jingbao-poc"
    existing = store_service.get_category_config(category_id, tenant_id=None)

    if existing:
        print(f"分類 {category_id} 已存在，跳過創建")
        print(f"現有配置：{existing.model_dump()}")
        return

    # 創建分類配置
    category_config = CategoryConfig(
        id=category_id,
        display_order=5,  # 放在最後
        is_visible=True,
        name=MultilingualText(
            en="JingBao PoC",
            zh_CN="经宝PoC",
            zh_TW="經寶PoC",
        ),
        icon="fa-flask",  # 使用實驗/測試相關的圖標
        description=MultilingualText(
            en="JingBao Proof of Concept agents",
            zh_CN="经宝概念验证代理",
            zh_TW="經寶概念驗證代理",
        ),
    )

    try:
        store_service.create_category(
            category_config=category_config,
            tenant_id=None,  # 系統級配置
            created_by="test_script",
        )
        print(f"✓ 分類 {category_id} 創建成功")
        print(f"  名稱（繁中）: {category_config.name.zh_TW}")
        print(f"  顯示順序: {category_config.display_order}")
        print(f"  圖標: {category_config.icon}")
    except Exception as e:
        print(f"✗ 分類 {category_id} 創建失敗: {e}")
        raise


if __name__ == "__main__":
    try:
        add_jingbao_poc_category()
        print("\n✅ 「經寶PoC」分類添加成功！")
        print("   請刷新前端頁面查看新的 tab。")
    except Exception as e:
        print(f"\n❌ 添加失敗: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
