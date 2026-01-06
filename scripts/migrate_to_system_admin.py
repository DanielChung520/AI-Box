# 代碼功能說明: 將系統設計任務遷移到 systemAdmin 用戶的 SystemDocs 任務
# 創建日期: 2026-01-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-06

"""將系統設計相關任務遷移到 systemAdmin 用戶的 SystemDocs 任務"""

import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.arangodb import ArangoDBClient
from services.api.services.user_task_service import get_user_task_service
from services.api.services.file_metadata_service import get_metadata_service
from services.api.models.user_task import UserTaskCreate
from datetime import datetime

# 系統設計文件關鍵字
SYSTEM_DESIGN_KEYWORDS = [
    '系统', '设计', '架构', '规格', '规范', '文档',
    'design', 'system', 'architecture', 'spec', 'specification', 'doc', 'document',
    'Security-Agent', '治理API', 'MD 示範'
]

SYSTEM_ADMIN_USER_ID = "systemAdmin"
SYSTEM_DOCS_TASK_ID = "SystemDocs"
OLD_USER_ID = "unauthenticated"


def is_system_design_file(filename: str) -> bool:
    """判斷文件是否為系統設計文件"""
    filename_lower = filename.lower()
    return any(keyword.lower() in filename_lower for keyword in SYSTEM_DESIGN_KEYWORDS)


