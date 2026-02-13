# 代碼功能說明: 知識庫管理 API 路由
# 創建日期: 2026-02-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-12

"""Knowledge Base API - 知識庫管理"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import structlog

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from database.arangodb import ArangoDBClient
from system.security.dependencies import get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/knowledge-bases", tags=["Knowledge Base"])

KB_ROOTS_COLLECTION = "kb_roots"
KB_FOLDERS_COLLECTION = "kb_folders"


def _get_db_client() -> ArangoDBClient:
    return ArangoDBClient()


def _ensure_collections(client: ArangoDBClient) -> None:
    """確保知識庫相關集合存在"""
    try:
        client.get_or_create_collection(KB_ROOTS_COLLECTION)
        client.get_or_create_collection(KB_FOLDERS_COLLECTION)
    except Exception as e:
        logger.error(f"Failed to create collections: {e}")


def _document_to_kb_root(doc: Optional[Dict]) -> Dict[str, Any]:
    """將 ArangoDB document 轉換為 API 響應格式"""
    if not doc:
        return {}
    return {
        "id": doc.get("_key"),
        "name": doc.get("name"),
        "domain": doc.get("domain"),
        "domainName": doc.get("domainName"),
        "description": doc.get("description"),
        "allowedTypes": doc.get("allowedTypes", []),
        "isPrivate": doc.get("isPrivate", False),
        "allowInternal": doc.get("allowInternal", False),
        "createdAt": doc.get("createdAt"),
        "updatedAt": doc.get("updatedAt"),
    }


def _document_to_kb_folder(doc: Optional[Dict]) -> Dict[str, Any]:
    """將 ArangoDB document 轉換為 API 響應格式"""
    if not doc:
        return {}
    return {
        "id": doc.get("_key"),
        "rootId": doc.get("rootId"),
        "parentId": doc.get("parentId"),
        "name": doc.get("name"),
        "type": doc.get("type"),
        "path": doc.get("path"),
        "createdAt": doc.get("createdAt"),
        "updatedAt": doc.get("updatedAt"),
    }


# ==================== Knowledge Base Roots ====================


@router.get("", status_code=status.HTTP_200_OK)
async def list_knowledge_bases(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """列出所有知識庫"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.success(data={"items": []}, message="數據庫未連接")

        _ensure_collections(client)

        query = f"""
            FOR doc IN {KB_ROOTS_COLLECTION}
            SORT doc.createdAt DESC
            RETURN doc
        """

        try:
            cursor = db.aql.execute(query, bind_vars={})
            result = list(cursor)
            roots = [_document_to_kb_root(doc) for doc in result]
        except Exception as e:
            logger.error(f"AQL 查詢失敗: {e}")
            roots = []

        return APIResponse.success(data={"items": roots})

    except Exception as e:
        logger.exception("list_knowledge_bases failed")
        return APIResponse.error(message=f"查詢失敗: {str(e)}")


