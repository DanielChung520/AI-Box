<!-- cad3f69c-c4aa-4733-89d1-82fb9de06fe0 0182aef3-08c9-4b3a-89bf-19083e56b4e1 -->
# WBS 1.3 ChromaDB 部署實施計劃

## 目標

於 4 個工作日內完成 ChromaDB 部署、SDK 封裝與檢索性能驗證，作為 RAG 的核心向量存儲。

## 當前狀態分析

- ✅ 已有基礎 SDK 封裝（`databases/chromadb/client.py`, `collection.py`）
- ✅ Docker Compose 中已配置 ChromaDB 服務
- ✅ 有基礎單元測試
- ❌ 缺少 K8s 部署配置
- ❌ SDK 缺少連線池管理
- ❌ 缺少批量操作優化
- ❌ 缺少 ChromaDB API 路由
- ❌ 缺少性能測試腳本
- ❌ 缺少監控配置

## 實施步驟

### 任務 1.3.1: ChromaDB 安裝與配置（Docker/K8s）

**文件操作：**

1. **完善 Docker Compose 配置**（`docker-compose.yml`）：

- 驗證現有 ChromaDB 服務配置
- 添加資源限制（CPU、記憶體）
- 配置持久化存儲優化（SSD 建議）
- 添加環境變數配置

2. **創建 K8s 部署配置**：

- 創建 `k8s/base/chromadb-deployment.yaml`：
- Deployment 配置（副本數、資源限制）
- Service 配置（ClusterIP）
- ConfigMap（環境變數配置）
- PersistentVolumeClaim（持久化存儲）
- 更新 `k8s/base/service.yaml` 添加 ChromaDB Service

3. **創建監控配置**：

- 創建 `k8s/monitoring/chromadb-metrics.yaml`（如果 ChromaDB 支持 Prometheus）
- 更新 `k8s/monitoring/prometheus-config.yaml` 添加 ChromaDB 監控目標
- 創建 `k8s/monitoring/chromadb-dashboard.yaml`（Grafana Dashboard）

4. **創建部署文檔**：

- 更新 `databases/chromadb/README.md` 添加 K8s 部署說明
- 創建 `docs/deployment/chromadb-deployment.md`（部署指南）

### 任務 1.3.2: SDK 封裝（連線池、錯誤處理、封裝方法）

**文件操作：**

1. **增強客戶端封裝**（`databases/chromadb/client.py`）：

- 實現連線池管理（使用連接復用）
- 添加重試機制和錯誤處理
- 添加連接健康檢查
- 實現自動重連機制
- 添加連接超時配置

2. **增強集合封裝**（`databases/chromadb/collection.py`）：

- 實現批量寫入優化（批量插入接口）
- 添加嵌入維度校驗和轉換
- 添加 metadata 驗證
- 實現命名空間管理（通過 metadata 或集合命名）

3. **創建工具模組**（`databases/chromadb/utils.py`）：

- 嵌入維度轉換工具
- Metadata 驗證工具
- 批量操作工具函數

4. **更新依賴**（`requirements.txt`）：

- 確保 chromadb 版本 >= 0.4.0
- 添加重試相關依賴（如 tenacity）

### 任務 1.3.3: 向量檢索功能、API 實例與單元測試

**文件操作：**

1. **創建 ChromaDB API 路由**（`services/api/routers/chromadb.py`）：

- `POST /api/v1/chromadb/collections` - 創建集合
- `GET /api/v1/chromadb/collections` - 列出集合
- `DELETE /api/v1/chromadb/collections/{name}` - 刪除集合
- `POST /api/v1/chromadb/collections/{name}/documents` - 添加文檔
- `GET /api/v1/chromadb/collections/{name}/documents` - 獲取文檔
- `POST /api/v1/chromadb/collections/{name}/query` - 向量檢索
- `PUT /api/v1/chromadb/collections/{name}/documents/{id}` - 更新文檔
- `DELETE /api/v1/chromadb/collections/{name}/documents/{id}` - 刪除文檔

2. **創建 API 模型**（`services/api/models/chromadb.py`）：

- CollectionCreateRequest
- DocumentAddRequest
- QueryRequest
- QueryResponse
- DocumentResponse

3. **註冊路由**（`services/api/main.py`）：

- 導入 chromadb router
- 添加到 API 路由中

4. **完善單元測試**（`databases/chromadb/tests/test_client.py`）：

- 測試連線池功能
- 測試錯誤處理和重試
- 測試批量操作
- 測試嵌入維度校驗
- 提高測試覆蓋率到 ≥80%

