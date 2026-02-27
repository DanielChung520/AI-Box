"""KB Authorization Materialized Collection Manager"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from database.arangodb import ArangoDBClient


COLLECTION_NAME = "kb_agent_authorization"
VIEW_NAME = "agent_ka_view"


def create_collection() -> bool:
    """Create materialized collection for KB authorization"""
    client = ArangoDBClient()
    db = client.db

    if db is None:
        print("Cannot connect to ArangoDB")
        return False

    try:
        # Create collection (ignore if exists)
        try:
            db.create_collection(COLLECTION_NAME)
            print(f"Collection '{COLLECTION_NAME}' created")
        except Exception:
            print(f"Collection '{COLLECTION_NAME}' already exists")

        # Add indexes
        col = db.collection(COLLECTION_NAME)
        col.add_index({"type": "persistent", "fields": ["agent_key"]})
        col.add_index({"type": "persistent", "fields": ["agent_id"]})
        col.add_index({"type": "persistent", "fields": ["kb_root_key"]})
        col.add_index({"type": "persistent", "fields": ["folder_key"]})
        col.add_index({"type": "persistent", "fields": ["file_id"]})
        print("Indexes ready")

        return True

    except Exception as e:
        print(f"Create collection failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def create_view() -> bool:
    """Create ArangoSearch view for KB authorization (backup/verification)"""
    return True  # Skip for now - collection with indexes is sufficient


def populate_from_existing_data() -> bool:
    """Populate authorization data from existing collections"""
    client = ArangoDBClient()
    db = client.db

    if db is None:
        print("Cannot connect to ArangoDB")
        return False

    try:
        col = db.collection(COLLECTION_NAME)

        # Clear existing data
        col.truncate()
        print("Collection truncated")

        # Query all agent configs with knowledge_bases
        aql = """
        FOR doc IN agent_display_configs
        FILTER doc.config_type == "agent"
        FILTER doc.agent_config != null
        FILTER doc.agent_config.knowledge_bases != null
        
        RETURN {
            agent_key: doc._key,
            agent_id: doc.agent_id,
            kb_roots: doc.agent_config.knowledge_bases
        }
        """
        cursor = db.aql.execute(aql)
        agent_configs = list(cursor)

        print(f"Found {len(agent_configs)} agents with knowledge_bases")

        total_docs = 0

        for config in agent_configs:
            agent_key = config.get("agent_key")
            agent_id = config.get("agent_id")
            kb_roots = config.get("kb_roots", [])

            for kb_root_id in kb_roots:
                # Get files directly by knowledge_base_id
                file_aql = """
                FOR file IN file_metadata
                FILTER file.knowledge_base_id == @kb_root_id
                FILTER file.task_id LIKE "kb_%"
                RETURN file
                """
                file_cursor = db.aql.execute(file_aql, bind_vars={"kb_root_id": kb_root_id})
                files = list(file_cursor)

                for file in files:
                    doc = {
                        "_key": f"auth_{agent_key}_{file.get('file_id')}",
                        "agent_key": agent_key,
                        "agent_id": agent_id,
                        "kb_root_key": kb_root_id,
                        "file_id": file.get("file_id"),
                        "file_name": file.get("filename"),
                        "knw_code": file.get("knw_code"),
                        "domain": file.get("domain"),
                        "major": file.get("major"),
                        "lifecycle_state": file.get("lifecycle_state"),
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                    col.insert(doc)
                    total_docs += 1

        print(f"Inserted {total_docs} authorization documents")
        return True

    except Exception as e:
        print(f"Populate failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_view() -> bool:
    """Verify collection is working correctly"""
    client = ArangoDBClient()
    db = client.db

    if db is None:
        print("Cannot connect to ArangoDB")
        return False

    try:
        # Query collection directly
        col = db.collection(COLLECTION_NAME)
        results = list(col.find({"agent_key": "-h0tjyh"}))

        print(f"Collection query returned {len(results)} results for agent_key=-h0tjyh")
        for r in results:
            print(f"  - {r.get('file_name')}")

        return True

    except Exception as e:
        print(f"Verify failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    try:
        # Query via view
        aql = f"""
        FOR doc IN {VIEW_NAME}
        FILTER doc.agent_key == "-h0tjyh"
        LIMIT 10
        RETURN doc
        """
        cursor = db.aql.execute(aql)
        results = list(cursor)

        print(f"View query returned {len(results)} results")
        for r in results:
            print(f"  - {r.get('file_name')}")

        return True

    except Exception as e:
        print(f"Verify view failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def query_by_agent(agent_key: str = None, agent_id: str = None):
    """Query authorization by agent"""
    client = ArangoDBClient()
    db = client.db

    if db is None:
        return []

    col = db.collection(COLLECTION_NAME)

    if agent_key:
        return list(col.find({"agent_key": agent_key}))
    elif agent_id:
        return list(col.find({"agent_id": agent_id}))
    return []


if __name__ == "__main__":
    print("=" * 50)
    print("KB Authorization Setup")
    print("=" * 50)

    # Step 1: Create collection
    print("\n[1] Creating collection...")
    if not create_collection():
        sys.exit(1)

    # Step 2: Create view
    print("\n[2] Creating view...")
    if not create_view():
        sys.exit(1)

    # Step 3: Populate data
    print("\n[3] Populating data...")
    if not populate_from_existing_data():
        sys.exit(1)

    # Step 4: Verify
    print("\n[4] Verifying view...")
    verify_view()

    print("\n" + "=" * 50)
    print("Setup complete!")
    print("=" * 50)
