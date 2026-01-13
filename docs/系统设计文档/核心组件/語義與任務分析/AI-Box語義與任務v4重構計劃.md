# AI-Box 語義與任務 v4 重構計劃

**創建日期**: 2026-01-12
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-12
**版本**: v1.2

---

## 📋 計劃概述

本文檔基於《可行性分析-AI-Box-Enterprise-GenAI-Semantic-Task-Orchestration.md》的評估結果，制定 AI-Box 語義與任務工程從 v3（現有系統）升級到 v4（新設計）的詳細重構計劃。

### 重構目標

將 AI-Box 語義與任務工程從「任務路由系統」升級為「Agent-first Enterprise AI Orchestration Platform」。

### 總體可行性

✅ **總體可行性：高（85%）**

現有系統已實現約60-70%的核心功能，主要工作集中在架構擴展和設計理念轉變。

### 重構原則

1. **漸進式遷移**：保留現有功能作為 Fallback，逐步遷移到新設計
2. **向後兼容**：API 接口保持不變，內部實現逐步遷移
3. **充分測試**：每個階段都進行充分測試
4. **風險可控**：通過分階段實施控制風險

---

## 一、現狀分析

### 1.1 現有系統架構

**當前狀態**：4層漸進式路由架構（Layer 0-3）

```
Layer 0: Cheap Gating（快速過濾）
   ↓
Layer 1: Fast Answer Layer（高級 LLM 直接回答）
   ↓
Layer 2: Semantic Intent Analysis（語義意圖分析）
   ↓
Layer 3: Decision Engine（綜合決策）
```

### 1.2 已實現組件

| 組件 | 文件位置 | 實現狀態 | 備註 |
|------|----------|----------|------|
| **Router LLM** | `agents/task_analyzer/router_llm.py` | ✅ 已實現 | 需擴展輸出 Schema |
| **Decision Engine** | `agents/task_analyzer/decision_engine.py` | ✅ 已實現 | 需支持 Task DAG |
| **Capability Matcher** | `agents/task_analyzer/capability_matcher.py` | ✅ 已實現 | 需擴展為 Registry |
| **Orchestrator** | `agents/services/orchestrator/orchestrator.py` | ✅ 已實現 | 需擴展職責 |
| **Observation Collector** | `agents/services/observation_collector/` | ✅ 已實現 | 需擴展指標記錄 |

### 1.3 缺失組件

| 組件 | 需要實現 | 優先級 |
|------|----------|--------|
| **Intent Registry** | 新建 | P0 |
| **Capability Registry** | 擴展現有 | P0 |
| **Task Planner** | 新建 | P1 |
| **Policy & Constraint Service** | 新建 | P0 |
| **RAG Namespace** | 新建 | P1 |

---

## 二、重構階段規劃

### 階段一：基礎設施完善（2-3周）

**目標**：建立新設計的基礎設施

#### 任務清單

1. ✅ **定義 Intent DSL Schema**
   - 設計 Intent DSL 數據模型
   - 定義 30 個核心 Intent
   - 建立 Intent 版本管理機制

2. ✅ **建立 Intent Registry**
   - 創建 `agents/task_analyzer/intent_registry.py`
   - 實現 Intent 存儲和查詢接口
   - 建立 ArangoDB Collection `intent_registry`
   - 實現版本管理邏輯

3. ✅ **擴展 Capability Registry Schema**
   - 擴展現有 Agent Registry 為 Capability Registry
   - 定義 Capability 數據模型（name, input, output, constraints）
   - 建立 ArangoDB Collection `capability_registry`

4. ✅ **建立 RAG Namespace 結構**
   - 設計三個獨立的 RAG Namespace（RAG-1, RAG-2, RAG-3）
   - 創建 `agents/task_analyzer/rag_namespace.py`
   - 實現 Namespace 分離和檢索邏輯

