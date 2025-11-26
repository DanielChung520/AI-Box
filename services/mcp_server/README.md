# MCP Server 服務

## 概述

MCP Server 是 AI-Box 項目的 Model Context Protocol (MCP) 服務器實現，提供統一的工具調用接口，供 Agent、工具與 FastAPI 使用。

## 功能特性

- ✅ MCP Protocol 2024-11-05 標準實現
- ✅ 工具註冊和管理
- ✅ 健康檢查和監控端點
- ✅ 請求指標收集
- ✅ 配置式工具註冊
- ✅ Docker 部署支持

## 快速開始

### 本地開發

1. 安裝依賴：
```bash
pip install -r requirements.txt
```

2. 啟動服務器：
```bash
python -m services.mcp_server.main
```

3. 或使用命令行參數：
```bash
python -m services.mcp_server.main --host 0.0.0.0 --port 8002 --reload
```

### Docker 部署

使用 docker-compose：
```bash
docker-compose up mcp-server
```

## 配置

### 環境變數

| 變數名 | 描述 | 默認值 |
|--------|------|--------|
| `MCP_SERVER_NAME` | 服務器名稱 | `ai-box-mcp-server` |
| `MCP_SERVER_VERSION` | 服務器版本 | `1.0.0` |
| `MCP_PROTOCOL_VERSION` | MCP 協議版本 | `2024-11-05` |
| `MCP_SERVER_HOST` | 服務器主機地址 | `0.0.0.0` |
| `MCP_SERVER_PORT` | 服務器端口 | `8002` |
| `LOG_LEVEL` | 日誌級別 | `INFO` |
| `MCP_ENABLE_MONITORING` | 啟用監控 | `true` |
| `MCP_METRICS_ENDPOINT` | 指標端點路徑 | `/metrics` |

### 配置文件

工具配置位於 `services/mcp_server/tools/config.yaml`。

## API 端點

### MCP 協議端點

- `POST /mcp` - MCP 協議請求端點

### 健康檢查端點

- `GET /health` - 健康檢查
- `GET /ready` - 就緒檢查
- `GET /metrics` - 指標端點（如果啟用監控）

## 工具註冊

### 使用工具基類

創建新工具時，繼承 `BaseTool` 類：

```python
from services.mcp_server.tools.base import BaseTool

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="我的工具描述",
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                },
                "required": ["param1"]
            }
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # 實現工具邏輯
        return {"result": "success"}
```

### 註冊工具

在 `services/mcp_server/main.py` 的 `_register_tools` 函數中註冊工具：

```python
def _register_tools(server: MCPServer, config) -> None:
    my_tool = MyTool()
    server.register_tool(
        name=my_tool.name,
        description=my_tool.description,
        input_schema=my_tool.input_schema,
        handler=my_tool.execute,
    )
```

## 內置工具

### Task Analyzer Tool

任務分析工具（Mock 實現），用於分析任務並返回分類結果。

**工具名稱**: `task_analyzer`

**參數**:
- `task` (string, required): 要分析的任務描述
- `context` (object, optional): 任務上下文信息

**示例**:
```json
{
  "name": "task_analyzer",
  "arguments": {
    "task": "Create a plan for the project",
    "context": {}
  }
}
```

### File Tool

文件操作工具，支持讀寫、列表、刪除操作。

**工具名稱**: `file_tool`

**參數**:
- `operation` (string, required): 操作類型 (`read`, `write`, `list`, `delete`)
- `path` (string, required): 文件路徑（相對於 base_path）
- `content` (string, optional): 文件內容（僅用於 write 操作）

**示例**:
```json
{
  "name": "file_tool",
  "arguments": {
    "operation": "write",
    "path": "test.txt",
    "content": "Hello, World!"
  }
}
```

## 測試

### 運行單元測試

```bash
pytest tests/mcp/
```

### 運行自動化測試腳本

```bash
# Shell 腳本
./scripts/test_mcp.sh

# Python 腳本（更詳細）
python scripts/test_mcp.py
```

## 監控

如果啟用監控（`MCP_ENABLE_MONITORING=true`），可以通過 `/metrics` 端點獲取指標：

```bash
curl http://localhost:8002/metrics
```

指標包括：
- 總請求數
- 錯誤數和錯誤率
- 平均延遲
- 各方法的統計信息

## 開發指南

### 項目結構

```
services/mcp_server/
├── __init__.py
├── main.py              # 啟動入口
├── config.py            # 配置管理
├── monitoring.py        # 監控模組
├── tools/               # 工具目錄
│   ├── __init__.py
│   ├── base.py         # 工具基類
│   ├── registry.py     # 工具註冊表
│   ├── task_analyzer.py
│   ├── file_tool.py
│   └── config.yaml     # 工具配置
└── README.md
```

### 添加新工具

1. 在 `services/mcp_server/tools/` 目錄創建新工具文件
2. 繼承 `BaseTool` 類並實現 `execute` 方法
3. 在 `main.py` 的 `_register_tools` 函數中註冊工具
4. 更新 `tools/config.yaml`（可選）

## 故障排除

### 服務器無法啟動

- 檢查端口是否被占用：`lsof -i :8002`
- 檢查日誌輸出：查看控制台或日誌文件

### 工具調用失敗

- 檢查工具是否已註冊：`GET /mcp` 調用 `tools/list` 方法
- 檢查工具參數是否符合 input_schema
- 查看服務器日誌獲取詳細錯誤信息

## 相關文檔

- [MCP Protocol 規範](https://modelcontextprotocol.io)
- [項目主 README](../README.md)
- [WBS 1.2 計劃](../../docs/plans/phase1/wbs-1.2-mcp-platform.md)

## 許可證

[待定]
