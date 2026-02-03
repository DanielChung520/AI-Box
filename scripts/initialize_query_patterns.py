# 代碼功能說明: 初始化知識庫查詢範例向量庫
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""初始化知識庫查詢範例向量庫腳本

此腳本用於初始化知識庫查詢範例向量庫，將查詢範例向量化並存儲到 Qdrant。

使用方法:
    python initialize_query_patterns.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    """主函數"""
    try:
        logger.info("開始初始化知識庫查詢範例向量庫...")

        from agents.task_analyzer.query_pattern_vector_store import (
            get_query_pattern_vector_store,
        )

        vector_store = get_query_pattern_vector_store()
        success = await vector_store.initialize_patterns()

        if success:
            logger.info("✅ 知識庫查詢範例向量庫初始化成功！")
            return 0
        else:
            logger.error("❌ 知識庫查詢範例向量庫初始化失敗！")
            return 1

    except Exception as e:
        logger.error(f"初始化過程中發生錯誤: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
