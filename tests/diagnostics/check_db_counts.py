
from database.arangodb.client import ArangoDBClient

# os.environ["AI_BOX_CONFIG_PATH"] = "/Users/daniel/GitHub/AI-Box/config/config.json"
client = ArangoDBClient()


def check_counts():
    if client.db is None:
        print("ArangoDB not connected")
        return

    entities = client.db.collection("entities")
    relations = client.db.collection("relations")

    print(f"Entities count: {entities.count()}")
    print(f"Relations count: {relations.count()}")

    # Check for a specific file_id
    file_id = "786316d7-5593-415e-b442-77d9fcf36028"

    entity_query = """
    FOR e IN entities
    FILTER e.file_id == @file_id OR @file_id IN e.file_ids
    COLLECT WITH COUNT INTO count
    RETURN count
    """
    entity_count = list(client.db.aql.execute(entity_query, bind_vars={"file_id": file_id}))[0]

    relation_query = """
    FOR r IN relations
    FILTER r.file_id == @file_id OR @file_id IN r.file_ids
    COLLECT WITH COUNT INTO count
    RETURN count
    """
    relation_count = list(client.db.aql.execute(relation_query, bind_vars={"file_id": file_id}))[0]

    print(f"\nFor file_id {file_id}:")
    print(f"Entities: {entity_count}")
    print(f"Relations: {relation_count}")


check_counts()
