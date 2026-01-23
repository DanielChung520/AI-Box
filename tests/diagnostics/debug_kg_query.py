# 代碼功能說明: 詳細調試 KG 查詢
# 創建日期: 2026-01-23 01:55 UTC+8
# 創建人: Daniel Chung

from database.arangodb.client import ArangoDBClient
from genai.api.services.kg_builder_service import KGBuilderService

fid = "786316d7-5593-415e-b442-77d9fcf36028"


def debug_query():
    client = ArangoDBClient(database="ai_box_kg")
    db = client.db

    # 1. 檢查集合是否存在且有數據
    rel_col = db.collection("relations")
    count = rel_col.count()
    print(f"Total relations in collection: {count}")

    # 2. 執行與 KGBuilderService 相同的 AQL
    query = """
    LET total = LENGTH(
        FOR r IN relations
            LET ids = (
                r.file_ids != null ? r.file_ids :
                (r.file_id != null ? [r.file_id] : [])
            )
            FILTER @file_id IN ids
            RETURN 1
    )
    RETURN { total: total }
    """
    res = list(db.aql.execute(query, bind_vars={"file_id": fid}))
    print(f"Debug AQL Result: {res}")

    # 3. 調用 KGBuilderService 方法
    service = KGBuilderService()  # 它應該會連線到 ai_box_kg
    res_service = service.list_triples_by_file_id(file_id=fid)
    print(f"Service Method Result: {res_service['total']}")


if __name__ == "__main__":
    debug_query()
