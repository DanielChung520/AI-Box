# 代码功能说明: MasterRAG 参数提取工具
# 创建日期: 2026-03-02
# 创建人: AI-Box 开发团队

"""MasterRAG 参数提取工具

用于从用户查询中提取结构化参数（料号、仓库等）
"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def extract_params_with_master_rag(instruction: str) -> Dict[str, Any]:
    """使用 MasterRAG 提取查询参数

    Args:
        instruction: 用户查询指令

    Returns:
        参数字典，如 {"item_no": "ZPLJ001PX_1", "warehouse_no": "8802"}
    """
    params = {}

    try:
        from database.qdrant.mm_master_rag_client import get_mm_master_rag_client
        from services.api.services.embedding_service import get_embedding_service

        # 获取 embedding service
        embedding_service = get_embedding_service()

        # 获取 MasterRAG client
        master_rag = get_mm_master_rag_client()

        # 1. 尝试提取料号 (item_no)
        # 匹配料号格式：字母数字组合，可能包含 - 或 _
        item_match = re.search(r"([A-Za-z0-9]+[-_]?[A-Za-z0-9]+)", instruction)
        if item_match:
            potential_item = item_match.group(1)
            # 过滤太短的匹配
            if len(potential_item) >= 5:
                try:
                    query_vector = embedding_service.generate_embedding(potential_item)
                    if query_vector:
                        items = master_rag.search_items(query_vector, text=potential_item, limit=3)
                        if items and items[0].get("score", 0) > 0.7:
                            params["item_no"] = items[0]["payload"]["item_no"]
                            logger.info(
                                f"[MasterRAG] 找到料号: {params['item_no']} (score={items[0]['score']})"
                            )
                except Exception as e:
                    logger.warning(f"[MasterRAG] 料号提取失败: {e}")

        # 2. 尝试提取仓库 (warehouse_no)
        warehouse_keywords = ["仓库", "仓", "warehouse", "仓别"]
        for kw in warehouse_keywords:
            if kw in instruction:
                # 匹配4位数字或字母数字组合
                wh_match = re.search(r"(\d{4}|[A-Za-z]+\d+)", instruction)
                if wh_match:
                    potential_wh = wh_match.group(1)
                    try:
                        query_vector = embedding_service.generate_embedding(potential_wh)
                        if query_vector:
                            warehouses = master_rag.search_warehouses(
                                query_vector, text=potential_wh, limit=3
                            )
                            if warehouses and warehouses[0].get("score", 0) > 0.7:
                                params["warehouse_no"] = warehouses[0]["payload"]["warehouse_no"]
                                logger.info(
                                    f"[MasterRAG] 找到仓库: {params['warehouse_no']} (score={warehouses[0]['score']})"
                                )
                    except Exception as e:
                        logger.warning(f"[MasterRAG] 仓库提取失败: {e}")
                break

    except Exception as e:
        logger.warning(f"[MasterRAG] 参数提取失败: {e}")

    return params


def get_extracted_params(instruction: str) -> Dict[str, Any]:
    """同步版本的参数提取（用于同步调用）"""
    params = {}

    try:
        from database.qdrant.mm_master_rag_client import get_mm_master_rag_client
        from services.api.services.embedding_service import get_embedding_service

        embedding_service = get_embedding_service()
        master_rag = get_mm_master_rag_client()

        # 1. 尝试提取料号
        item_match = re.search(r"([A-Za-z0-9]+[-_]?[A-Za-z0-9]+)", instruction)
        if item_match:
            potential_item = item_match.group(1)
            if len(potential_item) >= 5:
                try:
                    query_vector = embedding_service.generate_embedding(potential_item)
                    if query_vector:
                        items = master_rag.search_items(query_vector, text=potential_item, limit=3)
                        if items and items[0].get("score", 0) > 0.7:
                            params["item_no"] = items[0]["payload"]["item_no"]
                except Exception as e:
                    logger.warning(f"料号提取失败: {e}")

    except Exception as e:
        logger.warning(f"参数提取失败: {e}")

    return params
