# Agent 平台文檔歸檔說明

**歸檔日期**：2026-01-11
**歸檔人**：Daniel Chung
**最後更新**：2026-01-13

---

## 歸檔原因

本目錄包含已整合到 **AI-Box-Agent-架構規格書.md** 和 **Agent-Platform.md** 的舊版文檔和重複文件。

**歸檔原則**：

- 內容已基本整合到主文件的文檔 → 歸檔
- 有獨特價值、補充主文件的文檔 → 保留（如 ARCHITECTURE_AGENT_SEPARATION.md、AGENT_LIFECYCLE.md）

---

## 📋 文檔關係說明

### 主要架構文檔

#### v4 架構文檔（最新，實施中）

1. **[AI-Box 語義與任務工程-設計說明書-v4.md](../語義與任務分析/AI-Box 語義與任務工程-設計說明書-v4.md)** ⭐ **最新版本**
   - **定位**：v4 架構完整設計說明書（5層處理流程 L1-L5）
   - **內容**：語義理解、意圖抽象、能力映射、策略檢查、執行觀察
   - **用途**：了解 v4 架構的完整設計和實施計劃
   - **狀態**：L1-L2 已實現基礎，L3-L5 部分實現

#### v3 架構文檔（當前實現）

2. **AI-Box-Agent-架構規格書.md** ✅ **當前版本（主要文檔）**
   - **定位**：完整的架構規格書，包含所有技術規範
   - **內容**：GRO 理論框架、三層架構設計、技術規範（JSON Schema、Policy-as-Code、RBAC 權限矩陣等）
   - **用途**：作為獨立完整文檔使用，無需參考其他文檔即可進行實作
   - **行數**：約 1496 行
   - **狀態**：v4.0（已升級完成）

3. **Agent-Platform.md** ✅ **當前版本（簡化文檔）**
   - **定位**：簡化版本，重點突出意圖分析、參數調用、決策判斷
   - **內容**：5 層處理流程（v4.0）、Router LLM 機制、文件編輯強制修正邏輯、v3 架構歷史參考
   - **用途**：快速了解核心機制（意圖分析、參數調用、決策判斷）
   - **行數**：約 1475 行
   - **狀態**：v4.0（已升級完成，內部版本 v4.0）
   - **備註**：文件名保持 v3，內部版本為 v4.0

**關係**：三個文檔是**互補的**，不是重複的：

- **v4 設計說明書**：v4 架構的完整設計和實施計劃
- **v3 規格書**：完整的架構規格，適合深度技術實現
- **Agent-Platform.md**：簡化版本，適合快速理解核心機制（內部版本 v4.0）

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

**歸檔原因**：內容已整合到 v3 版架構規格書，新版 Agent-Platform.md 已重新創建（重點突出意圖分析、參數調用、決策判斷）

**原文件位置**：`docs/系统设计文档/核心组件/Agent平台/Agent-Platform.md`

**整合內容**（舊版）：

- Agent Platform 架構概述
- 三層架構說明
- 實現狀態統計
- 開發進度

**新位置**：v3 版架構規格書第 1、3、8 章

**備註**：Agent-Platform.md（內部版本 v4.0，2026-01-13 升級完成）重點突出意圖分析、參數調用、決策判斷，與 v3 規格書互補

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

### v4 架構相關（最新）

1. **[AI-Box 語義與任務工程-設計說明書-v4.md](../語義與任務分析/AI-Box 語義與任務工程-設計說明書-v4.md)** ⭐ **最新** - v4 架構完整設計說明（5層處理流程 L1-L5）

### v3 架構相關（當前實現）

2. **AI-Box-Agent-架構規格書.md** - 完整架構規格（所有技術規範，內部版本 v4.0）
3. **Agent-Platform.md** - 簡化版本（重點突出意圖分析、參數調用、決策判斷，內部版本 v4.0）
4. **Orchestrator-協調層規格書.md** - Orchestrator 詳細規格（v4 架構適配）
5. **Agent_Orchestration_White_Paper.md** - GRO 理論框架（詳細技術規範）

