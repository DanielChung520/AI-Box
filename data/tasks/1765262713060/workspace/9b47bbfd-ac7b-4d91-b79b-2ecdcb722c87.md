# Cursor DOCX Viewer 故障排除指南

## 問題描述
Cursor 的 DOCX Viewer 延伸工具中，Edit 區域無法顯示。

## 可能原因與解決方案

### 1. 檢查延伸工具是否已安裝

**步驟：**
1. 在 Cursor 中按 `Cmd + Shift + X`（macOS）或 `Ctrl + Shift + X`（Windows/Linux）打開延伸工具面板
2. 搜尋 "docx" 或 "word"
3. 確認是否有安裝 DOCX Viewer 相關延伸工具

**常見的 DOCX Viewer 延伸工具：**
- `cweijan.vscode-office`（Office Viewer）
- `davidanson.vscode-markdownlint`（可能影響）
- 其他 Office 相關延伸工具

### 2. 檢查延伸工具衝突 ⚠️ **最常見原因**

**Office Viewer 與 DOCX Viewer 衝突：**
如果您同時安裝了 `Office Viewer`（通常是 `cweijan.vscode-office`）和 `DOCX Viewer`，這兩個延伸工具會**互相衝突**，導致 Edit 區域無法顯示。

**解決步驟：**

1. **檢查已安裝的延伸工具：**
   - 按 `Cmd + Shift + X` 打開延伸工具面板
   - 搜尋 "office" 和 "docx"
   - 確認是否同時安裝了兩個延伸工具

2. **停用其中一個延伸工具（建議）：**
   - **推薦保留：** `Office Viewer`（`cweijan.vscode-office`）- 功能較完整
   - **建議停用：** `DOCX Viewer` - 功能較單一
   - 在延伸工具面板中，找到 `DOCX Viewer`
   - 點擊「停用」（Disable）按鈕

3. **重新啟動 Cursor：**
   - 完全關閉 Cursor（`Cmd + Q`）
   - 重新開啟 Cursor
   - 打開 DOCX 文件測試 Edit 區域是否正常顯示

4. **如果問題仍然存在：**
   - 嘗試停用 `Office Viewer`，只保留 `DOCX Viewer`
   - 或完全卸載其中一個延伸工具

**其他可能衝突的延伸工具：**
- Markdown 相關延伸工具
- 其他文件檢視器延伸工具
- 格式化延伸工具

### 3. 重置 Cursor 設定

**方法一：清除快取**
```bash
# macOS
rm -rf ~/Library/Application\ Support/Cursor/Cache
rm -rf ~/Library/Application\ Support/Cursor/CachedData

# 然後重新啟動 Cursor
```

**方法二：重置工作區設定**
1. 關閉 Cursor
2. 刪除或重命名工作區設定檔
3. 重新啟動 Cursor

### 4. 檢查 Cursor 版本

**步驟：**
1. 打開 Cursor
2. 點擊 `Cursor` > `About Cursor`（macOS）或 `Help` > `About`（Windows/Linux）
3. 確認版本是否為最新
4. 如有更新，請更新到最新版本

**更新 Cursor：**
- macOS: `Cursor` > `Check for Updates`
- Windows/Linux: `Help` > `Check for Updates`

### 5. 檢查文件格式

**確認 DOCX 文件是否損壞：**
```bash
# 檢查文件是否可以正常打開
file "/Users/Daniel/Documents/Notion/pages/傑羅德/傑羅德商學院AI智慧平台核心v3/宏康規格參考-AI智能商業培訓媒合平台計劃書-v3.docx"
```

**如果文件損壞：**
- 嘗試用 Microsoft Word 或 LibreOffice 打開並重新儲存
- 或重新生成 DOCX 文件

### 6. 重新安裝 DOCX Viewer 延伸工具

**步驟：**
1. 打開延伸工具面板：`Cmd + Shift + X`
2. 找到 DOCX Viewer 延伸工具
3. 點擊「卸載」
4. 重新啟動 Cursor
5. 重新安裝延伸工具

### 7. 檢查系統資源

**檢查 CPU 和記憶體使用率：**
```bash
# macOS
top -l 1 | grep -i cursor

# 或使用活動監視器
```

**如果資源使用率過高：**
- 關閉其他不必要的應用程式
- 重新啟動 Cursor
- 檢查是否有其他 Cursor 進程在運行

### 8. 使用替代方案

**如果以上方法都無法解決：**

**方案一：使用預覽模式**
- 在 Cursor 中右鍵點擊 DOCX 文件
- 選擇「Open With」>「Preview」（macOS）
- 或使用系統預設的 DOCX 檢視器

**方案二：轉換為 Markdown 編輯**
- 使用 MCP 工具將 DOCX 轉換為 Markdown
- 編輯 Markdown 文件
- 需要時再轉換回 DOCX

**方案三：使用外部編輯器**
- 使用 Microsoft Word、LibreOffice 或其他 DOCX 編輯器
- 在 Cursor 中僅作為檢視器使用

### 9. 檢查 Cursor 設定檔

**查看設定檔位置：**
- macOS: `~/Library/Application Support/Cursor/User/settings.json`
- Windows: `%APPDATA%\Cursor\User\settings.json`
- Linux: `~/.config/Cursor/User/settings.json`

**檢查是否有相關設定：**
```json
{
  "workbench.editor.enablePreview": false,
  "workbench.editor.enablePreviewFromQuickOpen": false
}
```

### 10. 聯絡 Cursor 支援

**如果以上方法都無法解決，請聯絡 Cursor 支援：**

**提供資訊：**
- Cursor 版本號
- 作業系統版本（macOS 24.6.0）
- 問題描述和截圖
- 已嘗試的解決方法
- 錯誤訊息（如有）

**聯絡方式：**
- 電子郵件：support@cursor.com
- 應用程式內：`Help` > `Contact Support`

## 快速檢查清單

- [ ] ⚠️ **優先檢查：** 確認是否同時安裝 Office Viewer 和 DOCX Viewer（會衝突）
- [ ] 停用其中一個 DOCX 相關延伸工具
- [ ] 重新啟動 Cursor
- [ ] 確認 DOCX Viewer 延伸工具已安裝
- [ ] 檢查延伸工具是否啟用
- [ ] 確認 Cursor 為最新版本
- [ ] 檢查文件是否損壞
- [ ] 清除 Cursor 快取
- [ ] 檢查系統資源使用率
- [ ] 嘗試重新安裝延伸工具
- [ ] 檢查延伸工具衝突

## 相關資源

- [Cursor 疑難排解指南](https://docs.cursor.com/zh-Hant/troubleshooting/troubleshooting-guide)
- [Cursor 更新日誌](https://cursor.com/zh-Hant/changelog)
- [Cursor 社群論壇](https://forum.cursor.com/)

---

**最後更新：** 2025-01-27

