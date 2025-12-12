# 代碼功能說明: MCP 自動化測試腳本 (Python)
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP 自動化測試腳本"""

import sys
import asyncio
import httpx
import time
from typing import Dict, Any, List

# 測試配置
MCP_SERVER_URL = "http://localhost:8002"
TIMEOUT = 10.0


class MCPTester:
    """MCP 測試器"""

    def __init__(self, base_url: str = MCP_SERVER_URL):
        """
        初始化測試器

        Args:
            base_url: MCP Server 基礎 URL
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.results: List[Dict[str, Any]] = []

    async def test_health_check(self) -> bool:
        """測試健康檢查端點"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                assert data.get("status") == "healthy"
                self._record_result("健康檢查", True, "健康檢查通過")
                return True
            else:
                self._record_result("健康檢查", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self._record_result("健康檢查", False, str(e))
            return False

    async def test_ready_check(self) -> bool:
        """測試就緒檢查端點"""
        try:
            response = await self.client.get(f"{self.base_url}/ready")
            if response.status_code == 200:
                data = response.json()
                assert data.get("status") == "ready"
                self._record_result("就緒檢查", True, "就緒檢查通過")
                return True
            else:
                self._record_result("就緒檢查", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self._record_result("就緒檢查", False, str(e))
            return False

    async def test_initialize(self) -> bool:
        """測試 MCP 初始化"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
            }
            response = await self.client.post(f"{self.base_url}/mcp", json=request)
            if response.status_code == 200:
                data = response.json()
                assert "result" in data
                self._record_result("MCP 初始化", True, "初始化成功")
                return True
            else:
                self._record_result("MCP 初始化", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self._record_result("MCP 初始化", False, str(e))
            return False

    async def test_list_tools(self) -> bool:
        """測試列出工具"""
        try:
            request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            response = await self.client.post(f"{self.base_url}/mcp", json=request)
            if response.status_code == 200:
                data = response.json()
                assert "result" in data
                assert "tools" in data["result"]
                tools_count = len(data["result"]["tools"])
                self._record_result("列出工具", True, f"找到 {tools_count} 個工具")
                return True
            else:
                self._record_result("列出工具", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self._record_result("列出工具", False, str(e))
            return False

    async def test_tool_call(self) -> bool:
        """測試工具調用"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "task_analyzer",
                    "arguments": {"task": "Test task for automation"},
                },
            }
            start_time = time.time()
            response = await self.client.post(f"{self.base_url}/mcp", json=request)
            latency = (time.time() - start_time) * 1000  # 轉換為毫秒

            if response.status_code == 200:
                data = response.json()
                assert "result" in data
                self._record_result(
                    "工具調用", True, f"調用成功，延遲: {latency:.2f}ms"
                )
                return True
            else:
                self._record_result("工具調用", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self._record_result("工具調用", False, str(e))
            return False

    async def test_performance(self, iterations: int = 10) -> Dict[str, Any]:
        """測試性能"""
        latencies = []
        errors = 0

        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}

        for i in range(iterations):
            try:
                start_time = time.time()
                response = await self.client.post(f"{self.base_url}/mcp", json=request)
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)

                if response.status_code != 200:
                    errors += 1
            except Exception:
                errors += 1

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        success_rate = (iterations - errors) / iterations * 100

        return {
            "iterations": iterations,
            "avg_latency_ms": avg_latency,
            "max_latency_ms": max_latency,
            "min_latency_ms": min_latency,
            "success_rate": success_rate,
            "errors": errors,
        }

    def _record_result(self, test_name: str, passed: bool, message: str):
        """記錄測試結果"""
        self.results.append(
            {
                "test": test_name,
                "passed": passed,
                "message": message,
            }
        )

    async def run_all_tests(self) -> Dict[str, Any]:
        """運行所有測試"""
        print("=" * 50)
        print("MCP Server/Client 自動化測試")
        print("=" * 50)

        # 基本功能測試
        await self.test_health_check()
        await self.test_ready_check()
        await self.test_initialize()
        await self.test_list_tools()
        await self.test_tool_call()

        # 性能測試
        print("\n執行性能測試...")
        perf_results = await self.test_performance(iterations=10)
        self._record_result(
            "性能測試",
            perf_results["success_rate"] >= 95,
            f"成功率: {perf_results['success_rate']:.1f}%, "
            f"平均延遲: {perf_results['avg_latency_ms']:.2f}ms",
        )

        # 輸出結果
        print("\n" + "=" * 50)
        print("測試結果")
        print("=" * 50)

        passed = sum(1 for r in self.results if r["passed"])
        failed = len(self.results) - passed

        for result in self.results:
            status = "✓" if result["passed"] else "✗"
            color = "\033[0;32m" if result["passed"] else "\033[0;31m"
            print(f"{color}{status} {result['test']}: {result['message']}\033[0m")

        print(f"\n通過: {passed}")
        print(f"失敗: {failed}")
        print(f"總計: {len(self.results)}")

        if perf_results:
            print("\n性能指標:")
            print(f"  平均延遲: {perf_results['avg_latency_ms']:.2f}ms")
            print(f"  最大延遲: {perf_results['max_latency_ms']:.2f}ms")
            print(f"  最小延遲: {perf_results['min_latency_ms']:.2f}ms")
            print(f"  成功率: {perf_results['success_rate']:.1f}%")

        return {
            "passed": passed,
            "failed": failed,
            "total": len(self.results),
            "results": self.results,
            "performance": perf_results,
        }

    async def close(self):
        """關閉測試器"""
        await self.client.aclose()


async def main():
    """主函數"""
    tester = MCPTester()
    try:
        results = await tester.run_all_tests()
        sys.exit(0 if results["failed"] == 0 else 1)
    except KeyboardInterrupt:
        print("\n測試中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n測試錯誤: {e}")
        sys.exit(1)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
