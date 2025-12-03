# Icon 圖標庫使用指南

## 更新日期：2025-01-27

## 概述

Agent 註冊功能支持使用 [react-icons](https://react-icons.github.io/react-icons/) 圖標庫中的圖標。系統預設了約 53 個精選圖標，同時也支持用戶從 react-icons 官網獲取任意圖標並通過輸入名稱使用。

---

## 功能特點

### 1. 預設圖標庫（約 53 個）

系統預設了 5 個分類的圖標：
- **常用**：13 個（機器人、代碼、閃電、星星等）
- **業務**：12 個（文件、數據庫、雲端、建築等）
- **技術**：10 個（Python、JavaScript、服務器等）
- **安全**：7 個（盾牌、鎖、密鑰等）
- **工具**：11 個（搜索、設置、工具等）

### 2. 自定義圖標輸入

支持從 [react-icons 官網](https://react-icons.github.io/react-icons/) 獲取任意圖標並輸入名稱使用。

---

## 使用方法

### 方法一：從預設圖標庫選擇

1. 打開 Agent 註冊頁面
2. 在「基本資訊」標籤頁找到「圖標」欄位
3. 點擊「選擇圖標」按鈕
4. 在彈出的圖標選擇器中：
   - 使用分類標籤切換不同分類
   - 使用搜索框搜索圖標
   - 點擊圖標即可選擇

### 方法二：從 react-icons 官網獲取自定義圖標

1. 訪問 [react-icons 官網](https://react-icons.github.io/react-icons/)
2. 瀏覽或搜索您需要的圖標
3. 點擊圖標查看其名稱（例如：`FaBeer`、`MdFavorite`、`HiOutlineSparkles`）
4. 在 Agent 註冊頁面的圖標選擇器中：
   - 點擊「自定義圖標」標籤
   - 在輸入框中輸入圖標名稱（例如：`FaBeer`）
   - 系統會自動預覽圖標
   - 點擊「使用」按鈕確認選擇

---

## 支持的圖標庫

系統支持以下 react-icons 圖標庫（根據圖標名稱前綴自動識別）：

| 前綴 | 圖標庫 | 示例 |
|------|--------|------|
| `Fa` | FontAwesome 5 | `FaRobot`, `FaBeer`, `FaCoffee` |
| `Fa6` | FontAwesome 6 | `Fa6Robot`, `Fa6Beer` |
| `Md` | Material Design | `MdFavorite`, `MdHome`, `MdSettings` |
| `Hi` | Heroicons 1 | `HiLightBulb`, `HiSparkles` |
| `HiOutline` | Heroicons 2 (Outline) | `HiOutlineSparkles` |
| `HiSolid` | Heroicons 2 (Solid) | `HiSolidSparkles` |
| `Si` | Simple Icons | `SiPython`, `SiJavascript` |
| `Lu` | Lucide | `LuHeart`, `LuStar` |
| `Tb` | Tabler Icons | `TbHeart`, `TbStar` |
| `Ri` | Remix Icon | `RiHeartLine`, `RiStarLine` |
| `Io` | Ionicons 5 | `IoHeart`, `IoStar` |

---

## 圖標命名規則

### FontAwesome 5/6
- 格式：`Fa[名稱]` 或 `Fa6[名稱]`
- 示例：`FaBeer`, `FaCoffee`, `FaRobot`
- 首字母大寫，使用駝峰命名

### Material Design
- 格式：`Md[名稱]`
- 示例：`MdFavorite`, `MdHome`, `MdSettings`
- 首字母大寫，使用駝峰命名

### Heroicons 2
- Outline 風格：`HiOutline[名稱]`
- Solid 風格：`HiSolid[名稱]`
- 示例：`HiOutlineSparkles`, `HiSolidSparkles`
- 注意：Heroicons 1 使用 `Hi` 前綴

### Simple Icons
- 格式：`Si[名稱]`
- 示例：`SiPython`, `SiJavascript`, `SiTypescript`
- 通常為技術/品牌圖標

---

## 獲取圖標名稱的步驟

1. **訪問官網**：打開 [https://react-icons.github.io/react-icons/](https://react-icons.github.io/react-icons/)

2. **選擇圖標庫**：在左側選擇圖標庫（如 Font Awesome 5、Material Design 等）

3. **瀏覽或搜索**：
   - 使用搜索框搜索關鍵詞
   - 或瀏覽圖標列表

4. **查看圖標名稱**：點擊圖標，查看顯示的圖標名稱
   - 例如：`FaBeer`、`MdFavorite`、`HiOutlineSparkles`

5. **複製名稱**：複製完整的圖標名稱（包括前綴）

6. **輸入使用**：在 Agent 註冊頁面的「自定義圖標」輸入框中輸入圖標名稱

---

## 示例

### 示例 1：使用 FontAwesome 圖標

1. 訪問 react-icons 官網
2. 選擇 "Font Awesome 5" 庫
3. 搜索 "beer"
4. 找到 `FaBeer` 圖標
5. 在自定義圖標輸入框輸入：`FaBeer`
6. 點擊「使用」

### 示例 2：使用 Material Design 圖標

1. 訪問 react-icons 官網
2. 選擇 "Material Design icons" 庫
3. 搜索 "favorite"
4. 找到 `MdFavorite` 圖標
5. 在自定義圖標輸入框輸入：`MdFavorite`
6. 點擊「使用」

### 示例 3：使用 Heroicons 2 圖標

1. 訪問 react-icons 官網
2. 選擇 "Heroicons 2" 庫
3. 搜索 "sparkles"
4. 找到 `HiOutlineSparkles` 或 `HiSolidSparkles`
5. 在自定義圖標輸入框輸入：`HiOutlineSparkles`
6. 點擊「使用」

---

## 注意事項

1. **圖標名稱大小寫敏感**：必須使用正確的大小寫（通常首字母大寫，使用駝峰命名）

2. **前綴必須正確**：圖標名稱必須以正確的前綴開頭（如 `Fa`、`Md`、`Hi` 等）

3. **動態加載**：系統會根據圖標名稱前綴自動從對應的圖標庫中動態加載圖標

4. **預覽功能**：輸入圖標名稱後，系統會自動預覽圖標，確認無誤後再點擊「使用」

5. **錯誤處理**：如果圖標名稱錯誤或圖標不存在，系統會顯示默認圖標（機器人圖標）

---

## 技術實現

### IconRenderer 組件

`IconRenderer` 組件支持動態加載圖標：
- 首先從預定義映射表中查找
- 如果找不到，根據圖標名稱前綴動態從對應的 react-icons 庫中加載
- 支持多個圖標庫（FontAwesome、Material Design、Heroicons、Simple Icons、Lucide、Tabler、Remix、Ionicons 等）

### IconPicker 組件

`IconPicker` 組件提供：
- 預設圖標庫瀏覽和搜索
- 自定義圖標名稱輸入功能
- 實時預覽功能

---

## 相關鏈接

- [react-icons 官網](https://react-icons.github.io/react-icons/)
- [react-icons GitHub](https://github.com/react-icons/react-icons)
- [FontAwesome 圖標庫](https://fontawesome.com/icons)
- [Material Design Icons](https://fonts.google.com/icons)
- [Heroicons](https://heroicons.com/)

---

## 總結

✅ **預設約 53 個圖標**供快速選擇
✅ **支持從 react-icons 官網獲取任意圖標**
✅ **動態加載**，無需預先配置
✅ **實時預覽**，確保圖標正確
✅ **支持多個圖標庫**（10+ 個庫）

**最後更新**：2025-01-27
