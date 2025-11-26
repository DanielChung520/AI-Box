# 代碼功能說明: API 版本管理
# 創建日期: 2025-11-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""API 版本常量和管理"""

# API 版本常量
API_VERSION = "1.0.0"
API_VERSION_MAJOR = 1
API_VERSION_MINOR = 0
API_VERSION_PATCH = 0

# API 版本前綴
API_PREFIX = "/api/v1"


def get_version_info() -> dict:
    """
    獲取版本信息

    Returns:
        版本信息字典
    """
    return {
        "version": API_VERSION,
        "major": API_VERSION_MAJOR,
        "minor": API_VERSION_MINOR,
        "patch": API_VERSION_PATCH,
        "prefix": API_PREFIX,
    }
