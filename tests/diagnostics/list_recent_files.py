
from database.arangodb.client import ArangoDBClient


def list_files():
    try:
        client = ArangoDBClient(database="ai_box_kg")
        db = client.db
        if db is None:
            print("Failed to connect to ai_box_kg")
            return

        query = "FOR d IN file_metadata SORT d.created_at DESC LIMIT 10 RETURN {key: d._key, filename: d.filename, kg_status: d.kg_status, task_id: d.task_id}"
        cursor = db.aql.execute(query)
        print("Recent 10 files in file_metadata:")
        for d in cursor:
            print(
                f"ID: {d['key']}, Filename: {d['filename']}, Status: {d['kg_status']}, TaskID: {d['task_id']}"
            )

        print("\nSearching for files with name matching '智能體開發平台規格書':")
        query2 = "FOR d IN file_metadata FILTER d.filename LIKE '%智能體開發平台規格書%' RETURN {key: d._key, filename: d.filename, kg_status: d.kg_status}"
        cursor2 = db.aql.execute(query2)
        for d in cursor2:
            print(f"ID: {d['key']}, Filename: {d['filename']}, Status: {d['kg_status']}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    list_files()
