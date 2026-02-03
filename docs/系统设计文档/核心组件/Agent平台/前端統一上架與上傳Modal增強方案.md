# 前端統一上架與上傳 Modal 增強方案

**最後更新**: 2026-01-27 27:00 UTC+8  
**維護人**: Daniel Chung  
**版本**: v2.3

**目標**：將專業知識上架與一般文件上傳**統一從前端**完成。提供兩種方案：
- **方案 A**（詳細版）：支援選擇目錄、標記檔案、點選 Ontology、JSON 校驗
- **方案 B**（簡化版，**推薦**）：僅對 systemAdmin/授權用戶顯示「Agent 知識庫」checkbox，若勾選且無 Ontology，則顯示兩個資料夾選擇（Ontology + 知識庫）

---

## 1. 概述

### 1.1 原則

- **單一入口**：前端上傳 Modal 為文件上傳與 Agent 知識上架的共同入口。
- **同一後端 API**：上傳仍走 `POST /api/v1/files/v2/upload`；Ontology 匯入另需後端 API（見 §5）。
- **體驗一致**：一般上傳、知識庫上架、Ontology 上傳，均透過同一 Modal，以選項區分行為。

### 1.2 方案選擇

| 方案 | 說明 | 適用場景 | 優先級 |
|------|------|----------|--------|
| **方案 A（詳細版）** | 支援選擇目錄、標記檔案、點選 Ontology、JSON 校驗 | 需要精細控制每個檔案類型 | P1 |
| **方案 B（簡化版，推薦）** | 僅對 systemAdmin/授權用戶顯示「Agent 知識庫」checkbox；若勾選且無 Ontology，顯示兩個資料夾選擇 | Agent 知識上架（批量） | **P0** |

**建議**：優先實作**方案 B**，更符合 Agent 知識上架的批量場景。

---

## 2. 方案 B：簡化版（推薦）

### 2.1 權限檢查

- **檢查條件**：用戶為 `systemAdmin` 或具備授權權限（如 `has_permission(Permission.ALL.value)`）。
- **實作方式**：
  - 前端：從 `get_current_user` 或登入響應取得 `user_id`、`roles`、`permissions`。
  - 判斷：`user_id === "systemAdmin"` 或 `permissions.includes("all")` 或 `has_permission(Permission.ALL.value)`。
  - 若符合，在 Modal 中顯示「**上架知識庫**」checkbox。

### 2.2 「上架知識庫」Checkbox 與 is_agent_task 檢查

- **任務 ID 來源**：
  - Modal **不提供任務代碼輸入欄位**；任務 ID 來自**當前任務**（`forceTaskId ?? defaultTaskId`），唯讀、不可編輯。
  - 須在任務工作區情境下開啟上傳（如 Chat 選中任務、ResultPanel 聚焦任務），否則提示「請在任務工作區中打開上傳（需有當前任務）」。

- **Checkbox 位置**：在「上傳到任務工作區」下方，僅對 systemAdmin/授權用戶顯示。
- **勾選時檢查**：
  - 當用戶嘗試勾選「上架知識庫」checkbox 時，系統會檢查當前任務的 `is_agent_task` 標記。
  - **如果 `is_agent_task: true`**：允許勾選，進入「Agent 知識庫上架模式」。
  - **如果 `is_agent_task: false` 或未設置**：**不允許勾選**，顯示提示「當前任務不是 Agent 任務，無法使用知識庫上架功能。請先在任務右鍵選單中「標記為 Agent 任務」。」，checkbox 保持未勾選狀態。
  - **如果任務不存在**：不允許勾選，顯示提示「任務不存在，無法使用知識庫上架功能。」。

- **行為**：
  - 勾選成功後，進入「Agent 知識庫上架模式」，顯示 Ontology 與知識庫資料夾選擇器。
  - 顯示唯讀「上架至任務：{task_id}」。
  - 系統依當前任務查詢是否存在、是否有 Ontology，以決定顯示一個或兩個資料夾選擇。
  - **取消勾選**：可以隨時取消勾選，退出 Agent 知識庫上架模式，清除已選擇的資料夾。

