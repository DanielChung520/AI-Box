# Agent 平台文檔歸檔說明

**歸檔日期**：2026-01-11
**歸檔人**：Daniel Chung
**最後更新**：2026-01-11

---

## 歸檔原因

本目錄包含已整合到 **AI-Box-Agent-架構規格書-v3.md** 和 **Agent-Platform-v3.md** 的舊版文檔和重複文件。

**歸檔原則**：

- 內容已基本整合到主文件的文檔 → 歸檔
- 有獨特價值、補充主文件的文檔 → 保留（如 ARCHITECTURE_AGENT_SEPARATION.md、AGENT_LIFECYCLE.md）

---

## 📋 文檔關係說明

### 主要架構文檔

1. **AI-Box-Agent-架構規格書-v3.md** ✅ **當前版本（主要文檔）**
   - **定位**：完整的架構規格書，包含所有技術規範
   - **內容**：GRO 理論框架、三層架構設計、技術規範（JSON Schema、Policy-as-Code、RBAC 權限矩陣等）
   - **用途**：作為獨立完整文檔使用，無需參考其他文檔即可進行實作
   - **行數**：約 1471 行

2. **Agent-Platform-v3.md** ✅ **當前版本（簡化文檔）**
   - **定位**：簡化版本，重點突出意圖分析、參數調用、決策判斷
   - **內容**：4 層漸進式路由架構、Router LLM 機制、文件編輯強制修正邏輯、參數調用流程、決策與行為判斷
   - **用途**：快速了解核心機制（意圖分析、參數調用、決策判斷）
   - **行數**：約 1227 行

**關係**：兩個文檔是**互補的**，不是重複的：

- **v3 規格書**：完整的架構規格，適合深度技術實現
- **Agent-Platform-v3.md**：簡化版本，適合快速理解核心機制

### 參考文檔（保留）

以下文檔作為參考文檔保留，與主要架構文檔不重複：

1. **ARCHITECTURE_AGENT_SEPARATION.md** ✅ **已整合並歸檔**（2026-01-11）
   - **原定位**：Agent 架構分離設計文檔（開發指南）
   - **整合位置**：`Agent-開發規範.md`（架構分離設計、通信協議、Agent Service Protocol、獨立服務開發、遷移計劃、最佳實踐）
   - **內容**：協調層與執行層的分離架構設計、HTTP/MCP 協議支持、獨立部署方案、遷移計劃、最佳實踐
   - **用途**：了解 Agent 服務分離設計和獨立部署方案，作為開發指南使用
   - **獨特價值**：獨立部署方案、遷移計劃（Phase 1-3）、最佳實踐（服務設計、錯誤處理、監控、安全）

2. **AGENT_LIFECYCLE.md** ✅ **保留**
   - **定位**：Agent 生命週期管理文檔（開發文檔）
   - **內容**：Agent 狀態定義、狀態轉換規則、權限控制、API 端點、使用場景示例
   - **用途**：了解 Agent 的完整生命週期（註冊、在線、維修中、已作廢），補充 Agent-註冊-規格書.md
   - **獨特價值**：完整狀態轉換規則、權限控制詳細說明、API 端點詳細說明、使用場景示例

3. **Agent_Orchestration_White_Paper.md** ✅ **保留**
   - **定位**：GRO 技術白皮書
   - **內容**：GraphRAG-Orchestrator 理論框架、ReAct 循環、Policy-as-Code
   - **用途**：了解 GRO 理論框架和技術規範

---

## 歸檔文件列表

### 1. AI-Box-Agent-架構規格書-v2.md

**歸檔原因**：內容已整合到 v3 版架構規格書

**原文件位置**：`docs/系统设计文档/核心组件/Agent平台/AI-Box-Agent-架構規格書-v2.md`

**整合內容**：

- 三層架構設計
- 實現狀態對比
- 開發路線圖
- 技術規範

**新位置**：v3 版架構規格書第 3-8 章

---

### 2. Agent-Platform.md（舊版）

**歸檔原因**：內容已整合到 v3 版架構規格書，新版 Agent-Platform-v3.md 已重新創建（重點突出意圖分析、參數調用、決策判斷）

**原文件位置**：`docs/系统设计文档/核心组件/Agent平台/Agent-Platform.md`

**整合內容**（舊版）：

- Agent Platform 架構概述
- 三層架構說明
- 實現狀態統計
- 開發進度

**新位置**：v3 版架構規格書第 1、3、8 章

**備註**：新版 Agent-Platform-v3.md（2026-01-11 創建）重點突出意圖分析、參數調用、決策判斷，與 v3 規格書互補

