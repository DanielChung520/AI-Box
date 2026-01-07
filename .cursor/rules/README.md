# Cursor 規則文件說明

**創建日期**: 2025-12-30
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-30

---

## 📋 規則文件整合說明

### 整合狀態

✅ **已完成整合**（2025-12-30）

兩個規則文件已整合為一個統一的規則文件，避免規則衝突並確保規則有效執行。

### 規則文件位置

#### 主規則文件（生效）

- **文件**: `.cursorrules`（項目根目錄）
- **狀態**: ✅ **生效中**
- **說明**: 這是 Cursor 的主要規則文件，包含所有開發規範
- **Cursor 自動讀取**: Cursor 會自動讀取項目根目錄的 `.cursorrules` 文件

#### 引用文件（生效）

- **文件**: `.cursor/rules/main-rules.mdc`
- **狀態**: ✅ **生效中**（`alwaysApply: true`）
- **說明**: 此文件指向 `.cursorrules`，確保 Cursor 能夠正確識別規則文件

#### 備份文件（已停用）

- **文件**: `.cursor/rules/develop-rule.mdc`
- **狀態**: ⚠️ **已停用**（`alwaysApply: false`）
- **說明**: 此文件已整合到 `.cursorrules`，保留僅作為備份參考

---

## 📚 整合後的規則結構

`.cursorrules` 文件包含以下章節：

1. **🔴 最高優先級規則**
   - 文件頭註釋更新流程
   - 代碼格式檢查流程
   - 禁止行為清單

2. **📝 文件頭註釋規範**
   - 基本要求
   - 日期確認規範（強制執行）

3. **⚙️ 配置規範**
   - 環境配置規範

4. **📋 pyproject.toml 配置規範**
   - Ruff 配置要求
   - Mypy 配置要求
   - 代碼生成範例

5. **🔷 類型注解規範**
   - 必須使用類型注解的情況
   - 類型匹配要求

6. **🛡️ 防御性編程規範**
   - None 檢查要求
   - API 調用檢查

7. **📐 代碼結構規範**
   - Import 語句規範
   - 變量使用規範
   - 文件格式規範

8. **✅ 代碼審查檢查清單**
   - 提交前必須檢查項目
   - 常見錯誤模式

9. **🔧 工具使用規範**
   - 開發時使用
   - CI/CD 檢查

10. **📤 Git 提交前檢查規範**
    - 提交前必須執行的步驟
    - Pre-commit Hooks 檢查項目詳解
    - 提交失敗處理流程

11. **📊 項目控制表更新規範**
    - 更新原則
    - 正確的更新方式
    - 錯誤的更新方式（禁止）

12. **🗄️ ArangoDB 數據存儲規範**
    - Collections 完整列表
    - 數據存儲規範
    - 服務層規範

---

## ⚠️ 重要說明

### 規則執行優先級

1. **`.cursorrules`**（項目根目錄）- **最高優先級**
   - 這是 Cursor 的主要規則文件
   - Cursor 會自動讀取項目根目錄的 `.cursorrules` 文件
   - 所有規則都在此文件中統一管理

2. **`.cursor/rules/main-rules.mdc`** - **引用文件**
   - 設置為 `alwaysApply: true`
   - 指向 `.cursorrules`，確保 Cursor 能夠正確識別規則
   - 包含規則文件結構說明

3. **`.cursor/rules/develop-rule.mdc`** - **已停用**
   - 設置為 `alwaysApply: false`
   - 不會被 Cursor 讀取
   - 僅作為備份參考

### 日期確認規範（強制執行）

**重要**：所有日期相關操作必須使用瀏覽器工具：

1. ✅ **必須**使用 `mcp_cursor-browser-extension_browser_navigate` 訪問 `https://tw.piliapp.com/time/`
2. ✅ **必須**使用 `browser_evaluate` 獲取頁面上的實際日期時間
3. ❌ **禁止**使用 `web_search` 獲取日期
4. ❌ **禁止**使用記憶中的日期

### 規則更新

如果需要更新規則：

1. **只更新 `.cursorrules`**：所有規則修改都在此文件中進行
2. **不要修改 `.cursor/rules/develop-rule.mdc`**：此文件已停用，僅作為備份
3. **更新後確認**：確保規則邏輯清晰，沒有衝突

---

## 🔍 規則文件對比

### 整合前

- `.cursorrules`：簡潔版本，主要強調日期確認和基本規範
- `.cursor/rules/develop-rule.mdc`：詳細版本，包含所有開發規範

### 整合後

- `.cursorrules`：**統一版本**，包含所有規則（1544 行）
- `.cursor/rules/main-rules.mdc`：**引用文件**，指向 `.cursorrules`（`alwaysApply: true`）
- `.cursor/rules/develop-rule.mdc`：**已停用**，僅作為備份（`alwaysApply: false`）

---

## ✅ 整合優勢

1. **避免規則衝突**：所有規則統一在一個文件中管理
2. **規則有效執行**：Cursor 只讀取 `.cursorrules`，確保規則一致
3. **易於維護**：只需維護一個規則文件
4. **清晰明確**：規則結構清晰，易於查找和理解

---

## 📝 使用建議

1. **開發時**：遵循 `.cursorrules` 中的所有規範
2. **更新規則**：只修改 `.cursorrules` 文件
3. **參考備份**：如需查看歷史規則，可參考 `.cursor/rules/develop-rule.mdc`

---

**最後更新日期**: 2025-12-30
**維護人**: Daniel Chung