5. ✅ **設計 RAG Namespace & Chunk Schema**
   - 定義 RAG-1: Architecture Awareness Chunk Schema
   - 定義 RAG-2: Capability Discovery Chunk Schema（最重要）
   - 定義 RAG-3: Policy & Constraint Chunk Schema
   - 設計 Chunk 生成規則和模板
   - 實現 Chunk 存儲和檢索接口
   - 設計防幻覺檢索策略（硬邊界檢查、Top-K 限制、相似度閾值）

6. ✅ **實現 Policy & Constraint Service 基礎**
   - 創建 `agents/task_analyzer/policy_service.py`
   - 設計規則引擎接口
   - 集成 Security Agent 權限檢查

#### 交付物

- Intent DSL 定義文件
- Capability Registry Schema 文檔
- RAG Namespace 設計文檔
- RAG Chunk Schema 定義（三個 Namespace）
- Chunk 生成規則和模板文檔
- Policy & Constraint Service 基礎實現
- 數據庫 Schema 腳本

#### 驗收標準

- [ ] Intent Registry 可以存儲和查詢 Intent
- [ ] Capability Registry Schema 已定義
- [ ] RAG Namespace 結構已建立（三個獨立 Namespace）
- [ ] RAG Chunk Schema 已定義（三個 Chunk 類型）
- [ ] Chunk 生成規則和模板已實現
- [ ] 防幻覺檢索策略已實現（硬邊界檢查、Top-K、相似度閾值）
- [ ] Policy Service 基礎框架已實現

---

### 階段二：L1-L2層級重構（2-3周）

**目標**：重構語義理解和意圖抽象層

#### 任務清單

1. ✅ **擴展 Router LLM 輸出 Schema**
   - 修改 `RouterDecision` 為 `SemanticUnderstandingOutput`
   - 添加 `topics`, `entities`, `action_signals`, `modality` 字段
   - 保留 `intent_type` 作為過渡期兼容

2. ✅ **修改 Router LLM 設計理念**
   - 從「意圖分類」轉為「語義理解」
   - 更新 System Prompt
   - 確保不產生 intent（intent 在 L2 產生）

3. ✅ **實現 Intent DSL 匹配邏輯**
   - 基於 L1 輸出（topics, entities, action_signals）匹配 Intent
   - 實現 Intent 匹配算法
   - 實現 Fallback Intent 機制

4. ✅ **集成 Intent Registry**
   - 在 L2 層級集成 Intent Registry
   - 實現 Intent 查詢和匹配
   - 保留動態分類作為 Fallback

5. ✅ **實現多模型 ensemble（可選）**
   - 實現多模型投票機制
   - 可選功能，不影響主流程

#### 交付物

- 重構後的 Router LLM
- Intent DSL 匹配器
- Intent Registry 集成
- 測試用例和測試結果

#### 驗收標準

- [ ] L1 層級輸出符合 `SemanticUnderstandingOutput` Schema
- [ ] L2 層級可以匹配 Intent DSL
- [ ] Intent 匹配準確率 ≥80%
- [ ] 向後兼容性測試通過

---

### 階段三：L3層級擴展（2-3周）

**目標**：擴展能力映射和任務規劃

#### 任務清單

1. ✅ **實現 Capability 向量化存儲（RAG-2）**
   - 將 Capability 信息向量化
   - 存儲到 RAG-2 Namespace
   - 實現 Capability 檢索接口

2. ✅ **實現 Task Planner（生成 DAG）**
   - 創建 `agents/task_analyzer/task_planner.py`
   - 實現 LLM-based Planner
   - 生成 Task DAG（包含依賴關係）
   - **實現 RAG + Planner Prompt（防幻覺版）**
     - 設計 Planner System Prompt（明確禁止發明 Capability）
     - 實現 `build_planner_prompt()` 函數
     - 實現 `format_capabilities_for_prompt()` 函數
     - 實現 `validate_planner_output()` 驗證邏輯
     - 確保 Planner 只能使用 RAG-2 檢索到的 Capability

