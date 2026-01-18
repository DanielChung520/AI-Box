# 代碼功能說明: 切換監控系統功能開關
# 創建日期: 2026-01-18 18:54 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 18:54 UTC+8

"""切換監控系統功能開關腳本

用於切換 USE_NEW_MONITORING 環境變量，啟用或禁用新的 Prometheus 監控系統
"""

import sys
from pathlib import Path

from dotenv import load_dotenv, set_key


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("用法: python switch_monitoring_system.py <enable|disable>")
        print("  enable  - 啟用新監控系統（USE_NEW_MONITORING=true）")
        print("  disable - 禁用新監控系統（USE_NEW_MONITORING=false）")
        return 1

    action = sys.argv[1].lower()

    if action not in ["enable", "disable"]:
        print(f"❌ 無效的操作: {action}")
        print("請使用 'enable' 或 'disable'")
        return 1

    # 獲取 .env 文件路徑
    project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / ".env"

    # 如果 .env 文件不存在，創建它
    if not env_file.exists():
        env_file.touch()
        print(f"📄 創建 .env 文件: {env_file}")

    # 加載現有環境變量
    load_dotenv(env_file, override=True)

    # 設置或移除環境變量
    if action == "enable":
        set_key(env_file, "USE_NEW_MONITORING", "true")
        print("✅ 已啟用新監控系統（Prometheus）")
        print("   USE_NEW_MONITORING=true")
    else:
        set_key(env_file, "USE_NEW_MONITORING", "false")
        print("✅ 已禁用新監控系統（使用舊系統）")
        print("   USE_NEW_MONITORING=false")

    print()
    print("⚠️  請重啟 FastAPI 服務以使更改生效：")
    print("   pkill -f 'uvicorn api.main:app'")
    print("   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &")
    print()

    return 0


if __name__ == "__main__":
    exit(main())