### 2.3 新 Agent vs 既有 Agent、Ontology 檢查

- **檢查時機**：勾選「上架知識庫」且**已通過 `is_agent_task` 檢查**後。
- **判斷「是否為新 Agent」**：
  - 呼叫 `GET /api/v1/user-tasks/{task_id}`（或等效）查詢任務是否存在。
  - **任務不存在** → 視為**新 Agent**：一律顯示「Ontology 資料夾」+「知識庫資料夾」兩者，不依 Ontology 查詢結果。
  - **任務存在** → **既有 Agent**：再依 Ontology 檢查決定一個或兩個資料夾（見下）。
- **Ontology 檢查**（僅於既有 Agent 時影響 UI）：
  - 呼叫 `GET /api/v1/ontologies?task_id={task_id}`（或依名稱匹配 domain/major）。
  - **有 Ontology**：僅顯示「知識庫資料夾」。
  - **無 Ontology**：顯示「Ontology 資料夾」+「知識庫資料夾」。
- **整理**：
  - **新 Agent**（無任務）→ 永遠顯示兩個資料夾。
  - **既有 Agent + 有 Ontology** → 僅知識庫資料夾。
  - **既有 Agent + 無 Ontology** → 兩個資料夾。

### 2.4 資料夾選擇（無 Ontology 時）

- **顯示條件**：勾選「上架知識庫」且**無 Ontology**。
- **UI 元素**：
  1. **Ontology 資料夾**：`<input type="file" webkitdirectory>`，選擇包含 `*-domain.json`、`*-major.json` 的目錄。
  2. **知識庫資料夾**：`<input type="file" webkitdirectory>`，選擇知識庫檔案目錄。
- **驗證**：
  - Ontology 資料夾：至少包含一個 `*-domain.json` 或 `*-major.json`。
  - 知識庫資料夾：至少包含一個檔案（排除 `.json` 或依需求過濾）。
- **觸發上傳**：**僅選擇路徑不會上傳**。須由用戶點擊 Modal 右下角「**上架 Agent 知識庫**」按鈕後，才開始上架。
- **執行順序**（點擊按鈕後）：
  1. 先上傳 Ontology（呼叫 Ontology 匯入 API，見 §5.2）。
  2. Ontology 上傳成功後，再上傳知識庫（呼叫 `POST /api/v1/files/v2/upload`，帶 `task_id`）。

### 2.5 資料夾選擇（有 Ontology 時）

- **顯示條件**：勾選「上架知識庫」且**已有 Ontology**。
- **UI 元素**：
  - 僅顯示「知識庫資料夾」選擇。
- **觸發上傳**：**僅選擇路徑不會上傳**。須由用戶點擊 Modal 右下角「**上架 Agent 知識庫**」按鈕後，才開始上架。
- **執行**（點擊按鈕後）：直接上傳知識庫（呼叫 `POST /api/v1/files/v2/upload`，帶 `task_id`）。

### 2.6 流程圖

```
用戶打開上傳 Modal（須在任務工作區情境，才有當前任務）
  ↓
檢查用戶權限（systemAdmin 或授權用戶？）
  ↓ 是
顯示「上架知識庫」checkbox
  ↓
系統自動檢查當前任務的 is_agent_task（後台查詢，不阻塞 UI）
  ↓
用戶嘗試勾選「上架知識庫」checkbox
  ↓
檢查 is_agent_task：
  ├─ is_agent_task: true → ✅ 允許勾選，進入 Agent 知識庫上架模式
  ├─ is_agent_task: false → ❌ 阻止勾選，提示「需先標記為 Agent 任務」
  └─ 任務不存在 → ❌ 阻止勾選，提示「任務不存在」
  ↓ 勾選成功
是否有當前任務（forceTaskId ?? defaultTaskId）？
  ↓ 否
提示「請在任務工作區中打開上傳（需有當前任務）」，禁用上架按鈕
  ↓ 是
並行：① 查詢任務是否存在  ② 查詢是否有 Ontology
  ↓
  ├─ 任務不存在 → 新 Agent → 顯示「Ontology 資料夾」+「知識庫資料夾」
  └─ 任務存在（既有 Agent）
        ├─ 有 Ontology → 僅「知識庫資料夾」
        └─ 無 Ontology → 「Ontology 資料夾」+「知識庫資料夾」
  ↓
用戶選擇路徑（僅選定，不觸發上傳）
  ↓
用戶點擊 Modal 右下角「知識庫上架」按鈕
  ↓
開始上架：先 Ontology（如需）再知識庫
  ↓
或取消勾選「上架知識庫」checkbox，退出上架模式
```