3. ✅ **擴展 Decision Engine 支持 DAG**
   - 修改 Decision Engine 支持 Task DAG 輸入
   - 實現 DAG 驗證邏輯
   - 確保 DAG 合法性

4. ✅ **確保 Capability 只能從 Registry 選擇**
   - 實現 Capability 驗證邏輯
   - 確保 Planner 不能發明 Capability
   - 實現硬邊界檢查

5. ✅ **集成 RAG-2 到 Planner**
   - 在 Planner 中集成 RAG-2 檢索
   - 確保「沒有檢索到的能力 = 不存在」
   - 實現 Capability 發現邏輯

#### 交付物

- Capability RAG 實現（RAG-2）
- RAG Chunk 存儲和檢索實現
- Task Planner 實現
- RAG + Planner Prompt 模板（防幻覺版）
- Capability 驗證邏輯實現
- DAG 執行引擎擴展
- 測試用例

#### 驗收標準

- [ ] Task Planner 可以生成有效的 DAG
- [ ] RAG + Planner Prompt（防幻覺版）已實現
- [ ] Planner System Prompt 明確禁止發明 Capability
- [ ] Capability 格式化函數正確格式化 RAG-2 結果
- [ ] Planner 輸出驗證邏輯可以檢測幻覺 Capability
- [ ] DAG 驗證邏輯正確
- [ ] Capability 只能從 Registry 選擇（硬邊界檢查）
- [ ] RAG-2 檢索準確率 ≥90%
- [ ] 防幻覺機制測試通過（測試 Planner 不能使用不存在的 Capability）

---

### 階段四：L4層級實現（1-2周）

**目標**：實現約束驗證與策略檢查

#### 任務清單

1. ✅ **實現 Policy & Constraint Service**
   - 完善 Policy Service 實現
   - 實現規則引擎（不使用 LLM）
   - 實現權限、風險、策略、資源檢查

2. ✅ **實現規則引擎**
   - 選擇規則引擎庫（如 Python Rules Engine）
   - 定義規則格式
   - 實現規則執行邏輯

3. ✅ **集成 Security Agent**
   - 重用 Security Agent 的權限檢查邏輯
   - 集成到 Policy Service
   - 實現統一權限檢查接口

4. ✅ **實現風險評估邏輯**
   - 定義風險評估規則
   - 實現風險等級計算
   - 實現風險提示邏輯

5. ✅ **實現資源限制檢查**
   - 定義資源限制規則
   - 實現資源使用檢查
   - 實現資源超限處理

6. ✅ **集成 RAG-3 到 Policy Service**
   - 將 Policy & Constraint 信息向量化存儲（RAG-3）
   - 在 Policy Service 中集成 RAG-3 檢索
   - 實現策略知識檢索

#### 交付物

- Policy & Constraint Service 完整實現
- 規則引擎實現
- 風險評估邏輯
- 資源限制檢查
- 測試用例

#### 驗收標準

- [ ] Policy Service 可以正確驗證權限
- [ ] 風險評估邏輯正確
- [ ] 資源限制檢查有效
- [ ] RAG-3 檢索準確率 ≥90%
- [ ] 所有任務都經過 L4 檢查

---

### 階段五：L5層級完善（1周）

**目標**：完善執行與觀察

#### 任務清單

1. ✅ **擴展執行指標記錄**
   - 擴展 `ExecutionRecord` Schema
   - 記錄 intent, task_count, execution_success, latency_ms 等
   - 實現執行記錄存儲

2. ✅ **實現命中率統計**
   - 統計 Intent → Task 命中率
   - 實現命中率計算邏輯
   - 實現命中率報告

3. ✅ **實現品質評估邏輯**
   - 評估 Agent 能力品質
   - 實現品質評分算法
   - 實現品質報告

4. ✅ **集成到 Orchestrator**
   - 在 Orchestrator 中集成執行記錄
   - 實現執行指標收集
   - 實現觀察數據聚合

