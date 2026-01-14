# 代碼功能說明: 為「經寶PoC」分類添加測試代理
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""為「經寶PoC」分類添加測試代理

用於測試前端代理展示區功能。
"""

from __future__ import annotations

import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(base_dir))

from dotenv import load_dotenv

load_dotenv(dotenv_path=base_dir / ".env")

from services.api.models.agent_display_config import AgentConfig, MultilingualText
from services.api.services.agent_display_config_store_service import AgentDisplayConfigStoreService


def add_jingbao_poc_agent() -> None:
    """為「經寶PoC」分類添加測試代理"""
    print("開始為「經寶PoC」分類添加測試代理...")

    store_service = AgentDisplayConfigStoreService()

    agent_id = "jingbao-poc-1"
    existing = store_service.get_agent_config(agent_id, tenant_id=None)

    if existing:
        print(f"代理 {agent_id} 已存在，跳過創建")
        return

    agent_config = AgentConfig(
        id=agent_id,
        category_id="jingbao-poc",
        display_order=1,
        is_visible=True,
        name=MultilingualText(
            en="JingBao PoC Agent",
            zh_CN="经宝PoC代理",
            zh_TW="經寶PoC代理",
        ),
        description=MultilingualText(
            en="Proof of Concept agent for JingBao project",
            zh_CN="经宝项目概念验证代理",
            zh_TW="經寶專案概念驗證代理",
        ),
        icon="fa-flask",
        status="online",
        usage_count=0,
    )

    try:
        store_service.create_agent(
            agent_config=agent_config,
            tenant_id=None,
            created_by="test_script",
        )
        print(f"✓ 代理 {agent_id} 創建成功")
    except Exception as e:
        print(f"✗ 代理 {agent_id} 創建失敗: {e}")
        raise


if __name__ == "__main__":
    try:
        add_jingbao_poc_agent()
        print("\n✅ 測試代理添加成功！")
    except Exception as e:
        print(f"\n❌ 添加失敗: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
