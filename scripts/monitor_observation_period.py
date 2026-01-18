# 代碼功能說明: 觀察期監控腳本
# 創建日期: 2026-01-18 18:54 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 18:54 UTC+8

"""觀察期監控腳本

用於在系統切換後的觀察期（24小時）內定期檢查系統狀態，記錄異常情況
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# 加載環境變數
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)


def check_service_status() -> dict:
    """檢查服務狀態 API"""
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    try:
        response = httpx.get(
            f"{api_url}/api/v1/admin/services",
            timeout=10.0,
            headers={"Authorization": f"Bearer {os.getenv('ACCESS_TOKEN', '')}"},
        )
        if response.status_code == 200:
            data = response.json()
            services = data.get("data", {}).get("services", [])
            healthy_count = sum(1 for s in services if s.get("health_status") == "healthy")
            return {
                "status": "ok",
                "total_services": len(services),
                "healthy_services": healthy_count,
                "unhealthy_services": len(services) - healthy_count,
            }
        else:
            return {"status": "error", "error_code": response.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_prometheus() -> dict:
    """檢查 Prometheus 狀態"""
    prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
    try:
        response = httpx.get(f"{prometheus_url}/api/v1/status/config", timeout=5.0)
        if response.status_code == 200:
            return {"status": "ok"}
        else:
            return {"status": "error", "error_code": response.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_alerts() -> dict:
    """檢查告警狀態"""
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    try:
        response = httpx.get(
            f"{api_url}/api/v1/admin/service-alerts",
            timeout=10.0,
            headers={"Authorization": f"Bearer {os.getenv('ACCESS_TOKEN', '')}"},
        )
        if response.status_code == 200:
            data = response.json()
            alerts = data.get("data", {}).get("alerts", [])
            active_alerts = [a for a in alerts if a.get("status") == "active"]
            return {
                "status": "ok",
                "total_alerts": len(alerts),
                "active_alerts": len(active_alerts),
            }
        else:
            return {"status": "error", "error_code": response.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="觀察期監控腳本")
    parser.add_argument(
        "--interval",
        type=int,
        default=7200,
        help="檢查間隔（秒），默認 2 小時（7200 秒）",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=86400,
        help="監控持續時間（秒），默認 24 小時（86400 秒）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="輸出文件路徑（默認：backup/observation_log_YYYYMMDD_HHMMSS.json）",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("觀察期監控腳本")
    print("=" * 80)
    print(f"檢查間隔: {args.interval} 秒（{args.interval // 3600} 小時）")
    print(f"監控持續時間: {args.duration} 秒（{args.duration // 3600} 小時）")
    print()

    # 創建輸出文件
    if args.output:
        output_file = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%HMMSS")
        output_dir = project_root / "backup"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"observation_log_{timestamp}.json"

    observations = []
    start_time = time.time()
    check_count = 0

    print(f"📄 監控日誌將保存到: {output_file}")
    print()
    print("開始監控... (按 Ctrl+C 停止)")
    print()

    try:
        while time.time() - start_time < args.duration:
            check_count += 1
            timestamp = datetime.now().isoformat()

            print(f"[{timestamp}] 執行第 {check_count} 次檢查...")

            observation = {
                "timestamp": timestamp,
                "check_number": check_count,
                "service_status": check_service_status(),
                "prometheus": check_prometheus(),
                "alerts": check_alerts(),
            }

            observations.append(observation)

            # 檢查是否有異常
            has_errors = False
            if observation["service_status"]["status"] != "ok":
                print("  ⚠️  服務狀態檢查失敗")
                has_errors = True
            if observation["prometheus"]["status"] != "ok":
                print("  ⚠️  Prometheus 檢查失敗")
                has_errors = True

            if not has_errors:
                print("  ✅ 所有檢查通過")

            # 保存到文件（每次檢查後都保存，避免數據丟失）
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "start_time": datetime.fromtimestamp(start_time).isoformat(),
                        "observations": observations,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            print()

            # 等待下一次檢查
            if time.time() - start_time < args.duration:
                time.sleep(args.interval)

        print("=" * 80)
        print("監控完成")
        print("=" * 80)
        print(f"✅ 總共執行 {check_count} 次檢查")
        print(f"📄 監控日誌已保存到: {output_file}")

    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("監控已中斷")
        print("=" * 80)
        print(f"✅ 總共執行 {check_count} 次檢查")
        print(f"📄 監控日誌已保存到: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
