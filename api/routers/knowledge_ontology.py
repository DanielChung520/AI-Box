# 代碼功能說明: 知識庫本體管理 API 路由
# 創建日期: 2026-02-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-12

"""Knowledge Ontology API - 知識庫本體管理（供 KnowledgeBaseModal 使用）"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, status, UploadFile
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from database.arangodb import ArangoDBClient
from system.security.dependencies import get_current_user
from system.security.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge/ontologies", tags=["Knowledge Ontology"])

ONTOLOGIES_COLLECTION = "ontologies"


def _get_db_client() -> ArangoDBClient:
    return ArangoDBClient()


def _document_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    """將 ArangoDB document 轉換為 API 響應格式"""
    return {
        "id": doc.get("_key"),
        "domain": doc.get("name"),
        "domainName": doc.get("ontology_name"),
        "description": doc.get("description"),
        "allowedTypes": doc.get("entity_classes", []),
        "version": doc.get("version"),
        "isActive": doc.get("is_active"),
        "tags": doc.get("tags", []),
        "useCases": doc.get("use_cases", []),
        "entityClasses": doc.get("entity_classes", []),
        "objectProperties": doc.get("object_properties", []),
        "inheritsFrom": doc.get("inherits_from", []),
        "compatibleDomains": doc.get("compatible_domains", []),
        "createdAt": doc.get("created_at"),
        "updatedAt": doc.get("updated_at"),
    }


@router.get("", status_code=status.HTTP_200_OK)
async def list_knowledge_ontologies(
    search: Optional[str] = Query(None, description="搜索關鍵詞"),
) -> JSONResponse:
    """列出所有知識庫本體"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            logger.warn("ArangoDB 未連接，返回空列表")
            return APIResponse.success(data={"items": []}, message="數據庫未連接")

        try:
            collection = db.collection(ONTOLOGIES_COLLECTION)
        except Exception as e:
            logger.warn(f"集合 {ONTOLOGIES_COLLECTION} 不存在: {e}")
            return APIResponse.success(data={"items": []}, message="集合不存在")

        query = """
            FOR doc IN @@collection
            FILTER doc.is_active == true
            SORT doc.created_at DESC
            RETURN doc
        """

        bind_vars = {"@collection": ONTOLOGIES_COLLECTION}

        try:
            cursor = db.aql.execute(query, bind_vars=bind_vars)
            result = list(cursor)
            ontologies = [_document_to_dict(doc) for doc in result]
            logger.info(f"AQL 查詢成功，返回 {len(ontologies)} 筆資料")
        except Exception as e:
            logger.error(f"AQL 查詢失敗: {e}")
            return APIResponse.success(data={"items": []}, message=f"查詢失敗: {str(e)}")

        return APIResponse.success(data={"items": ontologies})

    except Exception as e:
        logger.exception("list_knowledge_ontologies failed: %s", e)
        return APIResponse.error(message=f"查詢失敗: {str(e)}", status_code=500)