### 開發相關

6. **Agent-開發規範.md** - Agent 開發指南（包含架構分離設計）
7. **AGENT_LIFECYCLE.md** - Agent 生命週期管理（開發文檔）

### 已歸檔文檔（參考）

8. **archive/ARCHITECTURE_AGENT_SEPARATION.md** - Agent 架構分離設計（已整合到 Agent-開發規範.md）
9. **archive/ARCHITECTURE_DIAGRAM_EXPLANATION.md** - 架構圖說明（已歸檔，內容已整合到主文件）

---

## 版本對應關係

| 版本 | 文件 | 狀態 | 說明 |
|------|------|------|------|
| **v4（升級中）** | AI-Box 語義與任務工程-設計說明書-v4.md | 🔄 實施中 | 5層處理流程（L1-L5），L1-L2 已實現基礎 |
| **v4.0** | AI-Box-Agent-架構規格書.md | ✅ 當前版本 | 完整架構規格（已升級完成） |
| **v4.0** | Agent-Platform.md | ✅ 當前版本 | 簡化版本，內部版本 v4.0（已升級完成） |
| **v2.0** | archive/AI-Box-Agent-架構規格書-v2.md | 📦 已歸檔 | 內容已整合到 v3 |
| **舊版** | archive/Agent-Platform.md | 📦 已歸檔 | 內容已整合到 v3 |
| **v1.0** | - | 📦 已整合到 v2 | - |

---

## 📝 文檔更新記錄

### 2026-01-13

- ✅ 更新所有主要文檔以適配 v4 架構（5層處理流程）
- ✅ 更新 Agent-Platform.md：升級為 v4.0 架構（內部版本 v4.0，2026-01-13 完成）
- ✅ 更新 Orchestrator-協調層規格書.md：添加 v4 架構對應關係
- ✅ 更新 AI-Box-Agent-架構規格書.md：升級為 v4.0 架構（內部版本 v4.0，2026-01-13 完成）
- ✅ 更新 Router-LLM-Prompt-和模型信息.md：添加 v4 架構說明
- ✅ 所有文檔已添加 v4 架構設計說明書的引用鏈接
- ✅ 當前狀態：v3 架構已實現，v4 架構正在實施中（L1-L2 已實現基礎，L3-L5 部分實現）

### 2026-01-11

- ✅ 創建新版 Agent-Platform.md（重點突出意圖分析、參數調用、決策判斷）
- ✅ 歸檔 Notion 目錄下的 v2 版本到 `archive/old_versions/`
- ✅ 更新歸檔說明文檔
- ✅ 將 Agent-Platform.md 同步到 AI-Box 目錄
- ✅ 歸檔 ARCHITECTURE_DIAGRAM_EXPLANATION.md（內容已整合到主文件）
- ✅ ARCHITECTURE_AGENT_SEPARATION.md 已整合到 Agent-開發規範.md 並歸檔（2026-01-11）
- ✅ 保留 AGENT_LIFECYCLE.md（有獨特價值：狀態轉換、權限控制、API端點）

### 2026-01-08

- ✅ 歸檔 v2 版架構規格書和舊版 Agent-Platform.md
- ✅ 創建 v3 版架構規格書（整合 GRO 白皮書技術規範）

---

## 📋 當前文檔狀態（2026-01-13）

### 主目錄文檔（當前使用）

所有主目錄下的文檔都是當前使用的，無需歸檔：