### 2.7 標記為 Agent 任務（右鍵選單）

- **位置**：任務列表的右鍵選單中，僅對 systemAdmin/授權用戶顯示。
- **選項名稱**：
  - 如果任務未被標記：顯示「標記為 Agent 任務」
  - 如果任務已被標記：顯示「取消 Agent 任務標記」
- **行為**：
  - 點擊後，系統會更新任務的 `is_agent_task` 字段。
  - 標記後，該任務即可使用 Agent 知識庫上架功能，無需符合命名規範。
  - 取消標記後，任務恢復為一般任務（除非符合命名規範）。
- **圖標**：
  - 已標記：`fa-solid fa-robot`（實心機器人圖標，藍色）
  - 未標記：`fa-regular fa-robot`（空心機器人圖標，灰色）

---

## 3. 方案 A：詳細版（備選）

### 3.1 選擇檔案 / 選擇目錄

- **選擇檔案**（既有）：`<input type="file" multiple>`，可多選。
- **選擇目錄**（新增）：`<input type="file" webkitdirectory>`，選取整個目錄。
  - 取得 `FileList`，保留 `file.webkitRelativePath`（若瀏覽器支援）以便顯示相對路徑。
  - 目錄內所有檔案加入待上傳列表；子目錄遞迴包含（依瀏覽器行為）。
- UI：在拖放區並列 **「選擇檔案」** 與 **「選擇目錄」** 按鈕；拖放仍支援檔案（目錄拖放依瀏覽器）。

### 3.2 標記上傳檔案

- 待上傳列表每一筆可**標記**：
  - **類型**：`知識庫` | `Ontology`
  - **關聯 Ontology**（選填）：若為知識庫檔案，可選「要關聯的 Ontology」；若為 Ontology 檔案，此欄隱藏或忽略。
- 標記方式例如：
  - 每列有下拉選單「類型」＋可選「關聯 Ontology」；
  - 或支援批量標記：多選檔案後，一次性設為「知識庫」或「Ontology」。
- 預設：新加入的檔案為 **知識庫**；`.json` 且檔名符合 `*-domain.json` / `*-major.json` 可自動建議為 **Ontology**（使用者可改）。

### 3.3 點選 Ontology

- **關聯 Ontology**：
  - 下拉選單，選項來自後端「Ontology 列表」API（例如 `GET /api/v1/ontologies` 或既有查詢）。
  - 可支援「不限」表示不綁定 Ontology。
- **上傳為 Ontology**：
  - 將檔案標記為 `Ontology` 即視為上傳 Ontology；
  - 後端須能區分「一般檔案」與「Ontology 匯入」，例如靠 `metadata`、額外 `Form` 欄位或專用端點（見 §5）。

### 3.4 Ontology JSON 格式與屬性檢查

僅對**標記為 Ontology** 且副檔名為 `.json` 的檔案進行校驗。

#### 3.4.1 JSON 格式

- 可 `JSON.parse`，否則視為格式錯誤，阻擋上傳並顯示錯誤檔名與訊息。

#### 3.4.2 必填屬性（Domain / Major 共用）

| 屬性 | 類型 | 說明 |
|------|------|------|
| `type` | `string` | `"base"` \| `"domain"` \| `"major"` |
| `name` | `string` | Ontology 名稱（如 `KA_Agent_Domain`） |
| `version` | `string` | 語義化版本（如 `"1.0"`） |
| `ontology_name` | `string` | 顯示名稱（如 `KA_Agent_Domain_Ontology`） |
| `entity_classes` | `array` | 實體類別陣列 |
| `object_properties` | `array` | 物件屬性／關係類型陣列 |

