# 代碼功能說明: API 服務 Smoke Test Python 腳本
# 創建日期: 2025-11-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""使用 httpx 進行自動化 API 測試"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

try:
    import httpx
except ImportError:
    print("❌ httpx is required. Install it with: pip install httpx")
    sys.exit(1)


# 配置
API_BASE_URL = "http://localhost:8000"
TEST_REPORT_FILE = "smoke_test_report.txt"


class SmokeTest:
    """Smoke Test 測試類"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)
        self.passed = 0
        self.failed = 0
        self.results: list[Dict[str, Any]] = []

    async def test_endpoint(
        self,
        method: str,
        endpoint: str,
        expected_status: int = 200,
        description: str = "",
        **kwargs,
    ) -> bool:
        """
        測試端點

        Args:
            method: HTTP 方法
            endpoint: 端點路徑
            expected_status: 期望的 HTTP 狀態碼
            description: 測試描述
            **kwargs: 額外的請求參數

        Returns:
            測試是否通過
        """
        url = f"{self.base_url}{endpoint}"
        print(f"Testing {description or endpoint}... ", end="", flush=True)

        try:
            if method.upper() == "GET":
                response = await self.client.get(url, **kwargs)
            elif method.upper() == "POST":
                response = await self.client.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            result = {
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success,
                "description": description,
            }

            if success:
                print(f"✓ PASSED (HTTP {response.status_code})")
                self.passed += 1
            else:
                print(
                    f"✗ FAILED (Expected HTTP {expected_status}, got HTTP {response.status_code})"
                )
                print(f"  Response: {response.text[:200]}")
                self.failed += 1

            self.results.append(result)
            return success

        except Exception as e:
            print(f"✗ ERROR: {e}")
            self.failed += 1
            self.results.append(
                {
                    "endpoint": endpoint,
                    "method": method,
                    "success": False,
                    "error": str(e),
                    "description": description,
                }
            )
            return False

    async def run_all_tests(self):
        """運行所有測試"""
        print("=" * 50)
        print("API Smoke Test")
        print("=" * 50)
        print(f"API Base URL: {self.base_url}")
        print(f"Test Report: {TEST_REPORT_FILE}")
        print()

        # 健康檢查端點
        await self.test_endpoint("GET", "/health", 200, "Health Check")
        await self.test_endpoint("GET", "/ready", 200, "Readiness Check")
        await self.test_endpoint("GET", "/metrics", 200, "Metrics Endpoint")

        # 版本信息
        await self.test_endpoint("GET", "/version", 200, "Version Info")

        # OpenAPI 文檔
        await self.test_endpoint("GET", "/docs", 200, "OpenAPI Docs (Swagger UI)")
        await self.test_endpoint("GET", "/redoc", 200, "OpenAPI Docs (ReDoc)")
        await self.test_endpoint("GET", "/openapi.json", 200, "OpenAPI JSON Schema")

        # API 端點
        await self.test_endpoint(
            "GET", "/api/v1/agents/discover", 200, "Agents Discover"
        )

        llm_prompt = os.getenv("SMOKE_TEST_LLM_PROMPT")
        if llm_prompt:
            await self.test_endpoint(
                "POST",
                "/api/v1/llm/generate",
                200,
                "LLM Generate",
                json={"prompt": llm_prompt, "stream": False},
            )

        if os.getenv("SMOKE_TEST_OLLAMA_HOST"):
            await self.test_ollama_health()

        # 生成報告
        await self.generate_report()

    async def generate_report(self):
        """生成測試報告"""
        print()
        print("=" * 50)
        print("Test Summary")
        print("=" * 50)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")
        print()

        # 保存報告到文件
        report_path = Path(TEST_REPORT_FILE)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("API Smoke Test Report\n")
            f.write("=" * 50 + "\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"API Base URL: {self.base_url}\n")
            f.write("\n")
            f.write("Results:\n")
            f.write(f"  Passed: {self.passed}\n")
            f.write(f"  Failed: {self.failed}\n")
            f.write(f"  Total:  {self.passed + self.failed}\n")
            f.write("\n")
            f.write("Detailed Results:\n")
            f.write("-" * 50 + "\n")
            for result in self.results:
                status = "✓ PASSED" if result.get("success") else "✗ FAILED"
                f.write(
                    f"{status} - {result.get('description', result.get('endpoint'))}\n"
                )
                if not result.get("success"):
                    f.write(f"  Error: {result.get('error', 'Status code mismatch')}\n")

        print(f"Report saved to: {report_path}")

        if self.failed == 0:
            print("✅ All tests passed!")
            return 0
        else:
            print("❌ Some tests failed!")
            return 1

    async def close(self):
        """關閉客戶端"""
        await self.client.aclose()

    async def test_ollama_health(self):
        """直接檢查 Ollama 節點健康狀態。"""
        host = os.getenv("SMOKE_TEST_OLLAMA_HOST", "localhost")
        port = os.getenv("SMOKE_TEST_OLLAMA_PORT", "11434")
        url = f"http://{host}:{port}/api/version"
        print(f"Testing Ollama health ({url})... ", end="", flush=True)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
            if response.status_code == 200:
                print("✓ PASSED")
                self.passed += 1
            else:
                print(f"✗ FAILED (HTTP {response.status_code})")
                self.failed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"✗ ERROR: {exc}")
            self.failed += 1


async def main():
    """主函數"""
    base_url = os.getenv("API_BASE_URL", API_BASE_URL)
    tester = SmokeTest(base_url=base_url)

    try:
        exit_code = await tester.run_all_tests()
        sys.exit(exit_code)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
