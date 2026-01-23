import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock some things if needed
os.environ["AI_BOX_CONFIG_PATH"] = os.path.join(project_root, "config", "config.json")

from api.routers.file_management import get_file_graph
from system.security.models import Permission, User

fid = "786316d7-5593-415e-b442-77d9fcf36028"


async def test_get_file_graph():
    print(f"Testing get_file_graph for file_id: {fid}")

    # Mock current_user with ALL permission
    mock_user = User(
        user_id="user_admin", username="admin", roles=["admin"], permissions=[Permission.ALL.value]
    )

    try:
        response = await get_file_graph(
            file_id=fid, limit=10, offset=0, current_user=mock_user  # Higher limit
        )

        # response is a JSONResponse
        content = json.loads(response.body.decode("utf-8"))

        # Check for error status
        if content.get("status") == "error":
            print(f"API Error: {content.get('message')}")
            return

        print(f"Response status: {content.get('status')}")

        data = content.get("data", {})
        if not data:
            print("No data returned")
            return

        print(f"Data - nodes count: {len(data.get('nodes', []))}")
        print(f"Data - edges count: {len(data.get('edges', []))}")
        print(f"Data - stats: {data.get('stats')}")

        if len(data.get("nodes", [])) > 0:
            print(f"Sample node: {data.get('nodes')[0]}")
        if len(data.get("edges", [])) > 0:
            print(f"Sample edge: {data.get('edges')[0]}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_get_file_graph())
