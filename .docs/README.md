# AI-Box 交付文檔

**版本**: 1.1  
**日期**: 2026-02-27  
**目的**: 系統交付規格文檔

---

## 目錄結構

```
.docs/
├── 01-功能清單/
│   └── 01-功能清單.md        # 完整功能列表
├── 02-SRS-規格書/
│   ├── SRS-01-Agent平台核心架構.md   # Agent 平台核心架構
│   ├── SRS-02-意圖分類與任務路由.md  # 意圖分類與任務路由
│   ├── SRS-03-數據查詢服務.md        # 數據查詢服務 (Schema-Driven)
│   ├── SRS-04-文件編輯服務.md        # 文件編輯服務
│   ├── SRS-05-知識圖譜服務.md        # 知識圖譜服務
│   ├── SRS-06-存儲服務.md           # 存儲服務
│   ├── SRS-07-MoE模型路由.md        # MoE 模型路由
│   ├── SRS-10-上下文管理服務.md     # 上下文管理
│   ├── SRS-20-記憶管理服務.md        # 記憶管理
│   ├── SRS-30-多輪對話服務.md        # 多輪對話
│   └── SRS-40-鏈式處理與編排.md     # 鏈式處理與編排
└── README.md
```

---

## SRS 文件結構 (依據 IEEE/SRS 規範)

每個 SRS 文件包含以下章節：

1. **產品目的 (Product Purpose)** - 核心聲明、產品願景
2. **產品概覽 (Product Overview)** - 目標用戶、技術棧、運行環境
3. **功能需求 (Functional Requirements)** - 核心功能、組件清單 (Level 3-4)
4. **性能要求 (Performance Requirements)** - 響應時間、吞吐量、擴展性
5. **非功能性需求 (Non-Functional Requirements)** - 安全性、可靠性、可用性、維護性
6. **外部接口 (External Interfaces)** - API 接口、數據格式
7. **設計約束與假設 (Design Constraints & Assumptions)** - 技術約束、環境約束、假設條件
8. **質量標準 (Quality Standards)** - 可靠性指標、錯誤容忍
9. **錯誤碼詳細定義** - 各模組錯誤碼
10. **API 詳細規格** - 端點、請求/響應格式
11. **驗收標準** - 功能、性能、安全驗收

---

## 交付內容

### 1. 功能清單 (01-功能清單)
- 17 個內建 Agent
- 14 個服務層模組
- 14 個主要 API
- 5 個數據存儲
- 5 個 LLM 整合
- 6 個前端組件

### 2. SRS 規格書 (02-SRS-規格書)

| 編號 | 名稱 | 內容 |
|------|------|------|
| SRS-01 | Agent 平台核心架構 | 協調、意圖分類、政策引擎、狀態存儲 |
| SRS-02 | 意圖分類與任務路由 | MM-Agent、任務分析、路由邏輯 |
| SRS-03 | 數據查詢服務 | Schema-Driven Query、Intent 解析、SQL 生成 |
| SRS-04 | 文件編輯服務 | Markdown/Excel 編輯、格式轉換、會話管理 |
| SRS-05 | 知識圖譜服務 | 本體管理、NER/RE/RT、圖譜構建查詢 |
| SRS-06 | 存儲服務 | S3 文件、向量、圖數據、緩存 |
| SRS-07 | MoE 模型路由 | 場景路由、用戶偏好、成本控制 |
| SRS-10 | 上下文管理服務 | 對話/任務上下文維護 |
| SRS-20 | 記憶管理服務 | 短期/長期記憶分層管理 |
| SRS-30 | 多輪對話服務 | 對話歷史、狀態、澄清 |
| SRS-40 | 鏈式處理與編排 | 工作流引擎、混合編排 |

---

## 規範符合度

本文檔依據以下規範編制：

- **IEEE 830** - Software Requirements Specification
- **SRS 規範** - https://srs.pub/theory/srs-guid.html

### 檢查清單

- [x] 產品目的 (Product Purpose)
- [x] 產品概覽 (Product Overview)
- [x] 功能需求 (Functional Requirements) - Level 3-4 顆粒度
- [x] 性能要求 (Performance Requirements)
- [x] 非功能性需求 (Non-Functional Requirements)
- [x] 外部接口 (External Interfaces)
- [x] 設計約束與假設 (Design Constraints & Assumptions)
- [x] 質量標準 (Quality Standards)
- [x] 安全規範 (Security Requirements)
- [x] 錯誤碼詳細定義 (Error Code Definitions)
- [x] API 詳細規格 (API Specifications)
- [x] 驗收標準 (Acceptance Criteria)

---

## 技術約定

- **語言**: 繁體中文
- **圖表**: Mermaid 8.8.8 保守版本
- **編號格式**: SRS-XX-功能名稱
- **版本**: 1.x (持續更新)

---

## 依據

本文檔依據 `/home/daniel/ai-box/` 目錄下的實際代碼產出。