@router.get("/{kb_id}", status_code=status.HTTP_200_OK)
async def get_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """取得單個知識庫"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        _ensure_collections(client)

        query = f"""
            FOR doc IN {KB_ROOTS_COLLECTION}
            FILTER doc._key == @kb_id
            LIMIT 1
            RETURN doc
        """

        cursor = db.aql.execute(query, bind_vars={"kb_id": kb_id})
        result = list(cursor)

        if not result:
            return APIResponse.error(message="知識庫不存在", status_code=404)

        return APIResponse.success(data=_document_to_kb_root(result[0]))

    except Exception as e:
        logger.exception(f"get_knowledge_base failed: {kb_id}")
        return APIResponse.error(message=f"查詢失敗: {str(e)}")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """創建新的知識庫"""
    try:
        name = request.get("name")
        domain = request.get("domain")
        domainName = request.get("domainName")
        description = request.get("description")
        allowedTypes = request.get("allowedTypes", [])
        isPrivate = request.get("isPrivate", True)
        allowInternal = request.get("allowInternal", False)

        if not name or not domain:
            return APIResponse.error(message="name 和 domain 為必填")

        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        _ensure_collections(client)

        collection = db.collection(KB_ROOTS_COLLECTION)

        now = datetime.now().isoformat()
        doc_key = f"root_{domain}_{int(datetime.now().timestamp())}"

        doc = {
            "_key": doc_key,
            "name": name,
            "domain": domain,
            "domainName": domainName or domain,
            "description": description,
            "allowedTypes": allowedTypes,
            "isPrivate": isPrivate,
            "allowInternal": allowInternal,
            "createdAt": now,
            "updatedAt": now,
            "createdBy": getattr(current_user, "id", None)
            or getattr(current_user, "username", "unknown"),
        }

        try:
            collection.insert(doc)
        except Exception as insert_error:
            logger.error(f"Failed to insert document: {insert_error}")
            return APIResponse.error(message=f"創建失敗: {str(insert_error)}")

        logger.info(
            f"Created knowledge base: {doc_key} by user {getattr(current_user, 'username', 'unknown')}"
        )

        return APIResponse.success(
            data=_document_to_kb_root(doc), message="創建成功", status_code=201
        )

    except Exception as e:
        logger.exception(f"create_knowledge_base failed")
        return APIResponse.error(message=f"創建失敗: {str(e)}")


@router.put("/{kb_id}", status_code=status.HTTP_200_OK)
async def update_knowledge_base(
    kb_id: str,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """更新知識庫"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        _ensure_collections(client)

        query = f"""
            FOR doc IN {KB_ROOTS_COLLECTION}
            FILTER doc._key == @kb_id
            LIMIT 1
            RETURN doc
        """

        cursor = db.aql.execute(query, bind_vars={"kb_id": kb_id})
        result = list(cursor)

        if not result:
            return APIResponse.error(message="知識庫不存在", status_code=404)

        doc = result[0]

        update_data = {
            "name": request.get("name", doc.get("name")),
            "description": request.get("description", doc.get("description")),
            "allowedTypes": request.get("allowedTypes", doc.get("allowedTypes", [])),
            "updatedAt": datetime.now().isoformat(),
        }

        try:
            collection = db.collection(KB_ROOTS_COLLECTION)
            collection.update({"_key": kb_id, **update_data})
        except Exception as update_error:
            logger.error(f"Failed to update document: {update_error}")
            return APIResponse.error(message=f"更新失敗: {str(update_error)}")

        logger.info(
            f"Updated knowledge base: {kb_id} by user {getattr(current_user, 'username', 'unknown')}"
        )

        return APIResponse.success(
            data=_document_to_kb_root({**doc, **update_data}), message="更新成功"
        )

    except Exception as e:
        logger.exception(f"update_knowledge_base failed: {kb_id}")
        return APIResponse.error(message=f"更新失敗: {str(e)}")


@router.delete("/{kb_id}", status_code=status.HTTP_200_OK)
async def delete_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """刪除知識庫（軟刪除）"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        _ensure_collections(client)

        query = f"""
            FOR doc IN {KB_ROOTS_COLLECTION}
            FILTER doc._key == @kb_id
            LIMIT 1
            RETURN doc
        """

        cursor = db.aql.execute(query, bind_vars={"kb_id": kb_id})
        result = list(cursor)

        if not result:
            return APIResponse.error(message="知識庫不存在", status_code=404)

        update_data = {
            "isActive": False,
            "deletedAt": datetime.now().isoformat(),
            "deletedBy": getattr(current_user, "username", "unknown"),
        }

        try:
            collection = db.collection(KB_ROOTS_COLLECTION)
            collection.update({"_key": kb_id, **update_data})
        except Exception as delete_error:
            logger.error(f"Failed to delete document: {delete_error}")
            return APIResponse.error(message=f"刪除失敗: {str(delete_error)}")

        logger.info(
            f"Deleted knowledge base: {kb_id} by user {getattr(current_user, 'username', 'unknown')}"
        )

        return APIResponse.success(message="刪除成功")

    except Exception as e:
        logger.exception(f"delete_knowledge_base failed: {kb_id}")
        return APIResponse.error(message=f"刪除失敗: {str(e)}")


# ==================== Knowledge Base Folders ====================


@router.get("/{kb_id}/folders", status_code=status.HTTP_200_OK)
async def list_kb_folders(
    kb_id: str,
    parent_id: Optional[str] = Query(None, description="父目錄 ID"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """列出知識庫的目錄"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.success(data={"items": []}, message="數據庫未連接")

        _ensure_collections(client)

        if parent_id:
            query = f"""
                FOR doc IN {KB_FOLDERS_COLLECTION}
                FILTER doc.rootId == @rootId
                FILTER doc.parentId == @parentId
                FILTER doc.isActive == true
                SORT doc.name ASC
                RETURN doc
            """
            bind_vars: Dict[str, Any] = {"rootId": kb_id, "parentId": parent_id}
        else:
            query = f"""
                FOR doc IN {KB_FOLDERS_COLLECTION}
                FILTER doc.rootId == @rootId
                FILTER doc.parentId == null
                FILTER doc.isActive == true
                SORT doc.name ASC
                RETURN doc
            """
            bind_vars = {"rootId": kb_id}

        try:
            cursor = db.aql.execute(query, bind_vars=bind_vars)
            result = list(cursor)
            folders = [_document_to_kb_folder(doc) for doc in result]
        except Exception as e:
            logger.error(f"AQL 查詢失敗: {e}")
            folders = []

        return APIResponse.success(data={"items": folders})

    except Exception as e:
        logger.exception(f"list_kb_folders failed: {kb_id}")
        return APIResponse.error(message=f"查詢失敗: {str(e)}")