#### 3.4.3 檢核規則

- 缺少任一首填屬性 → 該檔不允許上傳，並在 Modal 內顯示錯誤（例如：「`xxx.json`：缺少 `entity_classes`」）。
- `type` 若為 `domain` 或 `major`，依現有 Ontology 慣例檢查即可；若有額外規則再補充。

#### 3.4.4 實作建議

- 前端在**上傳前**對標記為 Ontology 的 `.json` 逐一讀取（`FileReader`）、`JSON.parse`、檢查上述屬性。
- 全部通過才呼叫上傳 API；若有任一失敗，不送出並列出錯誤清單。

---

## 2. 上傳 Modal 行為規格

### 2.1 選擇檔案 / 選擇目錄

- **選擇檔案**（既有）：`<input type="file" multiple>`，可多選。
- **選擇目錄**（新增）：`<input type="file" webkitdirectory>`，選取整個目錄。
  - 取得 `FileList`，保留 `file.webkitRelativePath`（若瀏覽器支援）以便顯示相對路徑。
  - 目錄內所有檔案加入待上傳列表；子目錄遞迴包含（依瀏覽器行為）。
- UI：在拖放區並列 **「選擇檔案」** 與 **「選擇目錄」** 按鈕；拖放仍支援檔案（目錄拖放依瀏覽器）。

### 2.2 標記上傳檔案

- 待上傳列表每一筆可**標記**：
  - **類型**：`知識庫` | `Ontology`
  - **關聯 Ontology**（選填）：若為知識庫檔案，可選「要關聯的 Ontology」；若為 Ontology 檔案，此欄隱藏或忽略。
- 標記方式例如：
  - 每列有下拉選單「類型」＋可選「關聯 Ontology」；
  - 或支援批量標記：多選檔案後，一次性設為「知識庫」或「Ontology」。
- 預設：新加入的檔案為 **知識庫**；`.json` 且檔名符合 `*-domain.json` / `*-major.json` 可自動建議為 **Ontology**（使用者可改）。

### 2.3 點選 Ontology

- **關聯 Ontology**：
  - 下拉選單，選項來自後端「Ontology 列表」API（例如 `GET /api/v1/ontologies` 或既有查詢）。
  - 可支援「不限」表示不綁定 Ontology。
- **上傳為 Ontology**：
  - 將檔案標記為 `Ontology` 即視為上傳 Ontology；
  - 後端須能區分「一般檔案」與「Ontology 匯入」，例如靠 `metadata`、額外 `Form` 欄位或專用端點（見 §5）。

### 2.4 Ontology JSON 格式與屬性檢查

僅對**標記為 Ontology** 且副檔名為 `.json` 的檔案進行校驗。

#### 2.4.1 JSON 格式

- 可 `JSON.parse`，否則視為格式錯誤，阻擋上傳並顯示錯誤檔名與訊息。

#### 2.4.2 必填屬性（Domain / Major 共用）

| 屬性 | 類型 | 說明 |
|------|------|------|
| `type` | `string` | `"base"` \| `"domain"` \| `"major"` |
| `name` | `string` | Ontology 名稱（如 `KA_Agent_Domain`） |
| `version` | `string` | 語義化版本（如 `"1.0"`） |
| `ontology_name` | `string` | 顯示名稱（如 `KA_Agent_Domain_Ontology`） |
| `entity_classes` | `array` | 實體類別陣列 |
| `object_properties` | `array` | 物件屬性／關係類型陣列 |

#### 2.4.3 檢核規則

- 缺少任一首填屬性 → 該檔不允許上傳，並在 Modal 內顯示錯誤（例如：「`xxx.json`：缺少 `entity_classes`」）。
- `type` 若為 `domain` 或 `major`，依現有 Ontology 慣例檢查即可；若有額外規則再補充。

#### 2.4.4 實作建議

- 前端在**上傳前**對標記為 Ontology 的 `.json` 逐一讀取（`FileReader`）、`JSON.parse`、檢查上述屬性。
- 全部通過才呼叫上傳 API；若有任一失敗，不送出並列出錯誤清單。

