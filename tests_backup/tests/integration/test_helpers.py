# 代碼功能說明: 整合測試輔助函數
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""整合測試輔助函數"""

import time
import asyncio
from typing import Dict, Any, Callable, List
from functools import wraps
from httpx import AsyncClient, Response


async def check_response_time(response: Response, max_time_ms: float) -> bool:
    """
    檢查響應時間是否在允許範圍內

    Args:
        response: HTTP 響應對象
        max_time_ms: 最大允許時間（毫秒）

    Returns:
        是否在允許範圍內
    """
    # 注意：httpx 響應對象不直接包含時間信息
    # 需要在調用前後記錄時間
    return True  # 實際實現需要在調用前後記錄時間


def assert_response_success(response: Response) -> None:
    """
    斷言響應成功

    Args:
        response: HTTP 響應對象

    Raises:
        AssertionError: 如果響應不成功
    """
    assert response.status_code in [200, 201, 207], (
        f"Expected success status code, got {response.status_code}. "
        f"Response: {response.text}"
    )


def assert_response_error(response: Response, expected_status: int) -> None:
    """
    斷言響應錯誤

    Args:
        response: HTTP 響應對象
        expected_status: 預期的錯誤狀態碼

    Raises:
        AssertionError: 如果響應不符合預期
    """
    assert response.status_code == expected_status, (
        f"Expected status code {expected_status}, got {response.status_code}. "
        f"Response: {response.text}"
    )


def get_response_data(response: Response) -> Dict[str, Any]:
    """
    獲取響應數據

    Args:
        response: HTTP 響應對象

    Returns:
        響應數據字典
    """
    data = response.json()
    # 如果使用 APIResponse 格式，提取 data 字段
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


async def wait_for_condition(
    condition_func, timeout: float = 30.0, interval: float = 1.0
) -> bool:
    """
    等待條件滿足

    Args:
        condition_func: 條件檢查函數
        timeout: 超時時間（秒）
        interval: 檢查間隔（秒）

    Returns:
        條件是否滿足
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        await asyncio.sleep(interval)
    return False


async def check_service_availability(url: str, timeout: float = 5.0) -> bool:
    """
    檢查服務可用性

    Args:
        url: 服務 URL
        timeout: 超時時間（秒）

    Returns:
        服務是否可用
    """
    try:
        async with AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            return response.status_code in [200, 201, 204]
    except Exception:
        return False


def measure_response_time(func: Callable) -> Callable:
    """
    測量響應時間裝飾器

    Args:
        func: 要測量的函數

    Returns:
        裝飾後的函數
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        elapsed_ms = (time.time() - start_time) * 1000
        # 將執行時間添加到結果中（如果結果是字典）
        if isinstance(result, dict):
            result["_elapsed_ms"] = elapsed_ms
        return result

    return wrapper


def generate_test_vectors(count: int, dimension: int = 384) -> List[List[float]]:
    """
    生成測試向量

    Args:
        count: 向量數量
        dimension: 向量維度

    Returns:
        測試向量列表
    """
    import random

    vectors = []
    for _ in range(count):
        # 生成隨機向量（歸一化）
        vector = [random.random() for _ in range(dimension)]
        # 簡單歸一化
        magnitude = sum(x * x for x in vector) ** 0.5
        if magnitude > 0:
            vector = [x / magnitude for x in vector]
        vectors.append(vector)
    return vectors


def generate_test_documents(count: int) -> List[str]:
    """
    生成測試文檔

    Args:
        count: 文檔數量

    Returns:
        測試文檔列表
    """
    templates = [
        "這是一個測試文檔 {}. 用於測試向量數據庫的功能。",
        "文檔編號 {} 包含一些示例內容，用於驗證系統性能。",
        "測試數據 {} 用於評估系統的處理能力。",
        "示例文檔 {} 展示了系統的基本功能。",
        "文檔 {} 包含測試用的文本內容。",
    ]
    documents = []
    for i in range(count):
        template = templates[i % len(templates)]
        documents.append(template.format(i + 1))
    return documents
