# 代碼功能說明: AI-Box 統一備份腳本 - 備份 ArangoDB、Qdrant、SeaWeedFS
# 創建日期: 2026-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-27

"""AI-Box 統一備份腳本

支援備份：
1. ArangoDB - 圖資料庫
2. Qdrant - 向量資料庫
3. SeaWeedFS (AI-Box) - 物件存儲
4. SeaWeedFS (DataLake) - DataLake 物件存儲

備份策略：
- 每小時執行一次全量備份
- 保留最近 7 天的備份
- 自動清理過期備份

備份位置：
- /Users/daniel/GitHub/AI-Box/backups/
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import structlog

logger = structlog.get_logger(__name__)

# 備份配置
BACKUP_ROOT = project_root / "backups"
RETENTION_DAYS = 7
ARANGODB_CONTAINER = "arangodb"
QDRANT_CONTAINER = "qdrant"
SEAWEEDFS_CONTAINER = "seaweedfs"
SEAWEEDFS_DATALAKE_CONTAINER = "seaweedfs-datalake"


def setup_backup_directory(backup_type: str) -> Path:
    """設置備份目錄"""
    backup_dir = BACKUP_ROOT / backup_type / datetime.now().strftime("%Y%m%d")
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def cleanup_old_backups(backup_type: str) -> None:
    """清理過期備份"""
    backup_dir = BACKUP_ROOT / backup_type
    if not backup_dir.exists():
        return

    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)

    for date_dir in backup_dir.iterdir():
        if not date_dir.is_dir():
            continue

        try:
            date_dir_date = datetime.strptime(date_dir.name, "%Y%m%d")
            if date_dir_date < cutoff_date:
                logger.info("cleanup_old_backup", backup_type=backup_type, date=date_dir.name)
                shutil.rmtree(date_dir)
        except ValueError:
            logger.warning("invalid_backup_dir", dir=date_dir.name)


def backup_arangodb() -> bool:
    """備份 ArangoDB"""
    logger.info("starting_arangodb_backup")

    try:
        backup_dir = setup_backup_directory("arangodb")
        timestamp = datetime.now().strftime("%H%M%S")
        backup_file = backup_dir / f"arangodb_backup_{timestamp}.dump.gz"

        # 使用 arangodump 進行備份
        cmd = [
            "docker",
            "exec",
            ARANGODB_CONTAINER,
            "arangodump",
            "--server.endpoint",
            "tcp://localhost:8529",
            "--server.username",
            "root",
            "--server.password",
            os.getenv("ARANGODB_PASSWORD", "ai_box_arangodb_password"),
            "--server.database",
            "ai_box_kg",
            "--output-directory",
            "/tmp/backup",
            "--compress",
            "--overwrite",
            "true",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            logger.error(
                "arangodb_backup_failed",
                returncode=result.returncode,
                stderr=result.stderr,
            )
            return False

        # 從容器複製備份檔案
        docker_cp_cmd = [
            "docker",
            "cp",
            f"{ARANGODB_CONTAINER}:/tmp/backup",
            str(backup_file),
        ]
        subprocess.run(docker_cp_cmd, check=True, timeout=60)

        # 清理容器內的臨時備份
        cleanup_cmd = [
            "docker",
            "exec",
            ARANGODB_CONTAINER,
            "rm",
            "-rf",
            "/tmp/backup",
        ]
        subprocess.run(cleanup_cmd, timeout=30)

        logger.info("arangodb_backup_completed", backup_file=str(backup_file))
        return True

    except Exception as e:
        logger.error("arangodb_backup_error", error=str(e), exc_info=True)
        return False


def backup_qdrant() -> bool:
    """備份 Qdrant"""
    logger.info("starting_qdrant_backup")

    try:
        backup_dir = setup_backup_directory("qdrant")
        timestamp = datetime.now().strftime("%H%M%S")
        backup_file = backup_dir / f"qdrant_backup_{timestamp}.tar.gz"

        # 直接備份 Qdrant 的 data volume
        docker_cp_cmd = [
            "docker",
            "cp",
            f"{QDRANT_CONTAINER}:/qdrant/storage",
            str(backup_dir / "storage"),
        ]
        subprocess.run(docker_cp_cmd, check=True, timeout=600)

        # 壓縮
        subprocess.run(
            [
                "tar",
                "-czf",
                str(backup_file),
                "-C",
                str(backup_dir),
                "storage",
            ],
            check=True,
            timeout=300,
        )

        # 刪除原始備份目錄
        shutil.rmtree(backup_dir / "storage")

        logger.info("qdrant_backup_completed", backup_file=str(backup_file))
        return True

    except Exception as e:
        logger.error("qdrant_backup_error", error=str(e), exc_info=True)
        return False


def backup_seaweedfs(container_name: str, backup_type: str) -> bool:
    """備份 SeaWeedFS"""
    logger.info("starting_seaweedfs_backup", container=container_name, type=backup_type)

    try:
        backup_dir = setup_backup_directory(f"seaweedfs_{backup_type}")
        timestamp = datetime.now().strftime("%H%M%S")
        backup_file = backup_dir / f"seaweedfs_{backup_type}_backup_{timestamp}.tar.gz"

        # 備份 SeaWeedFS 的 data volume
        docker_cp_cmd = [
            "docker",
            "cp",
            f"{container_name}:/data",
            str(backup_dir / "data"),
        ]
        subprocess.run(docker_cp_cmd, check=True, timeout=600)

        # 壓縮
        subprocess.run(
            [
                "tar",
                "-czf",
                str(backup_file),
                "-C",
                str(backup_dir),
                "data",
            ],
            check=True,
            timeout=300,
        )

        # 刪除原始備份目錄
        shutil.rmtree(backup_dir / "data")

        logger.info(
            "seaweedfs_backup_completed",
            container=container_name,
            backup_file=str(backup_file),
        )
        return True

    except Exception as e:
        logger.error(
            "seaweedfs_backup_error",
            container=container_name,
            type=backup_type,
            error=str(e),
            exc_info=True,
        )
        return False


def backup_all() -> dict[str, bool]:
    """備份所有服務"""
    logger.info("starting_all_backups")

    results = {
        "arangodb": False,
        "qdrant": False,
        "seaweedfs_ai_box": False,
        "seaweedfs_datalake": False,
    }

    # ArangoDB
    try:
        result = subprocess.run(
            ["docker", "inspect", ARANGODB_CONTAINER],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            results["arangodb"] = backup_arangodb()
        else:
            logger.warning("arangodb_container_not_found")
    except Exception as e:
        logger.error("arangodb_backup_check_error", error=str(e))

    # Qdrant
    try:
        result = subprocess.run(
            ["docker", "inspect", QDRANT_CONTAINER],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            results["qdrant"] = backup_qdrant()
        else:
            logger.warning("qdrant_container_not_found")
    except Exception as e:
        logger.error("qdrant_backup_check_error", error=str(e))

    # SeaWeedFS (AI-Box)
    try:
        result = subprocess.run(
            ["docker", "inspect", SEAWEEDFS_CONTAINER],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            results["seaweedfs_ai_box"] = backup_seaweedfs(SEAWEEDFS_CONTAINER, "ai_box")
        else:
            logger.warning("seaweedfs_container_not_found")
    except Exception as e:
        logger.error("seaweedfs_backup_check_error", error=str(e))

    # SeaWeedFS (DataLake)
    try:
        result = subprocess.run(
            ["docker", "inspect", SEAWEEDFS_DATALAKE_CONTAINER],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            results["seaweedfs_datalake"] = backup_seaweedfs(
                SEAWEEDFS_DATALAKE_CONTAINER, "datalake"
            )
        else:
            logger.warning("seaweedfs_datalake_container_not_found")
    except Exception as e:
        logger.error("seaweedfs_datalake_backup_check_error", error=str(e))

    # 清理過期備份
    for service in ["arangodb", "qdrant", "seaweedfs_ai_box", "seaweedfs_datalake"]:
        try:
            cleanup_old_backups(service)
        except Exception as e:
            logger.error("cleanup_error", service=service, error=str(e))

    return results


def main() -> int:
    """主函數"""
    logger.info("backup_starting", timestamp=datetime.now().isoformat())

    results = backup_all()

    # 匯總結果
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    logger.info(
        "backup_completed",
        success=success_count,
        total=total_count,
        results=results,
    )

    # 輸出摘要
    print(f"\n備份完成 ({success_count}/{total_count}):")
    for service, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {service}")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
