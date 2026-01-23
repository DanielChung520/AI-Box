#!/usr/bin/env python3
# 代碼功能說明: LLM 模型遷移到 ArangoDB 遷移腳本
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-22

"""
將前端硬編碼的 LLM 模型列表遷移到 ArangoDB
並更新狀態為 ACTIVE

使用方法:
    python -m services.api.services.migrations.migrate_llm_models
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.api.models.llm_model import (  # noqa: E402
    LLMModelCreate,
    LLMModelUpdate,
    LLMProvider,
    ModelCapability,
    ModelStatus,
)
from services.api.services.llm_model_service import get_llm_model_service  # noqa: E402

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
    # Ollama 模型 (手動添加)
    {
        "model_id": "gpt-oss:120b-cloud",
        "name": "GPT-OSS 120B Cloud",
        "provider": LLMProvider.OLLAMA,
        "description": "GPT-OSS 120B 雲端託管版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "order": 5,
        "icon": "fa-cloud",
        "color": "text-blue-500",
    },
    {
        "model_id": "gpt-oss:20b",
        "name": "GPT-OSS 20B",
        "provider": LLMProvider.OLLAMA,
        "description": "GPT-OSS 20B 本地版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "order": 6,
        "icon": "fa-microchip",
        "color": "text-blue-400",
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
    # Google (Gemini) 模型
    {
        "model_id": "gemini-3-pro-preview",
        "name": "Gemini 3 Pro (Preview)",
        "provider": LLMProvider.GOOGLE,
        "description": "Gemini 3 Pro - 最新旗艦模型",
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
        "order": 65,
        "icon": "fa-gem",
        "color": "text-blue-400",
        "is_default": True,
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
    # 智譜 AI (ChatGLM) 模型
    {
        "model_id": "glm-4",
        "name": "GLM-4",
        "provider": LLMProvider.CHATGLM,
        "description": "GLM-4 - 智譜 AI 最新對話模型",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 128000,
        "order": 310,
        "icon": "fa-brain",
        "color": "text-blue-600",
        "is_default": True,
    },
    {
        "model_id": "glm-4v",
        "name": "GLM-4V",
        "provider": LLMProvider.CHATGLM,
        "description": "GLM-4V - 智譜 AI 多模態視覺模型",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.MULTIMODAL,
            ModelCapability.VISION,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 128000,
        "order": 320,
        "icon": "fa-eye",
        "color": "text-blue-600",
    },
    {
        "model_id": "glm-3-turbo",
        "name": "GLM-3 Turbo",
        "provider": LLMProvider.CHATGLM,
        "description": "GLM-3 Turbo - 快速版本",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 32000,
        "order": 330,
        "icon": "fa-bolt",
        "color": "text-blue-600",
    },
    # 字節跳動火山引擎 (Volcano Engine / Doubao) 模型
    {
        "model_id": "doubao-pro-4k",
        "name": "豆包 Pro 4K",
        "provider": LLMProvider.VOLCANO,
        "description": "豆包 Pro 4K - 火山引擎專業版模型（4K 上下文）",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 4096,
        "order": 340,
        "icon": "fa-fire",
        "color": "text-orange-500",
        "is_default": True,
    },
    {
        "model_id": "doubao-pro-32k",
        "name": "豆包 Pro 32K",
        "provider": LLMProvider.VOLCANO,
        "description": "豆包 Pro 32K - 火山引擎專業版模型（32K 上下文）",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 32768,
        "order": 350,
        "icon": "fa-fire",
        "color": "text-orange-500",
    },
    {
        "model_id": "doubao-lite-4k",
        "name": "豆包 Lite 4K",
        "provider": LLMProvider.VOLCANO,
        "description": "豆包 Lite 4K - 火山引擎輕量版模型（4K 上下文）",
        "capabilities": [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.STREAMING,
        ],
        "status": ModelStatus.ACTIVE,
        "context_window": 4096,
        "order": 360,
        "icon": "fa-fire",
        "color": "text-orange-400",
    },
]


def migrate():
    """執行遷移"""
    print("開始遷移並激活 LLM 模型到 ArangoDB...")
    service = get_llm_model_service()

    created_count = 0
    updated_count = 0
    error_count = 0

    for model_data in LLM_MODELS_DATA:
        try:
            model_id = model_data["model_id"]

            # 檢查模型是否已存在
            existing = service.get_by_id(model_id)
            if existing:
                # 更新現有模型為 ACTIVE 並更新其他屬性
                update_req = LLMModelUpdate(
                    **{k: v for k, v in model_data.items() if k != "model_id"}
                )
                update_req.status = ModelStatus.ACTIVE
                service.update(model_id, update_req)
                print(f"  🔄 更新並激活模型: {model_id}")
                updated_count += 1
                continue

            # 創建模型
            model_create = LLMModelCreate(**model_data)
            service.create(model_create)
            print(f"  ✅ 創建並激活模型: {model_id} ({model_data['name']})")
            created_count += 1

        except Exception as e:
            print(f"  ❌ 處理模型失敗 {model_data.get('model_id', 'unknown')}: {e}")
            error_count += 1

    print("\n遷移與激活完成!")
    print(f"  ✅ 創建: {created_count} 個模型")
    print(f"  🔄 更新: {updated_count} 個模型")
    print(f"  ❌ 錯誤: {error_count} 個模型")


if __name__ == "__main__":
    migrate()
