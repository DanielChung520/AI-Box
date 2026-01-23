#!/usr/bin/env python3
"""
同步處理系統設計文檔
直接處理檔案而不使用 RQ worker（因為 macOS 的 fork 安全限制）
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# Set config path
os.environ["AI_BOX_CONFIG_PATH"] = "/Users/daniel/GitHub/AI-Box/config/config.json"

import asyncio

from arango.client import ArangoClient



async def process_file(file_id: str, storage_path: str, file_type: str, user_id: str):
    """Process a single file"""
    from api.routers.file_upload import process_file_chunking_and_vectorization

    print(f"Processing: {file_id}")
    try:
        await process_file_chunking_and_vectorization(
            file_id=file_id,
            file_path=storage_path,
            file_type=file_type,
            user_id=user_id,
        )
        print(f"  SUCCESS: {file_id}")
        return True
    except Exception as e:
        print(f"  FAILED: {file_id} - {e}")
        return False


async def main():
    # Connect to ArangoDB
    client = ArangoClient(hosts="http://localhost:8529")
    db = client.db("ai_box_kg", username="root", password="changeme")
    coll = db.collection("file_metadata")

    # Get all files for the task
    docs = list(coll.all())
    task_files = [d for d in docs if d.get("task_id") == "systemAdmin_SystemDocs"]

    print(f"Found {len(task_files)} files to process")

    success_count = 0
    fail_count = 0

    # Process files
    for doc in task_files:
        file_id = doc["_key"]
        storage_path = doc.get("storage_path", "")
        file_type = doc.get("file_type", "text/markdown")
        user_id = doc.get("user_id", "systemAdmin")

        # Skip if already processed (has chunks or vectors)
        chunk_count = doc.get("chunk_count") or 0
        vector_count = doc.get("vector_count") or 0
        if chunk_count > 0 or vector_count > 0:
            print(f"SKIP (already processed): {doc.get('filename')}")
            continue

        if not storage_path:
            print(f"SKIP (no storage_path): {doc.get('filename')}")
            continue

        # Process the file
        success = await process_file(file_id, storage_path, file_type, user_id)

        if success:
            success_count += 1
        else:
            fail_count += 1

    print("\n=== Summary ===")
    print(f"Total files: {len(task_files)}")
    print(f"Processed successfully: {success_count}")
    print(f"Failed: {fail_count}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
