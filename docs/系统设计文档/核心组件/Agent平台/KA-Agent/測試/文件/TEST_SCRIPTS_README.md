# 測試腳本使用說明

**創建日期**: 2026-01-28

---

## 測試腳本列表

### 1. `test_llm_response.py` - LLM 響應生成流程基礎測試

**功能**: 測試 LLM 響應生成流程的各個步驟

**測試場景**:
- 正常流程（KA-Agent 執行成功）
- 空 Result 場景
- 異常 Result 格式場景

**使用方法**:
```bash
python3 test_llm_response.py
```

**適用場景**: 驗證 LLM 響應生成流程的代碼邏輯是否正確

---

### 2. `test_llm_response_integration.py` - LLM 響應生成流程集成測試

**功能**: 集成測試完整的 LLM 響應生成流程

**測試步驟**:
1. KA-Agent 執行結果模擬
2. Agent 結果格式化
3. Messages for LLM 構建
4. 服務初始化
5. Task Classification
6. moe.chat 調用
7. Content 提取
8. Routing 提取
9. RoutingInfo 創建
10. ObservabilityInfo 創建
11. ChatResponse 創建
12. ChatResponse 序列化

**使用方法**:
```bash
python3 test_llm_response_integration.py
```

**適用場景**: 驗證完整的 LLM 響應生成流程

---

### 3. `test_llm_response_simple.py` - LLM 響應生成流程簡化測試

**功能**: 快速測試關鍵步驟

**使用方法**:
```bash
python3 test_llm_response_simple.py
```

**適用場景**: 快速驗證 LLM 響應生成流程是否正常

---

### 4. `test_chat_api_endpoint.py` - Chat API 端點測試 ⭐

**功能**: 直接測試 Chat API 端點，模擬完整 HTTP 請求流程

**測試內容**:
- 完整的 HTTP 請求流程
- Agent 執行和結果處理
- LLM 響應生成
- 錯誤處理
- 空查詢處理
- 無效請求處理

**使用方法**:
```bash
# 確保 FastAPI 服務正在運行
python -m uvicorn api.main:app --reload

# 在另一個終端運行測試
python3 test_chat_api_endpoint.py
```

**適用場景**: 
- ✅ **驗證實際 API 調用是否正常**
- ✅ **定位 HTTP 層面的問題**
- ✅ **測試錯誤處理邏輯**

**輸出示例**:
```
測試用例 1: 知識庫文件數量查詢
[1] 請求數據: ...
[2] 發送 HTTP 請求...
[3] 解析響應...
[4] 驗證關鍵詞...
[5] 測試完成
```

---

### 5. `test_chat_internal_flow.py` - Chat 內部流程測試 ⭐

**功能**: 直接調用 chat.py 中的函數，測試內部流程

**測試內容**:
- `_process_chat_request` 函數邏輯
- Agent 執行流程
- LLM 響應生成
- 錯誤處理

**使用方法**:
```bash
python3 test_chat_internal_flow.py
```

**適用場景**: 
- ✅ **驗證代碼邏輯是否正確**
- ✅ **定位內部流程問題**
- ✅ **測試 Agent 執行流程**

**輸出示例**:
```
[1] 初始化服務...
[2] Task Classification...
[3] Agent 發現和執行...
[4] 構建 messages_for_llm...
[5] 調用 moe.chat...
[6] 提取 content...
[7] 提取 routing...
[8] 創建 ChatResponse...
[9] 序列化 ChatResponse...
```

---

## 推薦測試順序

### 場景 1: 驗證 LLM 響應生成流程

```bash
# 1. 快速測試
python3 test_llm_response_simple.py

# 2. 完整測試
python3 test_llm_response_integration.py
```

### 場景 2: 定位實際 API 調用問題 ⭐

```bash
# 1. 確保 FastAPI 服務運行
python -m uvicorn api.main:app --reload

# 2. 測試 API 端點
python3 test_chat_api_endpoint.py
```

### 場景 3: 定位內部流程問題 ⭐

```bash
# 直接測試內部流程
python3 test_chat_internal_flow.py
```

### 場景 4: 完整診斷

```bash
# 1. 測試內部流程
python3 test_chat_internal_flow.py

# 2. 測試 API 端點（需要 FastAPI 運行）
python3 test_chat_api_endpoint.py

# 3. 對比結果，找出差異
```

---

## 問題定位指南

### 問題: LLM 響應生成失敗

**步驟 1**: 運行 `test_llm_response_simple.py`
- ✅ 如果通過 → 代碼邏輯正常，問題在 API 層
- ❌ 如果失敗 → 檢查 LLM 響應生成流程代碼

**步驟 2**: 運行 `test_chat_internal_flow.py`
- ✅ 如果通過 → 內部流程正常，問題在 HTTP 層
- ❌ 如果失敗 → 檢查內部流程代碼

**步驟 3**: 運行 `test_chat_api_endpoint.py`
- ✅ 如果通過 → API 端點正常
- ❌ 如果失敗 → 檢查 API 路由和錯誤處理

### 問題: Agent 執行失敗

**步驟 1**: 運行 `test_chat_internal_flow.py`
- 查看 `[3] Agent 發現和執行...` 部分的輸出
- 檢查 Agent 是否被正確發現
- 檢查 Agent 執行結果

### 問題: 錯誤處理不正確

**步驟 1**: 運行 `test_chat_api_endpoint.py`
- 查看錯誤測試用例的輸出
- 檢查錯誤響應格式是否正確

---

## 注意事項

1. **FastAPI 服務**: `test_chat_api_endpoint.py` 需要 FastAPI 服務運行
2. **環境變數**: 所有測試腳本都需要正確的 `.env` 配置
3. **依賴**: 確保所有依賴都已安裝
4. **日誌**: 測試腳本會輸出詳細的日誌，用於問題定位

---

## 測試報告

測試完成後，會生成以下報告：
- `LLM_RESPONSE_TEST_REPORT.md` - 詳細測試報告
- `LLM_RESPONSE_TEST_SUMMARY.md` - 測試總結

---

**最後更新**: 2026-01-28