---

## 4. 待上傳列表 UI 要點

### 4.1 方案 B（簡化版）

- 勾選「Agent 知識庫」後：
  - 顯示 `task_id` 輸入框（若未提供 `defaultTaskId`）。
  - 根據 Ontology 檢查結果，顯示對應的資料夾選擇（Ontology + 知識庫，或僅知識庫）。
  - 顯示已選擇的資料夾路徑。
  - 上傳按鈕文字改為「上架 Agent 知識庫」。

### 4.2 方案 A（詳細版）

- 每個檔案顯示：檔名、大小、類型標記（知識庫 / Ontology）、關聯 Ontology（若有）。
- 可移除單一檔案；若為目錄加入，可考慮支援「移除整個目錄」。
- 顯示 Ontology 校驗結果：通過（勾）／不通過（叉＋簡短原因）。
- 上傳按鈕：若有任一 Ontology 校驗未過，可 disable 並提示先修正。

---

## 5. 上傳流程（前端）

### 5.1 方案 B（簡化版）

1. 用戶打開 Modal → 檢查權限 → 顯示「Agent 知識庫」checkbox（若符合）。
2. 用戶勾選「Agent 知識庫」→ 輸入/選擇 `task_id`。
3. 檢查 Ontology（查詢後端或前端列表）。
4. **無 Ontology**：
   - 顯示「Ontology 資料夾」+「知識庫資料夾」選擇。
   - 用戶選擇兩個資料夾。
   - 先上傳 Ontology（呼叫 Ontology 匯入 API，見 §6.2）。
   - Ontology 上傳成功後，再上傳知識庫（呼叫 `POST /api/v1/files/v2/upload`，帶 `task_id`）。
5. **有 Ontology**：
   - 顯示「知識庫資料夾」選擇。
   - 用戶選擇知識庫資料夾。
   - 直接上傳知識庫（呼叫 `POST /api/v1/files/v2/upload`，帶 `task_id`）。

### 5.2 方案 A（詳細版）

1. 使用者選擇檔案或目錄 → 加入待上傳列表。
2. 對每個檔案設定類型（知識庫 / Ontology）與關聯 Ontology（若為知識庫）。
3. 對標記為 Ontology 的 `.json` 執行 §3.4 的 JSON 與屬性檢查。
4. 若全部通過：
   - **一般檔案／知識庫**：照現有邏輯呼叫 `POST /api/v1/files/v2/upload`（可帶 `task_id`、`target_folder_id` 等）。
   - **Ontology 檔案**：呼叫 Ontology 匯入 API（見 §6），或同一 `v2/upload` 且以額外參數標記為 Ontology 由後端分流。

---

## 6. 後端配合事項

### 6.1 現有上傳 API

- `POST /api/v1/files/v2/upload` 維持不變，繼續作為**一般檔案／知識庫**上傳入口。

### 6.2 Ontology 匯入 API（新增建議）

- 若**統一從前端**完成 Ontology 上架，建議新增例如：
  - `POST /api/v1/ontologies/import`
- 請求：`multipart/form-data`，上傳一個或多個 Ontology JSON 檔案。
- 後端邏輯：
  - 再驗證 JSON 格式與必填屬性（與前端規則一致，見 §3.4.2）。
  - 呼叫既有 `OntologyStoreService.save_ontology` 寫入 ArangoDB。
- 權限：建議僅允許具備 Ontology 管理權限的使用者（如 systemAdmin 或指定角色），可使用 `require_system_admin` 依賴。

### 6.3 Ontology 查詢 API（方案 B 需要）

- 新增或擴展現有 API，支援依 `task_id` 查詢 Ontology：
  - `GET /api/v1/ontologies?task_id={task_id}` 或
  - `GET /api/v1/ontologies?name_pattern={task_id}_*`（查詢名稱包含 task_id 的 Ontology）
- 返回：對應的 domain/major Ontology 列表。
- 用途：前端判斷是否已有 Ontology，決定顯示一個或兩個資料夾選擇。

### 6.4 關聯 Ontology 的傳遞

