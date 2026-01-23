# 代碼功能說明: 測試 KG API 邏輯
# 創建日期: 2026-01-23 01:45 UTC+8
# 創建人: Daniel Chung

import json

from database.redis import get_redis_client
from genai.api.services.kg_builder_service import KGBuilderService
from services.api.services.file_metadata_service import FileMetadataService

file_id = "786316d7-5593-415e-b442-77d9fcf8e972"  # 這是用戶提供的 file_id
# 雖然我之前查到的是 786316d7-5593-415e-b442-77d9fcf8e972 (結尾不同，但用戶日誌裡是這個)
# 等等，我查到的 key 是 786316d7-5593-415e-b442-77d9fcf8e972 ?
# 讓我確認一下之前的查詢結果。


def test_chunk_status(fid):
    print(f"\n--- Testing chunk-status for {fid} ---")
    redis_client = get_redis_client()
    state_key = f"kg:chunk_state:{fid}"
    state_str = redis_client.get(state_key)
    if not state_str:
        print(f"Redis key {state_key} not found")
    else:
        state = json.loads(state_str)
        print(f"Chunk Status State: {json.dumps(state, indent=2, ensure_ascii=False)}")


def test_triples(fid):
    print(f"\n--- Testing triples for {fid} ---")
    kg_builder = KGBuilderService()
    # 我們不模擬 ACL，直接用 list_triples_by_file_id
    result = kg_builder.list_triples_by_file_id(file_id=fid, limit=100, offset=0)
    print(f"Triples Count: {result.get('total')}")
    triples = result.get("triples", [])
    for t in triples[:3]:
        print(f"Triple: {t['subject']['name']} -[{t['edge']['type']}]-> {t['object']['name']}")


def check_file_metadata(fid):
    print(f"\n--- Checking file_metadata for {fid} ---")
    metadata_service = FileMetadataService()
    f = metadata_service.get(fid)
    if f:
        print(f"Filename: {f.filename if hasattr(f, 'filename') else f.get('filename')}")
        print(f"KG Status: {f.kg_status if hasattr(f, 'kg_status') else f.get('kg_status')}")
    else:
        print("File metadata not found")


if __name__ == "__main__":
    # 用戶提到的 ID 是 786316d7-5593-415e-b442-77d9fcf8e972
    # 我之前的日誌裡看到的是 786316d7-5593-415e-b442-77d9fcf36028
    fids = ["786316d7-5593-415e-b442-77d9fcf8e972", "786316d7-5593-415e-b442-77d9fcf36028"]
    for fid in fids:
        check_file_metadata(fid)
        test_chunk_status(fid)
        test_triples(fid)
