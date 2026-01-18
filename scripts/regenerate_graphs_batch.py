# 代碼功能說明: 批量重新生成圖譜數據腳本
# 創建日期: 2026-01-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-03

"""批量重新生成圖譜數據 - 針對所有74個文件"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

# 配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEFAULT_USERNAME = os.getenv("TEST_USERNAME", "daniel@test.com")
DEFAULT_PASSWORD = os.getenv("TEST_PASSWORD", "1234")


class GraphRegenerationClient:
    """圖譜重新生成客戶端"""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.client = httpx.AsyncClient(timeout=1800.0)  # 30分鐘超時
        self.token: Optional[str] = None

    async def login(self) -> bool:
        """登錄並獲取token"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": self.username, "password": self.password},
            )
            response.raise_for_status()
            data = response.json()
            if data.get("success") and data.get("data", {}).get("access_token"):
                self.token = data["data"]["access_token"]
                logger.info("登錄成功", username=self.username)
                return True
            else:
                logger.error("登錄失敗", response=data)
                return False
        except Exception as e:
            logger.error("登錄錯誤", error=str(e))
            return False

    async def get_all_file_ids(self) -> List[str]:
        """從ArangoDB獲取所有文件的file_id"""
        try:
            from arango import ArangoClient
            from dotenv import load_dotenv

            # 加載環境變量
            env_path = Path(".env")
            if env_path.exists():
                load_dotenv(env_path)

            # 獲取ArangoDB配置
            arangodb_host = os.getenv("ARANGODB_HOST", "localhost")
            arangodb_port = int(os.getenv("ARANGODB_PORT", "8529"))
            arangodb_user = os.getenv("ARANGODB_USER", "root")
            arangodb_password = os.getenv("ARANGODB_PASSWORD", "")
            arangodb_database = os.getenv("ARANGODB_DATABASE", "ai_box_kg")

            # 連接ArangoDB
            client = ArangoClient(hosts=f"http://{arangodb_host}:{arangodb_port}")
            db = client.db(arangodb_database, username=arangodb_user, password=arangodb_password)

            # 查詢所有文件的file_id
            aql = """
            FOR doc IN file_metadata
                RETURN doc.file_id
            """
            cursor = db.aql.execute(aql)
            file_ids = list(cursor)

            logger.info("從ArangoDB獲取文件列表", count=len(file_ids))
            return file_ids

        except Exception as e:
            logger.error("獲取文件列表錯誤", error=str(e))
            return []

    async def regenerate_graph(self, file_id: str) -> Dict[str, any]:
        """重新生成文件的圖譜數據"""
        if not self.token:
            await self.login()

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/files/{file_id}/regenerate",
                json={"type": "graph"},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                logger.info("圖譜重新生成請求已提交", file_id=file_id)
                return {"success": True, "file_id": file_id, "data": data.get("data")}
            else:
                logger.error("圖譜重新生成請求失敗", file_id=file_id, response=data)
                return {"success": False, "file_id": file_id, "error": data.get("message")}
        except Exception as e:
            logger.error("圖譜重新生成錯誤", file_id=file_id, error=str(e))
            return {"success": False, "file_id": file_id, "error": str(e)}

    async def close(self):
        """關閉客戶端"""
        await self.client.aclose()


async def main():
    """主函數"""
    logger.info("開始批量重新生成圖譜數據")

    client = GraphRegenerationClient(API_BASE_URL, DEFAULT_USERNAME, DEFAULT_PASSWORD)

    try:
        # 登錄
        if not await client.login():
            logger.error("登錄失敗，退出")
            sys.exit(1)

        # 獲取所有文件的file_id
        file_ids = await client.get_all_file_ids()
        if not file_ids:
            logger.error("無法獲取文件列表，退出")
            sys.exit(1)

        logger.info("獲取文件列表成功", file_count=len(file_ids))

        results: List[Dict[str, any]] = []
        success_count = 0
        fail_count = 0

        # 逐個處理文件
        for i, file_id in enumerate(file_ids, 1):
            logger.info(f"[{i}/{len(file_ids)}] 處理文件", file_id=file_id)
            result = await client.regenerate_graph(file_id)
            results.append(result)

            if result.get("success"):
                success_count += 1
                logger.info(f"[{i}/{len(file_ids)}] 成功", file_id=file_id)
            else:
                fail_count += 1
                logger.error(
                    f"[{i}/{len(file_ids)}] 失敗", file_id=file_id, error=result.get("error")
                )

        # 保存結果
        output_file = "regenerate_graphs_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "total": len(file_ids),
                    "success": success_count,
                    "failed": fail_count,
                    "results": results,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(
            "批量重新生成圖譜數據完成",
            total=len(file_ids),
            success=success_count,
            failed=fail_count,
            output_file=output_file,
        )

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
