# Web 搜索工具實現說明

**創建日期**: 2025-12-30
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-30

---

## 📋 概述

本文檔說明 Web 搜索工具的實現，包括抽象層設計、多提供商支持和自動降級機制。

---

## 🏗️ 架構設計

### 設計理念

```
AI Agent
    ↓
WebSearchTool (工具層)
    ↓
WebSearchService (抽象層)
    ↓
┌─────────────────────────────┐
│ Provider Selection Strategy │
└─────────────────────────────┘
    ↓
優先級鏈（自動降級）：
1. SerperProvider     ← 首選（便宜快速）
2. SerpAPIProvider    ← 備用（功能全）
3. ScraperProvider    ← 備用（大量爬取）
4. GoogleCSEProvider  ← 最後（官方但貴）
```

### 目錄結構

```
tools/web_search/
├── __init__.py                 # 模組初始化
├── web_search_tool.py          # WebSearchTool 工具類
├── search_service.py            # WebSearchService 抽象層
└── providers/
    ├── __init__.py
    ├── base.py                 # SearchProviderBase 抽象基類
    ├── serper.py               # Serper.dev 提供商
    ├── serpapi.py             # SerpAPI 提供商
    ├── scraper.py             # ScraperAPI 提供商
    └── google_cse.py          # Google CSE 提供商
```

---

## 🔧 實現細節

### 1. 抽象基類 (base.py)

**SearchProviderBase** 定義了所有搜索提供商的統一接口：

- `search()`: 執行搜索（抽象方法，子類必須實現）
- `_parse_response()`: 解析響應為統一格式（抽象方法）
- `_make_request()`: 通用 HTTP 請求封裝（提供默認實現）

**統一返回格式**：

```python
{
    "status": SearchStatus.SUCCESS | SearchStatus.FAILED,
    "provider": SearchProvider.SERPER | ...,
    "results": [
        {
            "title": "...",
            "link": "...",
            "snippet": "...",
            "type": "organic" | "answer_box",
            "position": 1
        }
    ],
    "total": 10
}
```

### 2. 搜索提供商實現

#### SerperProvider (serper.py)

- **API**: `https://google.serper.dev/search`
- **認證**: Header `X-API-KEY`
- **特點**: 快速、便宜、支持答案框
- **環境變數**: `SERPER_API_KEY`

#### SerpAPIProvider (serpapi.py)

- **API**: `https://serpapi.com/search`
- **認證**: URL 參數 `api_key`
- **特點**: 功能完整、支持多種結果類型
- **環境變數**: `SERPAPI_API_KEY`

#### ScraperProvider (scraper.py)

- **API**: `http://api.scraperapi.com`
- **認證**: URL 參數 `api_key`
- **特點**: 通用爬蟲服務，可爬取 Google 搜索頁面
- **環境變數**: `SCRAPER_API_KEY`
- **注意**: 需要 HTML 解析（目前為簡化實現）

#### GoogleCSEProvider (google_cse.py)

- **API**: `https://www.googleapis.com/customsearch/v1`
- **認證**: URL 參數 `key` 和 `cx`
- **特點**: 官方 API，但價格較高且限制較多（最多 10 個結果）
- **環境變數**: `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_CX`

### 3. WebSearchService (抽象層)

**功能**：

- 自動初始化可用的提供商（按優先級）
- 執行搜索時自動降級（Fallback）
- 從環境變數或配置字典加載提供商配置

**使用方式**：

```python
# 方式 1: 從環境變數自動加載
service = WebSearchService()

# 方式 2: 手動配置
config = {
    'serper': {'api_key': 'xxx', 'enabled': True},
    'serpapi': {'api_key': 'xxx', 'enabled': True},
    'google_cse': {'api_key': 'xxx', 'cx': 'xxx', 'enabled': False}
}
service = WebSearchService(config)
```

### 4. WebSearchTool (工具層)

**繼承**: `BaseTool[WebSearchInput, WebSearchOutput]`

**輸入參數** (WebSearchInput):

- `query`: 搜索查詢（必填）
- `num`: 結果數量（1-100，默認 10）
- `location`: 地理位置（可選）

**輸出結果** (WebSearchOutput):

