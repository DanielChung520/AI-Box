# 代碼功能說明: GenAI 租戶（Tenant/Org）政策模型
# 創建日期: 2025-12-13 23:34:17 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 23:34:17 (UTC+8)

"""GenAI Tenant/Org policy models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GenAITenantPolicyUpdate(BaseModel):
    """租戶政策更新（僅允許覆蓋/收斂系統政策，不允許擴權）。"""

    allowed_providers: Optional[List[str]] = Field(
        default=None,
        description="允許的 provider（如 chatgpt/gemini/qwen/grok/ollama）",
    )
    allowed_models: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="允許的模型（per-provider patterns）。key=provider value=[pattern...]",
    )
    default_fallback: Optional[Dict[str, str]] = Field(
        default=None,
        description="預設 fallback 設定（例如 {provider: 'ollama', model: 'llama3.1:8b'}）",
    )
    model_registry_models: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="租戶額外的模型清單項（會併入 model registry，需通過 policy filter）",
    )


class GenAITenantPolicy(BaseModel):
    """租戶政策（對外可讀，無敏感資訊）。"""

    tenant_id: str
    allowed_providers: List[str] = Field(default_factory=list)
    allowed_models: Dict[str, List[str]] = Field(default_factory=dict)
    default_fallback: Optional[Dict[str, str]] = None
    model_registry_models: List[Dict[str, Any]] = Field(default_factory=list)
    updated_at: datetime
