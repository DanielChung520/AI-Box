#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代碼功能說明: Entity Memory 種子數據腳本
創建日期: 2026-02-04
創建人: Daniel Chung

初始化 Entity Memory 系統的種子數據。
預載入系統相關的實體名稱。
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(dotenv_path=project_root / ".env")

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# 系統實體種子數據
SEED_ENTITIES = [
    # AI 系統相關
    {"value": "AI-Box", "type": "entity_noun", "description": "AI-Box AI 輔助軟體開發平台"},
    {"value": "ChatGPT", "type": "entity_noun", "description": "OpenAI 的對話模型"},
    {"value": "Claude", "type": "entity_noun", "description": "Anthropic 的對話模型"},
    {"value": "Gemini", "type": "entity_noun", "description": "Google 的對話模型"},
    {"value": "Ollama", "type": "entity_noun", "description": "本地 LLM 運行框架"},
    {"value": "Llama", "type": "entity_noun", "description": "Meta 的開源 LLM 模型"},
    {"value": "DeepSeek", "type": "entity_noun", "description": "DeepSeek AI 模型"},
    # Agent 系統相關
    {
        "value": "mm-agent",
        "type": "entity_noun",
        "description": "物料管理代理（Material Management Agent）",
    },
    {
        "value": "KA-Agent",
        "type": "entity_noun",
        "description": "知識獲取代理（Knowledge Acquisition Agent）",
    },
    {"value": "Task Analyzer", "type": "entity_noun", "description": "任務分析器"},
    {"value": "Orchestrator", "type": "entity_noun", "description": "任務編排器"},
    # 數據庫相關
    {"value": "ArangoDB", "type": "entity_noun", "description": "圖資料庫"},
    {"value": "Qdrant", "type": "entity_noun", "description": "向量資料庫"},
    {"value": "ChromaDB", "type": "entity_noun", "description": "向量資料庫"},
    {"value": "Redis", "type": "entity_noun", "description": "記憶體資料庫"},
    {"value": "SeaweedFS", "type": "entity_noun", "description": "分散式檔案系統"},
    {"value": "PostgreSQL", "type": "entity_noun", "description": "關聯式資料庫"},
    {"value": "MongoDB", "type": "entity_noun", "description": "文件資料庫"},
    # 框架相關
    {"value": "FastAPI", "type": "entity_noun", "description": "Python Web 框架"},
    {"value": "React", "type": "entity_noun", "description": "前端框架"},
    {"value": "LangGraph", "type": "entity_noun", "description": "工作流框架"},
    {"value": "LangChain", "type": "entity_noun", "description": "LLM 應用框架"},
    {"value": "MCP", "type": "entity_noun", "description": "Model Context Protocol"},
    # 公司/組織相關
    {"value": "宏康 HCI", "type": "entity_noun", "description": "宏康 HCI 公司"},
    {"value": "OpenAI", "type": "entity_noun", "description": "OpenAI 公司"},
    {"value": "Anthropic", "type": "entity_noun", "description": "Anthropic 公司"},
    {"value": "Meta", "type": "entity_noun", "description": "Meta 公司"},
    {"value": "Google", "type": "entity_noun", "description": "Google 公司"},
    # 協議/標準相關
    {"value": "SSE", "type": "entity_noun", "description": "Server-Sent Events"},
    {"value": "WebSocket", "type": "entity_noun", "description": "WebSocket 協議"},
    {"value": "gRPC", "type": "entity_noun", "description": "gRPC 遠程過程調用框架"},
    # 其他常用術語
    {"value": "RAG", "type": "entity_noun", "description": "檢索增強生成"},
    {"value": "MoE", "type": "entity_noun", "description": "混合專家模型"},
    {"value": "LLM", "type": "entity_noun", "description": "大型語言模型"},
    {"value": "NER", "type": "entity_noun", "description": "命名實體識別"},
    {"value": "向量庫", "type": "entity_noun", "description": "向量資料庫"},
    {"value": "圖譜", "type": "entity_noun", "description": "知識圖譜"},
]


