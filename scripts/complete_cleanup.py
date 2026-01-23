#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代碼功能說明: AI-Box 完整清理腳本
創建日期: 2026-01-20
創建人: Daniel Chung

功能:
1. 清除 ArangoDB (tasks, file_metadata, entities, relations)
2. 清除 Qdrant collections
3. 清除 SeaweedFS test files
4. 清除 localStorage 緩存
"""

import json
import sys
import urllib.request
from pathlib import Path

import structlog

# 添加項目根目錄
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


logger = structlog.get_logger(__name__)

# ArangoDB 認證
ARANGO_HOST = "localhost"
ARANGO_PORT = 8529
ARANGO_USER = "root"
ARANGO_PASSWORD = "changeme"
ARANGO_DB = "ai_box_kg"

# Qdrant 配置
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

# SeaweedFS 配置
SEAWEEDFS_HOST = "localhost"
SEAWEEDFS_PORT = 8333
SEAWEEDFS_BUCKET = "bucket-ai-box-assets"
SEAWEEDFS_ACCESS_KEY = "admin"
SEAWEEDFS_SECRET_KEY = "admin"


def get_arangodb_url():
    """獲取 ArangoDB URL"""
    return f"http://{ARANGO_HOST}:{ARANGO_PORT}"


def get_auth_header():
    """獲取 Basic Auth Header"""
    import base64

    credentials = f"{ARANGO_USER}:{ARANGO_PASSWORD}"
    return "Basic " + base64.b64encode(credentials.encode()).decode()


def arango_request(method: str, endpoint: str, data: dict = None) -> dict:
    """發送 ArangoDB 請求"""
    url = f"{get_arangodb_url()}/_db/{ARANGO_DB}/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": get_auth_header(),
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data else None,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        logger.error(f"ArangoDB request failed: {e.code} {e.reason}", error=error_body)
        raise


def cleanup_arangodb():
    """清除 ArangoDB 數據"""
    logger.info("=" * 60)
    logger.info("開始清除 ArangoDB 數據")
    logger.info("=" * 60)

    total_deleted = 0

    # 1. 清除 user_tasks (保留 systemAdmin 默認任務)
    logger.info("1. 清除 user_tasks...")

    # 查詢所有 unauthenticated 用戶的任務
    result = arango_request(
        "POST",
        "_api/cursor",
        {"query": "FOR t IN user_tasks FILTER t.user_id == 'unauthenticated' RETURN t._key"},
    )
    unauth_tasks = result.get("result", [])

    if unauth_tasks:
        logger.info(f"   找到 {len(unauth_tasks)} 個 unauthenticated 任務")
        for task_key in unauth_tasks:
            arango_request("DELETE", f"_api/document/user_tasks/{task_key}")
            total_deleted += 1
        logger.info(f"   已刪除 {len(unauth_tasks)} 個 unauthenticated 任務")
    else:
        logger.info("   無 unauthenticated 任務需要清除")

    # 2. 清除多餘的 SystemDoc 任務
    logger.info("2. 清除多餘的 SystemDoc 任務...")
    result = arango_request(
        "POST",
        "_api/cursor",
        {
            "query": "FOR t IN user_tasks FILTER t.user_id == 'systemAdmin' AND t._key == 'systemAdmin_SystemDoc' RETURN t._key"
        },
    )
    extra_tasks = result.get("result", [])

    for task_key in extra_tasks:
        arango_request("DELETE", f"_api/document/user_tasks/{task_key}")
        total_deleted += 1
        logger.info(f"   已刪除: {task_key}")

    # 3. 清除 file_metadata (保留必要系統文件)
    logger.info("3. 清除 file_metadata...")

    # 清除非 SystemDocs 任務的文件 (保留 docs_system_design_README.md)
    result = arango_request(
        "POST",
        "_api/cursor",
        {
            "query": "FOR f IN file_metadata FILTER f.task_id != 'SystemDocs' AND f.filename != 'docs_system_design_README.md' RETURN f._key"
        },
    )
    file_keys = result.get("result", [])

    for file_key in file_keys:
        arango_request("DELETE", f"_api/document/file_metadata/{file_key}")
        total_deleted += 1
    logger.info(f"   已清除 {len(file_keys)} 個 file_metadata 記錄")

    # 4. 清除 entities (全部清除)
    logger.info("4. 清除 entities (全部清除)...")
    result = arango_request("POST", "_api/cursor", {"query": "FOR e IN entities RETURN e._key"})
    entity_keys = result.get("result", [])

    for key in entity_keys:
        arango_request("DELETE", f"_api/document/entities/{key}")
        total_deleted += 1
    logger.info(f"   已清除 {len(entity_keys)} 個 entities")

    # 5. 清除 relations (全部清除)
    logger.info("5. 清除 relations (全部清除)...")
    result = arango_request("POST", "_api/cursor", {"query": "FOR r IN relations RETURN r._key"})
    relation_keys = result.get("result", [])

    for key in relation_keys:
        arango_request("DELETE", f"_api/document/relations/{key}")
        total_deleted += 1
    logger.info(f"   已清除 {len(relation_keys)} 個 relations")

    # 6. 清除 fileTree 緩存
    logger.info("6. 清除 fileTree 緩存...")
    result = arango_request(
        "POST",
        "_api/cursor",
        {
            "query": "FOR t IN user_tasks FILTER t._key == 'systemAdmin_systemAdmin_SystemDocs' UPDATE t WITH { fileTree: [] } IN user_tasks RETURN NEW"
        },
    )
    logger.info("   已清除 SystemDocs 任務的 fileTree 緩存")

    logger.info("=" * 60)
    logger.info(f"ArangoDB 清理完成，共清除 {total_deleted} 筆數據")
    logger.info("=" * 60)

    return total_deleted


def cleanup_qdrant():
    """清除 Qdrant 數據"""
    logger.info("=" * 60)
    logger.info("開始清除 Qdrant 數據")
    logger.info("=" * 60)

    total_deleted = 0

    try:
        # 獲取所有 collections
        url = f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            collections = data.get("result", {}).get("collections", [])

        for coll in collections:
            coll_name = coll.get("name")

            # 刪除 SystemDocs 相關的 collection
            if "SystemDocs" in coll_name or "systemdocs" in coll_name.lower():
                delete_url = f"{url}/{coll_name}"
                req = urllib.request.Request(delete_url, method="DELETE")
                with urllib.request.urlopen(req):
                    logger.info(f"   已刪除 collection: {coll_name}")
                    total_deleted += 1

        logger.info(f"Qdrant 清理完成，共清除 {total_deleted} 個 collections")

    except Exception as e:
        logger.error(f"Qdrant 清理失敗: {e}")

    logger.info("=" * 60)

    return total_deleted


def cleanup_seaweedfs():
    """清除 SeaweedFS 測試文件"""
    logger.info("=" * 60)
    logger.info("開始清除 SeaweedFS 測試文件")
    logger.info("=" * 60)

    total_deleted = 0

    try:
        # 使用 filer API 直接操作
        filer_url = f"http://{SEAWEEDFS_HOST}:8888"

        # 列出 tasks/SystemDocs 目錄下的文件
        list_url = f"{filer_url}/bucket-ai-box-assets/tasks/SystemDocs/"
        req = urllib.request.Request(list_url)

        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            entries = data.get("entries", [])

        for entry in entries:
            if entry.get("IsDir", False):
                continue
            full_path = entry.get("FullPath", "")
            if full_path:
                # 刪除文件
                delete_url = f"{filer_url}{full_path}"
                del_req = urllib.request.Request(delete_url, method="DELETE")
                with urllib.request.urlopen(del_req):
                    logger.info(f"   已刪除: {full_path}")
                    total_deleted += 1

        logger.info(f"SeaweedFS 清理完成，共清除 {total_deleted} 個文件")

    except Exception as e:
        logger.error(f"SeaweedFS 清理失敗: {e}")
        # 嘗試使用 curl
        logger.info("嘗試使用 curl 清理...")
        import subprocess

        result = subprocess.run(
            f"curl -s -u admin:admin '{filer_url}/bucket-ai-box-assets/tasks/SystemDocs/' 2>/dev/null | grep -o '\"FullPath\":\"[^\"]*\"' | cut -d'\"' -f4",
            shell=True,
            capture_output=True,
            text=True,
        )
        paths = result.stdout.strip().split("\n")
        for path in paths:
            if path and not path.endswith("/"):
                delete_url = f"{filer_url}{path}"
                subprocess.run(f"curl -s -X DELETE -u admin:admin '{delete_url}'", shell=True)
                logger.info(f"   已刪除: {path}")
                total_deleted += 1

    logger.info("=" * 60)

    return total_deleted


def cleanup_localstorage_instructions():
    """輸出清除 localStorage 的指令"""
    logger.info("=" * 60)
    logger.info("清除 localStorage 緩存")
    logger.info("=" * 60)

    instructions = """
