# 代碼功能說明: ChromaDB 工具模組
# 創建日期: 2025-11-25 21:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 21:30 (UTC+8)

"""ChromaDB 工具模組 - 提供嵌入維度轉換、metadata 驗證等工具函數"""

import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def validate_embedding_dimension(
    embeddings: Union[List[List[float]], List[float]],
    expected_dim: Optional[int] = None,
) -> int:
    """
    驗證並獲取嵌入向量的維度

    Args:
        embeddings: 嵌入向量或向量列表
        expected_dim: 預期的維度（如果提供，將進行驗證）

    Returns:
        嵌入向量的維度

    Raises:
        ValueError: 如果嵌入向量格式無效或維度不一致
    """
    if not embeddings:
        raise ValueError("Embeddings cannot be empty")

    # 標準化為列表格式
    if isinstance(embeddings[0], (int, float)):
        # 單個向量
        embeddings_list: List[List[float]] = [embeddings]  # type: ignore[list-item]
    else:
        # 向量列表
        embeddings_list = embeddings  # type: ignore[assignment]

    # 獲取第一個向量的維度
    first_dim = len(embeddings_list[0])
    if first_dim == 0:
        raise ValueError("Embedding vector cannot be empty")

    # 驗證所有向量的維度一致
    for i, emb in enumerate(embeddings_list):
        if not isinstance(emb, list):
            raise ValueError(f"Embedding at index {i} is not a list")
        if len(emb) != first_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {first_dim}, "
                f"got {len(emb)} at index {i}"
            )

    # 如果提供了預期維度，進行驗證
    if expected_dim is not None and first_dim != expected_dim:
        raise ValueError(f"Embedding dimension mismatch: expected {expected_dim}, got {first_dim}")

    return first_dim


def normalize_embeddings(
    embeddings: Union[List[List[float]], List[float]],
) -> List[List[float]]:
    """
    將嵌入向量標準化為列表格式

    Args:
        embeddings: 嵌入向量或向量列表

    Returns:
        標準化後的向量列表
    """
    if not embeddings:
        return []

    if isinstance(embeddings[0], (int, float)):
        # 單個向量
        return [list(embeddings)]  # type: ignore[arg-type]
    # 向量列表
    return [list(emb) for emb in embeddings]  # type: ignore[arg-type]


def convert_embedding_dimension(
    embeddings: List[List[float]],
    target_dim: int,
    method: str = "pad",
    pad_value: float = 0.0,
) -> List[List[float]]:
    """
    轉換嵌入向量的維度

    Args:
        embeddings: 嵌入向量列表
        target_dim: 目標維度
        method: 轉換方法 ('pad' 或 'truncate')
        pad_value: 填充值（當使用 pad 方法時）

    Returns:
        轉換後的嵌入向量列表
    """
    result = []
    for emb in embeddings:
        current_dim = len(emb)
        if current_dim == target_dim:
            result.append(emb[:])
        elif current_dim < target_dim:
            if method == "pad":
                # 填充
                padded = emb[:] + [pad_value] * (target_dim - current_dim)
                result.append(padded)
            else:
                raise ValueError(
                    f"Cannot pad when method is {method}. "
                    f"Use method='pad' for dimension expansion."
                )
        else:
            # current_dim > target_dim
            if method == "truncate":
                # 截斷
                result.append(emb[:target_dim])
            else:
                raise ValueError(
                    f"Cannot truncate when method is {method}. "
                    f"Use method='truncate' for dimension reduction."
                )
    return result


def validate_metadata(
    metadatas: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]],
    required_fields: Optional[List[str]] = None,
    allowed_fields: Optional[List[str]] = None,
) -> None:
    """
    驗證 metadata 格式和字段

    Args:
        metadatas: 元數據字典或字典列表
        required_fields: 必需字段列表
        allowed_fields: 允許的字段列表（如果提供，將檢查是否包含不允許的字段）

    Raises:
        ValueError: 如果 metadata 格式無效或缺少必需字段
    """
    if metadatas is None:
        if required_fields:
            raise ValueError(
                f"Metadata is required but not provided. Required fields: {required_fields}"
            )
        return

    # 標準化為列表格式
    if isinstance(metadatas, dict):
        metadata_list = [metadatas]
    else:
        metadata_list = metadatas

    required_fields = required_fields or []

    for i, metadata in enumerate(metadata_list):
        if not isinstance(metadata, dict):
            raise ValueError(f"Metadata at index {i} is not a dictionary")

        # 檢查必需字段
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Missing required field '{field}' in metadata at index {i}")

        # 檢查允許的字段
        if allowed_fields is not None:
            for field in metadata.keys():
                if field not in allowed_fields:
                    logger.warning(
                        f"Unknown field '{field}' in metadata at index {i}. "
                        f"Allowed fields: {allowed_fields}"
                    )


def batch_items(
    items: List[Any],
    batch_size: int,
) -> List[List[Any]]:
    """
    將項目列表分批

    Args:
        items: 項目列表
        batch_size: 每批的大小

    Returns:
        分批後的項目列表
    """
    if batch_size <= 0:
        raise ValueError("Batch size must be greater than 0")

    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i : i + batch_size])
    return batches


def validate_collection_name(name: str) -> None:
    """
    驗證集合名稱格式

    Args:
        name: 集合名稱

    Raises:
        ValueError: 如果集合名稱無效
    """
    if not name:
        raise ValueError("Collection name cannot be empty")

    if len(name) > 200:
        raise ValueError("Collection name cannot exceed 200 characters")

    # 檢查是否包含不允許的字符
    invalid_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    for char in invalid_chars:
        if char in name:
            raise ValueError(f"Collection name cannot contain '{char}'")


def ensure_list(value):
    """
    將輸入轉換為列表格式，若為 None 則回傳空列表。
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