- 若知識庫上傳時要「關聯 Ontology」：
  - 可在 `v2/upload` 的 `Form` 中新增選填欄位，例如 `ontology_id` 或 `ontology_key`；
  - 後端在後續處理（如 KG 提取、編碼）時使用該關聯。

---

## 7. 實作順序建議

### 7.1 方案 B（簡化版，推薦）

| 階段 | 內容 |
|------|------|
| **1** | 前端：檢查用戶權限（systemAdmin 或授權用戶），在 Modal 中顯示「Agent 知識庫」checkbox。 |
| **2** | 前端：實作「Agent 知識庫」勾選邏輯，顯示 `task_id` 輸入框。 |
| **3** | 後端：新增或擴展 Ontology 查詢 API（§6.3），支援依 `task_id` 查詢。 |
| **4** | 前端：實作 Ontology 檢查邏輯（呼叫 §6.3 API），根據結果顯示對應的資料夾選擇。 |
| **5** | 前端：實作兩個資料夾選擇（Ontology + 知識庫）的 UI 與驗證。 |
| **6** | 後端：新增 `POST /api/v1/ontologies/import`（§6.2），並與 `OntologyStoreService` 整合。 |
| **7** | 前端：實作上傳流程（先 Ontology 後知識庫，或僅知識庫）。 |

### 7.2 方案 A（詳細版，備選）

| 階段 | 內容 |
|------|------|
| **1** | Modal：新增「選擇目錄」、支援 `webkitdirectory`；待上傳列表可顯示目錄結構（`webkitRelativePath`）。 |
| **2** | Modal：新增「類型」標記（知識庫 / Ontology）與「關聯 Ontology」選擇；必要時接 Ontology 列表 API。 |
| **3** | 前端：實作 Ontology JSON 格式與 §3.4.2 必填屬性檢查；標記為 Ontology 的 `.json` 上傳前強制校驗。 |
| **4** | 後端：新增 `POST /api/v1/ontologies/import`（§6.2），並與 `OntologyStoreService` 整合。 |
| **5** | 前端：上傳 Ontology 時改呼叫 Ontology 匯入 API；一般檔案仍用 `v2/upload`。 |
| **6** | （可選）`v2/upload` 支援 `ontology_id`，並在 pipeline 中使用；統一知識庫上架與一般上傳的差異僅在參數。 |

---

## 8. 參考

- [Agent 專業知識上架管理](./Agent專業知識知識上架管理.md)
- [專業知識上架代碼統一狀況檢討](./專業知識上架代碼統一狀況檢討.md)
- [上傳的功能架構說明 v4.0](../文件上傳向量圖譜/上傳的功能架構說明-v4.0.md)
- Ontology JSON 範例：`KA-Agent/Ontology/ka-agent-domain.json`、`ka-agent-major.json`
- 權限檢查：`api/routers/system_admin.py`、`api/routers/auth.py`（`require_system_admin`、`has_permission(Permission.ALL.value)`）

---

## 9. 附錄：權限檢查實作範例

### 9.1 前端檢查（TypeScript/React）

```typescript
// 檢查用戶是否為 systemAdmin 或授權用戶
const isAuthorizedForAgentOnboarding = (user: User | null): boolean => {
  if (!user) return false;
  
  // 方式 1：檢查 user_id
  if (user.user_id === "systemAdmin") return true;
  
  // 方式 2：檢查 permissions（從登入響應取得）
  if (user.permissions?.includes("all") || user.permissions?.includes(Permission.ALL.value)) {
    return true;
  }
  
  // 方式 3：檢查 roles（如果有 system_admin role）
  if (user.roles?.includes("system_admin")) return true;
  
  return false;
};
```

### 9.2 後端檢查（Python/FastAPI）

```python
# 使用現有的 require_system_admin 依賴
from api.routers.system_admin import require_system_admin

@router.post("/ontologies/import")
async def import_ontologies(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_system_admin),  # 僅 systemAdmin 可訪問
):
    # ...
```

---

**最後更新日期**: 2026-01-27 24:30 UTC+8  
**維護人**: Daniel Chung  
**版本**: v2.0（新增方案 B：簡化版）