---

### 3. architecture.html

**歸檔原因**：架構圖已整合到 v3 版架構規格書（使用 Mermaid 圖表）

**原文件位置**：`docs/系统设计文档/核心组件/Agent平台/architecture.html`

**備註**：如需查看原始 HTML 架構圖，請參考此文件

---

### 4. ARCHITECTURE_DIAGRAM_EXPLANATION.md

**歸檔原因**：內容已基本整合到 v3 版架構規格書

**原文件位置**：`docs/系统设计文档/核心组件/Agent平台/ARCHITECTURE_DIAGRAM_EXPLANATION.md`

**整合內容**：

- 三層架構詳細說明
- 協調層、執行層、基礎設施層詳細說明
- 通信協議與數據流
- 架構設計原則

**新位置**：v3 版架構規格書第 1.2、3、7 章

**備註**：獨特內容（數據流示例、架構優勢總結）可作為參考保留

---

### 4. 測試相關文件

**歸檔原因**：測試相關文件與架構、說明、規範無關，已歸檔到 `archive/testing/`

**歸檔文件**：

- `文件編輯意圖識別測試劇本.md`
- `測試劇本-50個場景.md`
- `文件編輯Agent追蹤結果.md`
- `文件編輯意圖識別問題分析報告.md`

**歸檔位置**：`archive/testing/`

---

### 5. 臨時數據文件

**歸檔原因**：臨時測試數據和日誌文件與架構、說明、規範無關，已歸檔到 `archive/temp_data/`

**歸檔文件**：

- `*.json`（模型分析、測試結果等）
- `*.log`（測試日誌）

**歸檔位置**：`archive/temp_data/`

---

### 6. 階段性報告

**歸檔原因**：階段性報告與當前架構無關，已歸檔

**歸檔文件**：

- `階段1完成總結.md`
- `階段2使用指南.md`
- `階段2實施完成報告.md`

**歸檔位置**：`archive/`

---

## 如何查找內容

如需查找特定內容，請按以下順序查找：

1. **AI-Box-Agent-架構規格書-v3.md** - 最新完整架構規格（所有技術規範）
2. **Agent-Platform-v3.md** - 簡化版本（重點突出意圖分析、參數調用、決策判斷）
3. **Agent_Orchestration_White_Paper.md** - GRO 理論框架（詳細技術規範）
4. **Orchestrator-協調層規格書.md** - Orchestrator 詳細規格
5. **ARCHITECTURE_AGENT_SEPARATION.md** - Agent 架構分離設計（開發指南）✅ **已整合到 Agent-開發規範.md 並歸檔**（2026-01-11）
6. **AGENT_LIFECYCLE.md** - Agent 生命週期管理（開發文檔）
7. **archive/ARCHITECTURE_DIAGRAM_EXPLANATION.md** - 架構圖說明（已歸檔，內容已整合到主文件）

---

## 版本對應關係

| 版本 | 文件 | 狀態 | 說明 |
|------|------|------|------|
| v3.0 | AI-Box-Agent-架構規格書-v3.md | ✅ 當前版本 | 完整架構規格（1471行） |
| - | Agent-Platform-v3.md（新版） | ✅ 當前版本 | 簡化版本，重點突出意圖分析（1227行） |
| v2.0 | archive/AI-Box-Agent-架構規格書-v2.md | 📦 已歸檔 | 內容已整合到 v3 |
| - | archive/Agent-Platform.md（舊版） | 📦 已歸檔 | 內容已整合到 v3 |
| v1.0 | - | 📦 已整合到 v2 | - |

---

## 📝 文檔更新記錄

### 2026-01-11

- ✅ 創建新版 Agent-Platform-v3.md（重點突出意圖分析、參數調用、決策判斷）
- ✅ 歸檔 Notion 目錄下的 v2 版本到 `archive/old_versions/`
- ✅ 更新歸檔說明文檔
- ✅ 將 Agent-Platform-v3.md 同步到 AI-Box 目錄
- ✅ 歸檔 ARCHITECTURE_DIAGRAM_EXPLANATION.md（內容已整合到主文件）
- ✅ ARCHITECTURE_AGENT_SEPARATION.md 已整合到 Agent-開發規範.md 並歸檔（2026-01-11）
- ✅ 保留 AGENT_LIFECYCLE.md（有獨特價值：狀態轉換、權限控制、API端點）

### 2026-01-08

- ✅ 歸檔 v2 版架構規格書和舊版 Agent-Platform.md
- ✅ 創建 v3 版架構規格書（整合 GRO 白皮書技術規範）

---

**最後更新**：2026-01-11
