#!/usr/bin/env python3
# 代碼功能說明: LLM 模型遷移到 ArangoDB 遷移腳本
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""
將前端硬編碼的 LLM 模型列表遷移到 ArangoDB

使用方法:
    python -m services.api.services.migrations.migrate_llm_models
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.api.models.llm_model import (
    LLMModelCreate,
    LLMProvider,
    ModelCapability,
    ModelStatus,
)
from services.api.services.llm_model_service import get_llm_model_service


# 完整的模型列表數據（從前端硬編碼遷移並擴展）
LLM_MODELS_DATA = [
    # Auto 選項（特殊處理）
    {
        "model_id": "auto",
        "name": "Auto",
        "provider": LLMProvider.AUTO,
        "description": "自動選擇最佳模型",
        "capabilities": [ModelCapability.CHAT],
        "status": ModelStatus.ACTIVE,
        "order": 0,
        "icon": "fa-magic",
        "color": "text-purple-400",
        "is_default": True,
    },
    # SmartQ 自定義模型
    {
        "model_id": "smartq-iee",
        "name": "SmartQ IEE",
        "provider": LLMProvider.SMARTQ,
        "description": "SmartQ IEE 專用模型",
        "capabilities": [ModelCapability.CHAT, ModelCapability.COMPLETION],
        "status": ModelStatus.ACTIVE,
        "order": 10,
        "icon": "fa-microchip",
        "color": "text-blue-400",
    },
    {
        "model_id": "smartq-hci",
        "name": "SmartQ HCI",
        "provider": LLMProvider.SMARTQ,
        "description": "SmartQ HCI 專用模型",
        "capabilities": [ModelCapability.CHAT, ModelCapability.COMPLETION],
        "status": ModelStatus.ACTIVE,
        "order": 20,
        "icon": "fa-robot",
        "color": "text-green-400",
    },
    # OpenAI (ChatGPT) 模型
    {
        "model_id": "gpt-4o",
        "name": "GPT-4o",
        "provider": LLMProvider.OPENAI,
        "description": "GPT-4 Optimized - 最新的 GPT-4 優化版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.MULTIMODAL,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 128000,
        "parameters": "~1.8T",
        "order": 30,
        "icon": "fa-robot",
        "color": "text-green-400",
        "is_default": True,
    },
    {
        "model_id": "gpt-4-turbo",
        "name": "GPT-4 Turbo",
        "provider": LLMProvider.OPENAI,
        "description": "GPT-4 Turbo - 快速響應版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 128000,
        "parameters": "~1.8T",
        "order": 40,
        "icon": "fa-robot",
        "color": "text-green-400",
    },
    {
        "model_id": "gpt-4",
        "name": "GPT-4",
        "provider": LLMProvider.OPENAI,
        "description": "GPT-4 - 強大的多模態模型",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 8192,
        "parameters": "~1.8T",
        "order": 50,
        "icon": "fa-robot",
        "color": "text-green-400",
    },
    {
        "model_id": "gpt-3.5-turbo",
        "name": "GPT-3.5 Turbo",
        "provider": LLMProvider.OPENAI,
        "description": "GPT-3.5 Turbo - 快速且經濟實惠",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 16385,
        "parameters": "~175B",
        "order": 60,
        "icon": "fa-robot",
        "color": "text-green-400",
    },
    # Google (Gemini) 模型
    {
        "model_id": "gemini-2.0-flash-exp",
        "name": "Gemini 2.0 Flash (Experimental)",
        "provider": LLMProvider.GOOGLE,
        "description": "Gemini 2.0 Flash - 實驗版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.MULTIMODAL,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.BETA,
        "context_window": 1000000,
        "order": 70,
        "icon": "fa-gem",
        "color": "text-blue-400",
    },
    {
        "model_id": "gemini-1.5-pro",
        "name": "Gemini 1.5 Pro",
        "provider": LLMProvider.GOOGLE,
        "description": "Gemini 1.5 Pro - 專業版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.MULTIMODAL,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 2000000,
        "parameters": "~540B",
        "order": 80,
        "icon": "fa-gem",
        "color": "text-blue-400",
        "is_default": True,
    },
    {
        "model_id": "gemini-pro",
        "name": "Gemini Pro",
        "provider": LLMProvider.GOOGLE,
        "description": "Gemini Pro - 標準版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 32768,
        "parameters": "~540B",
        "order": 90,
        "icon": "fa-gem",
        "color": "text-blue-400",
    },
    {
        "model_id": "gemini-ultra",
        "name": "Gemini Ultra",
        "provider": LLMProvider.GOOGLE,
        "description": "Gemini Ultra - 最強版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.MULTIMODAL,
            ModelCapability.VISION,
            ModelCapability.REASONING,
            ModelCapability.FUNCTION_CALLING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 2000000,
        "parameters": "~1.5T",
        "order": 100,
        "icon": "fa-gem",
        "color": "text-blue-400",
    },
    # Anthropic (Claude) 模型
    {
        "model_id": "claude-3.5-sonnet",
        "name": "Claude 3.5 Sonnet",
        "provider": LLMProvider.ANTHROPIC,
        "description": "Claude 3.5 Sonnet - 平衡性能和成本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.VISION,
            ModelCapability.REASONING,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 200000,
        "parameters": "~250B",
        "order": 110,
        "icon": "fa-brain",
        "color": "text-orange-400",
        "is_default": True,
    },
    {
        "model_id": "claude-3-opus",
        "name": "Claude 3 Opus",
        "provider": LLMProvider.ANTHROPIC,
        "description": "Claude 3 Opus - 最強版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.VISION,
            ModelCapability.REASONING,
            ModelCapability.FUNCTION_CALLING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 200000,
        "parameters": "~400B",
        "order": 120,
        "icon": "fa-brain",
        "color": "text-orange-400",
    },
    {
        "model_id": "claude-3-sonnet",
        "name": "Claude 3 Sonnet",
        "provider": LLMProvider.ANTHROPIC,
        "description": "Claude 3 Sonnet - 標準版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 200000,
        "parameters": "~250B",
        "order": 130,
        "icon": "fa-brain",
        "color": "text-orange-400",
    },
    {
        "model_id": "claude-3-haiku",
        "name": "Claude 3 Haiku",
        "provider": LLMProvider.ANTHROPIC,
        "description": "Claude 3 Haiku - 快速版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 200000,
        "parameters": "~80B",
        "order": 140,
        "icon": "fa-brain",
        "color": "text-orange-400",
    },
    # 阿里巴巴 (Qwen) 模型
    {
        "model_id": "qwen-2.5-72b-instruct",
        "name": "Qwen 2.5 72B Instruct",
        "provider": LLMProvider.ALIBABA,
        "description": "Qwen 2.5 72B - 大型指令模型",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 32768,
        "parameters": "72B",
        "order": 150,
        "icon": "fa-code",
        "color": "text-orange-400",
    },
    {
        "model_id": "qwen-plus",
        "name": "Qwen Plus",
        "provider": LLMProvider.ALIBABA,
        "description": "Qwen Plus - 增強版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 32000,
        "order": 160,
        "icon": "fa-code",
        "color": "text-orange-400",
        "is_default": True,
    },
    {
        "model_id": "qwen-turbo",
        "name": "Qwen Turbo",
        "provider": LLMProvider.ALIBABA,
        "description": "Qwen Turbo - 快速版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 8000,
        "order": 170,
        "icon": "fa-code",
        "color": "text-orange-400",
    },
    # xAI (Grok) 模型
    {
        "model_id": "grok-beta",
        "name": "Grok Beta",
        "provider": LLMProvider.XAI,
        "description": "Grok Beta - xAI 的對話模型",
        "capabilities": [ModelCapability.CHAT, ModelCapability.COMPLETION, ModelCapability.STREAMING],
        "status": ModelStatus.BETA,
        "context_window": 131072,
        "parameters": "~314B",
        "order": 180,
        "icon": "fa-bolt",
        "color": "text-yellow-400",
    },
    {
        "model_id": "grok-2",
        "name": "Grok-2",
        "provider": LLMProvider.XAI,
        "description": "Grok-2 - 最新版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.REASONING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 131072,
        "parameters": "~314B",
        "order": 190,
        "icon": "fa-bolt",
        "color": "text-yellow-400",
        "is_default": True,
    },
    # Mistral AI 模型
    {
        "model_id": "mistral-large",
        "name": "Mistral Large",
        "provider": LLMProvider.MISTRAL,
        "description": "Mistral Large - 大型模型",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 128000,
        "parameters": "~123B",
        "order": 250,
        "icon": "fa-wind",
        "color": "text-blue-300",
    },
    {
        "model_id": "mistral-medium",
        "name": "Mistral Medium",
        "provider": LLMProvider.MISTRAL,
        "description": "Mistral Medium - 中型模型",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 32000,
        "parameters": "~50B",
        "order": 260,
        "icon": "fa-wind",
        "color": "text-blue-300",
    },
    {
        "model_id": "mistral-small",
        "name": "Mistral Small",
        "provider": LLMProvider.MISTRAL,
        "description": "Mistral Small - 快速版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 32000,
        "parameters": "~24B",
        "order": 270,
        "icon": "fa-wind",
        "color": "text-blue-300",
    },
    # DeepSeek 模型
    {
        "model_id": "deepseek-chat",
        "name": "DeepSeek Chat",
        "provider": LLMProvider.DEEPSEEK,
        "description": "DeepSeek Chat - 對話模型",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 64000,
        "parameters": "~67B",
        "order": 280,
        "icon": "fa-search",
        "color": "text-purple-400",
    },
    {
        "model_id": "deepseek-coder",
        "name": "DeepSeek Coder",
        "provider": LLMProvider.DEEPSEEK,
        "description": "DeepSeek Coder - 代碼專用模型",
        "capabilities": [ModelCapability.CHAT, ModelCapability.CODE, ModelCapability.COMPLETION],
        "status": ModelStatus.ACTIVE,
        "context_window": 16000,
        "parameters": "~33B",
        "order": 290,
        "icon": "fa-code",
        "color": "text-purple-400",
    },
    # Databricks (DBRX) 模型
    {
        "model_id": "dbrx",
        "name": "DBRX",
        "provider": LLMProvider.DATABRICKS,
        "description": "Databricks DBRX - 專家混合模型",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 32768,
        "parameters": "132B",
        "order": 300,
        "icon": "fa-database",
        "color": "text-blue-500",
    },
    # 註：Ollama 模型會通過動態發現功能自動添加，不需要在此處手動添加
]


def migrate():
    """執行遷移"""
    print("開始遷移 LLM 模型到 ArangoDB...")
    service = get_llm_model_service()

    created_count = 0
    skipped_count = 0
    error_count = 0

    for model_data in LLM_MODELS_DATA:
        try:
            model_id = model_data["model_id"]

            # 檢查模型是否已存在
            existing = service.get_by_id(model_id)
            if existing:
                print(f"  ⏭️  跳過已存在的模型: {model_id}")
                skipped_count += 1
                continue

            # 創建模型
            model_create = LLMModelCreate(**model_data)
            service.create(model_create)
            print(f"  ✅ 創建模型: {model_id} ({model_data['name']})")
            created_count += 1

        except Exception as e:
            print(f"  ❌ 創建模型失敗 {model_data.get('model_id', 'unknown')}: {e}")
            error_count += 1

    print("\n遷移完成!")
    print(f"  ✅ 創建: {created_count} 個模型")
    print(f"  ⏭️  跳過: {skipped_count} 個模型")
    print(f"  ❌ 錯誤: {error_count} 個模型")


if __name__ == "__main__":
    migrate()

