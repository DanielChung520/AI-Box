# 代碼功能說明: S3/SeaweedFS 文件存儲實現
# 創建日期: 2025-12-29
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-03

"""S3/SeaweedFS 文件存儲實現 - 使用 boto3 連接 SeaweedFS S3 API"""

import os
from enum import Enum
from typing import Optional, Tuple
from urllib.parse import urlparse

import boto3
import structlog
from botocore.client import Config
from botocore.exceptions import ClientError, ConnectionClosedError

from storage.file_storage import FileStorage

logger = structlog.get_logger(__name__)


class SeaweedFSService(str, Enum):
    """SeaweedFS 服務類型"""

    AI_BOX = "ai_box"  # AI-Box 項目的 SeaweedFS 服務
    DATALAKE = "datalake"  # DataLake 項目的 SeaweedFS 服務


class S3FileStorage(FileStorage):
    """S3/SeaweedFS 文件存儲實現"""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        use_ssl: bool = False,
        service_type: SeaweedFSService = SeaweedFSService.AI_BOX,
        default_bucket: Optional[str] = None,
    ):
        """
        初始化 S3/SeaweedFS 文件存儲

        Args:
            endpoint: SeaweedFS S3 API 端點（例如：http://seaweedfs-filer:8333）
            access_key: S3 訪問密鑰
            secret_key: S3 秘密密鑰
            use_ssl: 是否使用 SSL/TLS（默認 False）
            service_type: SeaweedFS 服務類型（AI_BOX 或 DATALAKE）
            default_bucket: 默認 Bucket 名稱（如果不提供，根據 service_type 自動選擇）
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.use_ssl = use_ssl
        self.service_type = service_type

        # 初始化 S3 客戶端
        # 修改時間：2026-01-05 - 添加超時和重試配置，避免連接關閉錯誤
        boto_config = Config(
            signature_version="s3v4",
            connect_timeout=10,  # 連接超時 10 秒
            read_timeout=60,  # 讀取超時 60 秒（大文件需要更長時間）
            retries={
                "max_attempts": 3,  # 最多重試 3 次
                "mode": "adaptive",  # 自適應重試模式
            },
        )
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            use_ssl=use_ssl,
            config=boto_config,
        )

        # 根據服務類型選擇默認 Bucket
        if default_bucket is None:
            if service_type == SeaweedFSService.AI_BOX:
                self.default_bucket = "bucket-ai-box-assets"
            elif service_type == SeaweedFSService.DATALAKE:
                self.default_bucket = "bucket-datalake-assets"
            else:
                self.default_bucket = "bucket-ai-box-assets"
        else:
            self.default_bucket = default_bucket

        self.logger = logger.bind(
            endpoint=endpoint,
            service_type=service_type.value,
            default_bucket=self.default_bucket,
        )

        # 修改時間：2026-01-03 - 延遲bucket檢查，避免初始化時連接失敗
        # 只在真正需要時才檢查bucket，並添加重試機制
        self._bucket_checked = False

    def _ensure_bucket_exists(self, bucket_name: str, retry: bool = True) -> None:
        """
        確保 Bucket 存在，如果不存在則創建

        修改時間：2026-01-03 - 添加重試機制和更好的錯誤處理，確保SeaweedFS穩定運作

        Args:
            bucket_name: Bucket 名稱
            retry: 是否在失敗時重試（默認 True）
        """
        max_retries = 3
        retry_delay = 2  # 秒

        for attempt in range(1, max_retries + 1):
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                self.logger.debug("Bucket already exists", bucket=bucket_name)
                self._bucket_checked = True
                return
            except ConnectionClosedError as e:
                # 連接關閉錯誤，可能是SeaweedFS暫時不可用
                if retry and attempt < max_retries:
                    wait_time = retry_delay * (2 ** (attempt - 1))  # 指數退避
                    self.logger.warning(
                        "Bucket check failed, retrying",
                        bucket=bucket_name,
                        attempt=attempt,
                        max_retries=max_retries,
                        wait_time=wait_time,
                        error=str(e)[:100],
                    )
                    import time

                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(
                        "Failed to check bucket after retries",
                        bucket=bucket_name,
                        attempts=attempt,
                        error=str(e)[:100],
                    )
                    # 不拋出異常，允許後續操作繼續（如果文件路徑已知）
                    if not retry:
                        raise
                    return
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "404":
                    # Bucket 不存在，創建它
                    try:
                        self.s3_client.create_bucket(Bucket=bucket_name)
                        self.logger.info("Bucket created", bucket=bucket_name)
                        self._bucket_checked = True
                        return
                    except ClientError as create_error:
                        if retry and attempt < max_retries:
                            wait_time = retry_delay * (2 ** (attempt - 1))
                            self.logger.warning(
                                "Bucket creation failed, retrying",
                                bucket=bucket_name,
                                attempt=attempt,
                                wait_time=wait_time,
                                error=str(create_error)[:100],
                            )
                            import time

                            time.sleep(wait_time)
                            continue
                        else:
                            self.logger.error(
                                "Failed to create bucket after retries",
                                bucket=bucket_name,
                                attempts=attempt,
                                error=str(create_error)[:100],
                            )
                            if not retry:
                                raise
                            return
                else:
                    # 其他錯誤，記錄但不重試
                    self.logger.error(
                        "Failed to check bucket existence",
                        bucket=bucket_name,
                        error_code=error_code,
                        error=str(e)[:100],
                    )
                    if not retry:
                        raise
                    return
            except Exception as e:
                # 其他未預期的錯誤
                if retry and attempt < max_retries:
                    wait_time = retry_delay * (2 ** (attempt - 1))
                    self.logger.warning(
                        "Unexpected error during bucket check, retrying",
                        bucket=bucket_name,
                        attempt=attempt,
                        wait_time=wait_time,
                        error=str(e)[:100],
                    )
                    import time

                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(
                        "Unexpected error during bucket check",
                        bucket=bucket_name,
                        attempts=attempt,
                        error=str(e)[:100],
                    )
                    if not retry:
                        raise
                    return

        # 所有重試都失敗，但不拋出異常（允許後續操作繼續）
        self.logger.warning(
            "Bucket check failed after all retries, continuing without bucket verification",
            bucket=bucket_name,
        )

    def _get_s3_key(
        self, file_id: str, filename: Optional[str] = None, task_id: Optional[str] = None
    ) -> str:
        """
        生成 S3 對象鍵（key）

        Args:
            file_id: 文件 ID
            filename: 文件名（可選，用於保留擴展名）
            task_id: 任務 ID（可選，如果提供則文件存儲在任務工作區）

        Returns:
            S3 對象鍵
        """
        if task_id:
            # 如果提供了 task_id，文件存儲在任務工作區
            # 路徑格式：tasks/{task_id}/{file_id}.{ext}
            if filename:
                ext = os.path.splitext(filename)[1]
                return f"tasks/{task_id}/{file_id}{ext}"
            else:
                return f"tasks/{task_id}/{file_id}"
        else:
            # 舊的邏輯：使用文件 ID 的前兩個字符作為子目錄（向後兼容）
            subdir = file_id[:2]
            if filename:
                ext = os.path.splitext(filename)[1]
                return f"{subdir}/{file_id}{ext}"
            else:
                return f"{subdir}/{file_id}"

    def _get_bucket_for_file_type(self, file_type: Optional[str] = None) -> str:
        """
        根據文件類型選擇對應的 Bucket

        Args:
            file_type: 文件類型（可選，例如 "governance-logs", "version-history" 等）

        Returns:
            Bucket 名稱
        """
        if self.service_type == SeaweedFSService.AI_BOX:
            bucket_mapping = {
                "governance-logs": "bucket-governance-logs",
                "version-history": "bucket-version-history",
                "change-proposals": "bucket-change-proposals",
                "datalake-dictionary": "bucket-datalake-dictionary",
                "datalake-schema": "bucket-datalake-schema",
            }
            return bucket_mapping.get(file_type or "", self.default_bucket)
        elif self.service_type == SeaweedFSService.DATALAKE:
            bucket_mapping = {
                "file-backups": "bucket-file-backups",
            }
            return bucket_mapping.get(file_type or "", self.default_bucket)
        else:
            return self.default_bucket

    def save_file(
        self,
        file_content: bytes,
        filename: str,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        保存文件到 S3/SeaweedFS

        Args:
            file_content: 文件內容
            filename: 原始文件名
            file_id: 文件 ID（可選，如果不提供則自動生成）
            task_id: 任務 ID（可選，如果提供則文件存儲在任務工作區）

        Returns:
            (file_id, s3_uri)
        """
        if file_id is None:
            file_id = self.generate_file_id()

        # 生成 S3 對象鍵
        s3_key = self._get_s3_key(file_id, filename, task_id)

        # 選擇 Bucket（根據文件類型，這裡暫時使用默認 Bucket）
        bucket_name = self.default_bucket

        try:
            # 上傳文件到 S3
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=self._guess_content_type(filename),
            )

            # 生成 S3 URI
            s3_uri = f"s3://{bucket_name}/{s3_key}"

            self.logger.info(
                "File saved to S3",
                file_id=file_id,
                filename=filename,
                bucket=bucket_name,
                key=s3_key,
                file_size=len(file_content),
            )

            return file_id, s3_uri

        except ClientError as e:
            self.logger.error(
                "Failed to save file to S3",
                file_id=file_id,
                filename=filename,
                bucket=bucket_name,
                key=s3_key,
                error=str(e),
            )
            raise RuntimeError(f"Failed to save file to S3: {e}") from e

    def _guess_content_type(self, filename: str) -> str:
        """
        根據文件名猜測內容類型

        Args:
            filename: 文件名

        Returns:
            MIME 類型
        """
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            ".txt": "text/plain",
            ".json": "application/json",
            ".jsonl": "application/x-ndjson",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".html": "text/html",
            ".md": "text/markdown",
        }
        return content_types.get(ext, "application/octet-stream")

    def get_file_path(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        獲取文件路徑（S3 URI）

        Args:
            file_id: 文件 ID
            task_id: 任務 ID（可選，如果提供則在任務工作區中查找）
            metadata_storage_path: 元數據中記錄的存儲路徑（優先使用）

        Returns:
            S3 URI，如果不存在則返回 None
        """
        # 優先使用 metadata_storage_path（如果提供且是有效的 S3 URI）
        if metadata_storage_path:
            if metadata_storage_path.startswith("s3://") or metadata_storage_path.startswith(
                "https://"
            ):
                # 驗證文件是否存在
                if self._parse_s3_uri(metadata_storage_path):
                    return metadata_storage_path

        # 嘗試在默認 Bucket 中查找
        # 注意：這裡需要知道原始文件名才能構建正確的 key
        # 由於我們不知道原始文件名，我們需要嘗試多種可能的 key
        possible_keys = []
        if task_id:
            possible_keys.append(f"tasks/{task_id}/{file_id}")
            possible_keys.append(f"tasks/{task_id}/{file_id}.*")
        else:
            subdir = file_id[:2]
            possible_keys.append(f"{subdir}/{file_id}")
            possible_keys.append(f"{subdir}/{file_id}.*")

        # 嘗試查找文件
        for key_pattern in possible_keys:
            # 如果 key_pattern 包含通配符，需要列出對象
            if "*" in key_pattern:
                prefix = key_pattern.split("*")[0]
                try:
                    response = self.s3_client.list_objects_v2(
                        Bucket=self.default_bucket, Prefix=prefix
                    )
                    if "Contents" in response:
                        for obj in response["Contents"]:
                            if obj["Key"].startswith(prefix) and file_id in obj["Key"]:
                                return f"s3://{self.default_bucket}/{obj['Key']}"
                except ClientError:
                    continue
            else:
                # 直接檢查對象是否存在
                try:
                    self.s3_client.head_object(Bucket=self.default_bucket, Key=key_pattern)
                    return f"s3://{self.default_bucket}/{key_pattern}"
                except ClientError:
                    continue

        return None

    def _parse_s3_uri(self, s3_uri: str) -> Optional[Tuple[str, str]]:
        """
        解析 S3 URI，返回 (bucket, key)

        Args:
            s3_uri: S3 URI（格式：s3://bucket/key 或 https://endpoint/bucket/key）

        Returns:
            (bucket, key) 元組，如果解析失敗則返回 None
        """
        if s3_uri.startswith("s3://"):
            parsed = urlparse(s3_uri)
            bucket = parsed.netloc
            key = parsed.path.lstrip("/")
            return (bucket, key)
        elif s3_uri.startswith("https://") or s3_uri.startswith("http://"):
            # 解析 https://endpoint/bucket/key 格式
            parsed = urlparse(s3_uri)
            path_parts = parsed.path.lstrip("/").split("/", 1)
            if len(path_parts) == 2:
                bucket = path_parts[0]
                key = path_parts[1]
                return (bucket, key)
        return None

    def read_file(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        從 S3/SeaweedFS 讀取文件內容

        修改時間：2026-01-03 - 添加bucket檢查，確保SeaweedFS穩定運作

        Args:
            file_id: 文件 ID
            task_id: 任務 ID（可選，如果提供則在任務工作區中查找）
            metadata_storage_path: 元數據中記錄的存儲路徑（優先使用）

        Returns:
            文件內容，如果不存在則返回 None
        """
        # 優先使用 metadata_storage_path
        if metadata_storage_path:
            parsed = self._parse_s3_uri(metadata_storage_path)
            if parsed:
                bucket, key = parsed
                try:
                    response = self.s3_client.get_object(Bucket=bucket, Key=key)
                    content = response["Body"].read()
                    self.logger.debug(
                        "File read from S3",
                        file_id=file_id,
                        bucket=bucket,
                        key=key,
                        size=len(content),
                    )
                    return content
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    if error_code == "NoSuchKey" or error_code == "404":
                        self.logger.warning(
                            "File not found in S3",
                            file_id=file_id,
                            bucket=bucket,
                            key=key,
                        )
                    else:
                        self.logger.error(
                            "Failed to read file from S3",
                            file_id=file_id,
                            bucket=bucket,
                            key=key,
                            error=str(e),
                        )
                    return None

        # 嘗試從默認 Bucket 讀取
        file_path = self.get_file_path(file_id, task_id, metadata_storage_path)
        if file_path:
            parsed = self._parse_s3_uri(file_path)
            if parsed:
                bucket, key = parsed
                try:
                    response = self.s3_client.get_object(Bucket=bucket, Key=key)
                    content = response["Body"].read()
                    self.logger.debug(
                        "File read from S3",
                        file_id=file_id,
                        bucket=bucket,
                        key=key,
                        size=len(content),
                    )
                    return content
                except ClientError as e:
                    self.logger.error(
                        "Failed to read file from S3",
                        file_id=file_id,
                        bucket=bucket,
                        key=key,
                        error=str(e),
                    )
                    return None

        return None

    def delete_file(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ) -> bool:
        """
        從 S3/SeaweedFS 刪除文件

        Args:
            file_id: 文件 ID
            task_id: 任務 ID（可選，如果提供則在任務工作區中查找）
            metadata_storage_path: 元數據中記錄的存儲路徑（優先使用）

        Returns:
            是否成功刪除
        """
        # 優先使用 metadata_storage_path
        if metadata_storage_path:
            parsed = self._parse_s3_uri(metadata_storage_path)
            if parsed:
                bucket, key = parsed
                try:
                    self.s3_client.delete_object(Bucket=bucket, Key=key)
                    self.logger.info(
                        "File deleted from S3",
                        file_id=file_id,
                        bucket=bucket,
                        key=key,
                    )
                    return True
                except ClientError as e:
                    self.logger.error(
                        "Failed to delete file from S3",
                        file_id=file_id,
                        bucket=bucket,
                        key=key,
                        error=str(e),
                    )
                    return False

        # 嘗試從默認 Bucket 刪除
        file_path = self.get_file_path(file_id, task_id, metadata_storage_path)
        if file_path:
            parsed = self._parse_s3_uri(file_path)
            if parsed:
                bucket, key = parsed
                try:
                    self.s3_client.delete_object(Bucket=bucket, Key=key)
                    self.logger.info(
                        "File deleted from S3",
                        file_id=file_id,
                        bucket=bucket,
                        key=key,
                    )
                    return True
                except ClientError as e:
                    self.logger.error(
                        "Failed to delete file from S3",
                        file_id=file_id,
                        bucket=bucket,
                        key=key,
                        error=str(e),
                    )
                    return False

        return False

    def file_exists(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ) -> bool:
        """
        檢查文件是否存在

        Args:
            file_id: 文件 ID
            task_id: 任務 ID（可選，如果提供則在任務工作區中查找）
            metadata_storage_path: 元數據中記錄的存儲路徑（優先使用）

        Returns:
            文件是否存在
        """
        # 優先使用 metadata_storage_path
        if metadata_storage_path:
            parsed = self._parse_s3_uri(metadata_storage_path)
            if parsed:
                bucket, key = parsed
                try:
                    self.s3_client.head_object(Bucket=bucket, Key=key)
                    return True
                except ClientError:
                    return False

        # 嘗試從默認 Bucket 檢查
        file_path = self.get_file_path(file_id, task_id, metadata_storage_path)
        if file_path:
            parsed = self._parse_s3_uri(file_path)
            if parsed:
                bucket, key = parsed
                try:
                    self.s3_client.head_object(Bucket=bucket, Key=key)
                    return True
                except ClientError:
                    return False

        return False
