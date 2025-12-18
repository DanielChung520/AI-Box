<!--
代碼功能說明: WBS-G1 前端輸入框與模型選擇（Auto/收藏）
創建日期: 2025-12-13 13:55 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 15:49 (UTC+8)
-->

# WBS-G1：前端輸入框與模型選擇（Auto/收藏）

## 目標
前端輸入框具備：
- 模型選擇：**Auto** + **我的收藏**（可快速切換）
- 發送對話：支援 session_id / task_id
- 顯示：回覆、路由結果摘要（可選）、錯誤訊息

## 現況（已存在 / 尚未串接）

- **已存在**：模型選擇 UI（含 `auto`）已在 `ai-bot/src/components/ChatInput.tsx`。
- **尚未串接**：`ChatArea.tsx` 目前未傳 `onModelSelect`，且 `onMessageSend` 仍是 stub；因此選到的模型尚未進入後端請求。

> 本 WBS 的核心就是把「選擇結果」寫回 `task.executionConfig.modelId` 並在送出訊息時帶上 `model_selector`。

## 工作項
- **G1.1 UI 組件**
  - model selector：Auto / Favorites
  - 收藏管理：add/remove（MVP 可先 localStorage）

- **G1.2 API 整合**
  - 呼叫後端 Chat API（建議新路由，如 `/api/v1/chat`）
  - request 附帶：session_id、task_id、messages、model_selector
    - `model_selector.mode`: `auto` | `manual` | `favorite`
    - `model_selector.model_id`: 使用前端選到的 `selectedModelId`（manual/favorite 時必填）
    - `model_selector.policy_overrides`: （預留）你提到的「系統參數 json」覆蓋，例如 cost/latency/quality 偏好

- **G1.3 觀測顯示（MVP）**
  - 回覆下方顯示：provider/model/latency（若後端回）

## 驗收
- Auto/收藏模型切換可用，且送出請求會攜帶 `model_selector`
- 選擇結果會寫入並持久化到 `task.executionConfig.modelId`（切換任務可恢復）
- 可完成一次對話並顯示結果
