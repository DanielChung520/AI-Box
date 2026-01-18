# 代碼功能說明: 初始化 SystemAdmin 用戶腳本
# 創建日期: 2026-01-17 17:13 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 17:13 UTC+8

"""初始化 SystemAdmin 用戶腳本

從環境變數讀取 SYSTEM_ADMIN_PASSWORD，創建默認 systemAdmin 用戶。
如果用戶已存在，則跳過創建。
"""

import os
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加載環境變數（必須在導入其他模組之前）
from dotenv import load_dotenv

env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

import logging

from services.api.models.system_user import SystemUserCreate
from services.api.services.system_user_store_service import SystemUserStoreService

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """主函數"""
    try:
        # 獲取密碼
        password = os.getenv("SYSTEM_ADMIN_PASSWORD", "systemAdmin@2026")
        if not password:
            logger.error("SYSTEM_ADMIN_PASSWORD environment variable is not set")
            sys.exit(1)

        # 創建 Store Service
        service = SystemUserStoreService()

        # 檢查用戶是否已存在
        existing_user = service.get_system_user("systemAdmin")
        if existing_user:
            logger.info("SystemAdmin user already exists, skipping creation")
            logger.info(f"User ID: {existing_user.user_id}, Username: {existing_user.username}")
            return

        # 創建默認 systemAdmin 用戶
        user_data = SystemUserCreate(
            user_id="systemAdmin",
            username="systemAdmin",
            email="system@ai-box.internal",
            password=password,
            roles=["system_admin"],
            permissions=["*"],
            is_active=True,
            security_level="highest",
            metadata={
                "hidden_from_external": True,
                "last_login_at": None,
                "login_count": 0,
            },
        )

        created_user = service.create_system_user(user_data)
        logger.info("SystemAdmin user created successfully")
        logger.info(f"User ID: {created_user.user_id}, Username: {created_user.username}")
        logger.info(f"Email: {created_user.email}")

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to initialize SystemAdmin user: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
