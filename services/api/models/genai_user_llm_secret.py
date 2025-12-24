# 代碼功能說明: GenAI 使用者 LLM Secret（API Key）模型
# 創建日期: 2025-12-13 23:34:17 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 23:34:17 (UTC+8)

"""GenAI user secret models (API keys, etc.).

注意：
- API 只回傳「是否已配置」狀態，不回傳明文 key
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class GenAIUserLLMSecretUpsertRequest(BaseModel):
    """Upsert 使用者 provider API key。"""

    keys: Dict[str, str] = Field(
        default_factory=dict,
        description="provider -> api_key（例如 {chatgpt: 'sk-...', gemini: '...'}）",
    )


class GenAIUserLLMSecretStatusResponse(BaseModel):
    """回傳使用者各 provider 是否已配置 key。"""

    tenant_id: str
    user_id: str
    configured_providers: List[str] = Field(default_factory=list)
    updated_at: Optional[datetime] = None