async def seed_entity_memory():
    """初始化 Entity Memory 種子數據"""
    try:
        from agents.services.entity_memory.entity_memory_service import get_entity_memory_service
        from agents.services.entity_memory.models import EntityType

        logger.info("=" * 60)
        logger.info("Entity Memory 種子數據初始化")
        logger.info("=" * 60)

        # 獲取服務
        service = get_entity_memory_service()
        storage = service.storage

        # 確保存儲層初始化
        storage._ensure_initialized()
        logger.info("存儲層初始化完成")

        # 系統用戶 ID（用於存儲系統級別的實體）
        SYSTEM_USER_ID = "system"

        # 統計
        created_count = 0
        skipped_count = 0
        error_count = 0

        logger.info(f"\n開始載入 {len(SEED_ENTITIES)} 個系統實體...\n")

        for entity_data in SEED_ENTITIES:
            entity_value = entity_data["value"]
            description = entity_data.get("description", "")

            try:
                # 檢查是否已存在
                existing = await storage.get_entity_by_value(entity_value, SYSTEM_USER_ID)
                if existing:
                    logger.info(f"  ⏭️  跳過: {entity_value} (已存在)")
                    skipped_count += 1
                    continue

                # 創建新實體
                entity = await service.remember_entity(
                    entity_value=entity_value,
                    user_id=SYSTEM_USER_ID,
                    attributes={
                        "source": "seed",
                        "description": description,
                        "category": entity_data["type"],
                    },
                )

                logger.info(f"  ✅ 創建: {entity_value}")
                created_count += 1

            except Exception as e:
                logger.error(f"  ❌ 錯誤: {entity_value} - {e}")
                error_count += 1

        # 統計結果
        logger.info("\n" + "=" * 60)
        logger.info("種子數據初始化完成")
        logger.info("=" * 60)
        logger.info(f"  新建實體: {created_count}")
        logger.info(f"  跳過實體: {skipped_count}")
        logger.info(f"  錯誤數量: {error_count}")
        logger.info(f"  總計: {created_count + skipped_count + error_count}")

        # 列出所有系統實體
        all_entities = await storage.list_user_entities(SYSTEM_USER_ID)
        logger.info(f"\n系統實體列表 ({len(all_entities)} 個):")
        for entity in sorted(all_entities, key=lambda e: e.entity_value):
            logger.info(f"  - {entity.entity_value}")

        return True

    except Exception as e:
        logger.error(f"種子數據初始化失敗: {e}", exc_info=True)
        return False


async def clear_entity_memory():
    """清除所有實體數據（用於測試）"""
    try:
        from agents.services.entity_memory.entity_memory_service import get_entity_memory_service

        logger.info("清除 Entity Memory 數據...")

        service = get_entity_memory_service()
        storage = service.storage

        # 系統用戶 ID
        SYSTEM_USER_ID = "system"

        # 獲取所有實體
        entities = await storage.list_user_entities(SYSTEM_USER_ID)

        # 刪除每個實體
        # 注意：Qdrant 的刪除需要使用 delete_points
        if storage._qdrant_client and entities:
            entity_ids = [e.entity_id for e in entities]
            storage._qdrant_client.delete_points(
                collection_name="ai_box_entity_memory",
                points=entity_ids,
            )
            logger.info(f"已刪除 {len(entities)} 個實體")

        # 清除 ArangoDB 關係
        if storage._arangodb_client:
            try:
                db = storage._arangodb_client.db
                if db.has_collection("entity_relations"):
                    collection = db.collection("entity_relations")
                    # 刪除所有文檔
                    for doc in collection.all():
                        collection.delete(doc)
                    logger.info("已清除 ArangoDB 關係數據")
            except Exception as e:
                logger.warning(f"清除 ArangoDB 關係失敗: {e}")

        logger.info("Entity Memory 數據已清除")
        return True

    except Exception as e:
        logger.error(f"清除 Entity Memory 失敗: {e}", exc_info=True)
        return False


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="Entity Memory 種子數據管理")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="清除所有實體數據",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="載入種子數據",
    )

    args = parser.parse_args()

    if args.clear:
        asyncio.run(clear_entity_memory())
    elif args.seed:
        asyncio.run(seed_entity_memory())
    else:
        # 預設執行 seed
        asyncio.run(seed_entity_memory())


if __name__ == "__main__":
    main()