@router.get("/{ontology_id}", status_code=status.HTTP_200_OK)
async def get_knowledge_ontology(
    ontology_id: str,
) -> JSONResponse:
    """取得單個知識庫本體"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        collection = db.collection(ONTOLOGIES_COLLECTION)
        doc = collection.get(ontology_id)

        if not doc:
            return APIResponse.error(message="本體不存在", status_code=404)

        return APIResponse.success(data=_document_to_dict(doc))

    except Exception as e:
        logger.exception("get_knowledge_ontology failed: id=%s", ontology_id)
        return APIResponse.error(message=f"查詢失敗: {str(e)}")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_knowledge_ontology(
    domain: str,
    domainName: str,
    description: Optional[str] = None,
    allowedTypes: List[str] = [],
    domainFile: Optional[UploadFile] = None,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """創建新的知識庫本體"""
    try:
        if not domain or not domainName:
            return APIResponse.error(message="domain 和 domainName 為必填")

        if not allowedTypes:
            return APIResponse.error(message="allowedTypes 為必填")

        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        collection = db.collection(ONTOLOGIES_COLLECTION)

        now = datetime.now().isoformat()
        doc_key = f"ont_{domain}"

        existing = collection.get(doc_key)
        if existing:
            return APIResponse.error(message=f"本體已存在: {domain}", status_code=409)

        doc = {
            "_key": doc_key,
            "domain": domain,
            "domainName": domainName,
            "description": description,
            "allowedTypes": allowedTypes,
            "isActive": True,
            "createdAt": now,
            "updatedAt": now,
            "createdBy": getattr(current_user, "id", None)
            or getattr(current_user, "username", "unknown"),
        }

        collection.save(doc)

        logger.info(
            "Created knowledge ontology: %s by user %s",
            doc_key,
            getattr(current_user, "username", "unknown"),
        )

        return APIResponse.success(data=_document_to_dict(doc), message="創建成功", status_code=201)

    except Exception as e:
        logger.exception("create_knowledge_ontology failed: domain=%s", domain)
        return APIResponse.error(message=f"創建失敗: {str(e)}")


@router.put("/{ontology_id}", status_code=status.HTTP_200_OK)
async def update_knowledge_ontology(
    ontology_id: str,
    domainName: Optional[str] = None,
    description: Optional[str] = None,
    allowedTypes: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """更新知識庫本體"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        collection = db.collection(ONTOLOGIES_COLLECTION)
        doc = collection.get(ontology_id)

        if not doc:
            return APIResponse.error(message="本體不存在", status_code=404)

        update_data = {
            "updatedAt": datetime.now().isoformat(),
            "updatedBy": getattr(current_user, "id", None)
            or getattr(current_user, "username", "unknown"),
        }

        if domainName is not None:
            update_data["domainName"] = domainName
        if description is not None:
            update_data["description"] = description
        if allowedTypes is not None:
            update_data["allowedTypes"] = allowedTypes

        collection.update(ontology_id, update_data)

        updated_doc = collection.get(ontology_id)

        logger.info(
            "Updated knowledge ontology: %s by user %s",
            ontology_id,
            getattr(current_user, "username", "unknown"),
        )

        return APIResponse.success(data=_document_to_dict(updated_doc), message="更新成功")

    except Exception as e:
        logger.exception("update_knowledge_ontology failed: id=%s", ontology_id)
        return APIResponse.error(message=f"更新失敗: {str(e)}")


@router.delete("/{ontology_id}", status_code=status.HTTP_200_OK)
async def delete_knowledge_ontology(
    ontology_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """刪除知識庫本體（軟刪除）"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        collection = db.collection(ONTOLOGIES_COLLECTION)
        doc = collection.get(ontology_id)

        if not doc:
            return APIResponse.error(message="本體不存在", status_code=404)

        collection.update(
            ontology_id,
            {
                "isActive": False,
                "updatedAt": datetime.now().isoformat(),
                "updatedBy": getattr(current_user, "id", None)
                or getattr(current_user, "username", "unknown"),
            },
        )

        logger.info(
            "Deleted knowledge ontology: %s by user %s",
            ontology_id,
            getattr(current_user, "username", "unknown"),
        )

        return APIResponse.success(message="刪除成功")

    except Exception as e:
        logger.exception("delete_knowledge_ontology failed: id=%s", ontology_id)
        return APIResponse.error(message=f"刪除失敗: {str(e)}")


@router.post("/{ontology_id}/upload", status_code=status.HTTP_200_OK)
async def upload_ontology_file(
    ontology_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """上傳本體相關文件"""
    try:
        client = _get_db_client()
        db = client.db

        if db is None:
            return APIResponse.error(message="數據庫未連接")

        collection = db.collection(ONTOLOGIES_COLLECTION)
        doc = collection.get(ontology_id)

        if not doc:
            return APIResponse.error(message="本體不存在", status_code=404)

        file_content = await file.read()
        file_data = {
            "filename": file.filename,
            "contentType": file.content_type,
            "size": len(file_content),
            "uploadedAt": datetime.now().isoformat(),
            "uploadedBy": getattr(current_user, "id", None)
            or getattr(current_user, "username", "unknown"),
        }

        existing_files = doc.get("files", [])
        existing_files.append(file_data)

        collection.update(
            ontology_id,
            {
                "files": existing_files,
                "updatedAt": datetime.now().isoformat(),
            },
        )

        logger.info("Uploaded file to ontology: %s, filename: %s", ontology_id, file.filename)

        return APIResponse.success(
            data={"filename": file.filename, "size": file_data["size"]}, message="上傳成功"
        )

    except Exception as e:
        logger.exception("upload_ontology_file failed: id=%s", ontology_id)
        return APIResponse.error(message=f"上傳失敗: {str(e)}")
