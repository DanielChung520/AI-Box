# 代碼功能說明: 刪除經寶PoC測試代理
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""刪除經寶PoC測試代理

刪除之前為測試創建的「經寶PoC代理」。
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

from services.api.services.agent_display_config_store_service import AgentDisplayConfigStoreService


def remove_jingbao_poc_agent() -> None:
    """刪除經寶PoC測試代理"""
    print("開始刪除「經寶PoC代理」測試數據...")
    store_service = AgentDisplayConfigStoreService()

    agent_id = "jingbao-poc-1"

    try:
        # 檢查代理是否存在
        existing = store_service.get_agent_config(agent_id, tenant_id=None)
        if not existing:
            print(f"代理 {agent_id} 不存在，無需刪除")
            return

        # 刪除代理（軟刪除）
        success = store_service.delete_agent(agent_id=agent_id, tenant_id=None)

        if success:
            print(f"✓ 代理 {agent_id} 刪除成功")
        else:
            print(f"✗ 代理 {agent_id} 刪除失敗")
    except Exception as e:
        print(f"✗ 刪除代理 {agent_id} 時發生錯誤: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    try:
        remove_jingbao_poc_agent()
        print("\n✅ 刪除完成！")
    except Exception as e:
        print(f"\n❌ 刪除失敗: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
