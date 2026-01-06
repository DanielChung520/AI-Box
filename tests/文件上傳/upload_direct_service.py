#!/usr/bin/env python3
# 代碼功能說明: 直接使用系統服務上傳文件（繞過 HTTP API）
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""直接使用系統服務上傳文件並觸發處理"""

import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加載環境變數
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

from storage.file_storage import get_storage
from services.api.services.file_metadata_service import get_metadata_service
from services.api.services.upload_status_service import get_upload_status_service
from services.api.processors.parser_factory import get_parser_factory
from services.api.processors.chunk_processor import ChunkProcessor
from system.security.auth import get_system_user_token
from database.arangodb.client import get_arangodb_client

import uuid
from datetime import datetime


async def upload_and_process_file():
    """直接使用系統服務上傳並處理文件"""
    
    # 測試文件
    test_file = project_root / 'docs' / '东方伊厨-预制菜发展策略报告20250902.pdf'
    
    if not test_file.exists():
        print(f"❌ 錯誤：文件不存在: {test_file}")
        return
    
    file_size_mb = test_file.stat().st_size / (1024 * 1024)
    print("=" * 80)
    print("📤 直接使用系統服務上傳文件")
    print("=" * 80)
    print(f"文件: {test_file.name}")
    print(f"大小: {file_size_mb:.2f} MB")
    print()
    
    # 獲取系統用戶 ID（使用默認系統用戶）
    system_user_id = "system"
    
    try:
        # 1. 讀取文件內容
        print("📖 讀取文件內容...")
        with open(test_file, 'rb') as f:
            file_content = f.read()
        print(f"  ✅ 文件讀取完成 ({len(file_content) / (1024*1024):.2f} MB)")
        print()
        
        # 2. 保存文件到存儲
        print("💾 保存文件到存儲...")
        storage = get_storage()
        file_id = str(uuid.uuid4())
        file_path = storage.save_file(file_content, test_file.name, file_id=file_id)
        print(f"  ✅ 文件保存完成")
        print(f"     文件 ID: {file_id}")
        print(f"     存儲路徑: {file_path}")
        print()
        
        # 3. 創建文件元數據
        print("📝 創建文件元數據...")
        metadata_service = get_metadata_service()
        
        from services.api.models.file_metadata import FileMetadataCreate
        
        file_metadata = FileMetadataCreate(
            file_id=file_id,
            filename=test_file.name,
            file_type="application/pdf",
            file_size=len(file_content),
            user_id=system_user_id,
            storage_path=file_path,
            status="uploaded"
        )
        
        created_metadata = metadata_service.create(file_metadata)
        print(f"  ✅ 元數據創建完成")
        print()
        
        # 4. 初始化處理狀態
        print("⚙️  初始化處理狀態...")
        upload_status_service = get_upload_status_service()
        upload_status_service.update_upload_progress(
            file_id=file_id,
            progress=0,
            status="uploading",
            message="文件上傳完成，開始處理..."
        )
        print(f"  ✅ 處理狀態初始化完成")
        print()
        
        # 5. 觸發異步處理（這裡需要通過 RQ 隊列）
        print("🚀 觸發異步處理...")
        print("   注意：需要通過 RQ Worker 處理")
        print()
        
        # 嘗試直接調用處理函數（如果是同步的）
        # 否則需要使用 RQ 隊列
        
        from workers.service import get_rq_queue
        from api.routers.file_upload import process_file_chunking_and_vectorization
        
        queue = get_rq_queue('file_processing')
        
        # 獲取文件類型
        parser_factory = get_parser_factory()
        file_type = "application/pdf"
        
        # 提交任務到隊列
        job = queue.enqueue(
            process_file_chunking_and_vectorization,
            file_id=file_id,
            file_path=file_path,
            file_type=file_type,
            user_id=system_user_id,
            job_timeout='1h'
        )
        
        print(f"  ✅ 任務已提交到隊列")
        print(f"     任務 ID: {job.id}")
        print()
        
        print("=" * 80)
        print("✅ 文件上傳和任務提交完成！")
        print("=" * 80)
        print(f"文件 ID: {file_id}")
        print()
        print("⏳ 文件正在後台處理（分塊、向量化）...")
        print("   可以使用以下命令查詢狀態：")
        print(f"   GET /api/v1/files/{file_id}/processing-status")
        print()
        print(f"FILE_ID={file_id}")
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(upload_and_process_file())

