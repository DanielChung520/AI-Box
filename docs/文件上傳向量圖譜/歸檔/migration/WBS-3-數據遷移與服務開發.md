# WBS-3: 數據遷移與服務開發

## 文檔資訊

- **創建日期**: 2025-01-27
- **創建人**: Daniel Chung
- **最後修改日期**: 2025-01-27
- **版本**: 1.0
- **工期**: 12 天
- **狀態**: 待開始

## 工作概述

開發 Ontology 和 Config 的 Store Services，實現數據遷移，並更新現有服務以使用新的 Store Services。

## 工作任務

### 任務 3.1: ArangoDB Schema 建立 (1 天)

#### 3.1.1 Collections 建立

- [ ] 建立 `ontologies` collection
- [ ] 建立 `system_configs` collection
- [ ] 建立 `tenant_configs` collection
- [ ] 建立 `user_configs` collection（可選）

#### 3.1.2 索引建立

- [ ] 為 `ontologies` 建立索引（tenant_id, type, name, version）
- [ ] 為 `system_configs` 建立索引（scope, is_active）
- [ ] 為 `tenant_configs` 建立索引（tenant_id, scope, is_active）
- [ ] 為 `user_configs` 建立索引（tenant_id, user_id, scope）

#### 3.1.3 數據驗證規則

- [ ] 定義 Ontology 文檔驗證規則
- [ ] 定義 Config 文檔驗證規則
- [ ] 設定必填欄位約束

**交付物**:

- ArangoDB Schema 定義
- 索引建立腳本
- 數據驗證規則文檔

### 任務 3.2: OntologyStoreService 開發 (2.5 天)

#### 3.2.1 核心功能開發

- [ ] 實現 `save_ontology()` 方法
- [ ] 實現 `get_ontology()` 方法（支援多租戶優先級）
- [ ] 實現 `list_ontologies()` 方法
- [ ] 實現 `update_ontology()` 方法
- [ ] 實現 `delete_ontology()` 方法

#### 3.2.2 多租戶支援

- [ ] 實現租戶隔離查詢邏輯
- [ ] 實現租戶優先級邏輯（租戶專屬 > 全局共享）
- [ ] 實現租戶數據過濾機制

#### 3.2.3 版本控制

- [ ] 實現版本管理功能
- [ ] 實現版本查詢功能
- [ ] 實現版本回滾功能（可選）

**交付物**:

- `OntologyStoreService` 實現
- 單元測試（覆蓋率 ≥ 80%）
- API 文檔

### 任務 3.3: ConfigStoreService 開發 (2.5 天)

#### 3.3.1 核心功能開發

- [ ] 實現 `save_config()` 方法（支援 system/tenant/user）
- [ ] 實現 `get_config()` 方法
- [ ] 實現 `get_effective_config()` 方法（合併邏輯）
- [ ] 實現 `update_config()` 方法
- [ ] 實現 `delete_config()` 方法

#### 3.3.2 配置合併邏輯

- [ ] 實現 system → tenant → user 合併邏輯
- [ ] 實現配置收斂檢查（tenant 不能擴權）
- [ ] 實現配置繼承機制

#### 3.3.3 多租戶支援

- [ ] 實現租戶配置隔離
- [ ] 實現用戶配置隔離
- [ ] 實現配置查詢過濾

**交付物**:

- `ConfigStoreService` 實現
- 單元測試（覆蓋率 ≥ 80%）
- API 文檔

### 任務 3.4: 數據遷移腳本開發 (2 天)

#### 3.4.1 Ontology 遷移腳本

- [ ] 開發 Ontology JSON 檔案讀取邏輯
- [ ] 開發數據轉換邏輯
- [ ] 開發批量插入邏輯
- [ ] 開發數據驗證邏輯
- [ ] 開發遷移進度追蹤

#### 3.4.2 Config 遷移腳本

- [ ] 開發 Config JSON 檔案讀取邏輯
- [ ] 開發數據轉換邏輯
- [ ] 開發批量插入邏輯
- [ ] 開發數據驗證邏輯

#### 3.4.3 遷移驗證

- [ ] 開發數據完整性檢查
- [ ] 開發數據一致性檢查
- [ ] 開發回滾機制

**交付物**:

- 數據遷移腳本
- 遷移驗證腳本
- 遷移文檔

### 任務 3.5: 現有服務更新 (1.5 天)

#### 3.5.1 OntologyManager 更新

- [ ] 更新 `OntologyManager` 使用 `OntologyStoreService`
- [ ] 移除文件系統讀取邏輯
- [ ] 更新錯誤處理邏輯

