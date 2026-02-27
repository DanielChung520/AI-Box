"""Knowledge Base Authorization Service"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any, Optional
from database.arangodb import ArangoDBClient


class KBAuthService:
    """Knowledge Base Authorization Service"""

    def __init__(self):
        self.client = ArangoDBClient()
        self.db = self.client.db

    def get_authorized_folders(
        self,
        agent_key: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get authorized KB folders for an agent"""

        if self.db is None:
            return []

        bind_vars = {}

        if agent_key:
            filter_clause = "doc._key == @agent_key"
            bind_vars["agent_key"] = agent_key
        elif agent_id:
            filter_clause = "doc.agent_id == @agent_id"
            bind_vars["agent_id"] = agent_id
        else:
            return []

        aql = f"""
        FOR doc IN agent_display_configs
        FILTER doc.config_type == "agent"
        FILTER {filter_clause}
        FILTER doc.agent_config != null
        FILTER doc.agent_config.knowledge_bases != null
        
        LET kb_roots_ids = doc.agent_config.knowledge_bases
        
        FOR kb_root_id IN kb_roots_ids
            FOR folder IN kb_folders
                FILTER folder.rootId == kb_root_id OR folder.root_id == kb_root_id
                FILTER folder.isActive == true
                
                RETURN {{
                    folder_key: folder._key,
                    folder_name: folder.name,
                    folder_path: folder.path,
                    kb_root_key: kb_root_id
                }}
        """

        try:
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
            return list(cursor)
        except Exception:
            return []

    def get_authorized_files(
        self,
        agent_key: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get authorized KB files for an agent"""

        if self.db is None:
            return []

        bind_vars = {}

        if agent_key:
            filter_clause = "doc._key == @agent_key"
            bind_vars["agent_key"] = agent_key
        elif agent_id:
            filter_clause = "doc.agent_id == @agent_id"
            bind_vars["agent_id"] = agent_id
        else:
            return []

        aql = f"""
        FOR doc IN agent_display_configs
        FILTER doc.config_type == "agent"
        FILTER {filter_clause}
        FILTER doc.agent_config != null
        FILTER doc.agent_config.knowledge_bases != null
        
        LET kb_roots_ids = doc.agent_config.knowledge_bases
        
        FOR kb_root_id IN kb_roots_ids
            FOR file IN file_metadata
                FILTER file.knowledge_base_id == kb_root_id
                FILTER file.task_id LIKE "kb_%"
                
                RETURN {{
                    file_id: file.file_id,
                    file_name: file.filename,
                    kb_root_key: kb_root_id,
                    knw_code: file.knw_code,
                    domain: file.domain,
                    major: file.major,
                    lifecycle_state: file.lifecycle_state
                }}
        """

        try:
            cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
            result = list(cursor)
            return result
        except Exception as e:
            print(f"KBAuthService get_authorized_files error: {e}")
            return []

    def check_file_access(
        self,
        agent_key: Optional[str] = None,
        agent_id: Optional[str] = None,
        file_id: Optional[str] = None,
    ) -> bool:
        """Check if an agent has access to a specific file"""

        if not file_id:
            return False

        authorized_files = self.get_authorized_files(
            agent_key=agent_key,
            agent_id=agent_id,
        )

        for f in authorized_files:
            if f.get("file_id") == file_id:
                return True

        return False


def get_kb_auth_service() -> KBAuthService:
    """Get KB authorization service instance"""
    return KBAuthService()


def test():
    """Test KB authorization service"""
    print("=" * 50)
    print("Testing KB Authorization Service")
    print("=" * 50)

    svc = get_kb_auth_service()

    print("\n[Test 1] Get authorized folders for agent_key = '-h0tjyh'")
    folders = svc.get_authorized_folders(agent_key="-h0tjyh")
    print(f"Found {len(folders)} folders")
    for f in folders:
        print(f"  - {f}")

    print("\n[Test 2] Get authorized files for agent_key = '-h0tjyh'")
    files = svc.get_authorized_files(agent_key="-h0tjyh")
    print(f"Found {len(files)} files")
    for f in files[:5]:
        print(f"  - {f.get('file_name')}")

    print("\n[Test 3] Get authorized folders for agent_id = 'mm-agent'")
    folders = svc.get_authorized_folders(agent_id="mm-agent")
    print(f"Found {len(folders)} folders")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    test()
