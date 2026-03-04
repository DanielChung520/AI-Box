# LINE Bot 整合文檔

## 概述

本模組提供 LINE Messaging API 整合，讓用戶可以透過 LINE 與 AI-Box 對話。

## 目錄結構

```
line_integration/
├── agents/                  # Agent 適配器
│   ├── __init__.py
│   ├── base.py            # 基礎 Agent 介面
│   └── mm_agent.py        # MM-Agent 適配器
│
├── storage/                # 持久化存儲
│   ├── __init__.py
│   └── chat_store.py      # ArangoDB 對話存儲
│
├── line_bot/
│   ├── __init__.py
│   ├── client.py          # 主客戶端
│   └── router.py          # Agent 路由器
│
├── docs/
│   ├── README.md
│   └── 計劃.md
│
└── .env.example
```

```
line/
├── line_bot/              # LINE Bot 服務
│   ├── __init__.py
│   └── client.py          # LINE Bot 客戶端
├── docs/                  # 文檔
│   └── README.md         # 本文件
└── .env.example           # 環境變數示例
```

## 環境變數

| 變數 | 說明 | 必填 |
|------|------|------|
| `LINE_CHANNEL_ID` | LINE Channel ID | ✅ |
| `LINE_CHANNEL_SECRET` | LINE Channel Secret | ✅ |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Access Token | ✅ |
| `LINE_MM_AGENT_URL` | MM-Agent URL (預設 http://localhost:8003) | ❌ |

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v1/line/webhook` | LINE Webhook 接收端點 |
| GET | `/api/v1/line/webhook` | Webhook 驗證端點 |

## 工作流程

```
LINE 用戶發訊息
    ↓
LINE Platform 發送 Webhook
    ↓
API Server (8000) /api/v1/line/webhook
    ↓
LineBotClient 處理訊息
    ↓
調用 MM-Agent (8003) /execute
    ↓
回覆訊息到 LINE
```

## 相關文件

- [計劃](./計劃.md)
