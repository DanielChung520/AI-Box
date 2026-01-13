# 庫管員Agent整合測試快速開始

**版本**：1.0.0
**創建日期**：2026-01-13

## 快速執行

### 1. 確保服務運行

```bash
# 啟動Data-Agent服務（如果未運行）
cd /Users/daniel/GitHub/AI-Box/datalake-system
./scripts/data_agent/start.sh

# 檢查服務狀態
./scripts/data_agent/status.sh
```

### 2. 運行整合測試

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
./tests/warehouse_manager_agent/run_integration_tests.sh
```

或直接運行：

```bash
python3 tests/warehouse_manager_agent/test_integration_scenarios.py
```

### 3. 查看測試結果

```bash
# 查看JSON結果
cat tests/warehouse_manager_agent/integration_test_results.json | python3 -m json.tool

# 生成Markdown報告
python3 tests/warehouse_manager_agent/generate_test_report.py
cat tests/warehouse_manager_agent/INTEGRATION_TEST_REPORT.md
```

## 測試場景列表

共20個工作應用場景：

1. 簡單查詢料號信息
2. 簡單查詢庫存
3. 查詢庫存數量
4. 查詢庫存位置
5. 查詢物料規格
6. 查詢物料供應商
7. 缺料分析 - 庫存充足
8. 缺料分析 - 庫存偏低
9. 缺料分析並獲取建議
10. 生成採購單
11. 缺料檢查後生成採購單
12. 上下文指代解析（多輪對話）
13. 多輪對話完整流程
14. 查詢多個料號（連續查詢）
15. 複雜指令（包含多個動作）
16. 查詢不存在的料號
17. 生成採購單但未指定數量
18. 查詢零庫存
19. 不同格式的料號查詢
20. 完整工作流程（查詢→分析→採購）

## 詳細文檔

- [README.md](./README.md) - 完整測試文檔
- [INTEGRATION_TEST_SUMMARY.md](./INTEGRATION_TEST_SUMMARY.md) - 測試總結
