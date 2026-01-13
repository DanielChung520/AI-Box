# 代碼功能說明: Data Agent 環境配置檢查腳本
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""檢查 Data Agent 環境配置"""

import os
import sys
from pathlib import Path

# 獲取 AI-Box 根目錄
AI_BOX_ROOT = Path(__file__).resolve().parent.parent.parent
env_path = AI_BOX_ROOT / ".env"

# 加載環境變數
from dotenv import load_dotenv

load_dotenv(dotenv_path=env_path)


def check_environment() -> dict:
    """檢查環境配置"""
    results = {
        "passed": True,
        "checks": [],
        "errors": [],
        "warnings": [],
    }

    # 1. 檢查 Datalake SeaweedFS 配置
    print("📋 檢查 Datalake SeaweedFS 配置...")

    required_vars = {
        "DATALAKE_SEAWEEDFS_S3_ENDPOINT": os.getenv("DATALAKE_SEAWEEDFS_S3_ENDPOINT"),
        "DATALAKE_SEAWEEDFS_S3_ACCESS_KEY": os.getenv("DATALAKE_SEAWEEDFS_S3_ACCESS_KEY"),
        "DATALAKE_SEAWEEDFS_S3_SECRET_KEY": os.getenv("DATALAKE_SEAWEEDFS_S3_SECRET_KEY"),
    }

    for var_name, var_value in required_vars.items():
        if var_value:
            print(
                f"  ✅ {var_name}: {var_value[:20]}..."
                if len(var_value) > 20
                else f"  ✅ {var_name}: {var_value}"
            )
            results["checks"].append(f"{var_name}: ✅")
        else:
            print(f"  ❌ {var_name}: 未設置")
            results["errors"].append(f"{var_name} 未設置")
            results["passed"] = False

    # 2. 檢查 Data Agent Service 配置
    print("\n📋 檢查 Data Agent Service 配置...")

    service_host = os.getenv("DATA_AGENT_SERVICE_HOST", "localhost")
    service_port = os.getenv("DATA_AGENT_SERVICE_PORT", "8004")

    print(f"  ✅ DATA_AGENT_SERVICE_HOST: {service_host}")
    print(f"  ✅ DATA_AGENT_SERVICE_PORT: {service_port}")
    results["checks"].append(f"DATA_AGENT_SERVICE_HOST: ✅ ({service_host})")
    results["checks"].append(f"DATA_AGENT_SERVICE_PORT: ✅ ({service_port})")

    # 3. 檢查 Python 依賴
    print("\n📋 檢查 Python 依賴...")

    dependencies = {
        "fastapi": "FastAPI",
        "uvicorn": "Uvicorn",
        "boto3": "Boto3 (SeaweedFS S3 API)",
        "jsonschema": "JSON Schema",
        "structlog": "Structured Logging",
    }

    for module, name in dependencies.items():
        try:
            __import__(module)
            print(f"  ✅ {name}: 已安裝")
            results["checks"].append(f"{name}: ✅")
        except ImportError:
            print(f"  ❌ {name}: 未安裝")
            results["errors"].append(f"{name} 未安裝，請運行: pip install {module}")
            results["passed"] = False

    # 4. 檢查 SeaweedFS 服務連接（可選）
    print("\n📋 檢查 SeaweedFS 服務連接...")

    endpoint = os.getenv("DATALAKE_SEAWEEDFS_S3_ENDPOINT", "http://localhost:8334")

    try:
        import httpx

        response = httpx.get(f"{endpoint.replace(':8334', ':8889')}/", timeout=2)
        if response.status_code in [200, 404, 403]:  # 任何響應都表示服務在運行
            print(f"  ✅ SeaweedFS Filer API 可訪問: {endpoint.replace(':8334', ':8889')}")
            results["checks"].append("SeaweedFS Filer API: ✅ 可訪問")
        else:
            print(f"  ⚠️  SeaweedFS Filer API 響應異常: {response.status_code}")
            results["warnings"].append(f"SeaweedFS Filer API 響應異常: {response.status_code}")
    except Exception as e:
        print(f"  ⚠️  無法連接到 SeaweedFS Filer API: {e}")
        results["warnings"].append(f"無法連接到 SeaweedFS Filer API: {e}")

    return results


def main() -> None:
    """主函數"""
    print("=" * 60)
    print("Data Agent 環境配置檢查")
    print("=" * 60)
    print()

    results = check_environment()

    print()
    print("=" * 60)
    print("檢查結果")
    print("=" * 60)

    if results["passed"]:
        print("✅ 所有必需配置已設置")
    else:
        print("❌ 發現配置問題，請修復後重試")

    if results["warnings"]:
        print("\n⚠️  警告:")
        for warning in results["warnings"]:
            print(f"  - {warning}")

    if results["errors"]:
        print("\n❌ 錯誤:")
        for error in results["errors"]:
            print(f"  - {error}")

    print()
    sys.exit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
