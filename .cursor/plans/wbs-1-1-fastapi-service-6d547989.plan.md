<!-- 6d547989-1566-40bd-b0c9-6597c2c8242c 4f316fd0-5b72-48f5-9bc7-cf4bdb823538 -->
# WBS 1.1 FastAPI Service 實施計劃

## 目標

完成 WBS 1.1 的所有任務，建立符合計劃要求的 FastAPI 服務骨架，包括：

- 重構 api_gateway/ 到 services/api/
- 補齊缺失功能（Request ID 中間件、pyproject.toml、smoke test）
- 確保 OpenAPI 文檔生成和健康檢查功能完整

## 實施步驟

### 任務 1.1.1: 建立 FastAPI 基礎框架與專案模板

**文件操作：**

1. 創建 `services/api/` 目錄結構：

- `services/api/__init__.py`
- `services/api/main.py` (從 api_gateway/main.py 遷移)
- `services/api/core/__init__.py`
- `services/api/core/response.py` (從 api_gateway/core/response.py 遷移)
- `services/api/middleware/__init__.py`
- `services/api/middleware/logging.py` (從 api_gateway/middleware/logging.py 遷移)
- `services/api/middleware/error_handler.py` (從 api_gateway/middleware/error_handler.py 遷移)
- `services/api/routers/__init__.py`
- `services/api/routers/health.py` (從 api_gateway/routers/health.py 遷移)
- `services/api/routers/agents.py` (從 api_gateway/routers/agents.py 遷移)
- `services/api/routers/task_analyzer.py` (從 api_gateway/routers/task_analyzer.py 遷移)
- `services/api/routers/orchestrator.py` (從 api_gateway/routers/orchestrator.py 遷移)
- `services/api/models/__init__.py`

2. 更新所有 import 語句：

- 將 `from api_gateway.` 改為 `from services.api.`
- 更新 main.py 中的路由導入

3. 創建 `services/api/pyproject.toml`：

- 定義項目元數據
- 配置依賴管理
- 配置構建工具

### 任務 1.1.2: 設計 API 路由與命名空間，定義版本策略

**文件操作：**

1. 更新 `services/api/main.py`：

- 確保 API 版本策略（/api/v1）
- 驗證路由命名空間設計
- 添加版本信息端點

2. 創建 `services/api/core/version.py`：

- 定義 API 版本常量
- 提供版本查詢功能

### 任務 1.1.3: 中間件實作（CORS、Request ID、日誌、錯誤攔截）

**文件操作：**

1. 創建 `services/api/middleware/request_id.py`：

- 實現 Request ID 生成和傳遞
- 在響應頭中添加 X-Request-ID

2. 更新 `services/api/main.py`：

- 添加 Request ID 中間件
- 確保中間件順序正確（Request ID -> Logging -> Error Handler -> CORS）

3. 更新 `services/api/middleware/logging.py`：

- 整合 Request ID 到日誌記錄中

### 任務 1.1.4: 自動生成 API 文件（OpenAPI/Redoc）並加入 CI 檢查

**文件操作：**

1. 更新 `services/api/main.py`：

- 確保 OpenAPI 配置完整
- 添加 API 描述和標籤
- 配置 OpenAPI schema 路徑

2. 創建 `scripts/export_openapi.py`：

- 導出 OpenAPI JSON 到 `docs/openapi.json`
- 用於 CI/CD 檢查

3. 更新 `services/api/pyproject.toml`：

- 添加 OpenAPI 相關依賴（如果需要）

### 任務 1.1.5: 健康檢查端點與 smoke test 腳本

**文件操作：**

1. 驗證 `services/api/routers/health.py`：

- 確保 /health、/ready、/metrics 端點完整
- 添加版本信息到健康檢查響應

2. 創建 `scripts/smoke_test.sh`：

- 測試健康檢查端點
- 測試 API 版本端點
- 測試 OpenAPI 文檔可訪問性
- 生成測試報告

3. 創建 `scripts/smoke_test.py`（可選，Python 版本）：

- 使用 httpx 進行自動化測試
- 更詳細的測試覆蓋

### 配置更新

**文件操作：**

1. 更新 `docker-compose.yml`：

- 將 api-gateway 服務改為 api 服務
- 更新工作目錄和命令
- 更新健康檢查路徑

2. 更新 `Dockerfile`：

- 更新 CMD 命令指向 services.api.main:app
- 確保工作目錄正確

3. 創建 `services/api/.env.example`：

- 定義環境變數模板
- 包含 API_GATEWAY_HOST、API_GATEWAY_PORT、LOG_LEVEL 等

4. 更新 `requirements.txt`（如果需要）：

- 確保所有依賴已包含

### 清理工作

**文件操作：**

1. 刪除舊的 `api_gateway/` 目錄（在確認遷移成功後）

## 驗收標準

1. ✅ 服務可在 Docker Compose 中啟動
2. ✅ `/health` 端點返回 200
3. ✅ `/docs` 和 `/redoc` 可正常訪問
4. ✅ OpenAPI JSON 可導出
5. ✅ Smoke test 全部通過
6. ✅ 所有 import 語句正確更新
7. ✅ Request ID 中間件正常工作

## 風險與對策

- **風險**: 其他模組仍引用 api_gateway
- **對策**: 搜索並更新所有引用，或保留 api_gateway 作為兼容層
- **風險**: Docker 配置需要調整
- **對策**: 仔細測試 docker-compose up 確保服務正常啟動

### To-dos

- [x] Review docs/PROJECT_CONTROL_TABLE.md phase 1 WBS 1.1-1.6
- [x] Draft adjusted sub-plans for WBS 1.1-1.6
- [x] 創建 services/api/ 目錄結構並遷移所有文件（19個文件已創建）
- [x] 更新所有 import 語句從 api_gateway 改為 services.api
- [x] 創建 services/api/pyproject.toml 配置文件
- [x] 完善 API 路由設計和版本策略（已創建 version.py 和版本端點）
- [x] 實現 Request ID 中間件並整合到主應用
- [x] 確保 OpenAPI 文檔生成並創建導出腳本（export_openapi.py）
- [x] 創建 smoke test 腳本並驗證健康檢查端點（smoke_test.sh 和 smoke_test.py）
- [x] 更新 docker-compose.yml 和 Dockerfile 配置
- [x] 創建 .env.example 文件
- [ ] 清理舊的 api_gateway/ 目錄（可選，等階段一完成後一起測試）
- [ ] 創建 services/api/ 目錄結構並遷移所有文件
- [ ] 更新所有 import 語句從 api_gateway 改為 services.api
- [ ] 創建 services/api/pyproject.toml 配置文件
- [ ] 完善 API 路由設計和版本策略
- [ ] 實現 Request ID 中間件並整合到主應用
- [ ] 確保 OpenAPI 文檔生成並創建導出腳本
- [ ] 創建 smoke test 腳本並驗證健康檢查端點
- [ ] 更新 docker-compose.yml 和 Dockerfile 配置
- [ ] 創建 .env.example 文件
- [ ] 清理舊的 api_gateway/ 目錄（可選）