- `query`: 搜索查詢
- `provider`: 使用的提供商名稱
- `results`: 搜索結果列表
- `total`: 結果總數
- `status`: 搜索狀態

**緩存**: 30 分鐘（1800 秒）

---

## 🔑 API 密鑰配置

### 環境變數

在 `.env` 文件中配置：

```bash
# Serper.dev
SERPER_API_KEY=3a107488cd6b66099480e4e79f3dcb9fca9df6be

# SerpAPI
SERPAPI_API_KEY=d17168d378c27078fce0afbdfa513dfcce6511b43f4814511a4eb962600f943f

# ScraperAPI
SCRAPER_API_KEY=680f748560f6f3379d80caae88a630a0

# Google Custom Search Engine
GOOGLE_CSE_API_KEY=AIzaSyDdVtA9W9yzCrgn-lbPpfaCA94IudEZirc
GOOGLE_CSE_CX=56c53c7b593564e30
```

### Google CSE 設置

1. 訪問 [Google Cloud Console](https://console.cloud.google.com)
2. 創建 Custom Search Engine
3. 獲取 API Key 和 Search Engine ID (CX)
4. 公開網址: <https://cse.google.com/cse?cx=56c53c7b593564e30>

---

## 📝 使用示例

### 基本使用

```python
from tools.web_search import WebSearchTool, WebSearchInput

# 創建工具實例
tool = WebSearchTool()

# 執行搜索
result = await tool.execute(WebSearchInput(
    query="人工智能最新發展",
    num=5,
    location="Taiwan"
))

# 處理結果
print(f"使用提供商: {result.provider}")
print(f"找到 {result.total} 個結果:")
for item in result.results:
    print(f"- {item.title}: {item.link}")
    print(f"  {item.snippet}")
```

### 在 AI Agent 中使用

```python
from tools import get_tool_registry

# 註冊工具
registry = get_tool_registry()
tool = registry.get("web_search")

# 執行搜索
result = await tool.execute({
    "query": "Python async programming",
    "num": 10
})
```

---

## 🔄 自動降級機制

當搜索請求執行時：

1. **嘗試 SerperProvider**（首選）
   - 成功 → 返回結果
   - 失敗 → 繼續下一個

2. **嘗試 SerpAPIProvider**（備用）
   - 成功 → 返回結果
   - 失敗 → 繼續下一個

3. **嘗試 ScraperProvider**（備用）
   - 成功 → 返回結果
   - 失敗 → 繼續下一個

4. **嘗試 GoogleCSEProvider**（最後）
   - 成功 → 返回結果
   - 失敗 → 返回錯誤

**日誌記錄**：

- 每個提供商的嘗試都會記錄日誌
- 成功時記錄使用的提供商
- 失敗時記錄錯誤信息並嘗試下一個

---

## ✅ 代碼質量檢查

已通過以下檢查：

- ✅ **Black**: 代碼格式化
- ✅ **Ruff**: 代碼風格檢查（已自動修復 10 個問題）
- ✅ **Mypy**: 類型檢查（web_search 目錄無錯誤）

---

## 📊 工具註冊清單

已更新 `tools/tools_registry.json`，添加了 `web_search` 工具的完整說明：

- 工具名稱: `web_search`
- 版本: `1.0.0`
- 類別: `網絡搜索`
- 輸入參數、輸出字段、使用場景等完整文檔

---

## 🚀 後續改進

1. **ScraperProvider HTML 解析**
   - 實現完整的 HTML 解析邏輯
   - 使用 BeautifulSoup 解析 Google 搜索結果頁面

2. **結果排序和去重**
   - 實現結果去重邏輯
   - 支持自定義排序規則

3. **並發搜索**
   - 支持同時查詢多個提供商
   - 選擇最快返回的結果

4. **結果過濾**
   - 支持按域名、語言等過濾結果
   - 支持排除特定網站

---

## 📚 相關文檔

- [工具 API 文檔](./工具API文档.md)
- [工具使用指南](./工具使用指南.md)
- [工具註冊清單說明](./工具註冊清單說明.md)
- [工具組開發規格](./工具組開發規格.md)

---

**最後更新日期**: 2025-12-30
**維護人**: Daniel Chung
