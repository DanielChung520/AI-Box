# 代碼功能說明: 數據質量監控服務
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:47 (UTC+8)

"""數據質量監控服務 - 實現數據完整性、一致性和準確性檢查"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import structlog

from services.api.services.file_metadata_service import get_metadata_service

logger = structlog.get_logger(__name__)


class DataQualityIssue:
    """數據質量問題"""

    def __init__(
        self,
        issue_type: str,
        severity: str,
        description: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化數據質量問題

        Args:
            issue_type: 問題類型（完整性、一致性、準確性、異常）
            severity: 嚴重程度（critical, warning, info）
            description: 問題描述
            resource_id: 資源ID
            resource_type: 資源類型
            details: 詳細信息
        """
        self.issue_type = issue_type
        self.severity = severity
        self.description = description
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class DataQualityService:
    """數據質量監控服務"""

    def __init__(self, metadata_service: Optional[Any] = None):
        """
        初始化數據質量服務

        Args:
            metadata_service: 文件元數據服務（可選）
        """
        self.metadata_service = metadata_service or get_metadata_service()
        self.logger = logger

    def check_file_integrity(self, file_id: str) -> List[DataQualityIssue]:
        """
        檢查文件完整性

        Args:
            file_id: 文件ID

        Returns:
            數據質量問題列表
        """
        issues: List[DataQualityIssue] = []

        try:
            file_metadata = self.metadata_service.get(file_id)
            if file_metadata is None:
                issues.append(
                    DataQualityIssue(
                        issue_type="完整性",
                        severity="critical",
                        description=f"文件元數據不存在: {file_id}",
                        resource_id=file_id,
                        resource_type="file",
                    )
                )
                return issues

            # 檢查必需字段
            required_fields = ["file_id", "filename", "file_type", "user_id"]
            for field in required_fields:
                if (
                    not hasattr(file_metadata, field)
                    or getattr(file_metadata, field) is None
                ):
                    issues.append(
                        DataQualityIssue(
                            issue_type="完整性",
                            severity="critical",
                            description=f"文件元數據缺少必需字段: {field}",
                            resource_id=file_id,
                            resource_type="file",
                            details={"field": field},
                        )
                    )

            # 檢查文件大小合理性
            if hasattr(file_metadata, "file_size"):
                file_size = file_metadata.file_size
                if file_size is not None:
                    if file_size < 0:
                        issues.append(
                            DataQualityIssue(
                                issue_type="完整性",
                                severity="critical",
                                description=f"文件大小為負數: {file_size}",
                                resource_id=file_id,
                                resource_type="file",
                                details={"file_size": file_size},
                            )
                        )
                    elif file_size == 0:
                        issues.append(
                            DataQualityIssue(
                                issue_type="完整性",
                                severity="warning",
                                description="文件大小為0",
                                resource_id=file_id,
                                resource_type="file",
                            )
                        )

        except Exception as e:
            self.logger.error("文件完整性檢查失敗", file_id=file_id, error=str(e))
            issues.append(
                DataQualityIssue(
                    issue_type="完整性",
                    severity="critical",
                    description=f"文件完整性檢查失敗: {str(e)}",
                    resource_id=file_id,
                    resource_type="file",
                )
            )

        return issues

    def check_data_consistency(self, file_id: str) -> List[DataQualityIssue]:
        """
        檢查數據一致性

        Args:
            file_id: 文件ID

        Returns:
            數據質量問題列表
        """
        issues: List[DataQualityIssue] = []

        try:
            file_metadata = self.metadata_service.get(file_id)
            if file_metadata is None:
                return issues

            # 檢查文件名和文件類型的一致性
            if hasattr(file_metadata, "filename") and hasattr(
                file_metadata, "file_type"
            ):
                filename = file_metadata.filename
                file_type = file_metadata.file_type

                if filename and file_type:
                    # 檢查文件擴展名是否與文件類型匹配
                    extension = (
                        filename.split(".")[-1].lower() if "." in filename else ""
                    )
                    expected_types = {
                        "pdf": ["application/pdf"],
                        "doc": ["application/msword"],
                        "docx": [
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        ],
                        "xls": ["application/vnd.ms-excel"],
                        "xlsx": [
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        ],
                        "txt": ["text/plain"],
                        "md": ["text/markdown"],
                        "jpg": ["image/jpeg"],
                        "jpeg": ["image/jpeg"],
                        "png": ["image/png"],
                        "gif": ["image/gif"],
                    }

                    if extension in expected_types:
                        expected_mime_types = expected_types[extension]
                        if file_type not in expected_mime_types:
                            issues.append(
                                DataQualityIssue(
                                    issue_type="一致性",
                                    severity="warning",
                                    description=f"文件擴展名與MIME類型不匹配: {extension} vs {file_type}",
                                    resource_id=file_id,
                                    resource_type="file",
                                    details={
                                        "extension": extension,
                                        "file_type": file_type,
                                        "expected_types": expected_mime_types,
                                    },
                                )
                            )

        except Exception as e:
            self.logger.error("數據一致性檢查失敗", file_id=file_id, error=str(e))
            issues.append(
                DataQualityIssue(
                    issue_type="一致性",
                    severity="critical",
                    description=f"數據一致性檢查失敗: {str(e)}",
                    resource_id=file_id,
                    resource_type="file",
                )
            )

        return issues

    def check_data_accuracy(self, file_id: str) -> List[DataQualityIssue]:
        """
        檢查數據準確性

        Args:
            file_id: 文件ID

        Returns:
            數據質量問題列表
        """
        issues: List[DataQualityIssue] = []

        try:
            file_metadata = self.metadata_service.get(file_id)
            if file_metadata is None:
                return issues

            # 檢查時間戳的合理性
            if hasattr(file_metadata, "upload_time"):
                upload_time = file_metadata.upload_time
                if upload_time:
                    now = datetime.utcnow()
                    if upload_time > now:
                        issues.append(
                            DataQualityIssue(
                                issue_type="準確性",
                                severity="warning",
                                description=f"上傳時間在未來: {upload_time}",
                                resource_id=file_id,
                                resource_type="file",
                                details={"upload_time": upload_time.isoformat()},
                            )
                        )

        except Exception as e:
            self.logger.error("數據準確性檢查失敗", file_id=file_id, error=str(e))
            issues.append(
                DataQualityIssue(
                    issue_type="準確性",
                    severity="critical",
                    description=f"數據準確性檢查失敗: {str(e)}",
                    resource_id=file_id,
                    resource_type="file",
                )
            )

        return issues

    def detect_anomalies(self, file_id: str) -> List[DataQualityIssue]:
        """
        檢測異常數據

        Args:
            file_id: 文件ID

        Returns:
            數據質量問題列表
        """
        issues: List[DataQualityIssue] = []

        try:
            file_metadata = self.metadata_service.get(file_id)
            if file_metadata is None:
                return issues

            # 檢查異常大的文件名
            if hasattr(file_metadata, "filename"):
                filename = file_metadata.filename
                if filename and len(filename) > 255:
                    issues.append(
                        DataQualityIssue(
                            issue_type="異常",
                            severity="warning",
                            description=f"文件名過長: {len(filename)} 字符",
                            resource_id=file_id,
                            resource_type="file",
                            details={"filename_length": len(filename)},
                        )
                    )

            # 檢查異常大的文件
            if hasattr(file_metadata, "file_size"):
                file_size = file_metadata.file_size
                if file_size is not None:
                    # 100MB 作為異常大文件的閾值
                    max_normal_size = 100 * 1024 * 1024
                    if file_size > max_normal_size:
                        issues.append(
                            DataQualityIssue(
                                issue_type="異常",
                                severity="info",
                                description=f"文件異常大: {file_size / (1024 * 1024):.2f} MB",
                                resource_id=file_id,
                                resource_type="file",
                                details={"file_size": file_size},
                            )
                        )

        except Exception as e:
            self.logger.error("異常檢測失敗", file_id=file_id, error=str(e))
            issues.append(
                DataQualityIssue(
                    issue_type="異常",
                    severity="critical",
                    description=f"異常檢測失敗: {str(e)}",
                    resource_id=file_id,
                    resource_type="file",
                )
            )

        return issues

    def check_file_quality(self, file_id: str) -> Dict[str, Any]:
        """
        檢查文件質量（綜合檢查）

        Args:
            file_id: 文件ID

        Returns:
            質量檢查結果
        """
        all_issues: List[DataQualityIssue] = []

        # 執行所有檢查
        all_issues.extend(self.check_file_integrity(file_id))
        all_issues.extend(self.check_data_consistency(file_id))
        all_issues.extend(self.check_data_accuracy(file_id))
        all_issues.extend(self.detect_anomalies(file_id))

        # 統計問題
        critical_count = sum(1 for issue in all_issues if issue.severity == "critical")
        warning_count = sum(1 for issue in all_issues if issue.severity == "warning")
        info_count = sum(1 for issue in all_issues if issue.severity == "info")

        # 計算質量分數（0-100）
        quality_score = 100
        quality_score -= critical_count * 20  # 每個嚴重問題扣20分
        quality_score -= warning_count * 10  # 每個警告扣10分
        quality_score -= info_count * 5  # 每個信息扣5分
        quality_score = max(0, quality_score)  # 確保不低於0

        return {
            "file_id": file_id,
            "quality_score": quality_score,
            "total_issues": len(all_issues),
            "critical_issues": critical_count,
            "warning_issues": warning_count,
            "info_issues": info_count,
            "issues": [
                {
                    "type": issue.issue_type,
                    "severity": issue.severity,
                    "description": issue.description,
                    "resource_id": issue.resource_id,
                    "resource_type": issue.resource_type,
                    "details": issue.details,
                    "timestamp": issue.timestamp.isoformat(),
                }
                for issue in all_issues
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }


# 全局服務實例（懶加載）
_data_quality_service: Optional[DataQualityService] = None


def get_data_quality_service() -> DataQualityService:
    """獲取數據質量服務實例（單例模式）"""
    global _data_quality_service
    if _data_quality_service is None:
        _data_quality_service = DataQualityService()
    return _data_quality_service