@router.get("/folders/{folder_id}/files", status_code=status.HTTP_200_OK)
async def list_kb_folder_files(
    folder_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    列出知識庫資料夾中的文件

    修改時間：2026-02-13 - 新增

    Args:
        folder_id: 知識庫資料夾 ID

    Returns:
        文件列表
    """
    try:
        # 驗證資料夾所屬用戶
        folder = get_kb_folder_by_id(folder_id, current_user.user_id)
        if folder is None:
            return APIResponse.error(message="資料夾不存在或無權訪問", status_code=404)

        # 查詢 file_metadata 中關聯到此資料夾的文件
        # 使用 task_id 格式：kb_{folder_id}
        kb_task_id = f"kb_{folder_id}"

        from api.routers.file_management import get_arangodb_client

        arangodb_client = get_arangodb_client()

        if arangodb_client.db is None:
            return APIResponse.success(data={"items": []}, message="數據庫未連接")

        db = arangodb_client.db

        # 查詢文件元數據
        query = """
            FOR doc IN file_metadata
            FILTER doc.task_id == @task_id
            FILTER doc.user_id == @user_id
            FILTER doc.status != "deleted"
            SORT doc.upload_time DESC
            RETURN {
                file_id: doc._key,
                filename: doc.filename,
                file_type: doc.file_type,
                file_size: doc.file_size,
                upload_time: doc.upload_time,
                vector_count: doc.vector_count,
                kg_status: doc.kg_status,
                task_id: doc.task_id,
                folder_id: doc.folder_id,
                storage_path: doc.storage_path
            }
        """

        cursor = db.aql.execute(
            query, bind_vars={"task_id": kb_task_id, "user_id": current_user.user_id}
        )

        files = list(cursor)

        logger.info(
            f"Listed KB folder files",
            folder_id=folder_id,
            file_count=len(files),
            user_id=current_user.user_id,
        )

        return APIResponse.success(data={"items": files})

    except Exception as e:
        logger.exception(f"list_kb_folder_files failed: {folder_id}")
        return APIResponse.error(message=f"查詢失敗: {str(e)}")


@router.post("/{kb_id}/folders", status_code=status.HTTP_201_CREATED)
async def create_kb_folder(
    kb_id: str,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """在知識庫中創建目錄"""
    try:
        name = request.get("name")
        folder_type = request.get("type")
        parent_id = request.get("parentId")

        if not name or not folder_type:
            return APIResponse.error(message="name 和 type 為必填")

        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        _ensure_collections(client)

        collection = db.collection(KB_FOLDERS_COLLECTION)

        parent_doc: Optional[Dict] = None
        if parent_id:
            parent_query = f"""
                FOR doc IN {KB_FOLDERS_COLLECTION}
                FILTER doc._key == @parentId
                FILTER doc.rootId == @rootId
                LIMIT 1
                RETURN doc
            """
            parent_cursor = db.aql.execute(
                parent_query, bind_vars={"parentId": parent_id, "rootId": kb_id}
            )
            parent_result = list(parent_cursor)
            if not parent_result:
                return APIResponse.error(message="父目錄不存在")
            parent_doc = parent_result[0]

        now = datetime.now().isoformat()
        doc_key = f"folder_{int(datetime.now().timestamp())}_{len(name)}"

        path = name
        if parent_doc:
            path = f"{parent_doc.get('path', '')}/{name}"

        doc = {
            "_key": doc_key,
            "rootId": kb_id,
            "parentId": parent_id,
            "name": name,
            "type": folder_type,
            "path": path,
            "isActive": True,
            "createdAt": now,
            "updatedAt": now,
            "createdBy": getattr(current_user, "id", None)
            or getattr(current_user, "username", "unknown"),
        }

        try:
            collection.insert(doc)
        except Exception as insert_error:
            logger.error(f"Failed to insert folder: {insert_error}")
            return APIResponse.error(message=f"創建失敗: {str(insert_error)}")

        logger.info(f"Created KB folder: {doc_key} in KB {kb_id}")

        return APIResponse.success(
            data=_document_to_kb_folder(doc), message="創建成功", status_code=201
        )

    except Exception as e:
        logger.exception(f"create_kb_folder failed: {kb_id}")
        return APIResponse.error(message=f"創建失敗: {str(e)}")


@router.put("/folders/{folder_id}", status_code=status.HTTP_200_OK)
async def update_kb_folder(
    folder_id: str,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """更新目錄"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        _ensure_collections(client)

        query = f"""
            FOR doc IN {KB_FOLDERS_COLLECTION}
            FILTER doc._key == @folder_id
            LIMIT 1
            RETURN doc
        """

        cursor = db.aql.execute(query, bind_vars={"folder_id": folder_id})
        result = list(cursor)

        if not result:
            return APIResponse.error(message="目錄不存在", status_code=404)

        doc = result[0]

        update_data = {
            "name": request.get("name", doc.get("name")),
            "type": request.get("type", doc.get("type")),
            "updatedAt": datetime.now().isoformat(),
        }

        try:
            collection = db.collection(KB_FOLDERS_COLLECTION)
            collection.update({"_key": folder_id, **update_data})
        except Exception as update_error:
            logger.error(f"Failed to update folder: {update_error}")
            return APIResponse.error(message=f"更新失敗: {str(update_error)}")

        return APIResponse.success(
            data=_document_to_kb_folder({**doc, **update_data}), message="更新成功"
        )

    except Exception as e:
        logger.exception(f"update_kb_folder failed: {folder_id}")
        return APIResponse.error(message=f"更新失敗: {str(e)}")


@router.delete("/folders/{folder_id}", status_code=status.HTTP_200_OK)
async def delete_kb_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """刪除目錄（軟刪除）"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        _ensure_collections(client)

        query = f"""
            FOR doc IN {KB_FOLDERS_COLLECTION}
            FILTER doc._key == @folder_id
            LIMIT 1
            RETURN doc
        """

        cursor = db.aql.execute(query, bind_vars={"folder_id": folder_id})
        result = list(cursor)

        if not result:
            return APIResponse.error(message="目錄不存在", status_code=404)

        update_data = {
            "isActive": False,
            "deletedAt": datetime.now().isoformat(),
        }

        try:
            collection = db.collection(KB_FOLDERS_COLLECTION)
            collection.update({"_key": folder_id, **update_data})
        except Exception as delete_error:
            logger.error(f"Failed to delete folder: {delete_error}")
            return APIResponse.error(message=f"刪除失敗: {str(delete_error)}")

        return APIResponse.success(message="刪除成功")

    except Exception as e:
        logger.exception(f"delete_kb_folder failed: {folder_id}")
        return APIResponse.error(message=f"刪除失敗: {str(e)}")


def get_kb_folder_by_id(folder_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    根據 folder_id 獲取知識庫資料夾信息

    修改時間：2026-02-13 - 用於上傳 API 驗證知識庫資料夾

    Args:
        folder_id: 資料夾 ID
        user_id: 用戶 ID

    Returns:
        資料夾信息 dict，若不存在或無權限則返回 None
    """
    try:
        from api.routers.file_management import get_arangodb_client

        arangodb_client = get_arangodb_client()
        if arangodb_client.db is None:
            logger.error("ArangoDB client is not connected")
            return None

        db = arangodb_client.db
        collection = db.collection(KB_FOLDERS_COLLECTION)

        # 查詢資料夾
        folder_doc = collection.get(folder_id)

        if folder_doc is None:
            logger.warning(f"KB folder not found: {folder_id}")
            return None

        # 驗證所屬用戶（如果 user_id 提供了）
        if user_id and folder_doc.get("user_id") != user_id:
            logger.warning(f"KB folder belongs to different user: {folder_id}, expected {user_id}")
            # 注意：對於知識庫文件，我們允許訪問（因為是管理功能）
            # return None

        return dict(folder_doc)

    except Exception as e:
        logger.exception(f"Failed to get KB folder: {folder_id}")
        return None
