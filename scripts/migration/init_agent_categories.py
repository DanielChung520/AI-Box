# 代碼功能說明: 初始化代理分類數據
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""初始化代理分類數據

將默認的代理分類（人力資源、物流、財務、生產管理、經寶PoC）添加到數據庫中。
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加載環境變數
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from services.api.models.agent_category import AgentCategory
from services.api.models.agent_display_config import MultilingualText
from services.api.services.agent_category_store_service import AgentCategoryStoreService


def init_default_categories() -> None:
    """初始化默認的代理分類"""
    print("開始初始化代理分類數據...")
    store_service = AgentCategoryStoreService()

    # 定義默認分類
    default_categories = [
        AgentCategory(
            id="human-resource",
            display_order=1,
            is_visible=True,
            name=MultilingualText(
                en="Human Resource",
                zh_CN="人力资源",
                zh_TW="人力資源",
            ),
            icon="fa-users",
            description=MultilingualText(
                en="Human resource management agents",
                zh_CN="人力资源管理代理",
                zh_TW="人力資源管理代理",
            ),
        ),
        AgentCategory(
            id="logistics",
            display_order=2,
            is_visible=True,
            name=MultilingualText(
                en="Logistics",
                zh_CN="物流",
                zh_TW="物流",
            ),
            icon="fa-truck",
            description=MultilingualText(
                en="Logistics management agents",
                zh_CN="物流管理代理",
                zh_TW="物流管理代理",
            ),
        ),
        AgentCategory(
            id="finance",
            display_order=3,
            is_visible=True,
            name=MultilingualText(
                en="Finance",
                zh_CN="财务",
                zh_TW="財務",
            ),
            icon="fa-dollar-sign",
            description=MultilingualText(
                en="Finance management agents",
                zh_CN="财务管理代理",
                zh_TW="財務管理代理",
            ),
        ),
        AgentCategory(
            id="mes",
            display_order=4,
            is_visible=True,
            name=MultilingualText(
                en="Production Management",
                zh_CN="生产管理",
                zh_TW="生產管理",
            ),
            icon="fa-industry",
            description=MultilingualText(
                en="Production management agents",
                zh_CN="生产管理代理",
                zh_TW="生產管理代理",
            ),
        ),
        AgentCategory(
            id="jingbao-poc",
            display_order=5,
            is_visible=True,
            name=MultilingualText(
                en="JingBao PoC",
                zh_CN="经宝PoC",
                zh_TW="經寶PoC",
            ),
            icon="fa-flask",
            description=MultilingualText(
                en="JingBao Proof of Concept agents",
                zh_CN="经宝概念验证代理",
                zh_TW="經寶概念驗證代理",
            ),
        ),
    ]

    # 創建分類
    created_count = 0
    skipped_count = 0

    for category in default_categories:
        try:
            # 檢查分類是否已存在
            existing = store_service.get_category(category.id, tenant_id=None)
            if existing:
                print(f"分類 {category.id} 已存在，跳過創建")
                skipped_count += 1
                continue

            # 創建分類
            store_service.create_category(
                category=category,
                tenant_id=None,  # 系統級分類
                created_by="system_init",
            )
            print(f"✓ 分類 {category.id} 創建成功")
            print(f"  名稱（繁中）: {category.name.zh_TW}")
            print(f"  顯示順序: {category.display_order}")
            print(f"  圖標: {category.icon}")
            created_count += 1
        except Exception as e:
            print(f"✗ 分類 {category.id} 創建失敗: {e}")
            raise

    print("\n✅ 代理分類初始化完成！")
    print(f"   創建: {created_count} 個")
    print(f"   跳過: {skipped_count} 個")
    print(f"   總計: {len(default_categories)} 個")


if __name__ == "__main__":
    try:
        init_default_categories()
    except Exception as e:
        print(f"\n❌ 初始化失敗: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