5. **創建 API 測試**（`tests/api/test_chromadb_api.py`）：

- 測試所有 API 端點
- 測試錯誤處理
- 測試參數驗證

### 任務 1.3.4: 性能優化（批量寫入、index 調整、壓測）

**文件操作：**

1. **創建性能測試腳本**（`scripts/performance/chromadb_benchmark.py`）：

- 批量寫入性能測試（1k、10k、100k 文檔）
- 檢索性能測試（QPS、P95 latency）
- 並發測試
- 資源使用監控（CPU、記憶體、I/O）
- 生成性能報告

2. **創建性能優化文檔**（`docs/performance/chromadb-optimization.md`）：

- 批量寫入最佳實踐
- Index 調整建議
- 資源配置建議
- 性能調優指南

3. **實現批量寫入優化**（`databases/chromadb/collection.py`）：

- 實現批量插入接口（batch_add）
- 添加批量大小配置
- 實現異步批量寫入（可選）

4. **驗證性能標準**：

- 在 staging 環境寫入 1k 筆嵌入
- 驗證檢索時間 < 200ms
- 生成性能測試報告

### 配置更新

**文件操作：**

1. **創建環境變數模板**（`.env.example`）：

- 添加 ChromaDB 相關環境變數
- CHROMADB_HOST、CHROMADB_PORT
- CHROMADB_PERSIST_DIR
- CHROMADB_CONNECTION_POOL_SIZE
- CHROMADB_BATCH_SIZE

2. **更新項目文檔**：

- 更新 `README.md` 添加 ChromaDB 使用說明
- 更新 `docs/PROJECT_CONTROL_TABLE.md` 標記任務完成

## 驗收標準

1. ✅ 在 staging 環境成功寫入 1k 筆嵌入並於 200ms 內完成檢索
2. ✅ SDK 單元測試覆蓋率 ≥80%，並通過 CI
3. ✅ 監控儀表板顯示 CPU、記憶體、I/O 指標
4. ✅ 所有 API 端點正常工作
5. ✅ K8s 部署配置完整可用
6. ✅ 性能測試報告生成

## 風險與對策

- **風險**: I/O 性能不足
- **對策**: 採用本地 SSD 儲存與資源限制配置；必要時啟用 sharding

- **風險**: 嵌入維度不一致
- **對策**: 在 SDK 中加入 metadata 校驗與轉換

- **風險**: 連線池管理複雜
- **對策**: 使用簡單的連接復用機制，避免過度設計

## 時間表

- **Day 1 (1.3.1)**: 完成 Docker/K8s 部署配置和監控設定
- **Day 2-3 (1.3.2)**: 完成 SDK 封裝增強（連線池、錯誤處理）
- **Day 3-4 (1.3.3)**: 完成 API 路由和單元測試
- **Day 4 (1.3.4)**: 完成性能優化和壓測，產出報告

### To-dos

- [ ] 完善 docker-compose.yml 中的 ChromaDB 配置（資源限制、持久化優化）
- [ ] 創建 K8s 部署配置（deployment.yaml, service.yaml, configmap.yaml, pvc.yaml）
- [ ] 創建監控配置（Prometheus metrics, Grafana dashboard）
- [ ] 創建部署文檔（K8s 部署指南、環境配置說明）
- [ ] 實現連線池管理和自動重連機制（client.py）
- [ ] 增強錯誤處理和重試機制（client.py, collection.py）
- [ ] 實現批量寫入優化和命名空間管理（collection.py）
- [ ] 創建工具模組（嵌入維度轉換、metadata 驗證）
- [ ] 創建 ChromaDB API 路由（services/api/routers/chromadb.py）
- [ ] 創建 API 請求/響應模型（services/api/models/chromadb.py）
- [ ] 在 main.py 中註冊 ChromaDB 路由
- [ ] 完善單元測試，提高覆蓋率到 ≥80%
- [ ] 創建 API 端點測試（tests/api/test_chromadb_api.py）
- [ ] 創建性能測試腳本（scripts/performance/chromadb_benchmark.py）
- [ ] 創建性能優化文檔（批量寫入、index 調整建議）
- [ ] 實現批量寫入優化（batch_add 接口、批量大小配置）
- [ ] 執行性能測試並驗證驗收標準（1k 筆嵌入、<200ms 檢索）
- [ ] 更新 .env.example 添加 ChromaDB 環境變數
- [ ] 更新項目文檔（README.md, PROJECT_CONTROL_TABLE.md）
