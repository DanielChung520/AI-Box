# Data Agent 測試劇本

**版本**：1.0
**創建日期**：2026-01-13
**創建人**：Daniel Chung

## 概述

本測試劇本包含 **28 個測試場景**，全面測試 Data Agent 的各項功能。

## 測試場景列表

### Datalake 查詢測試（6 個）

1. **Datalake 精確查詢** - 查詢單個文件
2. **Datalake 模糊查詢** - 按前綴查詢多個文件
3. **Datalake 查詢 - 帶過濾條件** - 使用過濾器查詢
4. **Datalake 查詢 - 缺少 bucket 參數** - 錯誤處理
5. **Datalake 查詢 - 缺少 key 參數** - 錯誤處理
6. **Datalake 查詢 - 空 bucket** - 邊界情況
7. **Datalake 查詢 - 大量結果** - 性能測試

### 數據字典管理測試（5 個）

8. **創建數據字典** - 正常創建
9. **獲取數據字典** - 正常獲取
10. **獲取不存在的數據字典** - 錯誤處理
11. **創建數據字典 - 缺少數據** - 錯誤處理
12. **創建數據字典 - 重複 ID** - 錯誤處理

### Schema 管理測試（5 個）

13. **創建 JSON Schema** - 正常創建
14. **獲取 Schema** - 正常獲取
15. **獲取不存在的 Schema** - 錯誤處理
16. **創建無效的 Schema** - 錯誤處理
17. **創建 Schema - 帶引用** - 複雜結構

### 數據驗證測試（4 個）

18. **驗證數據 - 有效數據** - 正常驗證
19. **驗證數據 - 無效數據** - 錯誤檢測
20. **驗證數據 - 缺少 Schema ID** - 錯誤處理
21. **驗證數據 - 空列表** - 邊界情況

### Text-to-SQL 測試（3 個）

22. **Text-to-SQL - 簡單查詢** - 基本轉換
23. **Text-to-SQL - 複雜查詢** - 複雜轉換
24. **Text-to-SQL - 缺少自然語言** - 錯誤處理

### 查詢驗證測試（3 個）

25. **驗證查詢 - 有效的 SQL** - 正常驗證
26. **驗證查詢 - 無效的 SQL** - 語法錯誤檢測
27. **驗證查詢 - 危險的 SQL** - 安全檢查

### 其他測試（2 個）

28. **未知操作** - 錯誤處理
29. **綜合測試** - 多個操作組合

## 執行測試

### 方法 1：使用測試腳本（推薦）

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
./tests/data_agent/run_tests.sh
```

### 方法 2：直接運行 Python 腳本

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
python3 tests/data_agent/test_data_agent_scenarios.py
```

## 測試結果

測試完成後，結果會保存在：

```
tests/data_agent/test_results.json
```

查看結果：

```bash
cat tests/data_agent/test_results.json | python3 -m json.tool
```

## 測試覆蓋範圍

### 功能覆蓋

- ✅ Datalake 查詢（精確/模糊）
- ✅ 數據字典管理（創建/獲取）
- ✅ Schema 管理（創建/獲取）
- ✅ 數據驗證
- ✅ Text-to-SQL 轉換
- ✅ 查詢驗證

### 錯誤處理覆蓋

- ✅ 缺少必需參數
- ✅ 無效數據格式
- ✅ 不存在的資源
- ✅ 重複創建
- ✅ 危險操作檢測

### 邊界情況覆蓋

- ✅ 空數據
- ✅ 大量數據
- ✅ 複雜結構

## 注意事項

1. **測試前準備**：
   - 確保 Data Agent 服務已啟動
   - 確保 SeaweedFS Datalake 服務運行正常
   - 確保環境配置正確

2. **測試依賴**：
   - 某些測試依賴於其他測試的結果（如獲取需要先創建）
   - 測試會按順序執行，確保依賴關係

3. **預期結果**：
   - 某些測試可能因為環境配置而失敗（如文件不存在）
   - 這是正常的，重點是測試錯誤處理是否正確

## 自定義測試

可以修改 `test_data_agent_scenarios.py` 添加更多測試場景：

```python
async def test_29_custom_test(self):
    """測試 29: 自定義測試"""
    return await self.run_test(
        "自定義測試名稱",
        {
            "action": "your_action",
            # ... 其他參數
        },
        expected_success=True,
    )
```

然後在 `run_all_tests()` 方法中添加：

```python
self.test_29_custom_test,
```