#### 交付物

- 執行指標記錄系統
- 命中率統計服務
- 品質評估邏輯
- 測試用例

#### 驗收標準

- [ ] 執行指標記錄完整
- [ ] 命中率統計準確
- [ ] 品質評估邏輯正確
- [ ] 集成到 Orchestrator 成功

---

### 階段六：集成測試與優化（2周）

**目標**：端到端測試和性能優化

#### 任務清單

1. ✅ **端到端集成測試**
   - 測試完整流程（L1-L5）
   - 測試各種場景
   - 測試錯誤處理

2. ✅ **性能測試和優化**
   - 測試響應時間
   - 優化慢查詢
   - 優化 RAG 檢索
   - 優化規則引擎

3. ✅ **回歸測試**
   - 測試現有功能不受影響
   - 測試向後兼容性
   - 測試 API 兼容性

4. ✅ **文檔完善**
   - 更新 API 文檔
   - 更新開發文檔
   - 更新用戶文檔

#### 交付物

- 測試報告
- 性能優化報告
- 完整文檔
- 部署指南

#### 驗收標準

- [ ] 端到端測試通過率 100%
- [ ] 性能指標達到目標
- [ ] 回歸測試通過
- [ ] 文檔完整

---

## 二-1、任務執行階段管控記錄表

> **重要提醒**：每次完成階段任務或更新進度時，請及時更新此表格。

### 管控記錄表

| 階段 | 階段名稱 | 計劃開始日期 | 計劃結束日期 | 實際開始日期 | 實際結束日期 | 完成狀態 | 完成百分比 | 負責人 | 備註 | 最後更新日期 |
|------|---------|------------|------------|------------|------------|---------|-----------|--------|------|------------|
| **階段一** | 基礎設施完善 | 2026-01-12 | 2026-02-02 | 2026-01-12 | 2026-01-12 | ✅ 已完成 | 100% | Daniel Chung | 已完成所有任務：Intent DSL Schema定義、Intent Registry建立、Capability Registry Schema擴展、RAG Namespace結構建立、RAG Chunk Schema設計、Policy Service基礎實現 | 2026-01-12 |
| **階段二** | L1-L2層級重構 | 2026-02-02 | 2026-02-23 | 2026-01-12 | 2026-01-12 | ✅ 已完成 | 100% | Daniel Chung | 已完成所有任務：Router LLM 輸出 Schema 擴展、Router LLM 設計理念轉變、Intent DSL 匹配邏輯實現、Intent Registry 集成（多模型 ensemble 為可選功能，暫未實現） | 2026-01-12 |
| **階段三** | L3層級擴展 | 2026-02-23 | 2026-03-16 | 2026-01-12 | 2026-01-12 | ✅ 已完成 | 100% | Daniel Chung | 已完成所有任務：Capability 向量化存儲（RAG-2）實現、Task Planner 實現（生成 DAG）、RAG + Planner Prompt（防幻覺版）實現、Decision Engine 支持 DAG 擴展、Capability 驗證邏輯實現、RAG-2 集成到 Planner | 2026-01-12 |
| **階段四** | L4層級實現 | 2026-03-16 | 2026-03-30 | 2026-01-12 | 2026-01-12 | ✅ 已完成 | 100% | Daniel Chung | 已完成所有任務：Policy & Constraint Service 完整實現、規則引擎實現（支持多種條件類型和邏輯運算）、Security Agent 集成、風險評估邏輯實現（任務數量、敏感操作、資源消耗、時間、依賴等）、資源限制檢查實現、RAG-3 服務方法創建和集成到 Policy Service、Decision Engine 集成、測試用例添加 | 2026-01-12 |
| **階段五** | L5層級完善 | 2026-03-30 | 2026-04-06 | 2026-01-12 | 2026-01-12 | ✅ 已完成 | 100% | Daniel Chung | 已完成所有任務：1. ExecutionRecord Schema 擴展（添加 intent, task_count, execution_success, latency_ms 等字段）2. ExecutionRecordStoreService 實現（ArangoDB 存儲）3. 命中率統計服務實現（HitRateService，支持 Intent → Task 命中率計算和報告）4. 品質評估服務實現（QualityAssessmentService，支持 Agent 能力品質評分）5. 集成到 Orchestrator（在 execute_task 和 process_natural_language_request 中記錄執行指標） | 2026-01-12 |
| **階段六** | 集成測試與優化 | 2026-04-06 | 2026-04-20 | 2026-01-12 | 2026-01-12 | ✅ 已完成 | 100% | Daniel Chung | 已完成所有任務：1. 端到端集成測試框架搭建（E2E 測試目錄結構、測試環境配置、測試 fixtures）2. L1-L5 完整流程測試實現（測試各層級功能、驗證性能指標、測試各種場景）3. 錯誤處理測試實現（測試各種錯誤場景、驗證錯誤處理邏輯）4. 性能測試框架搭建（使用 pytest-benchmark、實現性能指標收集、實現性能報告生成）5. 響應時間測試實現（測試各層級響應時間、收集性能數據、識別性能瓶頸）6. 回歸測試實現（測試現有功能、測試向後兼容性、測試 API 兼容性）7. 文檔完善（更新 API 文檔、更新用戶文檔、創建部署指南）8. 測試報告生成（端到端測試報告、性能測試報告、回歸測試報告） | 2026-01-12 |

