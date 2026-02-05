# 代碼功能說明: 系統配置初始化服務
# 創建日期: 2026-01-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""系統配置初始化服務 - 在系統啟動時初始化默認配置到 ArangoDB"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

from services.api.models.config import ConfigCreate
from services.api.services.config_store_service import ConfigStoreService

logger = structlog.get_logger(__name__)

# 默認配置數據（內嵌在代碼中，避免依賴外部文件）
DEFAULT_SYSTEM_CONFIGS: Dict[str, Dict[str, Any]] = {
    "file_processing": {
        "max_file_size": 104857600,
        "supported_file_types": [
            "text/markdown",
            "application/pdf",
            "text/plain",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/json",
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
        ],
        "processing_timeout": 1800,
        "enable_auto_backup": True,
    },
    "chunk_processing": {
        "chunk_size": 768,
        "min_chunk_size": 50,
        "max_chunk_size": 2000,
        "chunk_strategy": "semantic",
        "overlap": 0.2,
        "max_code_block_size": 2000,
        "table_context_lines": 3,
        "combine_text_paragraphs": True,
        "separate_code_blocks": True,
        "separate_tables": True,
        "enable_quality_check": True,
        "enable_adaptive_size": True,
    },
    "streaming": {"chunk_size": 50},
    "kg_extraction": {
        "enabled": True,
        "mode": "all_chunks",
        "min_confidence": 0.5,
        "batch_size": 10,
        "insufficient_entities_threshold": 1,  # 實體數量不足的閾值（至少需要多少個實體才能構建三元組）
        "ner_model": "mistral-nemo:12b",  # NER模型配置
        "re_model": "mistral-nemo:12b",  # RE模型配置
        "rt_model": "mistral-nemo:12b",  # RT模型配置
    },
    "worker": {
        "queue_priority": {"file_processing": 1, "kg_extraction": 2, "vectorization": 3},
        "max_retries": 3,
        "retry_delay": 60,
        "job_timeout": 900,  # 测试阶段：900秒（15分钟）- 快速发现问题；生产环境可根据实际需求调整为 3600 秒（1小时）
    },
    "cache": {"enabled": True, "ttl": 3600, "max_size": 1024},
    "features": {"enable_experimental": False, "maintenance_mode": False, "enable_analytics": True},
}


def initialize_system_configs(force: bool = False) -> Dict[str, bool]:
    """
    初始化系統配置到 ArangoDB

    Args:
        force: 如果為 True，強制覆蓋現有配置；如果為 False，僅在配置不存在時創建

    Returns:
        字典，key 為 scope，value 為是否成功初始化
    """
    results: Dict[str, bool] = {}
    config_service = ConfigStoreService()

    for scope, config_data in DEFAULT_SYSTEM_CONFIGS.items():
        try:
            # 檢查配置是否已存在
            existing_config = config_service.get_config(scope, tenant_id=None)

            if existing_config and not force:
                logger.debug("config_already_exists", scope=scope, message="配置已存在，跳過初始化")
                results[scope] = False  # 已存在，未初始化
                continue

            # 創建或更新配置
            category_map = {
                "file_processing": "business",
                "chunk_processing": "business",
                "streaming": "performance",
                "kg_extraction": "feature_flag",
                "worker": "performance",
                "cache": "performance",
                "features": "feature_flag",
            }
            config_create = ConfigCreate(
                scope=scope,
                category=category_map.get(scope, "business"),
                config_data=config_data,
                metadata={"initialized": True, "source": "system_defaults"},
                tenant_id=None,
            )

            config_service.save_config(config_create, tenant_id=None, changed_by="system")
            logger.info(
                "config_initialized",
                scope=scope,
                force=force,
                message=f"系統配置 '{scope}' 已初始化",
            )
            results[scope] = True

        except Exception as e:
            logger.error(
                "config_initialization_failed",
                scope=scope,
                error=str(e),
                message=f"初始化系統配置 '{scope}' 失敗",
            )
            results[scope] = False

    return results


def initialize_mcp_external_services_config(force: bool = False) -> bool:
    """
    從 .env 加載 MCP 第三方服務配置到 ArangoDB（佔位實作，待整合）。

    Args:
        force: 是否強制覆蓋現有配置。

    Returns:
        是否成功初始化。
    """
    # TODO: 實作從 .env 加載 MCP 配置並寫入 ArangoDB
    _ = force
    return False


def load_default_configs_from_file(
    config_path: Optional[Path] = None,
) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    從文件加載默認配置（可選，如果文件存在則使用文件，否則使用內嵌配置）

    Args:
        config_path: 配置文件路徑，如果為 None 則嘗試從默認位置加載

    Returns:
        配置字典，如果文件不存在或讀取失敗則返回 None
    """
    if config_path is None:
        # 嘗試從項目根目錄的 config 目錄加載
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "config" / "system_configs.default.json"

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            configs = json.load(f)
            logger.info(
                "default_configs_loaded_from_file",
                path=str(config_path),
                scopes=list(configs.keys()),
            )
            return configs
    except Exception as e:
        logger.warning(
            "failed_to_load_default_configs_from_file",
            path=str(config_path),
            error=str(e),
            message="從文件加載默認配置失敗，將使用內嵌配置",
        )
        return None
