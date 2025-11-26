<!--
代碼功能說明: WBS 1.2 MCP Server/Client 子計劃
創建日期: 2025-11-25 19:13 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-11-25 19:13 (UTC+8)
-->

# WBS 1.2 MCP Server/Client 子計劃

## 1. 背景與目標
- 建立統一的 MCP server/client 框架，供後續 Agent、工具與 FastAPI 使用。
- 目標為 4 個工作日內完成範本、工具註冊、測試流程，確保可快速擴充。

## 2. 範圍
- MCP server 範本、客製協議、監控 hook。
- MCP client SDK、連線管理、錯誤處理。
- 工具整合與 loopback 測試、部署腳本。

## 3. 工作拆解
| 任務編號 | 描述 | 負責人 | 工期 | 依賴 |
|---------|------|--------|------|------|
| 1.2.1 | 建立 MCP Server 框架（目錄、啟動流程、配置檔） | Backend-1 | 2 天 | 1.1 完成健康端點 |
| 1.2.2 | MCP Client 框架與連線池 | Backend-1 | 1.5 天 | 1.2.1 |
| 1.2.3 | 工具整合（Task Analyzer mock、File tool 等） | Backend-1 | 1 天 | 1.2.1, 1.2.2 |
| 1.2.4 | MCP 測試（loopback、自動化腳本、CI） | Backend-1 | 1 天 | 1.2.3 |

## 4. 時間表（2025/11/28 - 2025/12/02）
- 11/28：完成 1.2.1 架構與基本測試。
- 12/01 上午：完成 1.2.2；下午開始 1.2.3 工具整合。
- 12/02：完成 1.2.4 測試、撰寫文件並與 FastAPI 整合驗證。

## 5. 資源與交付物
- 資源：Backend-1 主導；DevOps-1 支援部署腳本與監控整合。
- 交付物：
  - `services/mcp-server`、`clients/mcp-client` 代碼與 README。
  - 工具註冊表、範例工具。
  - 測試報告（loopback latency、連線穩定性）。

## 6. 風險與對策
- **協定兼容性**：優先與階段二既有 Agent 假資料連線，早期驗證兼容性。
- **工具膨脹**：採用配置式工具註冊，避免硬編碼。

## 7. 驗收標準
- MCP server/client 可在 docker-compose 中啟動，並由 FastAPI 呼叫成功。
- 工具整合清單至少包含 Task Analyzer mock 與 File tool。
- 自動化測試涵蓋連線、錯誤處理、基礎性能。

## 8. 更新紀錄
| 日期 | 說明 | 更新人 |
|------|------|--------|
| 2025-11-25 | 初版子計劃建立 | Daniel Chung |
