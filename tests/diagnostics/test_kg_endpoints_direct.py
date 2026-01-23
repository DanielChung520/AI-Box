# 代碼功能說明: 直接測試 get_kg_triples 和 get_kg_chunk_status API 端點邏輯
# 創建日期: 2026-01-22 17:35 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-22 17:35 UTC+8

import asyncio
import json
import os
import sys
from pathlib import Path

# 將項目根目錄添加到 sys.path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 設置環境變量
os.environ["AI_BOX_CONFIG_PATH"] = os.path.join(project_root, "config", "config.json")

from api.routers.file_upload import get_kg_chunk_status, get_kg_triples
from system.security.models import Permission, User

fid = "786316d7-5593-415e-b442-77d9fcf36028"


async def test_api_endpoints():
    print(f"--- 測試 API 端點 (file_id: {fid}) ---")

    # Mock current_user
    mock_user = User(
        user_id="daniel@test.com",
        username="daniel",
        roles=["admin"],
        permissions=[Permission.ALL.value],
    )

    # 1. 測試 get_kg_triples
    print("\n[1] 測試 get_kg_triples:")
    try:
        response = await get_kg_triples(file_id=fid, limit=10, offset=0, current_user=mock_user)
        content = json.loads(response.body.decode("utf-8"))
        print(f"成功: {content.get('success')}")
        if content.get("success"):
            data = content.get("data", {})
            print(f"三元組總數: {data.get('total')}")
            print(f"返回數量: {len(data.get('triples', []))}")
            if data.get("triples"):
                print(f"樣本三元組: {data.get('triples')[0]}")
        else:
            print(f"錯誤訊息: {content.get('message')}")
    except Exception as e:
        print(f"get_kg_triples 發生錯誤: {e}")

    # 2. 測試 get_kg_chunk_status
    print("\n[2] 測試 get_kg_chunk_status:")
    try:
        response = await get_kg_chunk_status(file_id=fid, current_user=mock_user)
        content = json.loads(response.body.decode("utf-8"))
        print(f"成功: {content.get('success')}")
        if content.get("success"):
            data = content.get("data", {})
            print(f"分塊狀態詳情: {data}")
        else:
            print(f"錯誤訊息: {content.get('message')}")
    except Exception as e:
        print(f"get_kg_chunk_status 發生錯誤: {e}")


if __name__ == "__main__":
    asyncio.run(test_api_endpoints())
