# 代碼功能說明: 知識圖譜服務
# 創建日期: 2026-02-01
# 創建人: Daniel Chung

"""知識圖譜服務 - 從 ArangoDB 獲取 MM-Agent 相關知識"""

import logging
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from database.arangodb.client import ArangoDBClient
from database.arangodb.queries import GraphQuery

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """知識圖譜服務 - 從 ArangoDB 獲取知識"""

    def __init__(self):
        """初始化知識圖譜服務"""
        self._arangodb_client: Optional[ArangoDBClient] = None
        self._db_name = "ai_box_kg"
        self._task_id = "1769909074960"  # MM-Agent 任務 ID

    async def initialize(self):
        """初始化服務"""
        try:
            self._arangodb_client = ArangoDBClient(
                database=self._db_name,
                connect_on_init=True,
            )
            logger.info("知識圖譜服務已初始化", db_name=self._db_name)
        except Exception as e:
            logger.error(f"初始化失敗: {e}", exc_info=True)
            raise

    def ensure_connection(self):
        """確保連接已建立"""
        if not self._arangodb_client:
            raise RuntimeError("ArangoDB 客戶端未初始化")
        self._arangodb_client.ensure_connection()

    async def get_agent_knowledge(
        self,
        task_id: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """獲取 Agent 專業知識

        Args:
            task_id: 任務 ID（默認 MM-Agent 任務）
            entity_type: 實體類型過濾（如 Job_Position、Operation）

        Returns:
            知識圖譜數據
        """
        self.ensure_connection()

        task_id = task_id or self._task_id

        try:
            # 查詢任務相關文件
            aql_query = """
            FOR task IN user_tasks
                FILTER task.task_id == @task_id
                    FOR file IN file_metadata
                        FILTER file.task_id == task._key AND file.kg_status == "completed"
                            LET file_entities = (
                                FOR e IN entities
                                    FILTER e.file_id == file._key
                                    RETURN e
                            )
                            LET file_relations = (
                                FOR r IN relations
                                    FILTER r.file_id == file._key
                                    RETURN r
                            )
                            RETURN {
                                "file_id": file.file_id,
                                "filename": file.filename,
                                "file_type": file.file_type,
                                "domain": file.domain,
                                "entities": file_entities,
                                "relations": file_relations,
                                "chunk_count": file.chunk_count,
                            }
            RETURN {
                "task_id": task._key,
                "task_title": task.title,
                "files": files
            }
            """

            result = self._arangodb_client.execute_aql(
                aql_query,
                bind_vars={"task_id": task_id},
                batch_size=100,
            )

            knowledge = {
                "task_id": task_id,
                "task_title": result["results"][0]["task_title"],
                "files": result["results"][0]["files"],
                "total_entities": 0,
                "total_relations": 0,
            }

            # 聚合實體和關係
            for file_data in knowledge["files"]:
                knowledge["total_entities"] += len(file_data["entities"])
                knowledge["total_relations"] += len(file_data["relations"])

            # 過濾實體類型
            if entity_type:
                for file_data in knowledge["files"]:
                    file_data["entities"] = [
                        e for e in file_data["entities"] if e["type"] == entity_type
                    ]

            logger.info(
                "獲取知識圖譜",
                task_id=task_id,
                files=len(knowledge["files"]),
                entities=knowledge["total_entities"],
                relations=knowledge["total_relations"],
            )

            return knowledge

        except Exception as e:
            logger.error(f"獲取知識失敗: {e}", exc_info=True)
            raise

    async def query_entity_relations(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        depth: int = 2,
    ) -> List[Dict[str, Any]]:
        """查詢實體關係

        Args:
            entity_id: 實體 ID
            relation_type: 關係類型（如 BELONGS_TO）
            depth: 遍歷深度

        Returns:
            關係鏈路
        """
        self.ensure_connection()

        try:
            # 構建 AQL 查詢
            if relation_type:
                aql_query = """
                WITH start_node, relations, related_nodes
                FOR s, e, p IN 1..@depth ANY @start_node, graph @relation_type OPTIONS bfs: true, uniqueVertices: true
                    FILTER s._key == @entity_id
                    LET relation = {
                        "_from": e._from,
                        "_to": e._to,
                        "type": e.type,
                        "confidence": e.confidence,
                        "context": e.context,
                    }
                    LET node = {
                        "_key": p._key,
                        "type": p.type,
                        "name": p.name,
                        "text": p.text,
                    }
                    RETURN {"relation": relation, "node": node}
                """
                bind_vars = {
                    "entity_id": entity_id,
                    "relation_type": relation_type,
                    "depth": depth,
                }
            else:
                aql_query = """
                WITH start_node, relations, related_nodes
                FOR s, e, p IN 1..@depth ANY @start_node, GRAPH 'knowledge_graph' OPTIONS bfs: true, uniqueVertices: true
                    FILTER s._key == @entity_id
                    LET relation = {
                        "_from": e._from,
                        "_to": e._to,
                        "type": e.type,
                        "confidence": e.confidence,
                        "context": e.context,
                    }
                    LET node = {
                        "_key": p._key,
                        "type": p.type,
                        "name": p.name,
                        "text": p.text,
                    }
                    RETURN {"relation": relation, "node": node}
                """
                bind_vars = {
                    "entity_id": entity_id,
                    "depth": depth,
                }

            result = self._arangodb_client.execute_aql(
                aql_query,
                bind_vars=bind_vars,
                batch_size=100,
            )

            logger.info(
                "查詢實體關係",
                entity_id=entity_id,
                depth=depth,
                results_count=len(result["results"]),
            )

            return result["results"]

        except Exception as e:
            logger.error(f"查詢實體關係失敗: {e}", exc_info=True)
            raise

    async def get_contextual_knowledge(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """獲取上下文相關知識

        根據查詢中的關鍵詞，從知識圖譜中提取相關實體

        Args:
            query: 用戶查詢
            top_k: 返回前 K 個相關知識

        Returns:
            相關實體和關係
        """
        self.ensure_connection()

        try:
            # 提取查詢中的關鍵詞（簡化版本）
            keywords = self._extract_keywords(query)

            if not keywords:
                return []

            # 查詢相關實體
            aql_query = """
            FOR e IN entities
                FILTER e.file_id IN [
                    FOR file IN file_metadata
                        FILTER file.task_id == @task_id
                        RETURN file.file_id
                ]
                FILTER @keywords ANY IN e.text
                LIMIT @top_k
                RETURN {
                    "_key": e._key,
                    "type": e.type,
                    "name": e.name,
                    "text": e.text,
                    "file_id": e.file_id,
                    "similarity": LENGTH(@keywords FILTER k IN e.text) / LENGTH(@keywords)
                }
            SORT similarity DESC
            """

            result = self._arangodb_client.execute_aql(
                aql_query,
                bind_vars={"task_id": self._task_id, "keywords": keywords, "top_k": top_k},
                batch_size=top_k,
            )

            # 獲取每個實體的關係
            enhanced_results = []
            for entity in result["results"]:
                entity_id = entity["_key"]

                relations = await self.query_entity_relations(
                    entity_id=entity_id,
                    depth=1,
                )

                enhanced_results.append(
                    {
                        "entity": entity,
                        "relations": relations[:3],  # 只取前 3 個關係
                    }
                )

            logger.info(
                "獲取上下文知識",
                query=query,
                keywords=keywords,
                results_count=len(enhanced_results),
            )

            return enhanced_results

        except Exception as e:
            logger.error(f"獲取上下文知識失敗: {e}", exc_info=True)
            raise

    def _extract_keywords(self, query: str) -> List[str]:
        """從查詢中提取關鍵詞

        Args:
            query: 用戶查詢

        Returns:
            關鍵詞列表
        """
        # 簡化的關鍵詞提取
        keywords = []

        # 物料管理相關詞彙
        domain_keywords = [
            "庫存",
            "採購",
            "銷售",
            "領料",
            "報廢",
            "盤點",
            "進貨",
            "出貨",
            "收料",
            "料號",
            "倉庫",
            "作業",
            "職責",
            "技能",
            "流程",
        ]

        for keyword in domain_keywords:
            if keyword in query:
                keywords.append(keyword)

        # 提取料號
        import re

        part_numbers = re.findall(r"[A-Z]{2,4}-?\d{2,6}", query)
        keywords.extend(part_numbers)

        return keywords

    async def get_job_position_knowledge(
        self,
        position_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """獲取職位相關知識

        Args:
            position_type: 職位類型

        Returns:
            職位知識
        """
        knowledge = await self.get_agent_knowledge(entity_type="Job_Position")

        if not knowledge["files"]:
            return {}

        # 聚合職位知識
        positions = []
        for file_data in knowledge["files"]:
            for entity in file_data["entities"]:
                if entity["type"] == "Job_Position":
                    positions.append(entity)

        return {
            "positions": positions,
            "total_count": len(positions),
        }

    async def get_operation_knowledge(
        self,
        operation_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """獲取作業操作知識

        Args:
            operation_type: 作業類型

        Returns:
            作業知識
        """
        knowledge = await self.get_agent_knowledge(entity_type="Operation")

        if not knowledge["files"]:
            return {}

        # 聚合作業知識
        operations = []
        for file_data in knowledge["files"]:
            for entity in file_data["entities"]:
                if entity["type"] in ["Operation", "OPERATION"]:
                    operations.append(entity)

        return {
            "operations": operations,
            "total_count": len(operations),
        }


if __name__ == "__main__":
    import asyncio

    async def test_kg_service():
        """測試知識圖譜服務"""
        service = KnowledgeGraphService()

        try:
            await service.initialize()

            # 測試 1：獲取 MM-Agent 知識
            print("\n" + "=" * 70)
            print("測試 1：獲取 MM-Agent 知識")
            print("=" * 70)

            knowledge = await service.get_agent_knowledge()
            print(f"任務標題: {knowledge['task_title']}")
            print(f"文件數量: {len(knowledge['files'])}")
            print(f"總實體: {knowledge['total_entities']}")
            print(f"總關係: {knowledge['total_relations']}")

            # 測試 2：查詢實體關係
            print("\n" + "=" * 70)
            print("測試 2：查詢實體關係")
            print("=" * 70)

            relations = await service.query_entity_relations(
                entity_id="entities/job_position_09271d2eeaf86b57",
                depth=2,
            )
            print(f"關係數量: {len(relations)}")
            for i, rel in enumerate(relations[:5], 1):
                print(f"  {i}. {rel['relation']['type']}: {rel['node']['name']}")

            # 測試 3：獲取上下文知識
            print("\n" + "=" * 70)
            print("測試 3：獲取上下文知識")
            print("=" * 70)

            contextual = await service.get_contextual_knowledge(query="庫存還有多少", top_k=3)
            print(f"相關知識數量: {len(contextual)}")

            # 測試 4：獲取職位知識
            print("\n" + "=" * 70)
            print("測試 4：獲取職位知識")
            print("=" * 70)

            position_knowledge = await service.get_job_position_knowledge()
            print(f"職位數量: {position_knowledge['total_count']}")
            for pos in position_knowledge["positions"][:3]:
                print(f"  - {pos['name']}: {pos['text']}")

        except Exception as e:
            logger.error(f"測試失敗: {e}", exc_info=True)
            raise

    asyncio.run(test_kg_service())
