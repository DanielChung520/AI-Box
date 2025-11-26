<!--
代碼功能說明: WBS 1.1 FastAPI Service 子計劃
創建日期: 2025-11-25 19:13 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-11-25 19:13 (UTC+8)
-->

# WBS 1.1 FastAPI Service 子計劃

## 1. 背景與目標
- 在階段一完成基礎設施後，需於 3 個工作日內建立可部署的 FastAPI 服務骨架。
- 目標為提供統一 API 入口、健康檢查、OpenAPI 文件，並預留日後整合 MCP 與安全模組的接口。

## 2. 範圍
- 建立 `services/api` 專案結構、環境設定與依賴。
- 實作主路由、基礎中間件、例外處理、logging、OpenAPI 自動文件。
- 產出健康檢查端點、基本 smoke test、Docker Compose 服務配置。

## 3. 工作拆解
| 任務編號 | 描述 | 負責人 | 工期 | 依賴 |
|---------|------|--------|------|------|
| 1.1.1 | 建立 FastAPI 基礎框架與專案模板 | Backend-1 | 1 天 | 已完成的 1.0.* 環境 |
| 1.1.2 | 設計 API 路由與命名空間，定義版本策略 | Backend-1 | 0.5 天 | 1.1.1 |
| 1.1.3 | 中間件實作（CORS、Request ID、日誌、錯誤攔截） | Backend-1 | 1 天 | 1.1.1 |
| 1.1.4 | 自動生成 API 文件（OpenAPI/Redoc）並加入 CI 檢查 | Backend-1 | 0.5 天 | 1.1.2 |
| 1.1.5 | 健康檢查端點與 smoke test 腳本 | Backend-1 | 0.5 天 | 1.1.3 |

## 4. 時間表（2025/11/26 - 2025/11/28）
- 11/26：完成 1.1.1、1.1.2，提交框架 PR。
- 11/27 上午：完成 1.1.3，中午前完成 code review。
- 11/27 下午：完成 1.1.4、1.1.5，產出 API 文件與 smoke test 報告。
- 11/28：預留整合緩衝，與 WBS 1.2 進行接口對齊。

## 5. 資源與交付物
- 資源：Backend-1 全職投入 2.5 日；DevOps-1 協助 `.env` 與 docker network。
- 交付物：
  - `services/api` 專案代碼與 `pyproject.toml` 依賴。
  - `docker-compose.api.yaml` 或整合至主 compose。
  - API 規格檔（`openapi.json`）、smoke test 報告。

## 6. 風險與對策
- **依賴未確認**：若後續模組尚未提供接口，先以 mock 實作，待 WBS 1.2/1.6 完成後更新。
- **部署環境差異**：本地與 CI 設定差異可透過 `.env.example` 與腳本統一。

## 7. 驗收標準
- FastAPI 服務可在 Docker Compose 中啟動並通過健康檢查。
- OpenAPI 文件可透過 `/docs` 與 `/redoc` 正常瀏覽。
- Smoke test（Ping/版本檢查）全數通過並附報告。

## 8. 更新紀錄
| 日期 | 說明 | 更新人 |
|------|------|--------|
| 2025-11-25 | 初版子計劃建立 | Daniel Chung |