| 文檔名稱 | 狀態 | 說明 |
|---------|------|------|
| **Agent-Platform.md** | ✅ 當前版本 | 內部版本 v4.0（已升級完成） |
| **AI-Box-Agent-架構規格書.md** | ✅ 當前版本 | v4.0（已升級完成） |
| **Orchestrator-協調層規格書.md** | ✅ 當前版本 | v1.2（v4 架構適配） |
| **Router-LLM-Prompt-和模型信息.md** | ✅ 當前版本 | 已添加 v4 架構說明 |
| **Agent-註冊-規格書.md** | ✅ 當前版本 | Agent 註冊完整規格 |
| **Agent-開發規範.md** | ✅ 當前版本 | Agent 開發指南 |
| **System-Config-Agent-規格書.md** | ✅ 當前版本 | System Config Agent 規格 |
| **Security-Agent-規格書.md** | ✅ 當前版本 | Security Agent 規格 |
| **System-Agent-Registry-實施總結.md** | ✅ 當前版本 | System Agent Registry 實施總結 |
| **System-Agent-註冊清冊.md** | ✅ 當前版本 | System Agent 註冊清冊 |
| **AI-Box-Agent-架構升級計劃-v3.md** | 📦 已歸檔 | v3 架構升級計劃（系統已升級至 v4.0） |
| **Agent_Orchestration_White_Paper.md** | ✅ 當前版本 | GRO 技術白皮書 |
| **AGENT_LIFECYCLE.md** | ✅ 當前版本 | Agent 生命週期管理（有獨特價值） |

### 已歸檔文檔

| 文檔名稱 | 歸檔位置 | 歸檔原因 |
|---------|---------|---------|
| **AI-Box-Agent-架構規格書-v2.md** | `archive/` | 內容已整合到 v3 版 |
| **Agent-Platform.md（舊版）** | `archive/` | 內容已整合到 v3 版 |
| **ARCHITECTURE_DIAGRAM_EXPLANATION.md** | `archive/` | 內容已整合到 v3 版 |
| **ARCHITECTURE_AGENT_SEPARATION.md** | `archive/` | 內容已整合到 Agent-開發規範.md |
| **architecture.html** | `archive/` | 架構圖已整合到 v3 版（使用 Mermaid） |
| **測試相關文件** | `archive/testing/` | 測試劇本和報告 |
| **臨時數據文件** | `archive/temp_data/` | 測試數據和日誌 |
| **階段性報告** | `archive/` | 階段1、階段2報告 |
| **Agent-Platform-v3-升級分析報告.md** | `archive/` | 升級分析已完成並歸檔（2026-01-13） |
| **AI-Box-Agent-架構升級計劃-v3.md** | `archive/` | v3 架構升級計劃已歸檔（2026-01-13） |

---

### 歸檔文件詳情

#### Agent-Platform-v3-升級分析報告.md

**歸檔日期**：2026-01-13

**歸檔原因**：升級分析已完成，文檔已成功升級為 v4.0 架構

**原文件位置**：`docs/系统设计文档/核心组件/Agent平台/Agent-Platform-v3-升級分析報告.md`（已歸檔）

**歸檔內容**：
- Agent-Platform.md 與 v4 架構的差距分析
- 需要調整的內容清單
- 升級建議和優先級

**升級結果**：
- ✅ Agent-Platform.md 已成功升級為 v4.0 架構（內部版本 v4.0）
- ✅ 所有引用文件已更新
- ✅ 升級計劃書已創建：[Agent-Platform-v4-升級計劃書.md](../Agent-Platform-v4-升級計劃書.md)

**新位置**：`archive/Agent-Platform-v3-升級分析報告.md`

---

#### AI-Box-Agent-架構升級計劃-v3.md

**歸檔日期**：2026-01-13

**歸檔原因**：v3 架構升級計劃已完成歷史使命，系統已升級至 v4.0

**原文件位置**：`docs/系统设计文档/核心组件/Agent平台/AI-Box-Agent-架構升級計劃-v3.md`

**歸檔內容**：
- v3 架構升級計劃（階段0-4）
- 現狀盤點、差距分析、實施步驟
- 進度管控表、風險評估、驗收標準

**當前狀態**：
- v3 架構升級計劃：本文檔（已歸檔）
- v4.0 架構升級計劃：[Agent-Platform-v4-升級計劃書.md](../Agent-Platform-v4-升級計劃書.md)（當前版本）

**新位置**：`archive/AI-Box-Agent-架構升級計劃-v3.md`

---

**最後更新**：2026-01-13
