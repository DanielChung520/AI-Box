# Web 搜索工具 ArangoDB 註冊說明

**創建日期**: 2025-12-30
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-30

---

## 📋 概述

`web_search` 工具已經在 JSON 文件中註冊（`tools/tools_registry.json`），但需要同步到 ArangoDB 的 `tools_registry` collection 中，以便任務分析時能夠發現該工具的能力。

---

## ✅ 確認事項

### 1. 工具註冊表存儲機制

根據項目設計：

- **主要存儲**: ArangoDB Collection `tools_registry`
- **備份存儲**: JSON 文件 `tools/tools_registry.json`
- **載入優先級**: 優先從 ArangoDB 讀取，回退到 JSON

### 2. 任務分析能力發現

任務分析器通過 `tools/registry_loader.py` 中的 `get_tools_for_task_analysis()` 函數獲取工具清單：

```python
from tools.registry_loader import get_tools_for_task_analysis

# 獲取所有工具（用於任務分析）
tools_info = get_tools_for_task_analysis()
```

該函數會：

1. 優先從 ArangoDB 讀取工具註冊清單
2. 如果 ArangoDB 不可用，回退到 JSON 文件
3. 返回格式化的工具清單，包含每個工具的用途、使用場景等信息

---

## 🔧 註冊方式

### 方式一：通過 API 註冊（推薦）

使用 `POST /api/v1/tools/registry` API 接口：

```bash
curl -X POST "http://localhost:8000/api/v1/tools/registry" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "web_search",
    "version": "1.0.0",
    "category": "網絡搜索",
    "description": "執行 Web 搜索，支持多個搜索提供商的自動降級（Serper -> SerpAPI -> ScraperAPI -> Google CSE）",
    "purpose": "提供統一的 Web 搜索功能，自動選擇可用的搜索提供商，確保搜索服務的高可用性",
    "use_cases": [
      "用戶詢問實時信息或最新資訊 → 使用 web_search 搜索網絡",
      "需要獲取當前事件、新聞或趨勢 → 使用 web_search",
      "本地知識庫無法回答的問題 → 使用 web_search 補充信息",
      "需要驗證或查找最新資料 → 使用 web_search"
    ],
    "input_parameters": {
      "query": {
        "type": "str",
        "required": true,
        "description": "搜索查詢字符串"
      },
      "num": {
        "type": "int",
        "required": false,
        "default": 10,
        "description": "結果數量（1-100）"
      },
      "location": {
        "type": "Optional[str]",
        "required": false,
        "default": null,
        "description": "地理位置（可選，如 \"Taiwan\"）"
      }
    },
    "output_fields": {
      "query": "搜索查詢",
      "provider": "使用的搜索提供商（serper/serpapi/scraper/google_cse）",
      "results": "搜索結果列表，每個結果包含 title、link、snippet、type、position",
      "total": "結果總數",
      "status": "搜索狀態（success/failed）"
    },
    "example_scenarios": [
      "用戶詢問：『最新的人工智能發展是什麼？』→ 使用 web_search 搜索最新資訊",
      "需要查找特定產品的價格或規格 → 使用 web_search 搜索",
      "驗證某個事實或數據 → 使用 web_search 查找權威來源",
      "查找實時新聞或事件 → 使用 web_search 獲取最新信息"
    ]
  }'
```

### 方式二：通過 Python 腳本註冊

創建腳本 `scripts/sync_web_search_to_arangodb.py`：

```python
#!/usr/bin/env python3
"""將 web_search 工具從 JSON 同步到 ArangoDB"""

import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.api.models.tool_registry import ToolRegistryCreate
from services.api.services.tool_registry_store_service import (
    get_tool_registry_store_service,
)

# 從 JSON 加載
json_path = project_root / "tools" / "tools_registry.json"
with open(json_path, "r", encoding="utf-8") as f:
    registry = json.load(f)

# 找到 web_search 工具
tool_data = next(t for t in registry["tools"] if t["name"] == "web_search")

# 創建工具註冊記錄
tool_create = ToolRegistryCreate(
    name=tool_data["name"],
    version=tool_data["version"],
    category=tool_data["category"],
    description=tool_data["description"],
    purpose=tool_data["purpose"],
    use_cases=tool_data["use_cases"],
    input_parameters=tool_data["input_parameters"],
    output_fields=tool_data["output_fields"],
    example_scenarios=tool_data["example_scenarios"],
)

# 註冊到 ArangoDB
service = get_tool_registry_store_service()

# 檢查是否已存在
existing = service.get_tool("web_search")
if existing:
    print(f"工具已存在，版本: {existing.version}")
    # 如果需要更新，使用 update_tool
else:
    created = service.create_tool(tool_create)
    print(f"✓ 工具註冊成功: {created.name} (版本: {created.version})")
```

