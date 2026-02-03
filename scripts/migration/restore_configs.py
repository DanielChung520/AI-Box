# 代碼功能說明: 配置恢復腳本 - 從環境變數和 config.json 恢復 GenAI 配置
# 創建日期: 2026-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-27

"""配置恢復腳本 - 恢復 GenAI 租戶策略和 API Keys

用途：
1. 從 config.json 恢復 GenAI 租戶策略
2. 從環境變數恢復加密的 API Keys
"""

import json
import os
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import structlog

from database.arangodb import ArangoDBClient
from services.api.services.genai_tenant_policy_service import (
    GenAITenantPolicyService,
    get_genai_tenant_policy_service,
)

logger = structlog.get_logger(__name__)


def load_config_json(config_path: Path = None) -> dict:
    """載入 config.json"""
    if config_path is None:
        # 嘗試多個可能的配置路徑
        possible_paths = [
            project_root / "config" / "config.json",
            project_root / "config.json",
            Path(os.getenv("AI_BOX_CONFIG_PATH", "")),
        ]
        for path in possible_paths:
            if path.exists():
                config_path = path
                break
        else:
            config_path = project_root / "config" / "config.json"

    if not config_path or not config_path.exists():
        logger.warning("config_json_not_found", path=str(config_path))
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def restore_tenant_policy(service: GenAITenantPolicyService, config: dict) -> bool:
    """恢復租戶策略"""
    genai_config = config.get("genai", {})
    policy = genai_config.get("policy", {})

    if not policy:
        logger.warning("no_policy_found_in_config")
        return False

    try:
        # 默認租戶 ID
        tenant_id = "default"

        # 檢查是否已存在
        existing = service.get_policy(tenant_id)
        if existing:
            logger.info("tenant_policy_already_exists", tenant_id=tenant_id)
            return True

        # 創建策略
        from services.api.models.genai_tenant_policy import GenAITenantPolicyCreate

        policy_create = GenAITenantPolicyCreate(
            tenant_id=tenant_id,
            allowed_providers=policy.get("allowed_providers", []),
            allowed_models=policy.get("allowed_models", {}),
            default_fallback=policy.get("default_fallback", {}),
            model_registry_models=policy.get("model_registry_models", []),
        )

        result = service.save_policy(policy_create)
        logger.info("tenant_policy_restored", tenant_id=tenant_id)
        return True

    except Exception as e:
        logger.error("restore_tenant_policy_failed", error=str(e), exc_info=True)
        return False


def restore_api_keys(service: GenAITenantPolicyService) -> dict[str, bool]:
    """恢復 API Keys 從環境變數"""
    results = {}

    # 定義環境變數映射
    env_mappings = {
        "OPENAI_API_KEY": "openai",
        "ANTHROPIC_API_KEY": "anthropic",
        "GEMINI_API_KEY": "gemini",
        "QWEN_API_KEY": "qwen",
        "CHATGLM_API_KEY": "chatglm",
        "DAOBAO_API_KEY": "volcano",  # doubao 使用 volcano provider
    }

    tenant_id = "default"

    for env_key, provider in env_mappings.items():
        api_key = os.getenv(env_key)
        if not api_key or api_key.startswith("your-"):
            logger.debug("api_key_not_found", provider=provider, env_key=env_key)
            results[provider] = False
            continue

        try:
            # 檢查是否已存在
            existing = service.get_tenant_api_key(tenant_id, provider)
            if existing:
                logger.info("api_key_already_exists", provider=provider)
                results[provider] = True
                continue

            # 保存 API Key（會自動加密）
            service.set_tenant_secret(tenant_id, provider, api_key)
            logger.info("api_key_restored", provider=provider)
            results[provider] = True

        except Exception as e:
            logger.error("restore_api_key_failed", provider=provider, error=str(e), exc_info=True)
            results[provider] = False

    return results


def main() -> int:
    """主函數"""
    logger.info("starting_config_restore")

    # 載入環境變數
    env_file = project_root / ".env"
    if env_file.exists():
        from dotenv import load_dotenv

        load_dotenv(env_file)
        logger.info("env_file_loaded", path=str(env_file))

    # 載入配置
    config = load_config_json()

    if not config:
        logger.error("no_config_found")
        return 1

    # 初始化服務
    try:
        service = get_genai_tenant_policy_service()
        if not service._use_db:
            logger.warning("genai_service_db_disabled_using_memory")
    except Exception as e:
        logger.error("init_service_failed", error=str(e), exc_info=True)
        return 1

    # 恢復租戶策略
    policy_restored = restore_tenant_policy(service, config)

    # 恢復 API Keys
    api_key_results = restore_api_keys(service)

    # 匯總結果
    success_count = sum(1 for v in api_key_results.values() if v)
    total_count = len(api_key_results)

    logger.info(
        "config_restore_completed",
        policy_restored=policy_restored,
        api_keys_restored=success_count,
        api_keys_total=total_count,
    )

    # 列出成功恢復的 API Keys
    restored_providers = [provider for provider, success in api_key_results.items() if success]
    if restored_providers:
        print(f"\n✓ 成功恢復 {len(restored_providers)} 個 API Keys:")
        for provider in restored_providers:
            print(f"  - {provider}")

    # 列出未恢復的 API Keys
    missing_providers = [provider for provider, success in api_key_results.items() if not success]
    if missing_providers:
        print(f"\n⚠ 未設置或恢復失敗的 API Keys:")
        for provider in missing_providers:
            print(f"  - {provider}")

    return 0 if policy_restored or success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
