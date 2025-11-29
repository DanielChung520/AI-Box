# LLM 多提供商整合測試

## 測試概述

本目錄包含多LLM整合系統的單元測試和集成測試。

## 測試結構

```
tests/
├── conftest.py                    # pytest 配置和共享 fixtures
├── llm/
│   ├── __init__.py
│   ├── test_clients_factory.py   # LLM 客戶端工廠測試
│   ├── test_load_balancer.py    # 負載均衡器測試
│   ├── test_failover.py          # 故障轉移機制測試
│   ├── test_moe_manager.py       # MoE 管理器測試
│   └── test_integration.py       # 集成測試
```

## 運行測試

### 運行所有測試
```bash
pytest tests/llm/
```

### 運行單元測試
```bash
pytest tests/llm/ -m "not integration"
```

### 運行集成測試
```bash
pytest tests/llm/test_integration.py
```

### 運行特定測試文件
```bash
pytest tests/llm/test_load_balancer.py
```

### 運行特定測試類
```bash
pytest tests/llm/test_load_balancer.py::TestMultiLLMLoadBalancer
```

### 運行特定測試方法
```bash
pytest tests/llm/test_load_balancer.py::TestMultiLLMLoadBalancer::test_init
```

## 測試覆蓋範圍

### 單元測試
- ✅ LLM 客戶端工廠（緩存、創建、清除）
- ✅ 多LLM負載均衡器（輪詢、加權、最少連接）
- ✅ 故障轉移機制（健康檢查、重試）
- ✅ MoE 管理器（生成、對話、嵌入）

### 集成測試
- ✅ 端到端生成流程
- ✅ 多LLM切換
- ✅ 故障轉移場景
- ✅ 負載均衡器集成
- ✅ 路由與任務分類

## 注意事項

1. 測試使用 mock 對象，不需要真實的 API 密鑰
2. 環境變數會在測試中自動設置（見 conftest.py）
3. 異步測試使用 pytest-asyncio
4. 所有測試都標記了適當的 pytest markers

## 依賴

測試需要以下依賴：
- pytest
- pytest-asyncio
- unittest.mock (標準庫)

安裝測試依賴：
```bash
pip install pytest pytest-asyncio
```
