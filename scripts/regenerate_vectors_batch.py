# 代碼功能說明: 批量重新生成向量數據腳本
# 創建日期: 2026-01-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-03

"""批量重新生成向量數據 - 針對無向量數據的文件"""

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

# 8個無向量數據的文件ID
FILE_IDS_NO_VECTOR = [
    "9f0bb605-c72d-4396-9bbf-0dfa654db276",  # Security-Agent-規格書.md
    "0e7ce498-6fbe-4d2b-be3b-6fa375ab77dc",  # System-Config-Agent-規格書.md
    "2d2dd9a4-b17d-4bd3-b6ef-b983b3fdae63",  # IEE前端系统.md
    "d3d0fae5-56e6-42de-86fa-a4cde19bee81",  # AI-Box-IEE-式-Markdown-文件編輯器開發規格書.md
    "bdc17ee3-95ca-4409-8207-2c71112f80b0",  # README.md
    "b7490598-1890-4c5e-96dc-587759c173b5",  # SeaweedFS使用指南.md
    "e0850b6c-ca79-43e8-af2e-fb4eaea97ecf",  # 负载均衡器API文档.md
    "6a52cb5e-32de-44da-b722-e45c9675e1a0",  # 部署架构-参数策略符合性检核.md
]


class VectorRegenerationClient:
    """向量重新生成客戶端"""

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

    async def regenerate_vector(self, file_id: str) -> Dict[str, any]:
        """重新生成文件的向量數據"""
        if not self.token:
            await self.login()

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/files/{file_id}/regenerate",
                json={"type": "vector"},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                logger.info("向量重新生成請求已提交", file_id=file_id)
                return {"success": True, "file_id": file_id, "data": data.get("data")}
            else:
                logger.error("向量重新生成請求失敗", file_id=file_id, response=data)
                return {"success": False, "file_id": file_id, "error": data.get("message")}
        except Exception as e:
            logger.error("向量重新生成錯誤", file_id=file_id, error=str(e))
            return {"success": False, "file_id": file_id, "error": str(e)}

    async def close(self):
        """關閉客戶端"""
        await self.client.aclose()


async def main():
    """主函數"""
    logger.info("開始批量重新生成向量數據", file_count=len(FILE_IDS_NO_VECTOR))

    client = VectorRegenerationClient(API_BASE_URL, DEFAULT_USERNAME, DEFAULT_PASSWORD)

    try:
        # 登錄
        if not await client.login():
            logger.error("登錄失敗，退出")
            sys.exit(1)

        results: List[Dict[str, any]] = []
        success_count = 0
        fail_count = 0

        # 逐個處理文件
        for i, file_id in enumerate(FILE_IDS_NO_VECTOR, 1):
            logger.info(f"[{i}/{len(FILE_IDS_NO_VECTOR)}] 處理文件", file_id=file_id)
            result = await client.regenerate_vector(file_id)
            results.append(result)

            if result.get("success"):
                success_count += 1
                logger.info(f"[{i}/{len(FILE_IDS_NO_VECTOR)}] 成功", file_id=file_id)
            else:
                fail_count += 1
                logger.error(f"[{i}/{len(FILE_IDS_NO_VECTOR)}] 失敗", file_id=file_id, error=result.get("error"))

        # 保存結果
        output_file = "regenerate_vectors_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "total": len(FILE_IDS_NO_VECTOR),
                    "success": success_count,
                    "failed": fail_count,
                    "results": results,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(
            "批量重新生成向量數據完成",
            total=len(FILE_IDS_NO_VECTOR),
            success=success_count,
            failed=fail_count,
            output_file=output_file,
        )

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
