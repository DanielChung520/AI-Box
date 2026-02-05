# 代碼功能說明: RQ Worker 模組初始化
# 創建日期: 2025-12-10
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

"""RQ Worker 模組 - 提供任務處理 Worker"""

# 導入任務以供 RQ Worker 註冊（re-export 供 RQ 發現）
from .tasks import process_file_chunking_and_vectorization_task

__all__ = ["process_file_chunking_and_vectorization_task"]
