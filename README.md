# AI-Box

Agent AI Box 系統 - 基於 GenAI 的智能代理系統

**版本**: 0.1.0  
**創建日期**: 2025-01-27  
**創建人**: Daniel Chung  
**最後修改日期**: 2025-01-27

---

## 項目簡介

AI-Box 是一個基於 GenAI 的智能代理系統，整合了多種 AI 技術棧，實現從用戶請求到任務執行的端到端智能處理流程。

## 快速開始

### 前置要求

- Python 3.11+
- Node.js 18+
- Docker Desktop
- Git 2.40+

### 環境設置

1. 克隆倉庫
   ```bash
   git clone https://github.com/[username]/AI-Box.git
   cd AI-Box
   ```

2. 設置開發環境
   ```bash
   ./scripts/setup_dev_env.sh
   ```

3. 驗證環境
   ```bash
   ./scripts/verify_env.sh
   ```

4. 激活虛擬環境
   ```bash
   source venv/bin/activate
   ```

## 項目結構

```
AI-Box/
├── docs/                    # 文檔目錄
│   ├── plans/              # 計劃文檔
│   └── progress/           # 進度報告
├── scripts/                 # 腳本目錄
│   ├── setup_dev_env.sh    # 環境設置腳本
│   └── verify_env.sh       # 環境驗證腳本
└── README.md               # 本文件
```

## 開發規範

請參考 `.cursor/rules/develop-rule.mdc` 了解開發規範。

## 貢獻指南

請參考 `CONTRIBUTING.md` 了解如何貢獻代碼。

## 許可證

[待定]

## 聯繫方式

- **項目負責人**: Daniel Chung
- **郵箱**: daniel.chung@example.com

---

**最後更新**: 2025-01-27

