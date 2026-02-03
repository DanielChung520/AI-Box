#!/usr/bin/env python3
# 代碼功能說明: 初始化所有 Provider 的 Base URL 配置
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24 22:47 UTC+8

"""
為所有 Provider 初始化 Base URL 配置（不包含 API Key）

使用方法:
    python -m services.api.services.migrations.init_provider_base_urls
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.api.models.llm_model import LLMProvider  # noqa: E402
from services.api.models.llm_provider_config import (  # noqa: E402
    LLMProviderConfigCreate,
)
from services.api.services.llm_provider_config_service import (  # noqa: E402
    get_default_base_url,
    get_llm_provider_config_service,
)


def init_all_provider_base_urls():
    """為所有有默認 Base URL 的 Provider 初始化配置"""
    print("🚀 開始初始化所有 Provider 的 Base URL 配置...")
    print("=" * 60)

    config_service = get_llm_provider_config_service()
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0

    # 獲取所有 Provider（排除 auto 和 ollama，它們不需要 Base URL）
    providers_to_init = [
        LLMProvider.OPENAI,
        LLMProvider.GOOGLE,
        LLMProvider.ANTHROPIC,
        LLMProvider.ALIBABA,
        LLMProvider.XAI,
        LLMProvider.MISTRAL,
        LLMProvider.DEEPSEEK,
        LLMProvider.DATABRICKS,
        LLMProvider.COHERE,
        LLMProvider.PERPLEXITY,
        LLMProvider.VOLCANO,
        LLMProvider.CHATGLM,
    ]

    for provider in providers_to_init:
        try:
            default_base_url = get_default_base_url(provider)
            if not default_base_url:
                print(f"  ⚠️  跳過 {provider.value}: 沒有默認 Base URL")
                skipped_count += 1
                continue

            # 檢查是否已存在配置
            existing_config = config_service.get_by_provider(provider)
            if existing_config:
                # 如果已存在但沒有 base_url 或 base_url 不同，則更新
                if not existing_config.base_url or existing_config.base_url != default_base_url:
                    from services.api.models.llm_provider_config import (
                        LLMProviderConfigUpdate,
                    )

                    update_req = LLMProviderConfigUpdate(base_url=default_base_url)
                    config_service.update(provider, update_req)
                    old_url = existing_config.base_url or "未設置"
                    print(
                        f"  🔄 更新 {provider.value}: Base URL = {default_base_url} (原: {old_url})"
                    )
                    updated_count += 1
                else:
                    print(
                        f"  ✅ 跳過 {provider.value}: Base URL 已存在 ({existing_config.base_url})"
                    )
                    skipped_count += 1
            else:
                # 創建新配置（只包含 Base URL，不包含 API Key）
                create_data = LLMProviderConfigCreate(
                    provider=provider,
                    base_url=default_base_url,
                    api_key=None,  # 不設置 API Key
                )
                config_service.create(create_data)
                print(f"  ✅ 創建 {provider.value}: Base URL = {default_base_url}")
                created_count += 1

        except ValueError as e:
            # 配置已存在（並發創建）
            print(f"  ⚠️  {provider.value}: {str(e)}")
            skipped_count += 1
        except Exception as e:
            print(f"  ❌ 處理 {provider.value} 失敗: {e}")
            error_count += 1

    print("=" * 60)
    print("初始化完成!")
    print(f"  ✅ 創建: {created_count} 個配置")
    print(f"  🔄 更新: {updated_count} 個配置")
    print(f"  ⚠️  跳過: {skipped_count} 個配置")
    print(f"  ❌ 錯誤: {error_count} 個配置")


if __name__ == "__main__":
    init_all_provider_base_urls()
