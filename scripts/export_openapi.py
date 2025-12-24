# 代碼功能說明: OpenAPI 文檔導出腳本
# 創建日期: 2025-11-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""導出 OpenAPI JSON 文檔用於 CI/CD 檢查"""

import json
import sys
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.api.main import app  # noqa: E402


def export_openapi():
    """導出 OpenAPI JSON 文檔"""
    # 獲取 OpenAPI schema
    openapi_schema = app.openapi()

    # 確保 docs 目錄存在
    docs_dir = project_root / "docs"
    docs_dir.mkdir(exist_ok=True)

    # 導出到 docs/openapi.json
    output_file = docs_dir / "openapi.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

    print(f"✅ OpenAPI schema exported to {output_file}")
    return output_file


if __name__ == "__main__":
    try:
        export_openapi()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to export OpenAPI schema: {e}", file=sys.stderr)
        sys.exit(1)