### 狀態說明

- **⏸️ 未開始**：階段尚未開始
- **🔄 進行中**：階段正在進行中
- **✅ 已完成**：階段已完成
- **⚠️ 延期**：階段進度延遲
- **❌ 已取消**：階段已取消

### 更新說明

**更新頻率**：
- 每週至少更新一次進度
- 階段開始時更新「實際開始日期」和「完成狀態」
- 階段完成時更新「實際結束日期」、「完成狀態」和「完成百分比」
- 重要里程碑達成時立即更新

**更新內容**：
1. **完成百分比**：根據任務清單完成情況計算（已完成任務數 / 總任務數 × 100%）
2. **完成狀態**：根據實際進度更新狀態標記
3. **備註**：記錄重要進展、遇到的問題、風險等
4. **最後更新日期**：記錄本次更新的日期

**示例更新**：
```
| **階段一** | 基礎設施完善 | 2026-01-12 | 2026-02-02 | 2026-01-15 | - | 🔄 進行中 | 40% | 張三 | 已完成 Intent DSL Schema 定義，正在實現 Intent Registry | 2026-01-20 |
```

### 階段任務完成檢查清單

#### 階段一：基礎設施完善

- [x] Intent DSL Schema 已定義
- [x] Intent Registry 已實現
- [x] Capability Registry Schema 已擴展
- [x] RAG Namespace 結構已建立
- [x] RAG Chunk Schema 已定義
- [x] Policy & Constraint Service 基礎框架已實現

#### 階段二：L1-L2層級重構

- [x] Router LLM 輸出 Schema 已擴展
- [x] Router LLM 設計理念已轉變
- [x] Intent DSL 匹配邏輯已實現
- [x] Intent Registry 已集成
- [ ] 多模型 ensemble 已實現（可選，暫未實現）

#### 階段三：L3層級擴展

- [x] Capability 向量化存儲（RAG-2）已實現
- [x] Task Planner 已實現
- [x] RAG + Planner Prompt（防幻覺版）已實現
- [x] Decision Engine 已支持 DAG
- [x] Capability 驗證邏輯已實現
- [x] RAG-2 已集成到 Planner

#### 階段四：L4層級實現

- [x] Policy & Constraint Service 已實現
- [x] 規則引擎已實現
- [x] Security Agent 已集成
- [x] 風險評估邏輯已實現
- [x] 資源限制檢查已實現
- [x] RAG-3 已集成到 Policy Service

#### 階段五：L5層級完善

