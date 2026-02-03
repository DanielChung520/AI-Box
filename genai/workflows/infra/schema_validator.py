# 代碼功能說明: JSON Schema 驗證引擎
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""JSON Schema 驗證引擎，用於實施「註冊即防護」機制。"""

import logging
from typing import Any, Dict, Optional, Tuple

try:
    import jsonschema
    from jsonschema import validate, ValidationError

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

logger = logging.getLogger(__name__)


class SchemaValidator:
    """JSON Schema 驗證器。"""

    @staticmethod
    def validate_data(data: Any, schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        驗證數據是否符合 Schema。

        Args:
            data: 要驗證的數據
            schema: JSON Schema 定義

        Returns:
            (是否成功, 錯誤訊息),
        """
        if not JSONSCHEMA_AVAILABLE:
            logger.warning("jsonschema library not available, skipping validation.")
            return True, None

        if not schema:
            return True, None

        try:
            validate(instance=data, schema=schema)
            return True, None
        except ValidationError as e:
            error_msg = f"Schema Validation Failed: {e.message} at {list(e.path)}"
            logger.warning(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during schema validation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    @staticmethod
    def check_schema_validity(schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        檢查 Schema 定義本身是否有效。

        Args:
            schema: JSON Schema 定義

        Returns:
            (是否有效, 錯誤訊息),
        """
        if not JSONSCHEMA_AVAILABLE:
            return True, None

        try:
            jsonschema.Draft7Validator.check_schema(schema)
            return True, None
        except jsonschema.SchemaError as e:
            return False, f"Invalid JSON Schema: {e.message}"
        except Exception as e:
            return False, str(e)
