# 代碼功能說明: 驗證監控系統運行狀態
# 創建日期: 2026-01-18 18:54 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 18:54 UTC+8

"""驗證監控系統運行狀態腳本

用於驗證新監控系統（Prometheus）是否正常運行
"""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

# 加載環境變數
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)


def check_prometheus() -> bool:
    """檢查 Prometheus 是否可訪問"""
    prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
    try:
        response = httpx.get(f"{prometheus_url}/api/v1/status/config", timeout=5.0)
        if response.status_code == 200:
            print(f"✅ Prometheus 可訪問: {prometheus_url}")
            return True
        else:
            print(f"❌ Prometheus 返回錯誤狀態碼: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Prometheus 不可訪問: {str(e)}")
        return False


def check_alertmanager() -> bool:
    """檢查 Alertmanager 是否可訪問"""
    alertmanager_url = os.getenv("ALERTMANAGER_URL", "http://localhost:9093")
    try:
        response = httpx.get(f"{alertmanager_url}/api/v1/status", timeout=5.0)
        if response.status_code == 200:
            print(f"✅ Alertmanager 可訪問: {alertmanager_url}")
            return True
        else:
            print(f"❌ Alertmanager 返回錯誤狀態碼: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Alertmanager 不可訪問: {str(e)}")
        return False


def check_grafana() -> bool:
    """檢查 Grafana 是否可訪問"""
    grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3001")
    try:
        response = httpx.get(f"{grafana_url}/api/health", timeout=5.0)
        if response.status_code == 200:
            print(f"✅ Grafana 可訪問: {grafana_url}")
            return True
        else:
            print(f"❌ Grafana 返回錯誤狀態碼: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Grafana 不可訪問: {str(e)}")
        return False


def check_fastapi_metrics() -> bool:
    """檢查 FastAPI /metrics 端點"""
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    try:
        response = httpx.get(f"{api_url}/metrics", timeout=5.0)
        if response.status_code == 200:
            print(f"✅ FastAPI /metrics 端點可訪問: {api_url}/metrics")
            return True
        else:
            print(f"❌ FastAPI /metrics 返回錯誤狀態碼: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ FastAPI /metrics 不可訪問: {str(e)}")
        return False


def check_prometheus_targets() -> bool:
    """檢查 Prometheus targets 狀態"""
    prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
    try:
        response = httpx.get(f"{prometheus_url}/api/v1/targets", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                targets = data.get("data", {}).get("activeTargets", [])
                up_targets = [t for t in targets if t.get("health") == "up"]
                print(f"✅ Prometheus Targets: {len(up_targets)}/{len(targets)} UP")
                if len(up_targets) < len(targets):
                    print("⚠️  部分 targets 未運行:")
                    for target in targets:
                        if target.get("health") != "up":
                            print(
                                f"   - {target.get('labels', {}).get('job', 'unknown')}: {target.get('health')}"
                            )
                return len(up_targets) > 0
            else:
                print("❌ Prometheus targets 查詢失敗")
                return False
        else:
            print(f"❌ Prometheus targets API 返回錯誤狀態碼: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 無法查詢 Prometheus targets: {str(e)}")
        return False


def main():
    """主函數"""
    print("=" * 80)
    print("監控系統驗證腳本")
    print("=" * 80)
    print()

    use_new_monitoring = os.getenv("USE_NEW_MONITORING", "false").lower() == "true"
    print(f"📊 當前監控系統: {'新系統（Prometheus）' if use_new_monitoring else '舊系統（ArangoDB）'}")
    print()

    checks = []

    # 檢查 Prometheus（如果啟用新系統）
    if use_new_monitoring:
        print("檢查 Prometheus 監控組件...")
        print("-" * 80)
        checks.append(("Prometheus", check_prometheus()))
        checks.append(("Alertmanager", check_alertmanager()))
        checks.append(("Grafana", check_grafana()))
        checks.append(("FastAPI Metrics", check_fastapi_metrics()))
        checks.append(("Prometheus Targets", check_prometheus_targets()))
        print()
    else:
        print("⚠️  新監控系統未啟用，跳過 Prometheus 相關檢查")
        print("   如需驗證新系統，請先設置 USE_NEW_MONITORING=true")
        print()

    # 總結
    print("=" * 80)
    print("驗證結果")
    print("=" * 80)

    passed = sum(1 for _, result in checks if result)
    total = len(checks)

    for name, result in checks:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{name}: {status}")

    print()
    if total > 0:
        print(f"總體結果: {passed}/{total} 項檢查通過")
        if passed == total:
            print("✅ 所有檢查通過，監控系統運行正常")
            return 0
        else:
            print("⚠️  部分檢查失敗，請檢查相關服務")
            return 1
    else:
        print("⚠️  未執行任何檢查")
        return 0


if __name__ == "__main__":
    exit(main())
