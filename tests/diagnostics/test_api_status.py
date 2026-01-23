import json
import logging

from database.redis import get_redis_client
from genai.api.services.kg_builder_service import KGBuilderService
from services.api.services.file_metadata_service import FileMetadataService

# Disable excessive logging
logging.getLogger("database.arangodb.client").setLevel(logging.WARNING)

fid = "786316d7-5593-415e-b442-77d9fcf36028"


def test_api_logic():
    print(f"Testing API logic for file_id: {fid}")

    # 1. Check File Metadata
    metadata_service = FileMetadataService()
    f = metadata_service.get(fid)
    if f:
        print(f"File Metadata Found: filename={f.filename}, kg_status={f.kg_status}")
    else:
        print("File Metadata NOT Found")
        return

    # 2. Check KG Triples (simulating get_kg_triples)
    kg_builder = KGBuilderService()
    # list_triples_by_file_id is the core method
    triples_res = kg_builder.list_triples_by_file_id(fid)
    print(f"Triples Total: {triples_res.get('total')}")
    # print(f"Triples Sample: {triples_res.get('triples')[:1] if triples_res.get('triples') else 'None'}")

    # 3. Check Chunk Status (simulating get_kg_chunk_status)
    redis_client = get_redis_client()
    state_key = f"kg:chunk_state:{fid}"
    state_str = redis_client.get(state_key)
    if state_str:
        state = json.loads(state_str)
        print(
            f"Redis kg:chunk_state found: status={state.get('status')}, progress={state.get('progress')}"
        )
    else:
        print(f"Redis kg:chunk_state NOT found for {fid}")


if __name__ == "__main__":
    test_api_logic()
