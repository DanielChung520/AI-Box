import sys
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.redis.client import get_redis_client
from genai.api.services.kg_builder_service import KGBuilderService
from services.api.services.file_metadata_service import FileMetadataService

fid = "786316d7-5593-415e-b442-77d9fcf36028"


def test():
    print(f"Testing for file_id: {fid}")

    # Metadata
    meta_service = FileMetadataService()
    f = meta_service.get(fid)
    if f:
        print(f"Metadata: status={f.kg_status}, task_id={f.task_id}")
    else:
        print("Metadata not found")

    # Triples
    kg_builder = KGBuilderService()
    res = kg_builder.list_triples_by_file_id(fid)
    print(f"Triples total: {res['total']}")

    # Redis
    redis = get_redis_client()
    state = redis.get(f"kg:chunk_state:{fid}")
    print(f"Redis chunk state: {state}")


if __name__ == "__main__":
    test()
