# 代碼功能說明: Document Editing Agent v2.0
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Document Editing Agent v2.0

基於 Intent DSL 和 Block Patch 的結構化文件編輯 Agent。
"""

# 延遲導入以避免循環導入
# from .agent import DocumentEditingAgentV2
from .models import (
    Action,
    BlockPatch,
    BlockPatchOperation,
    Constraints,
    DocumentContext,
    EditIntent,
    PatchResponse,
    TargetSelector,
)

__all__ = [
    # "DocumentEditingAgentV2",  # 延遲導入
    "DocumentContext",
    "EditIntent",
    "PatchResponse",
    "TargetSelector",
    "Action",
    "Constraints",
    "BlockPatch",
    "BlockPatchOperation",
]
