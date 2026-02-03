# 代碼功能說明: LangGraph 效能基準測試腳本
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""效能基準測試腳本，用於驗證 LangGraph 架構優化後的效能。"""

import asyncio
import time
import logging
from typing import List

from genai.workflows.langgraph.state import AIBoxState
from genai.workflows.langgraph.engine import TaskExecutionEngine
from genai.workflows.infra.cache import MultiLayerCache

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_benchmark():
    """執行基準測試"""
    logger.info("Starting LangGraph Performance Benchmark...")

    # 1. 初始化引擎
    cache = MultiLayerCache()
    engine = TaskExecutionEngine(cache=cache)

    # 2. 測試場景：連續 10 個任務
    user_id = "test_user_001"
    tasks = [f"Test Task {i}: Generate a summary of document {i}" for i in range(10)]

    start_time = time.time()
    results = []

    for i, task_text in enumerate(tasks):
        state = AIBoxState(
            user_id=user_id,
            session_id=f"session_{i}",
            task_id=f"task_{i}",
        )
        # 模擬設置任務屬性
        setattr(state, "task", task_text)

        logger.info(f"Executing task {i + 1}/10...")
        result = await engine.execute_task(state)
        results.append(result)

    total_time = time.time() - start_time
    logger.info(f"Benchmark completed in {total_time:.2f}s")
    logger.info(f"Average time per task: {total_time / 10:.2f}s")

    # 3. 測試快取效能 (執行重複任務)
    logger.info("Testing Cache Performance...")
    cache_start = time.time()

    state = AIBoxState(
        user_id=user_id,
        session_id="session_cache_test",
        task_id="task_cache_test",
    )
    setattr(state, "task", tasks[0])  # 使用重複的任務

    result = await engine.execute_task(state)
    cache_time = time.time() - cache_start

    logger.info(f"Cache test completed. Execution time: {cache_time:.4f}s")

    if cache_time < 0.1:
        logger.info("✅ Cache Optimization Verified: Significant speedup detected!")
    else:
        logger.info("⚠️ Cache optimization might need further tuning.")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