def extract_files_from_filetree(filetree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """從 fileTree 遞歸提取所有文件"""
    files = []
    
    def extract(node: Dict[str, Any], path: str = ""):
        if isinstance(node, dict):
            if node.get('type') == 'file':
                files.append({
                    'id': node.get('id', ''),
                    'name': node.get('name', ''),
                    'path': f"{path}/{node.get('name', '')}" if path else node.get('name', ''),
                })
            elif node.get('type') == 'folder':
                folder_name = node.get('name', '')
                children = node.get('children', [])
                for child in children:
                    extract(child, f"{path}/{folder_name}" if path else folder_name)
    
    for node in filetree:
        extract(node)
    
    return files


def main():
    """主函數"""
    print("=== 遷移系統設計任務到 systemAdmin/SystemDocs ===\n")
    
    try:
        # 1. 連接到 ArangoDB
        client = ArangoDBClient()
        if client.db is None:
            print("❌ ArangoDB 未連接")
            return
        
        # 2. 查詢所有 unauthenticated 的任務
        print(f"1. 查詢 {OLD_USER_ID} 用戶的所有任務...")
        task_service = get_user_task_service()
        old_tasks = task_service.list(
            user_id=OLD_USER_ID,
            limit=10000,
            offset=0,
        )
        
        print(f"   找到 {len(old_tasks)} 個任務\n")
        
        # 3. 篩選系統設計相關的任務
        print("2. 篩選系統設計相關的任務...")
        system_design_tasks = []
        for task in old_tasks:
            task_files = extract_files_from_filetree(task.fileTree or [])
            has_system_design = any(
                is_system_design_file(f.get('name', '')) for f in task_files
            )
            
            # 如果任務標題包含系統設計關鍵字，也認為是系統設計任務
            title_lower = (task.title or '').lower()
            if has_system_design or any(
                keyword.lower() in title_lower for keyword in SYSTEM_DESIGN_KEYWORDS
            ):
                system_design_tasks.append(task)
        
        print(f"   找到 {len(system_design_tasks)} 個系統設計相關的任務\n")
        
        if len(system_design_tasks) == 0:
            print("✅ 沒有需要遷移的任務")
            return
        
        # 4. 創建或獲取 SystemDocs 任務
        print("3. 創建或獲取 SystemDocs 任務...")
        collection = client.db.collection("user_tasks")
        system_docs_key = f"{SYSTEM_ADMIN_USER_ID}_{SYSTEM_DOCS_TASK_ID}"
        
        existing_system_docs = collection.get(system_docs_key)
        
        if existing_system_docs:
            print("   SystemDocs 任務已存在，將合併文件...")
            existing_files = extract_files_from_filetree(existing_system_docs.get('fileTree', []))
            existing_file_ids = {f.get('id') for f in existing_files}
        else:
            print("   創建新的 SystemDocs 任務...")
            system_docs_task = UserTaskCreate(
                task_id=SYSTEM_DOCS_TASK_ID,
                user_id=SYSTEM_ADMIN_USER_ID,
                title="SystemDocs",
                status="in-progress",
                task_status="activate",
                messages=[],
                fileTree=[],
            )
            task_service.create(system_docs_task)
            existing_file_ids = set()
        
        # 5. 合併所有系統設計任務的文件到 SystemDocs
        print("\n4. 合併文件到 SystemDocs 任務...")
        all_files = []
        migrated_tasks = []
        
        for task in system_design_tasks:
            task_files = extract_files_from_filetree(task.fileTree or [])
            for file_info in task_files:
                file_id = file_info.get('id')
                if file_id and file_id not in existing_file_ids:
                    all_files.append(file_info)
                    existing_file_ids.add(file_id)
            migrated_tasks.append(task.task_id)
        
        # 6. 更新 SystemDocs 任務的 fileTree
        if all_files:
            print(f"   添加 {len(all_files)} 個新文件到 SystemDocs...")
            
            workspace_folder = {
                "id": f"{SYSTEM_DOCS_TASK_ID}_workspace",
                "name": "任務工作區",
                "type": "folder",
                "children": [
                    {
                        "id": f.get('id', ''),
                        "name": f.get('name', ''),
                        "type": "file",
                        "children": None
                    }
                    for f in all_files
                ]
            }
            
            existing_doc = collection.get(system_docs_key)
            if existing_doc:
                existing_filetree = existing_doc.get('fileTree', [])
                workspace_found = False
                for node in existing_filetree:
                    if node.get('id') == f"{SYSTEM_DOCS_TASK_ID}_workspace":
                        existing_children = node.get('children', [])
                        new_children = [
                            {
                                "id": f.get('id', ''),
                                "name": f.get('name', ''),
                                "type": "file",
                                "children": None
                            }
                            for f in all_files
                        ]
                        node['children'] = existing_children + new_children
                        workspace_found = True
                        break
                
                if not workspace_found:
                    existing_filetree.append(workspace_folder)
                
                collection.update(
                    {
                        "_key": system_docs_key,
                        "fileTree": existing_filetree,
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                )
            else:
                collection.update(
                    {
                        "_key": system_docs_key,
                        "fileTree": [workspace_folder],
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                )
        
        # 7. 更新文件元數據
        print("\n5. 更新文件元數據...")
        file_collection = client.db.collection("file_metadata")
        updated_files = 0
        
        for task in system_design_tasks:
            task_files = extract_files_from_filetree(task.fileTree or [])
            for file_info in task_files:
                file_id = file_info.get('id')
                if file_id:
                    try:
                        file_collection.update(
                            {
                                "_key": file_id,
                                "user_id": SYSTEM_ADMIN_USER_ID,
                                "task_id": SYSTEM_DOCS_TASK_ID,
                                "updated_at": datetime.utcnow().isoformat(),
                            }
                        )
                        updated_files += 1
                    except Exception as e:
                        print(f"   ⚠️  更新文件 {file_id} 失敗: {e}")
        
        print(f"   更新了 {updated_files} 個文件的元數據\n")
        
        # 8. 歸檔舊任務
        print("6. 歸檔舊任務...")
        archived = 0
        for task in system_design_tasks:
            try:
                old_key = f"{OLD_USER_ID}_{task.task_id}"
                collection.update(
                    {
                        "_key": old_key,
                        "task_status": "archive",
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                )
                archived += 1
            except Exception as e:
                print(f"   ⚠️  歸檔任務 {task.task_id} 失敗: {e}")
        
        print(f"   歸檔了 {archived} 個任務\n")
        
        # 9. 總結
        print("=== 遷移完成 ===\n")
        print(f"✅ 遷移了 {len(system_design_tasks)} 個系統設計任務")
        print(f"✅ 合併了 {len(all_files)} 個文件到 SystemDocs")
        print(f"✅ 更新了 {updated_files} 個文件的元數據")
        print(f"✅ 歸檔了 {archived} 個舊任務")
        print(f"\nSystemDocs 任務 ID: {SYSTEM_DOCS_TASK_ID}")
        print(f"SystemDocs 任務 Key: {system_docs_key}")
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