請在瀏覽器控制台執行以下命令：

(function(){const r=[];for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k&&(k.startsWith('tasks_')||k.startsWith('ai-box-')||k.startsWith('file_tree_cache_')||k.startsWith('draft_files_')||k.startsWith('ai-box-mock-files-')||k.includes('Task')||k.includes('FileTree')||k.includes('fileTree'))){r.push(k)}};r.forEach(k=>{console.log('清除:',k);localStorage.removeItem(k)});console.log('完成! 清除'+r.length+'個key');console.log('請按 Ctrl+F5 強制刷新');})();

執行後按 Ctrl+F5 (Windows) 或 Cmd+Shift+R (Mac) 強制刷新頁面
"""
    logger.info(instructions)
    logger.info("=" * 60)


def main():
    """主函數"""
    print("=" * 60)
    print("AI-Box 完整清理腳本")
    print("=" * 60)
    print()

    # 1. 清除 ArangoDB
    arango_deleted = cleanup_arangodb()
    print()

    # 2. 清除 Qdrant
    qdrant_deleted = cleanup_qdrant()
    print()

    # 3. 清除 SeaweedFS
    seaweed_deleted = cleanup_seaweedfs()
    print()

    # 4. 清除 localStorage
    cleanup_localstorage_instructions()

    # 總結
    print("=" * 60)
    print("清理完成！")
    print("=" * 60)
    print(f"ArangoDB: {arango_deleted} 筆")
    print(f"Qdrant: {qdrant_deleted} 個 collections")
    print(f"SeaweedFS: {seaweed_deleted} 個文件")
    print()
    print("請執行 localStorage 清除並刷新頁面")


if __name__ == "__main__":
    main()
