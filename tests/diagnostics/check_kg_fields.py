import json

from database.arangodb.client import ArangoDBClient

fid = "786316d7-5593-415e-b442-77d9fcf36028"


def check_entities_and_relations():
    try:
        client = ArangoDBClient(database="ai_box_kg")
        db = client.db

        # Check Entities
        query_ent = """
        FOR e IN entities
        FILTER e.file_id == @file_id OR @file_id IN e.file_ids
        LIMIT 5
        RETURN e
        """
        entities = list(db.aql.execute(query_ent, bind_vars={"file_id": fid}))
        print(f"Entities found with fid: {len(entities)}")
        if entities:
            print(f"Sample entity: {json.dumps(entities[0], indent=2)}")

        # Check Relations
        query_rel = """
        FOR r IN relations
        FILTER r.file_id == @file_id OR @file_id IN r.file_ids
        LIMIT 5
        RETURN r
        """
        relations = list(db.aql.execute(query_rel, bind_vars={"file_id": fid}))
        print(f"Relations found with fid: {len(relations)}")
        if relations:
            print(f"Sample relation: {json.dumps(relations[0], indent=2)}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_entities_and_relations()
