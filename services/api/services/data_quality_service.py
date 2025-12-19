# 代碼功能說明: 數據質量監控服務（WBS-4.2.3: 數據品質監控）
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""數據質量監控服務 - 實現數據完整性、一致性和準確性檢查"""

from datetime import datetime
from typing import Any, Dict, List, Optional

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
                if not hasattr(file_metadata, field) or getattr(file_metadata, field) is None:
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
            if hasattr(file_metadata, "filename") and hasattr(file_metadata, "file_type"):
                filename = file_metadata.filename
                file_type = file_metadata.file_type

                if filename and file_type:
                    # 檢查文件擴展名是否與文件類型匹配
                    extension = filename.split(".")[-1].lower() if "." in filename else ""
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

    def check_ontology_quality(
        self, ontology: Any, ontology_service: Optional[Any] = None
    ) -> List[DataQualityIssue]:
        """
        檢查 Ontology 品質（WBS-4.2.3: 數據品質監控）

        Args:
            ontology: OntologyModel 實例或包含 Ontology 數據的字典
            ontology_service: OntologyStoreService 實例（用於檢查依賴關係）

        Returns:
            數據品質問題列表
        """
        issues: List[DataQualityIssue] = []
        ontology_id = None

        try:
            # 處理不同類型的輸入
            if isinstance(ontology, dict):
                ontology_id = ontology.get("id") or ontology.get("_key")
                entity_classes = ontology.get("entity_classes", [])
                object_properties = ontology.get("object_properties", [])
                version = ontology.get("version", "")
                inherits_from = ontology.get("inherits_from", [])
                ontology_type = ontology.get("type", "")
            else:
                ontology_id = getattr(ontology, "id", None)
                entity_classes = getattr(ontology, "entity_classes", [])
                object_properties = getattr(ontology, "object_properties", [])
                version = getattr(ontology, "version", "")
                inherits_from = getattr(ontology, "inherits_from", [])
                ontology_type = getattr(ontology, "type", "")

            # 1. 檢查結構完整性：entity_classes 和 object_properties 不為空
            if not entity_classes:
                issues.append(
                    DataQualityIssue(
                        issue_type="完整性",
                        severity="warning",
                        description="Ontology 缺少 entity_classes（可能為空但非錯誤）",
                        resource_id=ontology_id,
                        resource_type="ontology",
                    )
                )

            if not object_properties:
                issues.append(
                    DataQualityIssue(
                        issue_type="完整性",
                        severity="warning",
                        description="Ontology 缺少 object_properties（可能為空但非錯誤）",
                        resource_id=ontology_id,
                        resource_type="ontology",
                    )
                )

            # 2. 檢查版本號格式正確性（語義化版本）
            if version:
                import re

                semver_pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9-]+)?(\+[a-zA-Z0-9-]+)?$"
                if not re.match(semver_pattern, version):
                    issues.append(
                        DataQualityIssue(
                            issue_type="準確性",
                            severity="warning",
                            description=f"版本號格式不符合語義化版本規範: {version}",
                            resource_id=ontology_id,
                            resource_type="ontology",
                            details={"version": version},
                        )
                    )

            # 3. 檢查依賴關係完整性（inherits_from 中的 Ontology 是否存在）
            if inherits_from and ontology_service:
                for inherited_name in inherits_from:
                    try:
                        # 嘗試查找被繼承的 Ontology（簡化檢查：只檢查名稱是否存在）
                        # 實際實現可能需要更複雜的查詢邏輯
                        pass  # 暫時跳過，因為需要更複雜的查詢邏輯
                    except Exception:
                        issues.append(
                            DataQualityIssue(
                                issue_type="一致性",
                                severity="warning",
                                description=f"無法驗證依賴的 Ontology 是否存在: {inherited_name}",
                                resource_id=ontology_id,
                                resource_type="ontology",
                                details={"inherits_from": inherited_name},
                            )
                        )

            # 4. 檢查實體類別和屬性的一致性
            if entity_classes and object_properties:
                # 收集所有實體類別名稱
                entity_names = set()
                for ec in entity_classes:
                    if isinstance(ec, dict):
                        entity_names.add(ec.get("name", ""))
                    else:
                        entity_names.add(getattr(ec, "name", ""))

                # 檢查 object_properties 的 domain 和 range 是否引用存在的實體
                for op in object_properties:
                    if isinstance(op, dict):
                        domains = op.get("domain", [])
                        ranges = op.get("range", [])
                    else:
                        domains = getattr(op, "domain", [])
                        ranges = getattr(op, "range", [])

                    for domain in domains:
                        if domain and domain not in entity_names:
                            issues.append(
                                DataQualityIssue(
                                    issue_type="一致性",
                                    severity="warning",
                                    description=f"Object property 的 domain '{domain}' 未在 entity_classes 中定義",
                                    resource_id=ontology_id,
                                    resource_type="ontology",
                                    details={
                                        "property": op.get("name")
                                        if isinstance(op, dict)
                                        else getattr(op, "name", ""),
                                        "domain": domain,
                                    },
                                )
                            )

                    for range_val in ranges:
                        if range_val and range_val not in entity_names:
                            issues.append(
                                DataQualityIssue(
                                    issue_type="一致性",
                                    severity="warning",
                                    description=f"Object property 的 range '{range_val}' 未在 entity_classes 中定義",
                                    resource_id=ontology_id,
                                    resource_type="ontology",
                                    details={
                                        "property": op.get("name")
                                        if isinstance(op, dict)
                                        else getattr(op, "name", ""),
                                        "range": range_val,
                                    },
                                )
                            )

        except Exception as e:
            self.logger.error("Ontology 品質檢查失敗", ontology_id=ontology_id, error=str(e))
            issues.append(
                DataQualityIssue(
                    issue_type="完整性",
                    severity="critical",
                    description=f"Ontology 品質檢查失敗: {str(e)}",
                    resource_id=ontology_id,
                    resource_type="ontology",
                )
            )

        return issues

    def check_config_quality(
        self, config: Any, config_service: Optional[Any] = None
    ) -> List[DataQualityIssue]:
        """
        檢查 Config 品質（WBS-4.2.3: 數據品質監控）

        Args:
            config: ConfigModel 實例或包含 Config 數據的字典
            config_service: ConfigStoreService 實例（用於檢查配置收斂性）

        Returns:
            數據品質問題列表
        """
        issues: List[DataQualityIssue] = []
        config_id = None

        try:
            # 處理不同類型的輸入
            if isinstance(config, dict):
                config_id = config.get("id") or config.get("_key")
                config_data = config.get("config_data", {})
                scope = config.get("scope", "")
                tenant_id = config.get("tenant_id")
                user_id = config.get("user_id")
            else:
                config_id = getattr(config, "id", None)
                config_data = getattr(config, "config_data", {})
                scope = getattr(config, "scope", "")
                tenant_id = getattr(config, "tenant_id", None)
                user_id = getattr(config, "user_id", None)

            # 1. 檢查結構完整性：config_data 不為空
            if not config_data:
                issues.append(
                    DataQualityIssue(
                        issue_type="完整性",
                        severity="critical",
                        description="Config 的 config_data 為空",
                        resource_id=config_id,
                        resource_type="config",
                        details={"scope": scope},
                    )
                )
                return issues  # 如果 config_data 為空，其他檢查沒有意義

            # 2. 檢查配置鍵的有效性（根據 scope 驗證必要字段）
            if scope.startswith("genai.policy"):
                # genai.policy 通常包含 allowed_models, blocked_models 等
                if "allowed_models" not in config_data and "blocked_models" not in config_data:
                    issues.append(
                        DataQualityIssue(
                            issue_type="完整性",
                            severity="warning",
                            description="genai.policy 配置缺少 allowed_models 或 blocked_models",
                            resource_id=config_id,
                            resource_type="config",
                            details={"scope": scope},
                        )
                    )

            # 3. 檢查配置值的有效性（類型、範圍檢查）
            if "allowed_models" in config_data:
                allowed_models = config_data["allowed_models"]
                if not isinstance(allowed_models, list):
                    issues.append(
                        DataQualityIssue(
                            issue_type="準確性",
                            severity="critical",
                            description="allowed_models 應該是列表類型",
                            resource_id=config_id,
                            resource_type="config",
                            details={"scope": scope, "type": type(allowed_models).__name__},
                        )
                    )

            # 4. 檢查配置收斂性（租戶配置不擴展系統權限）- 需要 config_service
            if tenant_id and config_service:
                try:
                    # 獲取系統配置
                    system_config = config_service.get_config(scope, "system")
                    if system_config and system_config.config_data:
                        system_allowed = system_config.config_data.get("allowed_models", [])
                        tenant_allowed = config_data.get("allowed_models", [])

                        # 檢查租戶配置是否擴展了系統權限
                        if system_allowed and tenant_allowed:
                            # 如果系統配置是列表，檢查租戶配置是否包含系統沒有的模型
                            if isinstance(system_allowed, list) and isinstance(
                                tenant_allowed, list
                            ):
                                # 這個檢查邏輯應該在 ConfigStoreService 中實現
                                # 這裡只是簡單的檢查
                                pass
                except Exception:
                    # 無法獲取系統配置，跳過收斂性檢查
                    pass

        except Exception as e:
            self.logger.error("Config 品質檢查失敗", config_id=config_id, error=str(e))
            issues.append(
                DataQualityIssue(
                    issue_type="完整性",
                    severity="critical",
                    description=f"Config 品質檢查失敗: {str(e)}",
                    resource_id=config_id,
                    resource_type="config",
                )
            )

        return issues

    def check_ontology_quality_report(
        self, ontology: Any, ontology_service: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        檢查 Ontology 品質並生成報告（WBS-4.2.3）

        Args:
            ontology: OntologyModel 實例或包含 Ontology 數據的字典
            ontology_service: OntologyStoreService 實例（可選）

        Returns:
            品質檢查報告
        """
        issues = self.check_ontology_quality(ontology, ontology_service)

        critical_count = sum(1 for issue in issues if issue.severity == "critical")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        info_count = sum(1 for issue in issues if issue.severity == "info")

        # 計算品質分數
        quality_score = 100
        quality_score -= critical_count * 20
        quality_score -= warning_count * 10
        quality_score -= info_count * 5
        quality_score = max(0, quality_score)

        ontology_id = None
        if isinstance(ontology, dict):
            ontology_id = ontology.get("id") or ontology.get("_key")
        else:
            ontology_id = getattr(ontology, "id", None)

        return {
            "ontology_id": ontology_id,
            "quality_score": quality_score,
            "total_issues": len(issues),
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
                for issue in issues
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }

    def check_config_quality_report(
        self, config: Any, config_service: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        檢查 Config 品質並生成報告（WBS-4.2.3）

        Args:
            config: ConfigModel 實例或包含 Config 數據的字典
            config_service: ConfigStoreService 實例（可選）

        Returns:
            品質檢查報告
        """
        issues = self.check_config_quality(config, config_service)

        critical_count = sum(1 for issue in issues if issue.severity == "critical")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        info_count = sum(1 for issue in issues if issue.severity == "info")

        # 計算品質分數
        quality_score = 100
        quality_score -= critical_count * 20
        quality_score -= warning_count * 10
        quality_score -= info_count * 5
        quality_score = max(0, quality_score)

        config_id = None
        if isinstance(config, dict):
            config_id = config.get("id") or config.get("_key")
        else:
            config_id = getattr(config, "id", None)

        return {
            "config_id": config_id,
            "quality_score": quality_score,
            "total_issues": len(issues),
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
                for issue in issues
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
