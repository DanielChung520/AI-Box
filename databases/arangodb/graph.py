# 代碼功能說明: ArangoDB 圖操作封裝
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""ArangoDB 圖操作封裝，提供圖遍歷和關係查詢功能"""

from typing import Dict, Any, List, Optional
from arango.graph import Graph
import logging

logger = logging.getLogger(__name__)


class ArangoGraph:
    """ArangoDB 圖操作封裝類"""

    def __init__(self, graph: Graph):
        """
        初始化圖封裝

        Args:
            graph: ArangoDB Graph 對象
        """
        self.graph = graph
        self.name = graph.name

    def create_vertex_collection(self, name: str) -> None:
        """
        創建頂點集合

        Args:
            name: 頂點集合名稱
        """
        try:
            self.graph.create_vertex_collection(name)
            logger.info(f"Created vertex collection '{name}' in graph '{self.name}'")
        except Exception as e:
            logger.error(f"Failed to create vertex collection '{name}': {e}")
            raise

    def create_edge_definition(
        self,
        edge_collection: str,
        from_vertex_collections: List[str],
        to_vertex_collections: List[str],
    ) -> None:
        """
        創建邊定義

        Args:
            edge_collection: 邊集合名稱
            from_vertex_collections: 源頂點集合列表
            to_vertex_collections: 目標頂點集合列表
        """
        try:
            self.graph.create_edge_definition(
                edge_collection=edge_collection,
                from_vertex_collections=from_vertex_collections,
                to_vertex_collections=to_vertex_collections,
            )
            logger.info(
                f"Created edge definition '{edge_collection}' in graph '{self.name}'"
            )
        except Exception as e:
            logger.error(f"Failed to create edge definition '{edge_collection}': {e}")
            raise

    def insert_vertex(self, collection: str, vertex: Dict[str, Any]) -> Dict[str, Any]:
        """
        插入頂點

        Args:
            collection: 頂點集合名稱
            vertex: 頂點文檔

        Returns:
            插入結果
        """
        try:
            result = self.graph.insert_vertex(collection, vertex)
            logger.debug(
                f"Inserted vertex into collection '{collection}' in graph '{self.name}'"
            )
            return result  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to insert vertex into collection '{collection}': {e}")
            raise

    def insert_edge(
        self,
        collection: str,
        edge: Dict[str, Any],
        from_vertex: str,
        to_vertex: str,
    ) -> Dict[str, Any]:
        """
        插入邊

        Args:
            collection: 邊集合名稱
            edge: 邊文檔
            from_vertex: 源頂點 ID（格式: collection/_key）
            to_vertex: 目標頂點 ID（格式: collection/_key）

        Returns:
            插入結果
        """
        try:
            result = self.graph.insert_edge(collection, edge, from_vertex, to_vertex)  # type: ignore[call-arg,arg-type]
            logger.debug(
                f"Inserted edge into collection '{collection}' in graph '{self.name}'"
            )
            return result  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to insert edge into collection '{collection}': {e}")
            raise

    def get_vertex(self, vertex_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取頂點

        Args:
            vertex_id: 頂點 ID（格式: collection/_key）

        Returns:
            頂點文檔或 None
        """
        try:
            vertex = self.graph.vertex(vertex_id)
            logger.debug(f"Retrieved vertex '{vertex_id}' from graph '{self.name}'")
            return vertex  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to get vertex '{vertex_id}': {e}")
            raise

    def get_edge(self, edge_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取邊

        Args:
            edge_id: 邊 ID（格式: collection/_key）

        Returns:
            邊文檔或 None
        """
        try:
            edge = self.graph.edge(edge_id)
            logger.debug(f"Retrieved edge '{edge_id}' from graph '{self.name}'")
            return edge  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to get edge '{edge_id}': {e}")
            raise

    def traverse(
        self,
        start_vertex: str,
        direction: str = "outbound",
        item_order: str = "forward",
        strategy: str = "depthfirst",
        order: str = "preorder",
        edge_uniqueness: str = "global",
        vertex_uniqueness: str = "global",
        max_depth: Optional[int] = None,
        min_depth: Optional[int] = None,
        visitor: Optional[str] = None,
        filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        圖遍歷

        Args:
            start_vertex: 起始頂點 ID
            direction: 遍歷方向 ('outbound', 'inbound', 'any')
            item_order: 項目順序 ('forward', 'backward')
            strategy: 遍歷策略 ('depthfirst', 'breadthfirst')
            order: 遍歷順序 ('preorder', 'postorder', 'preorder-expander')
            edge_uniqueness: 邊唯一性 ('global', 'path')
            vertex_uniqueness: 頂點唯一性 ('global', 'path')
            max_depth: 最大深度
            min_depth: 最小深度
            visitor: 訪問者函數（AQL）
            filter: 過濾函數（AQL）

        Returns:
            遍歷結果
        """
        try:
            result = self.graph.traverse(  # type: ignore[call-arg]
                start_vertex=start_vertex,
                direction=direction,
                item_order=item_order,
                strategy=strategy,
                order=order,
                edge_uniqueness=edge_uniqueness,
                vertex_uniqueness=vertex_uniqueness,
                max_depth=max_depth,
                min_depth=min_depth,
                visitor=visitor,
                filter=filter,
            )
            logger.debug(f"Traversed graph '{self.name}' from vertex '{start_vertex}'")
            return result  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to traverse graph '{self.name}': {e}")
            raise

    def get_neighbors(
        self,
        vertex_id: str,
        direction: str = "any",
        edge_collections: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        獲取鄰居頂點

        Args:
            vertex_id: 頂點 ID
            direction: 方向 ('outbound', 'inbound', 'any')
            edge_collections: 邊集合列表（過濾）

        Returns:
            鄰居頂點列表
        """
        try:
            neighbors = self.graph.neighbors(  # type: ignore[attr-defined]
                vertex_id, direction=direction, edge_collections=edge_collections
            )
            logger.debug(f"Found {len(neighbors)} neighbor(s) for vertex '{vertex_id}'")
            return neighbors
        except Exception as e:
            logger.error(f"Failed to get neighbors for vertex '{vertex_id}': {e}")
            raise

    def get_shortest_path(
        self,
        start_vertex: str,
        end_vertex: str,
        direction: str = "outbound",
        weight_attribute: Optional[str] = None,
        default_weight: float = 1.0,
    ) -> Optional[Dict[str, Any]]:
        """
        獲取最短路徑

        Args:
            start_vertex: 起始頂點 ID
            end_vertex: 結束頂點 ID
            direction: 方向 ('outbound', 'inbound', 'any')
            weight_attribute: 權重屬性名稱
            default_weight: 默認權重

        Returns:
            最短路徑信息或 None
        """
        try:
            path = self.graph.shortest_path(  # type: ignore[attr-defined]
                start_vertex=start_vertex,
                end_vertex=end_vertex,
                direction=direction,
                weight_attribute=weight_attribute,
                default_weight=default_weight,
            )
            if path:
                logger.debug(
                    f"Found shortest path from '{start_vertex}' to '{end_vertex}'"
                )
            return path
        except Exception as e:
            logger.error(f"Failed to get shortest path: {e}")
            raise