#### 3.5.2 OntologySelector 更新

- [ ] 更新 `OntologySelector` 使用 `OntologyStoreService`
- [ ] 更新查詢邏輯支援多租戶

#### 3.5.3 genai_config_resolver_service 更新

- [ ] 更新配置讀取邏輯使用 `ConfigStoreService`
- [ ] 更新配置合併邏輯
- [ ] 保持向後兼容性

#### 3.5.4 其他服務更新

- [ ] 識別並更新所有依賴文件系統的服務
- [ ] 更新相關測試

**交付物**:

- 更新的服務代碼
- 更新的測試
- 遷移指南

### 任務 3.6: API 端點開發 (0.5 天)

#### 3.6.1 Ontology API

- [ ] 開發 GET `/api/ontologies` 端點
- [ ] 開發 GET `/api/ontologies/{id}` 端點
- [ ] 開發 POST `/api/ontologies` 端點
- [ ] 開發 PUT `/api/ontologies/{id}` 端點
- [ ] 開發 DELETE `/api/ontologies/{id}` 端點

#### 3.6.2 Config API

- [ ] 開發 GET `/api/configs/effective` 端點
- [ ] 開發 GET `/api/configs/system` 端點
- [ ] 開發 GET `/api/configs/tenant/{tenant_id}` 端點
- [ ] 開發 POST `/api/configs` 端點

**交付物**:

- API 端點實現
- API 測試
- API 文檔

### 任務 3.7: 文件上傳流程重構 (2 天)

#### 3.7.1 處理狀態遷移到 ArangoDB

- [ ] 設計處理狀態數據模型（file_processing_status collection）
- [ ] 建立 `file_processing_status` collection
- [ ] 實現處理狀態 Store Service
- [ ] 遷移現有 Redis 狀態到 ArangoDB（可選，或保持雙寫）
- [ ] 實現狀態查詢 API

#### 3.7.2 事件機制統一

- [ ] 建立統一的事件派發服務（前端）
- [ ] 文件上傳後同時派發 `fileUploaded` 和 `fileTreeUpdated` 事件
- [ ] 處理狀態更新時派發事件
- [ ] FileTree 組件監聽多個事件（fileUploaded + fileTreeUpdated）
- [ ] 實現事件去重機制

#### 3.7.3 文件樹同步機制

- [ ] 實現文件樹自動刷新機制
- [ ] 優化文件樹查詢性能（快取策略）
- [ ] 實現增量更新機制
- [ ] 添加文件樹緩存失效機制
- [ ] 實現文件樹狀態同步

#### 3.7.4 異步處理流程優化

- [ ] 重構處理流程為狀態機模式
- [ ] 實現處理進度追蹤（使用 ArangoDB）
- [ ] 優化錯誤處理和重試機制
- [ ] 實現處理狀態持久化
- [ ] 優化前端輪詢機制（改為事件驅動或 WebSocket）

**交付物**:

- 處理狀態管理服務（FileProcessingStatusService）
- 統一事件派發機制
- 文件樹同步機制
- 優化的異步處理流程
- 狀態查詢 API

## 治理標準對應

### ISO/IEC 42001

- **8.1 運作規劃**: 服務開發與部署
- **9.1 監控與測量**: 服務監控整合

### AIGP

- **數據治理**: 數據遷移與驗證
- **模型治理**: Ontology 版本控制

### AAIA

- **數據完整性**: 數據遷移驗證
- **變更追蹤**: 版本控制實現

## 驗收標準

- [ ] 所有 Store Services 開發完成
- [ ] 所有單元測試通過（覆蓋率 ≥ 80%）
- [ ] 數據遷移成功完成
- [ ] 現有服務正常運作
- [ ] API 端點正常運作

## 風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| 數據遷移失敗 | 高 | 完整備份、分階段遷移、回滾計劃 |
| 性能問題 | 中 | 性能測試、索引優化 |
| 向後兼容性問題 | 中 | 兼容性測試、漸進式遷移 |

## 依賴關係

- **前置任務**: WBS-1 (需求分析與架構設計), WBS-2 (DevSecOps 基礎設施)
- **後續任務**: WBS-4 (AI 治理與合規), WBS-5 (測試與驗證)

## 資源需求

- 後端開發工程師: 9 天（+1 天處理狀態遷移）
- 架構師: 1 天（技術指導）
- 測試工程師: 1.5 天（協助測試，包含文件上傳流程測試）

## 變更記錄

| 版本 | 日期 | 變更內容 | 變更人 |
|------|------|---------|--------|
| 1.0 | 2025-01-27 | 初始版本 | Daniel Chung |
