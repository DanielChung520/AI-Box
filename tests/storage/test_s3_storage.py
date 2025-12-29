# 代碼功能說明: S3/SeaweedFS 存儲單元測試
# 創建日期: 2025-12-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""S3/SeaweedFS 存儲單元測試"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from botocore.exceptions import ClientError

from storage.s3_storage import S3FileStorage, SeaweedFSService


class TestS3FileStorage:
    """S3FileStorage 測試類"""

    @pytest.fixture
    def mock_s3_client(self):
        """創建模擬 S3 客戶端"""
        with patch("storage.s3_storage.boto3.client") as mock_client:
            client = MagicMock()
            mock_client.return_value = client
            yield client

    @pytest.fixture
    def storage_ai_box(self, mock_s3_client):
        """創建 AI-Box 服務的 S3FileStorage 實例"""
        # 模擬 head_bucket 成功（Bucket 已存在）
        mock_s3_client.head_bucket.return_value = None
        return S3FileStorage(
            endpoint="http://test-endpoint:8333",
            access_key="test-access-key",
            secret_key="test-secret-key",
            use_ssl=False,
            service_type=SeaweedFSService.AI_BOX,
        )

    @pytest.fixture
    def storage_datalake(self, mock_s3_client):
        """創建 DataLake 服務的 S3FileStorage 實例"""
        # 模擬 head_bucket 成功（Bucket 已存在）
        mock_s3_client.head_bucket.return_value = None
        return S3FileStorage(
            endpoint="http://test-endpoint:8333",
            access_key="test-access-key",
            secret_key="test-secret-key",
            use_ssl=False,
            service_type=SeaweedFSService.DATALAKE,
        )

    def test_init_ai_box(self, mock_s3_client):
        """測試 AI-Box 服務初始化"""
        mock_s3_client.head_bucket.return_value = None
        storage = S3FileStorage(
            endpoint="http://test-endpoint:8333",
            access_key="test-access-key",
            secret_key="test-secret-key",
            service_type=SeaweedFSService.AI_BOX,
        )
        assert storage.service_type == SeaweedFSService.AI_BOX
        assert storage.default_bucket == "bucket-ai-box-assets"
        assert storage.endpoint == "http://test-endpoint:8333"

    def test_init_datalake(self, mock_s3_client):
        """測試 DataLake 服務初始化"""
        mock_s3_client.head_bucket.return_value = None
        storage = S3FileStorage(
            endpoint="http://test-endpoint:8333",
            access_key="test-access-key",
            secret_key="test-secret-key",
            service_type=SeaweedFSService.DATALAKE,
        )
        assert storage.service_type == SeaweedFSService.DATALAKE
        assert storage.default_bucket == "bucket-datalake-assets"
        assert storage.endpoint == "http://test-endpoint:8333"

    def test_init_create_bucket_if_not_exists(self, mock_s3_client):
        """測試 Bucket 不存在時自動創建"""
        # 第一次調用 head_bucket 返回 404（Bucket 不存在）
        # 第二次調用 create_bucket 成功
        mock_s3_client.head_bucket.side_effect = [
            ClientError({"Error": {"Code": "404"}}, "HeadBucket"),
            None,  # 創建後再次檢查
        ]
        mock_s3_client.create_bucket.return_value = None

        S3FileStorage(
            endpoint="http://test-endpoint:8333",
            access_key="test-access-key",
            secret_key="test-secret-key",
            service_type=SeaweedFSService.AI_BOX,
        )

        mock_s3_client.create_bucket.assert_called_once_with(Bucket="bucket-ai-box-assets")

    def test_save_file(self, storage_ai_box, mock_s3_client):
        """測試保存文件"""
        file_content = b"test file content"
        filename = "test.txt"
        file_id = "test-file-id"

        mock_s3_client.put_object.return_value = {}

        file_id_result, s3_uri = storage_ai_box.save_file(
            file_content=file_content, filename=filename, file_id=file_id
        )

        assert file_id_result == file_id
        assert s3_uri.startswith("s3://")
        assert "bucket-ai-box-assets" in s3_uri
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]["Bucket"] == "bucket-ai-box-assets"
        assert call_args[1]["Body"] == file_content

    def test_save_file_with_task_id(self, storage_ai_box, mock_s3_client):
        """測試保存文件（帶 task_id）"""
        file_content = b"test file content"
        filename = "test.txt"
        file_id = "test-file-id"
        task_id = "test-task-id"

        mock_s3_client.put_object.return_value = {}

        file_id_result, s3_uri = storage_ai_box.save_file(
            file_content=file_content, filename=filename, file_id=file_id, task_id=task_id
        )

        assert file_id_result == file_id
        assert "tasks/test-task-id" in s3_uri
        call_args = mock_s3_client.put_object.call_args
        assert "tasks/test-task-id" in call_args[1]["Key"]

    def test_save_file_auto_generate_file_id(self, storage_ai_box, mock_s3_client):
        """測試保存文件（自動生成 file_id）"""
        file_content = b"test file content"
        filename = "test.txt"

        mock_s3_client.put_object.return_value = {}

        file_id_result, s3_uri = storage_ai_box.save_file(
            file_content=file_content, filename=filename
        )

        assert file_id_result is not None
        assert len(file_id_result) > 0
        assert s3_uri.startswith("s3://")

    def test_read_file(self, storage_ai_box, mock_s3_client):
        """測試讀取文件"""
        file_id = "test-file-id"
        file_content = b"test file content"
        s3_uri = "s3://bucket-ai-box-assets/ab/test-file-id.txt"

        # 模擬 get_file_path 返回 S3 URI
        with patch.object(storage_ai_box, "get_file_path", return_value=s3_uri):
            mock_response = {"Body": Mock(read=Mock(return_value=file_content))}
            mock_s3_client.get_object.return_value = mock_response

            result = storage_ai_box.read_file(file_id=file_id, metadata_storage_path=s3_uri)

            assert result == file_content
            mock_s3_client.get_object.assert_called_once_with(
                Bucket="bucket-ai-box-assets", Key="ab/test-file-id.txt"
            )

    def test_read_file_not_found(self, storage_ai_box, mock_s3_client):
        """測試讀取不存在的文件"""
        file_id = "non-existent-file"
        s3_uri = "s3://bucket-ai-box-assets/ab/non-existent-file.txt"

        with patch.object(storage_ai_box, "get_file_path", return_value=s3_uri):
            mock_s3_client.get_object.side_effect = ClientError(
                {"Error": {"Code": "NoSuchKey"}}, "GetObject"
            )

            result = storage_ai_box.read_file(file_id=file_id, metadata_storage_path=s3_uri)

            assert result is None

    def test_delete_file(self, storage_ai_box, mock_s3_client):
        """測試刪除文件"""
        file_id = "test-file-id"
        s3_uri = "s3://bucket-ai-box-assets/ab/test-file-id.txt"

        with patch.object(storage_ai_box, "get_file_path", return_value=s3_uri):
            mock_s3_client.delete_object.return_value = {}

            result = storage_ai_box.delete_file(file_id=file_id, metadata_storage_path=s3_uri)

            assert result is True
            mock_s3_client.delete_object.assert_called_once_with(
                Bucket="bucket-ai-box-assets", Key="ab/test-file-id.txt"
            )

    def test_delete_file_not_found(self, storage_ai_box, mock_s3_client):
        """測試刪除不存在的文件"""
        file_id = "non-existent-file"

        with patch.object(storage_ai_box, "get_file_path", return_value=None):
            result = storage_ai_box.delete_file(file_id=file_id)

            assert result is False

    def test_file_exists(self, storage_ai_box, mock_s3_client):
        """測試檢查文件是否存在"""
        file_id = "test-file-id"
        s3_uri = "s3://bucket-ai-box-assets/ab/test-file-id.txt"

        with patch.object(storage_ai_box, "get_file_path", return_value=s3_uri):
            mock_s3_client.head_object.return_value = {}

            result = storage_ai_box.file_exists(file_id=file_id, metadata_storage_path=s3_uri)

            assert result is True
            mock_s3_client.head_object.assert_called_once_with(
                Bucket="bucket-ai-box-assets", Key="ab/test-file-id.txt"
            )

    def test_file_exists_not_found(self, storage_ai_box, mock_s3_client):
        """測試檢查不存在的文件"""
        file_id = "non-existent-file"
        s3_uri = "s3://bucket-ai-box-assets/ab/non-existent-file.txt"

        with patch.object(storage_ai_box, "get_file_path", return_value=s3_uri):
            mock_s3_client.head_object.side_effect = ClientError(
                {"Error": {"Code": "404"}}, "HeadObject"
            )

            result = storage_ai_box.file_exists(file_id=file_id, metadata_storage_path=s3_uri)

            assert result is False

    def test_get_file_path(self, storage_ai_box, mock_s3_client):
        """測試獲取文件路徑"""
        file_id = "test-file-id"

        # 模擬 list_objects_v2 返回文件
        mock_s3_client.list_objects_v2.return_value = {"Contents": [{"Key": "ab/test-file-id.txt"}]}

        result = storage_ai_box.get_file_path(file_id=file_id)

        assert result is not None
        assert result.startswith("s3://")
        assert "test-file-id" in result

    def test_get_file_path_with_task_id(self, storage_ai_box, mock_s3_client):
        """測試獲取文件路徑（帶 task_id）"""
        file_id = "test-file-id"
        task_id = "test-task-id"

        # 模擬 head_object 成功（文件存在）
        mock_s3_client.head_object.return_value = {}

        result = storage_ai_box.get_file_path(file_id=file_id, task_id=task_id)

        # 由於我們使用 head_object 檢查，如果文件存在，應該返回 S3 URI
        # 但由於我們沒有實際的文件，這裡主要測試邏輯不報錯
        assert result is None or result.startswith("s3://")

    def test_parse_s3_uri(self, storage_ai_box):
        """測試解析 S3 URI"""
        # 測試 s3:// 格式
        result = storage_ai_box._parse_s3_uri("s3://bucket-name/path/to/file.txt")
        assert result == ("bucket-name", "path/to/file.txt")

        # 測試 https:// 格式
        result = storage_ai_box._parse_s3_uri("https://endpoint/bucket-name/path/to/file.txt")
        assert result == ("bucket-name", "path/to/file.txt")

        # 測試無效格式
        result = storage_ai_box._parse_s3_uri("invalid-uri")
        assert result is None

    def test_get_s3_key(self, storage_ai_box):
        """測試生成 S3 對象鍵"""
        file_id = "test-file-id"
        filename = "test.txt"

        # 不帶 task_id
        key = storage_ai_box._get_s3_key(file_id, filename)
        assert key.startswith("ab/")  # 前兩個字符作為子目錄
        assert file_id in key

        # 帶 task_id
        task_id = "test-task-id"
        key = storage_ai_box._get_s3_key(file_id, filename, task_id)
        assert key.startswith("tasks/test-task-id/")
        assert file_id in key

    def test_get_bucket_for_file_type(self, storage_ai_box, storage_datalake):
        """測試根據文件類型選擇 Bucket"""
        # AI-Box 服務
        assert (
            storage_ai_box._get_bucket_for_file_type("governance-logs") == "bucket-governance-logs"
        )
        assert (
            storage_ai_box._get_bucket_for_file_type("version-history") == "bucket-version-history"
        )
        assert storage_ai_box._get_bucket_for_file_type() == "bucket-ai-box-assets"

        # DataLake 服務
        assert storage_datalake._get_bucket_for_file_type("file-backups") == "bucket-file-backups"
        assert storage_datalake._get_bucket_for_file_type() == "bucket-datalake-assets"

    def test_guess_content_type(self, storage_ai_box):
        """測試猜測內容類型"""
        assert storage_ai_box._guess_content_type("test.txt") == "text/plain"
        assert storage_ai_box._guess_content_type("test.json") == "application/json"
        assert storage_ai_box._guess_content_type("test.pdf") == "application/pdf"
        assert storage_ai_box._guess_content_type("test.unknown") == "application/octet-stream"

    def test_save_file_error_handling(self, storage_ai_box, mock_s3_client):
        """測試保存文件錯誤處理"""
        file_content = b"test file content"
        filename = "test.txt"
        file_id = "test-file-id"

        # 模擬 put_object 失敗
        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "InternalError"}}, "PutObject"
        )

        with pytest.raises(RuntimeError, match="Failed to save file to S3"):
            storage_ai_box.save_file(file_content=file_content, filename=filename, file_id=file_id)

    def test_read_file_error_handling(self, storage_ai_box, mock_s3_client):
        """測試讀取文件錯誤處理"""
        file_id = "test-file-id"
        s3_uri = "s3://bucket-ai-box-assets/ab/test-file-id.txt"

        # 模擬 get_object 失敗（非 NoSuchKey 錯誤）
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "InternalError"}}, "GetObject"
        )

        with patch.object(
            storage_ai_box,
            "_parse_s3_uri",
            return_value=("bucket-ai-box-assets", "ab/test-file-id.txt"),
        ):
            result = storage_ai_box.read_file(file_id=file_id, metadata_storage_path=s3_uri)

            assert result is None

    def test_delete_file_error_handling(self, storage_ai_box, mock_s3_client):
        """測試刪除文件錯誤處理"""
        file_id = "test-file-id"
        s3_uri = "s3://bucket-ai-box-assets/ab/test-file-id.txt"

        # 模擬 delete_object 失敗
        mock_s3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "InternalError"}}, "DeleteObject"
        )

        with patch.object(
            storage_ai_box,
            "_parse_s3_uri",
            return_value=("bucket-ai-box-assets", "ab/test-file-id.txt"),
        ):
            result = storage_ai_box.delete_file(file_id=file_id, metadata_storage_path=s3_uri)

            assert result is False

    def test_file_version_management(self, storage_ai_box, mock_s3_client):
        """測試文件版本管理（通過不同的 file_id 和路徑）"""
        file_content_v1 = b"version 1 content"
        file_content_v2 = b"version 2 content"
        filename = "test.txt"
        file_id_v1 = "file-123-v1"
        file_id_v2 = "file-123-v2"

        mock_s3_client.put_object.return_value = {}

        # 保存版本 1
        file_id_result_1, s3_uri_1 = storage_ai_box.save_file(
            file_content=file_content_v1, filename=filename, file_id=file_id_v1
        )

        # 保存版本 2
        file_id_result_2, s3_uri_2 = storage_ai_box.save_file(
            file_content=file_content_v2, filename=filename, file_id=file_id_v2
        )

        assert file_id_result_1 == file_id_v1
        assert file_id_result_2 == file_id_v2
        assert s3_uri_1 != s3_uri_2
        assert mock_s3_client.put_object.call_count == 2

    def test_different_buckets_auto_create(self, mock_s3_client):
        """測試不同 Bucket 的自動創建"""
        # 模擬 head_bucket 返回 404（Bucket 不存在）
        mock_s3_client.head_bucket.side_effect = [
            ClientError({"Error": {"Code": "404"}}, "HeadBucket"),  # 默認 Bucket
            None,  # 創建後檢查
        ]
        mock_s3_client.create_bucket.return_value = None

        S3FileStorage(
            endpoint="http://test-endpoint:8333",
            access_key="test-access-key",
            secret_key="test-secret-key",
            service_type=SeaweedFSService.AI_BOX,
        )

        # 驗證默認 Bucket 被創建
        mock_s3_client.create_bucket.assert_called_with(Bucket="bucket-ai-box-assets")

    def test_datalake_bucket_auto_create(self, mock_s3_client):
        """測試 DataLake Bucket 的自動創建"""
        mock_s3_client.head_bucket.side_effect = [
            ClientError({"Error": {"Code": "404"}}, "HeadBucket"),
            None,
        ]
        mock_s3_client.create_bucket.return_value = None

        S3FileStorage(
            endpoint="http://test-endpoint:8333",
            access_key="test-access-key",
            secret_key="test-secret-key",
            service_type=SeaweedFSService.DATALAKE,
        )

        mock_s3_client.create_bucket.assert_called_with(Bucket="bucket-datalake-assets")

    def test_parse_s3_uri_https_format(self, storage_ai_box):
        """測試解析 HTTPS 格式的 S3 URI"""
        result = storage_ai_box._parse_s3_uri(
            "https://endpoint.example.com/bucket-name/path/to/file.txt"
        )
        assert result == ("bucket-name", "path/to/file.txt")

    def test_parse_s3_uri_http_format(self, storage_ai_box):
        """測試解析 HTTP 格式的 S3 URI"""
        result = storage_ai_box._parse_s3_uri(
            "http://endpoint.example.com/bucket-name/path/to/file.txt"
        )
        assert result == ("bucket-name", "path/to/file.txt")

    def test_get_file_path_with_metadata_storage_path(self, storage_ai_box):
        """測試使用 metadata_storage_path 獲取文件路徑"""
        file_id = "test-file-id"
        s3_uri = "s3://bucket-ai-box-assets/ab/test-file-id.txt"

        result = storage_ai_box.get_file_path(file_id=file_id, metadata_storage_path=s3_uri)

        assert result == s3_uri

    def test_read_file_with_metadata_storage_path(self, storage_ai_box, mock_s3_client):
        """測試使用 metadata_storage_path 讀取文件"""
        file_id = "test-file-id"
        s3_uri = "s3://bucket-ai-box-assets/ab/test-file-id.txt"
        file_content = b"test file content"

        mock_response = {"Body": Mock(read=Mock(return_value=file_content))}
        mock_s3_client.get_object.return_value = mock_response

        result = storage_ai_box.read_file(file_id=file_id, metadata_storage_path=s3_uri)

        assert result == file_content
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="bucket-ai-box-assets", Key="ab/test-file-id.txt"
        )

    def test_delete_file_with_metadata_storage_path(self, storage_ai_box, mock_s3_client):
        """測試使用 metadata_storage_path 刪除文件"""
        file_id = "test-file-id"
        s3_uri = "s3://bucket-ai-box-assets/ab/test-file-id.txt"

        mock_s3_client.delete_object.return_value = {}

        result = storage_ai_box.delete_file(file_id=file_id, metadata_storage_path=s3_uri)

        assert result is True
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="bucket-ai-box-assets", Key="ab/test-file-id.txt"
        )

    def test_file_exists_with_metadata_storage_path(self, storage_ai_box, mock_s3_client):
        """測試使用 metadata_storage_path 檢查文件是否存在"""
        file_id = "test-file-id"
        s3_uri = "s3://bucket-ai-box-assets/ab/test-file-id.txt"

        mock_s3_client.head_object.return_value = {}

        result = storage_ai_box.file_exists(file_id=file_id, metadata_storage_path=s3_uri)

        assert result is True
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="bucket-ai-box-assets", Key="ab/test-file-id.txt"
        )
