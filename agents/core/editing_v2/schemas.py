# 代碼功能說明: JSON Schema 定義
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""JSON Schema 定義

定義 Intent DSL、DocumentContext、Constraints、Target Selector 的 JSON Schema。
"""

from typing import Any, Dict

# Intent DSL JSON Schema
INTENT_DSL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["intent_id", "intent_type", "target_selector", "action"],
    "properties": {
        "intent_id": {"type": "string"},
        "intent_type": {
            "type": "string",
            "enum": ["insert", "update", "delete", "move", "replace"],
        },
        "target_selector": {
            "type": "object",
            "required": ["type", "selector"],
            "properties": {
                "type": {"type": "string", "enum": ["heading", "anchor", "block"]},
                "selector": {"type": "object"},
            },
        },
        "action": {
            "type": "object",
            "required": ["mode"],
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["insert", "update", "delete", "move", "replace"],
                },
                "content": {"type": "string"},
                "position": {
                    "type": "string",
                    "enum": ["before", "after", "inside", "start", "end"],
                },
            },
        },
        "constraints": {
            "type": "object",
            "properties": {
                "max_tokens": {"type": "integer", "minimum": 1},
                "style_guide": {"type": "string"},
                "no_external_reference": {"type": "boolean"},
            },
        },
    },
}

# DocumentContext JSON Schema
DOCUMENT_CONTEXT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["doc_id", "file_path", "task_id", "user_id"],
    "properties": {
        "doc_id": {"type": "string"},
        "version_id": {"type": "string"},
        "file_path": {"type": "string"},
        "task_id": {"type": "string"},
        "user_id": {"type": "string"},
        "tenant_id": {"type": "string"},
    },
}

# Constraints JSON Schema
CONSTRAINTS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "max_tokens": {"type": "integer", "minimum": 1},
        "style_guide": {"type": "string"},
        "no_external_reference": {"type": "boolean"},
    },
}

# Target Selector JSON Schema (Heading)
HEADING_SELECTOR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "level": {"type": "integer", "minimum": 1, "maximum": 6},
        "occurrence": {"type": "integer", "minimum": 1},
        "path": {"type": "array", "items": {"type": "string"}},
    },
}

# Target Selector JSON Schema (Anchor)
ANCHOR_SELECTOR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["anchor_id"],
    "properties": {
        "anchor_id": {"type": "string"},
    },
}

# Target Selector JSON Schema (Block)
BLOCK_SELECTOR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["block_id"],
    "properties": {
        "block_id": {"type": "string"},
    },
}
