# 代碼功能說明: ArangoDB 集合操作封裝
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""ArangoDB 集合操作封裝，提供文檔 CRUD 操作"""

import logging
from typing import Any, Dict, List, Optional, Union

from arango.collection import StandardCollection

logger = logging.getLogger(__name__)


class ArangoCollection:
    """ArangoDB 集合操作封裝類"""

    def __init__(self, collection: StandardCollection):
        """
        初始化集合封裝

        Args:
            collection: ArangoDB Collection 對象
        """
        self.collection = collection
        self.name = collection.name

    def insert(
        self,
        document: Union[Dict[str, Any], List[Dict[str, Any]]],
        return_new: bool = False,
    ) -> Dict[str, Any]:
        """
        插入文檔

        Args:
            document: 文檔字典或文檔列表
            return_new: 是否返回新文檔

        Returns:
            插入結果
        """
        try:
            result = self.collection.insert(document, return_new=return_new)  # type: ignore[arg-type]
            if isinstance(document, list):
                logger.info(
                    f"Inserted {len(document)} document(s) " f"into collection '{self.name}'"
                )
            else:
                logger.info(f"Inserted document into collection '{self.name}'")
            return result  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to insert document(s) into collection '{self.name}': {e}")
            raise

    def get(
        self, key: str, rev: Optional[str] = None, check_rev: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        根據鍵獲取文檔

        Args:
            key: 文檔鍵（_key）
            rev: 修訂版本號
            check_rev: 是否檢查修訂版本

        Returns:
            文檔字典或 None
        """
        try:
            document = self.collection.get(key, rev=rev, check_rev=check_rev)
            if document:
                logger.debug(f"Retrieved document '{key}' from collection '{self.name}'")
            return document  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to get document '{key}' from collection '{self.name}': {e}")
            raise

    def update(
        self,
        document: Union[Dict[str, Any], List[Dict[str, Any]]],
        check_rev: bool = True,
        merge: bool = True,
        return_new: bool = False,
        return_old: bool = False,
    ) -> Dict[str, Any]:
        """
        更新文檔

        Args:
            document: 文檔字典或文檔列表（必須包含 _key）
            check_rev: 是否檢查修訂版本
            merge: 是否合併更新（True）或替換（False）
            return_new: 是否返回新文檔
            return_old: 是否返回舊文檔

        Returns:
            更新結果
        """
        try:
            result = self.collection.update(  # type: ignore[arg-type]
                document,
                check_rev=check_rev,
                merge=merge,
                return_new=return_new,
                return_old=return_old,
            )
            if isinstance(document, list):
                logger.info(f"Updated {len(document)} document(s) in collection '{self.name}'")
            else:
                logger.info(f"Updated document in collection '{self.name}'")
            return result  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to update document(s) in collection '{self.name}': {e}")
            raise

    def replace(
        self,
        document: Union[Dict[str, Any], List[Dict[str, Any]]],
        check_rev: bool = True,
        return_new: bool = False,
        return_old: bool = False,
    ) -> Dict[str, Any]:
        """
        替換文檔

        Args:
            document: 文檔字典或文檔列表（必須包含 _key）
            check_rev: 是否檢查修訂版本
            return_new: 是否返回新文檔
            return_old: 是否返回舊文檔

        Returns:
            替換結果
        """
        try:
            result = self.collection.replace(  # type: ignore[arg-type]
                document,
                check_rev=check_rev,
                return_new=return_new,
                return_old=return_old,
            )
            if isinstance(document, list):
                logger.info(f"Replaced {len(document)} document(s) in collection '{self.name}'")
            else:
                logger.info(f"Replaced document in collection '{self.name}'")
            return result  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to replace document(s) in collection '{self.name}': {e}")
            raise

    def delete(
        self,
        document: Union[str, Dict[str, Any], List[Union[str, Dict[str, Any]]]],
        rev: Optional[str] = None,
        check_rev: bool = True,
        return_old: bool = False,
    ) -> Dict[str, Any]:
        """
        刪除文檔

        Args:
            document: 文檔鍵、文檔字典或列表
            rev: 修訂版本號
            check_rev: 是否檢查修訂版本
            return_old: 是否返回舊文檔

        Returns:
            刪除結果
        """
        try:
            result = self.collection.delete(  # type: ignore[arg-type]
                document, rev=rev, check_rev=check_rev, return_old=return_old
            )
            if isinstance(document, list):
                logger.info(f"Deleted {len(document)} document(s) from collection '{self.name}'")
            else:
                logger.info(f"Deleted document from collection '{self.name}'")
            return result  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to delete document(s) from collection '{self.name}': {e}")
            raise

    def find(
        self,
        filters: Optional[Dict[str, Any]] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        查找文檔

        Args:
            filters: 過濾條件字典
            skip: 跳過數量
            limit: 返回數量限制
            sort: 排序字段列表

        Returns:
            文檔列表
        """
        try:
            # 轉換 sort 參數類型：list[str] -> list[dict[str, Any]]
            # ArangoDB Python 客戶端期望的格式：{"sort_by": field, "sort_order": "asc"|"desc"}
            sort_converted: list[dict[str, Any]] | None = None
            if sort:
                sort_converted = [{"sort_by": s, "sort_order": "asc"} for s in sort]  # type: ignore[arg-type]
            result = self.collection.find(  # type: ignore[arg-type]
                filters=filters or {}, skip=skip, limit=limit, sort=sort_converted
            )
            documents = list(result)  # type: ignore[arg-type]
            logger.debug(f"Found {len(documents)} document(s) in collection '{self.name}'")
            return documents
        except Exception as e:
            logger.error(f"Failed to find documents in collection '{self.name}': {e}")
            raise

    def count(self) -> int:
        """
        獲取集合中文檔數量

        Returns:
            文檔數量
        """
        try:
            count = self.collection.count()
            logger.debug(f"Collection '{self.name}' contains {count} document(s)")
            return count  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to count documents in collection '{self.name}': {e}")
            raise

    def truncate(self) -> bool:
        """
        清空集合（刪除所有文檔但保留集合結構）

        Returns:
            是否成功
        """
        try:
            result = self.collection.truncate()
            logger.warning(f"Truncated collection '{self.name}'")
            return result  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to truncate collection '{self.name}': {e}")
            raise
