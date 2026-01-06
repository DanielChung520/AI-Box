# SystemAdmin 與 SystemAgent 架構設計規格書

# 最後修改日期: 2026-01-06
# 創建日期: 2026-01-06
# 創建人: Daniel Chung

## 1. 概述

本文件定義了 AI-Box 系統中最高權限實體——`systemAdmin` 用戶以及未來即將設計的 **`systemAgent`** 的架構、職責與安全規範。該設計旨在通過 AI 協助實現對複雜系統的自動化管理、健康理解與策略優化。

## 2. 身份與定位

### 2.1 systemAdmin (內部系統管理員)
- **類型**: 系統級內部用戶。
- **定位**: 系統操作與數據的終極權限持有者。
- **權限**: 擁有 `system_admin` 角色與 `Permission.ALL`（全局所有權限）。
- **可見性**: 該用戶及其關聯的所有任務、日誌對任何外部用戶（包括一般管理員）均為不可見（Hidden）。

### 2.2 systemAgent (系統管理代理人)
- **類型**: 基於 LLM 的智能 Agent。
- **身份綁定**: 未來將直接映射或操作 `systemAdmin` 賬號。
- **核心目標**: 
    1. **理解系統**: 實時讀取並學習系統文檔、代碼結構與日誌。
    2. **管理系統**: 自動化處理配置變更、數據遷移與資源調度。
    3. **安全審計**: 監控系統異常行為並提出優化建議。

## 3. 核心能力與職責

### 3.1 系統理解 (System Understanding)
- **知識庫基礎**: 以 `SystemDocs` 任務為核心知識庫，包含所有架構文檔、API 規格、數據模型定義等。
- **動態學習**: 能夠識別系統代碼的變更，並自動同步更新相關說明文檔。
- **決策支持**: 當開發者或用戶提出技術問題時，基於當前系統真實架構（非過時文檔）給出準確回答。

### 3.2 系統管理 (System Management)
- **自動化維運**: 負責定期的數據清理、緩存優化以及遷移任務（如全量文檔歸檔）。
- **權限管理**: 管理租戶策略與敏感密鑰（Secrets），確保最高等級的安全隔離。
- **跨組件協調**: 調度工作流（Workflows）與微服務，處理複雜的長時任務。

## 4. 安全架構 (Security Architecture)

### 4.1 最高安全等級
- **密鑰保護**: `systemAdmin` 的認證憑證僅存儲於受保護的環境變量（`.env`）中，不存入數據庫明文。
- **操作審計**: `systemAgent` 的所有行為均記錄於 `audit_logs`，但該日誌僅對 `systemAdmin` 可見。
- **物理隔離**: 系統管理任務的數據存儲於 ArangoDB 的專屬 Key 空間中，並通過應用層邏輯強制隔離。

### 4.2 隱藏邏輯
```python
# 代碼層面實現的過濾邏輯範例
if current_user.user_id != "systemAdmin":
    # 自動排除所有標記為 systemAdmin 的資源
    query_filters.append("task.user_id != 'systemAdmin'")
```

## 5. SystemDocs 任務定義

`SystemDocs` 是 `systemAdmin` 下的專屬任務，其定義如下：
- **任務 ID**: `SystemDocs`
- **內容**: 
    - 核心架構文件（Architecture Docs）
    - 系統規格書（Specs）
    - 部署與運維指南（Deployment Guides）
    - 項目管制表（Project Control Tables）
- **功能**: 作為 `systemAgent` 的 RAG（檢索增強生成）核心來源。

## 6. 未來路徑

1. **第一階段 (已完成)**: 創建 `systemAdmin` 身份，完成全量系統文件遷移至 `SystemDocs`。
2. **第二階段**: 實現 `systemAgent` 的核心循環，支持對 `SystemDocs` 的主動檢索。
3. **第三階段**: 授權 `systemAgent` 執行敏感操作（如：自動歸檔、配置熱更新）。
4. **第四階段**: 建立「系統自我修復」機制，由 Agent 監控日誌並自動修復常見運行錯誤。

---
*備註：本文件為系統核心組件之一，修改需經由 Daniel Chung 授權。*

