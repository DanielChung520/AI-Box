# 代碼功能說明: SeaweedFS Buckets 創建腳本
# 創建日期: 2025-12-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""SeaweedFS Buckets 創建腳本 - 為 AI-Box 和 DataLake 服務創建所有必要的 Buckets"""

import os
import sys
from typing import List, Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def create_bucket(s3_client, bucket_name: str, service_name: str, dry_run: bool = False) -> bool:
    """
    創建一個 Bucket

    Args:
        s3_client: boto3 S3 客戶端
        bucket_name: Bucket 名稱
        service_name: 服務名稱（用於日誌）
        dry_run: 是否為乾運行模式（不實際創建）

    Returns:
        是否成功創建
    """
    try:
        if dry_run:
            print(f"[DRY RUN] Would create bucket: {bucket_name} ({service_name})")
            return True

        # 檢查 Bucket 是否已存在
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✓ Bucket already exists: {bucket_name} ({service_name})")
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                # Bucket 不存在，創建它
                s3_client.create_bucket(Bucket=bucket_name)
                print(f"✓ Created bucket: {bucket_name} ({service_name})")
                return True
            else:
                print(f"✗ Failed to check bucket: {bucket_name} ({service_name}), error: {e}")
                return False
    except Exception as e:
        print(f"✗ Failed to create bucket: {bucket_name} ({service_name}), error: {e}")
        return False


def get_s3_client(endpoint: str, access_key: str, secret_key: str, use_ssl: bool = False):
    """
    創建 S3 客戶端

    Args:
        endpoint: SeaweedFS S3 API 端點
        access_key: S3 訪問密鑰
        secret_key: S3 秘密密鑰
        use_ssl: 是否使用 SSL/TLS

    Returns:
        boto3 S3 客戶端
    """
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        use_ssl=use_ssl,
        config=Config(signature_version="s3v4"),
    )


def create_ai_box_buckets(
    endpoint: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    use_ssl: bool = False,
    dry_run: bool = False,
) -> List[str]:
    """
    為 AI-Box 服務創建所有必要的 Buckets

    Args:
        endpoint: SeaweedFS S3 API 端點（如果不提供，從環境變量讀取）
        access_key: S3 訪問密鑰（如果不提供，從環境變量讀取）
        secret_key: S3 秘密密鑰（如果不提供，從環境變量讀取）
        use_ssl: 是否使用 SSL/TLS
        dry_run: 是否為乾運行模式

    Returns:
        成功創建的 Bucket 名稱列表
    """
    # 從環境變量讀取配置（如果未提供）
    if endpoint is None:
        endpoint = os.getenv("AI_BOX_SEAWEEDFS_S3_ENDPOINT", "http://seaweedfs-ai-box-filer:8333")
    if access_key is None:
        access_key = os.getenv("AI_BOX_SEAWEEDFS_S3_ACCESS_KEY", "")
    if secret_key is None:
        secret_key = os.getenv("AI_BOX_SEAWEEDFS_S3_SECRET_KEY", "")

    if not endpoint or not access_key or not secret_key:
        print("✗ AI-Box SeaweedFS 配置不完整，請設置環境變量或提供參數")
        return []

    # AI-Box 服務的 Buckets
    buckets = [
        "bucket-governance-logs",
        "bucket-version-history",
        "bucket-change-proposals",
        "bucket-datalake-dictionary",
        "bucket-datalake-schema",
        "bucket-ai-box-assets",
    ]

    s3_client = get_s3_client(endpoint, access_key, secret_key, use_ssl)
    created_buckets = []

    print("\n=== 創建 AI-Box 服務 Buckets ===")
    print(f"Endpoint: {endpoint}")
    for bucket_name in buckets:
        if create_bucket(s3_client, bucket_name, "AI-Box", dry_run):
            created_buckets.append(bucket_name)

    return created_buckets


def create_datalake_buckets(
    endpoint: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    use_ssl: bool = False,
    dry_run: bool = False,
) -> List[str]:
    """
    為 DataLake 服務創建所有必要的 Buckets

    Args:
        endpoint: SeaweedFS S3 API 端點（如果不提供，從環境變量讀取）
        access_key: S3 訪問密鑰（如果不提供，從環境變量讀取）
        secret_key: S3 秘密密鑰（如果不提供，從環境變量讀取）
        use_ssl: 是否使用 SSL/TLS
        dry_run: 是否為乾運行模式

    Returns:
        成功創建的 Bucket 名稱列表
    """
    # 從環境變量讀取配置（如果未提供）
    if endpoint is None:
        endpoint = os.getenv(
            "DATALAKE_SEAWEEDFS_S3_ENDPOINT", "http://seaweedfs-datalake-filer:8333"
        )
    if access_key is None:
        access_key = os.getenv("DATALAKE_SEAWEEDFS_S3_ACCESS_KEY", "")
    if secret_key is None:
        secret_key = os.getenv("DATALAKE_SEAWEEDFS_S3_SECRET_KEY", "")

    if not endpoint or not access_key or not secret_key:
        print("✗ DataLake SeaweedFS 配置不完整，請設置環境變量或提供參數")
        return []

    # DataLake 服務的 Buckets
    buckets = [
        "bucket-file-backups",
        "bucket-datalake-assets",
    ]

    s3_client = get_s3_client(endpoint, access_key, secret_key, use_ssl)
    created_buckets = []

    print("\n=== 創建 DataLake 服務 Buckets ===")
    print(f"Endpoint: {endpoint}")
    for bucket_name in buckets:
        if create_bucket(s3_client, bucket_name, "DataLake", dry_run):
            created_buckets.append(bucket_name)

    return created_buckets


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="創建 SeaweedFS Buckets")
    parser.add_argument(
        "--service",
        choices=["ai_box", "datalake", "all"],
        default="all",
        help="要創建 Buckets 的服務（默認：all）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="乾運行模式（不實際創建 Buckets）",
    )
    parser.add_argument(
        "--ai-box-endpoint",
        help="AI-Box SeaweedFS S3 端點（覆蓋環境變量）",
    )
    parser.add_argument(
        "--ai-box-access-key",
        help="AI-Box SeaweedFS S3 訪問密鑰（覆蓋環境變量）",
    )
    parser.add_argument(
        "--ai-box-secret-key",
        help="AI-Box SeaweedFS S3 秘密密鑰（覆蓋環境變量）",
    )
    parser.add_argument(
        "--datalake-endpoint",
        help="DataLake SeaweedFS S3 端點（覆蓋環境變量）",
    )
    parser.add_argument(
        "--datalake-access-key",
        help="DataLake SeaweedFS S3 訪問密鑰（覆蓋環境變量）",
    )
    parser.add_argument(
        "--datalake-secret-key",
        help="DataLake SeaweedFS S3 秘密密鑰（覆蓋環境變量）",
    )

    args = parser.parse_args()

    all_created = []

    if args.service in ("ai_box", "all"):
        created = create_ai_box_buckets(
            endpoint=args.ai_box_endpoint,
            access_key=args.ai_box_access_key,
            secret_key=args.ai_box_secret_key,
            dry_run=args.dry_run,
        )
        all_created.extend(created)

    if args.service in ("datalake", "all"):
        created = create_datalake_buckets(
            endpoint=args.datalake_endpoint,
            access_key=args.datalake_access_key,
            secret_key=args.datalake_secret_key,
            dry_run=args.dry_run,
        )
        all_created.extend(created)

    print("\n=== 總結 ===")
    print(f"成功創建/驗證 {len(all_created)} 個 Buckets")
    if args.dry_run:
        print("（乾運行模式，未實際創建）")


if __name__ == "__main__":
    main()
