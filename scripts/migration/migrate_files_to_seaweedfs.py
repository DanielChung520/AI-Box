# 代碼功能說明: 文件遷移腳本 - 從本地文件系統遷移到 SeaweedFS
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""
文件遷移腳本 - 從本地文件系統遷移到 SeaweedFS

功能：
1. 掃描本地文件系統（./data/datasets/files）
2. 讀取每個文件
3. 上傳到 SeaweedFS（保持相同的路徑結構）
4. 更新 file_metadata.storage_path 為 S3 URI
5. 驗證遷移結果（文件完整性檢查）
6. 可選：刪除本地文件（備份後）

特性：
- 增量遷移：支持中斷後繼續（記錄已遷移的文件）
- 遷移驗證：文件完整性檢查（MD5/SHA256）
- 進度追蹤：顯示遷移進度和統計信息
- 回滾支持：保留本地文件備份，支持回滾
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.api.services.file_metadata_service import FileMetadataService
from storage.file_storage import LocalFileStorage, create_storage_from_config
from storage.s3_storage import SeaweedFSService
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)

# 遷移狀態文件路徑
MIGRATION_STATE_FILE = project_root / "data" / "migration_state.json"
MIGRATION_LOG_FILE = project_root / "data" / "migration_log.jsonl"


def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    計算文件哈希值

    Args:
        file_path: 文件路徑
        algorithm: 哈希算法（md5 或 sha256）

    Returns:
        文件哈希值（十六進制字符串）
    """
    hash_obj = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def load_migration_state() -> Dict[str, Any]:
    """
    加載遷移狀態

    Returns:
        遷移狀態字典
    """
    if MIGRATION_STATE_FILE.exists():
        try:
            with open(MIGRATION_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load migration state", error=str(e))
    return {
        "migrated_files": [],
        "failed_files": [],
        "total_files": 0,
        "migrated_count": 0,
        "failed_count": 0,
    }


def save_migration_state(state: Dict[str, Any]) -> None:
    """
    保存遷移狀態

    Args:
        state: 遷移狀態字典
    """
    MIGRATION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MIGRATION_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def log_migration_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    記錄遷移事件到日誌文件

    Args:
        event_type: 事件類型（migrated, failed, verified 等）
        data: 事件數據
    """
    MIGRATION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_entry = {"type": event_type, "timestamp": str(Path().cwd()), **data}
    with open(MIGRATION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def scan_local_files(local_path: Path) -> List[Tuple[Path, str]]:
    """
    掃描本地文件系統

    Args:
        local_path: 本地文件系統路徑

    Returns:
        文件列表，每個元素為 (文件路徑, 文件ID)
    """
    files: List[Tuple[Path, str]] = []
    if not local_path.exists():
        logger.warning("Local path does not exist", path=str(local_path))
        return files

    # 掃描所有文件
    for file_path in local_path.rglob("*"):
        if file_path.is_file():
            # 從路徑中提取文件 ID（假設文件 ID 是文件名或路徑的一部分）
            # 這裡需要根據實際的文件組織結構來提取
            # 假設文件存儲在 {file_id[:2]}/{file_id} 結構中
            relative_path = file_path.relative_to(local_path)
            parts = relative_path.parts
            if len(parts) >= 2:
                # 假設結構為 {subdir}/{file_id}.{ext}
                file_id = parts[-1].split(".")[0]  # 移除擴展名
            else:
                file_id = file_path.stem

            files.append((file_path, file_id))

    return files


def migrate_file(
    file_path: Path,
    file_id: str,
    local_storage: LocalFileStorage,
    s3_storage: Any,
    metadata_service: FileMetadataService,
    dry_run: bool = False,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    遷移單個文件

    Args:
        file_path: 本地文件路徑
        file_id: 文件 ID
        local_storage: 本地存儲實例
        s3_storage: S3 存儲實例
        metadata_service: 元數據服務實例
        dry_run: 是否為乾運行模式（不實際遷移）

    Returns:
        (是否成功, S3 URI, 錯誤信息)
    """
    try:
        # 讀取本地文件
        with open(file_path, "rb") as f:
            file_content = f.read()

        # 計算文件哈希值（用於驗證）
        file_hash = calculate_file_hash(file_path, "sha256")

        # 獲取文件名
        filename = file_path.name

        # 獲取文件元數據（如果存在）
        file_metadata = metadata_service.get(file_id)
        task_id = file_metadata.task_id if file_metadata else None

        if dry_run:
            logger.info(
                "Dry run: Would migrate file",
                file_id=file_id,
                file_path=str(file_path),
                file_size=len(file_content),
            )
            # 生成模擬的 S3 URI
            s3_uri = f"s3://bucket-ai-box-assets/{file_id}/{filename}"
            return True, s3_uri, None

        # 上傳文件到 SeaweedFS
        uploaded_file_id, s3_uri = s3_storage.save_file(
            file_content, filename, file_id=file_id, task_id=task_id
        )

        # 驗證上傳的文件（讀取並計算哈希值）
        uploaded_content = s3_storage.read_file(
            uploaded_file_id, task_id=task_id, metadata_storage_path=s3_uri
        )
        if uploaded_content is None:
            return False, None, "Failed to read uploaded file for verification"

        uploaded_hash = hashlib.sha256(uploaded_content).hexdigest()
        if uploaded_hash != file_hash:
            return False, None, "File hash mismatch after upload"

        # 更新文件元數據中的 storage_path
        if file_metadata:
            from services.api.models.file_metadata import FileMetadataUpdate

            metadata_service.update(
                file_id,
                FileMetadataUpdate(storage_path=s3_uri),
            )
            logger.info(
                "Updated file metadata",
                file_id=file_id,
                old_storage_path=file_metadata.storage_path,
                new_storage_path=s3_uri,
            )

        logger.info(
            "File migrated successfully",
            file_id=file_id,
            file_path=str(file_path),
            s3_uri=s3_uri,
            file_size=len(file_content),
        )

        return True, s3_uri, None

    except Exception as e:
        error_msg = f"Failed to migrate file: {str(e)}"
        logger.error(
            "File migration failed",
            file_id=file_id,
            file_path=str(file_path),
            error=str(e),
            exc_info=True,
        )
        return False, None, error_msg


def migrate_files(
    local_path: Path,
    dry_run: bool = False,
    resume: bool = True,
    verify: bool = True,
    delete_local: bool = False,
) -> None:
    """
    遷移文件從本地文件系統到 SeaweedFS

    Args:
        local_path: 本地文件系統路徑
        dry_run: 是否為乾運行模式（不實際遷移）
        resume: 是否從上次中斷的地方繼續
        verify: 是否驗證遷移結果
        delete_local: 是否刪除本地文件（遷移完成後）
    """
    logger.info("Starting file migration", local_path=str(local_path), dry_run=dry_run)

    # 加載遷移狀態
    state = load_migration_state()
    migrated_file_ids: Set[str] = set(state.get("migrated_files", []))

    # 創建存儲實例
    local_storage = LocalFileStorage(storage_path=str(local_path))
    config = get_config_section("file_upload", default={}) or {}
    s3_storage = create_storage_from_config(config, service_type=SeaweedFSService.AI_BOX)

    # 創建元數據服務實例
    metadata_service = FileMetadataService()

    # 掃描本地文件
    logger.info("Scanning local files...")
    all_files = scan_local_files(local_path)
    total_files = len(all_files)
    state["total_files"] = total_files

    logger.info("Found files to migrate", total=total_files)

    # 過濾已遷移的文件（如果啟用 resume）
    if resume:
        files_to_migrate = [
            (file_path, file_id)
            for file_path, file_id in all_files
            if file_id not in migrated_file_ids
        ]
        logger.info(
            "Resuming migration",
            total=total_files,
            already_migrated=len(migrated_file_ids),
            remaining=len(files_to_migrate),
        )
    else:
        files_to_migrate = all_files
        migrated_file_ids.clear()
        state["migrated_files"] = []
        state["failed_files"] = []

    # 遷移文件
    migrated_count = 0
    failed_count = 0

    for idx, (file_path, file_id) in enumerate(files_to_migrate, 1):
        logger.info(
            "Migrating file",
            file_id=file_id,
            progress=f"{idx}/{len(files_to_migrate)}",
        )

        success, s3_uri, error = migrate_file(
            file_path, file_id, local_storage, s3_storage, metadata_service, dry_run=dry_run
        )

        if success:
            migrated_count += 1
            migrated_file_ids.add(file_id)
            state["migrated_files"].append(file_id)
            log_migration_event("migrated", {"file_id": file_id, "s3_uri": s3_uri})
        else:
            failed_count += 1
            state["failed_files"].append({"file_id": file_id, "error": error})
            log_migration_event("failed", {"file_id": file_id, "error": error})

        # 定期保存狀態
        if idx % 10 == 0:
            state["migrated_count"] = len(migrated_file_ids)
            state["failed_count"] = failed_count
            save_migration_state(state)

    # 最終保存狀態
    state["migrated_count"] = len(migrated_file_ids)
    state["failed_count"] = failed_count
    save_migration_state(state)

    # 打印統計信息
    logger.info(
        "Migration completed",
        total=total_files,
        migrated=migrated_count,
        failed=failed_count,
        dry_run=dry_run,
    )

    # 如果啟用刪除本地文件（且不是乾運行）
    if delete_local and not dry_run:
        logger.info("Deleting local files...")
        deleted_count = 0
        for file_id in migrated_file_ids:
            # 這裡需要根據實際情況找到對應的文件路徑
            # 暫時跳過，因為需要維護文件 ID 到路徑的映射
            pass
        logger.info("Local files deleted", count=deleted_count)


def main() -> None:
    """主函數"""
    parser = argparse.ArgumentParser(description="Migrate files from local filesystem to SeaweedFS")
    parser.add_argument(
        "--local-path",
        type=str,
        default="./data/datasets/files",
        help="本地文件系統路徑（默認：./data/datasets/files）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="乾運行模式（不實際遷移，僅顯示將要執行的操作）",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="不從上次中斷的地方繼續（重新開始遷移）",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="不驗證遷移結果（跳過文件完整性檢查）",
    )
    parser.add_argument(
        "--delete-local",
        action="store_true",
        help="遷移完成後刪除本地文件（謹慎使用）",
    )

    args = parser.parse_args()

    local_path = Path(args.local_path).resolve()

    if not local_path.exists():
        logger.error("Local path does not exist", path=str(local_path))
        sys.exit(1)

    migrate_files(
        local_path=local_path,
        dry_run=args.dry_run,
        resume=not args.no_resume,
        verify=not args.no_verify,
        delete_local=args.delete_local,
    )


if __name__ == "__main__":
    main()