- [x] 執行指標記錄已擴展
- [x] 命中率統計已實現
- [x] 品質評估邏輯已實現
- [x] 已集成到 Orchestrator

#### 階段六：集成測試與優化

- [x] 端到端集成測試已完成
- [x] 性能測試和優化已完成
- [x] 回歸測試已通過
- [x] 文檔已完善

---

## 三、關鍵挑戰與解決方案

### 3.1 挑戰一：Intent DSL 化重構

**挑戰描述**：從「動態意圖分類」重構為「DSL化固定集合」

**影響範圍**：Router LLM、Decision Engine、測試用例

**解決方案**：
1. **漸進式遷移**：保留動態分類作為 Fallback，逐步遷移到 DSL
2. **版本管理**：建立 Intent Registry 版本管理機制
3. **兼容性保證**：保持 API 向後兼容，內部實現切換

**風險等級**：🟡 中等

**緩解措施**：
- 充分測試 Intent 匹配邏輯
- 保留 Fallback 機制
- 逐步遷移，不一次性切換

---

### 3.2 挑戰二：RAG 角色轉變

**挑戰描述**：從「知識庫RAG」轉變為「能力約束RAG」

**影響範圍**：RAG 數據結構、檢索邏輯、Capability Registry

**解決方案**：
1. **Namespace分離**：建立三個獨立的 RAG Namespace
2. **數據遷移**：將現有 Capability 信息遷移到 RAG-2
3. **檢索邏輯調整**：確保「沒有檢索到的能力 = 不存在」

**風險等級**：🟡 中等

**緩解措施**：
- 雙寫過渡期（新舊系統並行）
- 充分測試檢索邏輯
- 逐步遷移數據

---

### 3.3 挑戰三：Task DAG 規劃實現

**挑戰描述**：實現任務規劃器，生成 DAG

**影響範圍**：Task Planner、Orchestrator、執行引擎

**解決方案**：
1. **使用LLM Planner**：初期使用LLM生成DAG
2. **規則驗證**：使用規則引擎驗證DAG合法性
3. **模式學習**：後期可訓練專屬小模型

**風險等級**：🟡 中等

**緩解措施**：
- 實現嚴格的 DAG 驗證邏輯
- 充分測試 DAG 生成
- 保留簡單任務的直線執行作為 Fallback

---

### 3.4 挑戰四：Policy & Constraint Layer 新建

**挑戰描述**：新建 L4 層級，實現規則引擎

**影響範圍**：Policy Service、Security Agent集成、Orchestrator

**解決方案**：
1. **規則引擎選擇**：使用成熟的規則引擎（如 Python Rules Engine）
2. **集成現有組件**：重用 Security Agent 的權限檢查邏輯
3. **RAG-3集成**：使用 RAG-3 檢索 Policy 知識

**風險等級**：🟢 低（技術成熟）

**緩解措施**：
- 選擇成熟的規則引擎庫
- 充分測試規則邏輯
- 逐步擴展規則覆蓋範圍

---

## 四、成功指標（KPI）

### 4.1 功能指標

| 指標 | 目標值 | 測量方式 |
|------|--------|----------|
| **Intent匹配準確率** | ≥90% | 測試用例通過率 |
| **Capability發現準確率** | ≥95% | RAG檢索命中率 |
| **Task DAG生成成功率** | ≥85% | DAG驗證通過率 |
| **Policy檢查覆蓋率** | 100% | 所有任務都經過L4檢查 |
| **執行成功率** | ≥95% | 任務執行成功率 |

### 4.2 性能指標

| 指標 | 目標值 | 測量方式 |
|------|--------|----------|
| **端到端響應時間** | ≤3秒（P95） | 性能測試 |
| **L1層級響應時間** | ≤1秒（P95） | 性能測試 |
| **RAG檢索時間** | ≤200ms（P95） | 性能測試 |
| **Policy檢查時間** | ≤100ms（P95） | 性能測試 |

