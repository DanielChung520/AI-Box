# 代碼功能說明: 文件存儲模組初始化文件
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""文件存儲模組 - 提供文件存儲接口和實現"""

from .file_storage import FileStorage, LocalFileStorage, create_storage_from_config

# S3 存儲是可選依賴（需要 boto3），如果不可用則跳過導入
try:
    from .s3_storage import S3FileStorage, SeaweedFSService

    __all__ = [
        "FileStorage",
        "LocalFileStorage",
        "S3FileStorage",
        "SeaweedFSService",
        "create_storage_from_config",
    ]
except ImportError:
    # boto3 不可用時，只導出基本存儲功能
    __all__ = [
        "FileStorage",
        "LocalFileStorage",
        "create_storage_from_config",
    ]
