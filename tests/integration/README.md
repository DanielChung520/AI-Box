# AI-Box 整合測試

本目錄包含 AI-Box 系統的整合測試文件。

## 目錄結構

```
tests/
├── conftest.py                    # pytest 配置和共享 fixtures
├── integration/                   # 整合測試目錄
│   ├── test_helpers.py          # 測試輔助函數
│   ├── phase1/                   # 階段一：基礎架構測試
│   ├── phase2/                   # 階段二：Agent 核心測試
│   ├── phase3/                   # 階段三：工作流引擎測試
│   ├── phase4/                   # 階段四：數據處理測試
│   ├── phase5/                   # 階段五：LLM MoE 測試
│   └── e2e/                      # 端到端測試
├── run_integration_tests.sh      # 測試運行腳本
└── integration_test_report_template.md  # 測試報告模板
```

## 運行測試

### 前置條件

1. 確保所有服務已啟動：
   - FastAPI 服務（端口 8000）
   - ChromaDB 服務
   - ArangoDB 服務
   - Ollama 服務（端口 11434）
   - Redis 服務（如需要）

2. 安裝測試依賴：
   ```bash
   pip install pytest pytest-asyncio httpx
   ```

### 運行所有測試

```bash
./tests/run_integration_tests.sh
```

### 運行特定階段測試

```bash
# 階段一測試
pytest tests/integration/phase1/ -v -m integration

# 階段二測試
pytest tests/integration/phase2/ -v -m integration

# 階段三測試
pytest tests/integration/phase3/ -v -m integration

# 階段四測試
pytest tests/integration/phase4/ -v -m integration

# 階段五測試
pytest tests/integration/phase5/ -v -m integration

# 端到端測試
pytest tests/integration/e2e/ -v -m integration
```

### 運行特定測試文件

```bash
pytest tests/integration/phase1/test_fastapi_service.py -v
```

## 測試標記

- `@pytest.mark.integration`: 標記為整合測試
- `@pytest.mark.asyncio`: 標記為異步測試

## 測試報告

測試執行完成後，會生成：
- JUnit XML 報告：`tests/integration_test_results.xml`
- 使用模板填寫測試報告：`tests/integration_test_report_template.md`

## 注意事項

1. 某些測試可能需要實際的服務運行，如果服務不可用，測試會自動跳過
2. 測試執行時間可能較長，特別是涉及 LLM 推理的測試
3. 建議在測試環境中運行，避免影響生產環境
