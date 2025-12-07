# 代碼功能說明: Redis 模組初始化
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""Redis 模組 - 提供 Redis 客戶端封裝"""

from database.redis.client import get_redis_client, reset_redis_client

__all__ = ["get_redis_client", "reset_redis_client"]
