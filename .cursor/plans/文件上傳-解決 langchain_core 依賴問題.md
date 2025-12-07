<!-- 7f8029d4-8f20-4d06-ae76-818cf9d11195 7d542e6d-9257-46d6-b59b-d4ebd482c09f -->
# 解決 langchain_core 依賴問題

## 問題分析

### 當前狀況

1. **錯誤信息**: `ModuleNotFoundError: No module named 'langchain_core'`
2. **影響位置**:

   - `genai/workflows/langchain/workflow.py` 第13行
   - `genai/workflows/langchain/checkpoint.py` 第16行
   - `agents/crewai/llm_adapter.py` 第14行

3. **影響範圍**:

   - 無法通過 `conftest.py` 運行完整測試套件
   - `services/api/__init__.py` 導入 `api.main` 時觸發連鎖導入失敗

4. **依賴配置**: `requirements.txt` 中已包含：

   - `langchain-core>=1.1.0,<2.0.0`
   - `langchain-community>=0.3.0,<1.0.0`
   - `langgraph>=1.0.4,<2.0.0`

### 根本原因

當前 Python 環境中未安裝 `requirements.txt` 中列出的 langchain 相關依賴包。

## 解決方案

### 方案 1: 安裝依賴（推薦）

直接安裝 `requirements.txt` 中的 langchain 相關依賴。

**優點**:

- 符合項目依賴配置
- 完整支持 LangChain 工作流功能
- 解決所有相關導入問題

**步驟**:

1. 安裝 langchain 相關依賴：
   ```bash
   pip install langchain-core>=1.1.0,<2.0.0
   pip install langchain-community>=0.3.0,<1.0.0
   pip install langgraph>=1.0.4,<2.0.0
   ```


或直接安裝整個 requirements.txt：

   ```bash
   pip install -r requirements.txt
   ```

2. 驗證安裝：
   ```bash
   python3 -c "from langchain_core.runnables import RunnableConfig; print('✅ langchain_core 安裝成功')"
   ```

3. 重新運行測試：
   ```bash
   pytest tests/integration/rag-file-upload/ -v
   ```


### 方案 2: 可選導入（備選）

如果 LangChain 功能不是必需的，可以將導入改為可選導入。

**優點**:

- 不強制安裝 langchain 依賴
- 允許在沒有 langchain 的環境中運行其他功能

**缺點**:

- LangChain 工作流功能將無法使用
- 需要修改多個文件的導入邏輯

**步驟**:

1. 修改 `genai/workflows/langchain/workflow.py`，將導入改為可選：
   ```python
   try:
       from langchain_core.runnables import RunnableConfig, RunnableLambda
       from langgraph.graph import END, StateGraph
       LANGCHAIN_AVAILABLE = True
   except ImportError:
       LANGCHAIN_AVAILABLE = False
       # 定義占位符類
       class RunnableConfig: pass
       class RunnableLambda: pass
       class END: pass
       class StateGraph: pass
   ```

2. 在類中使用前檢查可用性：
   ```python
   if not LANGCHAIN_AVAILABLE:
       raise ImportError("langchain_core 未安裝，請運行: pip install langchain-core langgraph")
   ```

3. 同樣修改 `genai/workflows/langchain/checkpoint.py` 和 `agents/crewai/llm_adapter.py`

## 推薦方案

**推薦使用方案 1（安裝依賴）**，因為：

1. `requirements.txt` 中已經明確列出了這些依賴
2. LangChain 工作流是項目的核心功能之一
3. 安裝依賴是最直接和標準的解決方案
4. 不會影響現有代碼結構

## 實施步驟

### 步驟 1: 安裝依賴

執行 `pip install` 命令安裝 langchain 相關依賴。

### 步驟 2: 驗證安裝

確認 langchain_core 和 langgraph 可以正常導入。

### 步驟 3: 測試修復

重新運行階段3測試，確認導入錯誤已解決。

### 步驟 4: 驗證完整測試框架

運行完整的測試套件，確認所有測試可以正常執行。

## 注意事項

1. **版本兼容性**: 確保安裝的版本符合 `requirements.txt` 中的版本範圍
2. **虛擬環境**: 如果使用虛擬環境，確保在正確的環境中安裝
3. **依賴衝突**: 檢查是否有其他依賴與 langchain 版本衝突
4. **測試環境**: 確保測試環境和運行環境都安裝了相同的依賴

### To-dos

- [ ] 安裝 langchain-core、langchain-community 和 langgraph 依賴包
- [ ] 驗證 langchain_core 和 langgraph 可以正常導入
- [ ] 重新運行階段3測試，確認導入錯誤已解決
- [ ] 運行完整的測試套件，確認所有測試可以正常執行