執行腳本：

```bash
cd /Users/daniel/GitHub/AI-Box
python scripts/sync_web_search_to_arangodb.py
```

### 方式三：通過 Python REPL 註冊

```python
from services.api.models.tool_registry import ToolRegistryCreate
from services.api.services.tool_registry_store_service import (
    get_tool_registry_store_service,
)
import json

# 從 JSON 加載
with open("tools/tools_registry.json", "r", encoding="utf-8") as f:
    registry = json.load(f)

tool_data = next(t for t in registry["tools"] if t["name"] == "web_search")

tool_create = ToolRegistryCreate(
    name=tool_data["name"],
    version=tool_data["version"],
    category=tool_data["category"],
    description=tool_data["description"],
    purpose=tool_data["purpose"],
    use_cases=tool_data["use_cases"],
    input_parameters=tool_data["input_parameters"],
    output_fields=tool_data["output_fields"],
    example_scenarios=tool_data["example_scenarios"],
)

service = get_tool_registry_store_service()
created = service.create_tool(tool_create)
print(f"✓ 註冊成功: {created.name}")
```

---

## ✅ 驗證註冊

### 1. 通過 API 查詢

```bash
# 查詢 web_search 工具
curl "http://localhost:8000/api/v1/tools/registry/web_search"

# 列出所有工具
curl "http://localhost:8000/api/v1/tools/registry"

# 按類別查詢
curl "http://localhost:8000/api/v1/tools/registry?category=網絡搜索"
```

### 2. 通過 Python 驗證

```python
from tools.registry_loader import get_tool_info, get_tools_for_task_analysis

# 獲取 web_search 工具信息
tool_info = get_tool_info("web_search")
print(tool_info)

# 獲取所有工具（用於任務分析）
all_tools = get_tools_for_task_analysis()
web_search = next(t for t in all_tools["tools"] if t["name"] == "web_search")
print(web_search)
```

---

## 📊 任務分析中的能力發現

當任務分析器執行時，會通過以下流程發現工具能力：

1. **調用 `get_tools_for_task_analysis()`**
   - 優先從 ArangoDB 讀取
   - 回退到 JSON 文件

2. **獲取工具清單**
   - 包含所有工具的用途、使用場景、輸入參數、輸出字段等

3. **能力匹配**
   - 根據任務需求匹配合適的工具
   - `web_search` 工具會被識別為「網絡搜索」能力

4. **工具選擇**
   - 當任務需要實時信息、最新資訊、網絡搜索時
   - 任務分析器會選擇 `web_search` 工具

---

## 🔍 相關代碼位置

- **工具註冊表 Store Service**: `services/api/services/tool_registry_store_service.py`
- **工具註冊表 API**: `api/routers/tools_registry.py`
- **工具註冊表載入器**: `tools/registry_loader.py`
- **工具註冊表模型**: `services/api/models/tool_registry.py`
- **JSON 文件**: `tools/tools_registry.json`

---

## 📝 注意事項

1. **JSON 文件作為備份**
   - JSON 文件保留作為備份和初始數據源
   - 新增工具時，建議同時更新 JSON 和 ArangoDB

2. **版本管理**
   - 更新工具時，記得更新版本號
   - 使用 `ToolRegistryUpdate` 模型更新現有工具

3. **多租戶支持**
   - `tools_registry` collection 是全局共享的（非多租戶）
   - 所有租戶共享同一套工具註冊清單

4. **任務分析優先級**
   - 任務分析器優先從 ArangoDB 讀取
   - 確保 ArangoDB 中的數據是最新的

---

**最後更新日期**: 2025-12-30
**維護人**: Daniel Chung