### 4.3 質量指標

| 指標 | 目標值 | 測量方式 |
|------|--------|----------|
| **代碼覆蓋率** | ≥80% | 單元測試 |
| **集成測試通過率** | 100% | 集成測試 |
| **API向後兼容性** | 100% | 兼容性測試 |

---

## 五、風險管理

### 5.1 風險識別

| 風險項 | 風險等級 | 影響範圍 | 緩解措施 |
|--------|---------|---------|---------|
| **架構重構風險** | 🟡 中等 | 核心組件 | 漸進式遷移 |
| **數據遷移風險** | 🟢 低 | RAG數據 | 雙寫過渡期 |
| **兼容性風險** | 🟢 低 | API接口 | 保持向後兼容 |
| **性能風險** | 🟡 中等 | 響應時間 | 性能測試和優化 |
| **測試覆蓋風險** | 🟡 中等 | 功能測試 | 逐步擴展測試用例 |

### 5.2 風險應對策略

1. **漸進式遷移**：分階段實施，每階段充分測試
2. **向後兼容**：保持 API 不變，內部實現切換
3. **Fallback 機制**：每層都有 Safe Fallback
4. **充分測試**：單元測試、集成測試、端到端測試
5. **性能監控**：實時監控性能指標

---

## 六、時間計劃

### 6.1 總體時間估算

**總時間**：10-14周（約2.5-3.5個月）

| 階段 | 時間 | 開始時間 | 結束時間 |
|------|------|----------|----------|
| **階段一：基礎設施完善** | 2-3周 | T+0 | T+3周 |
| **階段二：L1-L2層級重構** | 2-3周 | T+3周 | T+6周 |
| **階段三：L3層級擴展** | 2-3周 | T+6周 | T+9周 |
| **階段四：L4層級實現** | 1-2周 | T+9周 | T+11周 |
| **階段五：L5層級完善** | 1周 | T+11周 | T+12周 |
| **階段六：集成測試與優化** | 2周 | T+12周 | T+14周 |

### 6.2 里程碑

- **M1（T+3周）**：基礎設施完成
- **M2（T+6周）**：L1-L2 重構完成
- **M3（T+9周）**：L3 擴展完成
- **M4（T+11周）**：L4 實現完成
- **M5（T+12周）**：L5 完善完成
- **M6（T+14周）**：集成測試完成，準備發布

---

## 七、資源需求

### 7.1 人力資源

- **開發工程師**：2-3人
- **測試工程師**：1人
- **架構師**：1人（兼職）

### 7.2 技術資源

- **開發環境**：現有開發環境
- **測試環境**：需要獨立的測試環境
- **數據庫**：ArangoDB、ChromaDB（現有）

---

## 八、下一步行動

### 8.1 立即行動（本週）

1. ✅ 審查本重構計劃
2. ✅ 確認時間計劃和資源分配
3. ✅ 開始階段一：基礎設施完善

### 8.2 準備工作

1. 建立項目追蹤（在項目控制表中建立任務）
2. 分配開發任務
3. 準備開發環境

---

## 附錄

### A. 參考文檔

- `AI-Box 語義與任務工程-設計說明書-v4.md`（設計說明書）
- `可行性分析-AI-Box-Enterprise-GenAI-Semantic-Task-Orchestration.md`（可行性分析）
- `AI-Box Enterprise GenAI Semantic & Task Orchestration.md`（新設計理念）

### B. 相關代碼文件

- `agents/task_analyzer/analyzer.py`（Task Analyzer 核心）
- `agents/task_analyzer/router_llm.py`（Router LLM）
- `agents/task_analyzer/decision_engine.py`（Decision Engine）
- `agents/task_analyzer/capability_matcher.py`（Capability Matcher）
- `agents/services/orchestrator/orchestrator.py`（Orchestrator）

---

**文檔版本**: v1.2
**最後更新**: 2026-01-12
**維護人**: Daniel Chung
