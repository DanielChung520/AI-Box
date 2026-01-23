import json

from database.arangodb.client import ArangoDBClient

client = ArangoDBClient()
file_id = "786316d7-5593-415e-b442-77d9fcf36028"


def check_status():
    if client.db is None:
        print("ArangoDB not connected")
        return

    status_col = client.db.collection("processing_status")
    status_doc = status_col.get(file_id)
    print(f"Status for {file_id}:")
    print(json.dumps(status_doc, indent=2, ensure_ascii=False))


check_status()
