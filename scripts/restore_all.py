# 代碼功能說明: AI-Box 數據恢復腳本 - 恢復 ArangoDB、Qdrant、SeaWeedFS
# 創建日期: 2026-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-27

"""AI-Box 數據恢復腳本

支援恢復：
1. ArangoDB - 圖資料庫
2. Qdrant - 向量資料庫
3. SeaWeedFS (AI-Box) - 物件存儲
4. SeaWeedFS (DataLake) - DataLake 物件存儲

⚠️ 重要提醒：
- 恢復操作會覆蓋現有數據
- 執行前請務必備份當前數據
- 建議在維護時間窗執行
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import structlog

logger = structlog.get_logger(__name__)

# 備份目錄
BACKUP_ROOT = project_root / "backups"
ARANGODB_CONTAINER = "arangodb"
QDRANT_CONTAINER = "qdrant"
SEAWEEDFS_CONTAINER = "seaweedfs"
SEAWEEDFS_DATALAKE_CONTAINER = "seaweedfs-datalake"


def list_available_backups(backup_type: str) -> list[Path]:
    """列出可用的備份"""
    backup_dir = BACKUP_ROOT / backup_type
    if not backup_dir.exists():
        return []

    backups = []
    for date_dir in backup_dir.iterdir():
        if not date_dir.is_dir():
            continue
        for backup_file in date_dir.iterdir():
            if backup_file.is_file() and backup_file.suffix in [".gz", ".dump", ".tar"]:
                backups.append(backup_file)

    return sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)


def select_backup(backup_type: str, interactive: bool = True) -> Optional[Path]:
    """選擇要恢復的備份"""
    backups = list_available_backups(backup_type)

    if not backups:
        logger.error("no_backups_found", backup_type=backup_type)
        print(f"\n❌ 沒有找到 {backup_type} 的備份")
        return None

    print(f"\n找到 {len(backups)} 個 {backup_type} 備份:")
    for i, backup in enumerate(backups[:10], 1):
        size_mb = backup.stat().st_size / 1024 / 1024
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"  {i}. {backup.name} ({size_mb:.1f} MB, {mtime.strftime('%Y-%m-%d %H:%M')})")

    if len(backups) > 10:
        print(f"  ... 還有 {len(backups) - 10} 個更舊的備份")

    if not interactive:
        # 非互動模式，選擇最新的備份
        return backups[0]

    # 互動模式
    while True:
        try:
            choice = input("\n請選擇要恢復的備份編號（或 q 取消）：")
            if choice.lower() == "q":
                return None

            index = int(choice) - 1
            if 0 <= index < len(backups):
                return backups[index]
            else:
                print("❌ 編號無效，請重新選擇")
        except ValueError:
            print("❌ 請輸入有效的編號")


def confirm_restore(backup_type: str, backup_file: Path) -> bool:
    """確認恢復操作"""
    size_mb = backup_file.stat().st_size / 1024 / 1024

    print(f"\n⚠️  警告：即將恢復 {backup_type} 數據")
    print(f"   備份文件：{backup_file.name}")
    print(f"   文件大小：{size_mb:.1f} MB")
    print(f"\n   此操作將覆蓋現有數據！")
    print(f"   建議先備份當前數據。")

    while True:
        choice = input("\n   確認恢復？(yes/no): ").lower()
        if choice in ["yes", "y"]:
            return True
        elif choice in ["no", "n"]:
            return False
        else:
            print("   請輸入 yes 或 no")


def restore_arangodb(backup_file: Path) -> bool:
    """恢復 ArangoDB"""
    logger.info("starting_arangodb_restore", backup=str(backup_file))

    try:
        # 停止容器
        print("1. 停止 ArangoDB 容器...")
        subprocess.run(["docker", "stop", ARANGODB_CONTAINER], check=True, timeout=60)

        # 解壓備份到臨時目錄
        print("2. 解壓備份文件...")
        temp_dir = project_root / "temp" / "arangodb_restore"
        temp_dir.mkdir(parents=True, exist_ok=True)

        if backup_file.suffix == ".gz":
            subprocess.run(
                ["gunzip", "-c", str(backup_file)],
                open(temp_dir / "backup.dump", "wb"),
                check=True,
                timeout=300,
            )
        else:
            shutil.copy2(backup_file, temp_dir / "backup.dump")

        # 複製到容器
        print("3. 複製備份到容器...")
        subprocess.run(
            [
                "docker",
                "cp",
                str(temp_dir / "backup.dump"),
                f"{ARANGODB_CONTAINER}:/tmp/backup.dump",
            ],
            check=True,
            timeout=60,
        )

        # 啟動容器
        print("4. 啟動 ArangoDB 容器...")
        subprocess.run(["docker", "start", ARANGODB_CONTAINER], check=True, timeout=60)
        subprocess.run(["sleep", "10"], check=True)  # 等待 ArangoDB 啟動

        # 執行恢復
        print("5. 執行數據恢復...")
        cmd = [
            "docker",
            "exec",
            ARANGODB_CONTAINER,
            "arangorestore",
            "--server.endpoint",
            "tcp://localhost:8529",
            "--server.username",
            "root",
            "--server.password",
            os.getenv("ARANGODB_PASSWORD", "ai_box_arangodb_password"),
            "--server.database",
            "ai_box_kg",
            "--input-directory",
            "/tmp",
            "--overwrite",
            "true",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            logger.error(
                "arangodb_restore_failed",
                returncode=result.returncode,
                stderr=result.stderr,
            )
            print(f"\n❌ ArangoDB 恢復失敗:")
            print(result.stderr)
            return False

        # 清理
        print("6. 清理臨時文件...")
        subprocess.run(
            ["docker", "exec", ARANGODB_CONTAINER, "rm", "-rf", "/tmp/backup.dump"],
            timeout=30,
        )
        shutil.rmtree(temp_dir)

        logger.info("arangodb_restore_completed", backup=str(backup_file))
        print("\n✓ ArangoDB 恢復完成")
        return True

    except Exception as e:
        logger.error("arangodb_restore_error", error=str(e), exc_info=True)
        print(f"\n❌ ArangoDB 恢復失敗: {e}")
        return False


def restore_qdrant(backup_file: Path) -> bool:
    """恢復 Qdrant"""
    logger.info("starting_qdrant_restore", backup=str(backup_file))

    try:
        # 停止容器
        print("1. 停止 Qdrant 容器...")
        subprocess.run(["docker", "stop", QDRANT_CONTAINER], check=True, timeout=60)

        # 解壓備份到臨時目錄
        print("2. 解壓備份文件...")
        temp_dir = project_root / "temp" / "qdrant_restore"
        temp_dir.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["tar", "-xzf", str(backup_file), "-C", str(temp_dir)],
            check=True,
            timeout=300,
        )

        # 啟動容器
        print("3. 啟動 Qdrant 容器...")
        subprocess.run(["docker", "start", QDRANT_CONTAINER], check=True, timeout=60)
        subprocess.run(["sleep", "5"], check=True)  # 等待 Qdrant 啟動

        # 複製數據
        print("4. 複製數據到容器...")
        subprocess.run(
            ["docker", "cp", str(temp_dir / "storage"), f"{QDRANT_CONTAINER}:/qdrant/storage"],
            check=True,
            timeout=600,
        )

        # 重啟容器
        print("5. 重啟 Qdrant 容器...")
        subprocess.run(["docker", "restart", QDRANT_CONTAINER], check=True, timeout=60)
        subprocess.run(["sleep", "10"], check=True)

        # 清理
        print("6. 清理臨時文件...")
        shutil.rmtree(temp_dir)

        logger.info("qdrant_restore_completed", backup=str(backup_file))
        print("\n✓ Qdrant 恢復完成")
        return True

    except Exception as e:
        logger.error("qdrant_restore_error", error=str(e), exc_info=True)
        print(f"\n❌ Qdrant 恢復失敗: {e}")
        return False


def restore_seaweedfs(backup_file: Path, container_name: str, service_name: str) -> bool:
    """恢復 SeaWeedFS"""
    logger.info("starting_seaweedfs_restore", container=container_name, backup=str(backup_file))

    try:
        # 停止容器
        print(f"1. 停止 {service_name} 容器...")
        subprocess.run(["docker", "stop", container_name], check=True, timeout=60)

        # 解壓備份到臨時目錄
        print("2. 解壓備份文件...")
        temp_dir = project_root / "temp" / f"{service_name}_restore"
        temp_dir.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["tar", "-xzf", str(backup_file), "-C", str(temp_dir)],
            check=True,
            timeout=300,
        )

        # 啟動容器
        print(f"3. 啟動 {service_name} 容器...")
        subprocess.run(["docker", "start", container_name], check=True, timeout=60)
        subprocess.run(["sleep", "5"], check=True)  # 等待 SeaWeedFS 啟動

        # 複製數據
        print("4. 複製數據到容器...")
        subprocess.run(
            ["docker", "cp", str(temp_dir / "data"), f"{container_name}:/data"],
            check=True,
            timeout=600,
        )

        # 重啟容器
        print(f"5. 重啟 {service_name} 容器...")
        subprocess.run(["docker", "restart", container_name], check=True, timeout=60)
        subprocess.run(["sleep", "5"], check=True)

        # 清理
        print("6. 清理臨時文件...")
        shutil.rmtree(temp_dir)

        logger.info(
            "seaweedfs_restore_completed",
            container=container_name,
            backup=str(backup_file),
        )
        print(f"\n✓ {service_name} 恢復完成")
        return True

    except Exception as e:
        logger.error(
            "seaweedfs_restore_error",
            container=container_name,
            error=str(e),
            exc_info=True,
        )
        print(f"\n❌ {service_name} 恢復失敗: {e}")
        return False


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="AI-Box 數據恢復腳本")
    parser.add_argument(
        "service",
        choices=["all", "arangodb", "qdrant", "seaweedfs_ai_box", "seaweedfs_datalake"],
        help="要恢復的服務",
    )
    parser.add_argument(
        "--backup",
        type=str,
        help="備份文件路徑（如果不指定，會互動式選擇）",
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="跳過確認提示",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("AI-Box 數據恢復工具")
    print("=" * 60)

    results = {}

    # 恢復函數映射
    restore_functions = {
        "arangodb": {
            "func": restore_arangodb,
            "container": ARANGODB_CONTAINER,
            "type": "arangodb",
        },
        "qdrant": {
            "func": restore_qdrant,
            "container": QDRANT_CONTAINER,
            "type": "qdrant",
        },
        "seaweedfs_ai_box": {
            "func": lambda f: restore_seaweedfs(f, SEAWEEDFS_CONTAINER, "SeaWeedFS (AI-Box)"),
            "container": SEAWEEDFS_CONTAINER,
            "type": "seaweedfs_ai_box",
        },
        "seaweedfs_datalake": {
            "func": lambda f: restore_seaweedfs(
                f, SEAWEEDFS_DATALAKE_CONTAINER, "SeaWeedFS (DataLake)"
            ),
            "container": SEAWEEDFS_DATALAKE_CONTAINER,
            "type": "seaweedfs_datalake",
        },
    }

    if args.service == "all":
        # 恢復所有服務
        services = ["arangodb", "qdrant", "seaweedfs_ai_box", "seaweedfs_datalake"]
    else:
        services = [args.service]

    for service in services:
        restore_config = restore_functions[service]

        # 選擇備份
        if args.backup:
            backup_file = Path(args.backup)
            if not backup_file.exists():
                logger.error("backup_file_not_found", path=str(backup_file))
                print(f"\n❌ 備份文件不存在: {backup_file}")
                results[service] = False
                continue
        else:
            backup_file = select_backup(restore_config["type"])
            if not backup_file:
                print(f"\n✗ {service}: 未選擇備份")
                results[service] = False
                continue

        # 確認
        if not args.no_confirm:
            if not confirm_restore(service, backup_file):
                print(f"\n✗ {service}: 已取消")
                results[service] = False
                continue

        # 執行恢復
        results[service] = restore_config["func"](backup_file)

        print("\n" + "-" * 60 + "\n")

    # 匯總結果
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print("=" * 60)
    print(f"恢復完成 ({success_count}/{total_count}):")
    for service, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {service}")
    print("=" * 60)

    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
