# 庫管員Agent測試

**版本**：1.0.0
**創建日期**：2026-01-13
**創建人**：Daniel Chung
**最後修改日期**：2026-01-13

## 測試概述

本測試套件包含：

1. **單元測試**：測試各個模塊的功能
2. **整合測試**：20個工作應用場景，實際調用Data-Agent進行測試

## 測試結構

```
tests/mm_agent/
├── __init__.py
├── test_agent.py                    # Agent主類測試
├── test_semantic_analyzer.py        # 語義分析測試
├── test_context_manager.py          # 上下文管理測試
├── test_business_logic.py           # 業務邏輯測試
├── test_integration.py              # 整合測試（使用Mock）
├── test_integration_scenarios.py    # 整合測試場景（實際調用Data-Agent）
├── run_integration_tests.sh         # 整合測試執行腳本
└── README.md                        # 本文件
```

## 整合測試場景（20個）

### 基礎查詢場景（6個）

1. **場景1：簡單查詢料號信息**
   - 指令：`查詢料號 ABC-123 的信息`
   - 測試：基本料號查詢功能

2. **場景2：簡單查詢庫存**
   - 指令：`查詢料號 ABC-123 的庫存`
   - 測試：基本庫存查詢功能

3. **場景3：查詢庫存數量**
   - 指令：`ABC-123 還有多少庫存？`
   - 測試：自然語言查詢庫存數量

4. **場景4：查詢庫存位置**
   - 指令：`料號 ABC-123 存放在哪裡？`
   - 測試：查詢庫存位置信息

5. **場景5：查詢物料規格**
   - 指令：`查詢料號 ABC-123 的規格`
   - 測試：查詢物料規格信息

6. **場景6：查詢物料供應商**
   - 指令：`料號 ABC-123 的供應商是誰？`
   - 測試：查詢供應商信息

### 缺料分析場景（3個）

7. **場景7：缺料分析 - 庫存充足**
   - 指令：`檢查料號 ABC-123 是否需要補貨`
   - 測試：庫存充足時的缺料分析

8. **場景8：缺料分析 - 庫存偏低**
   - 指令：`ABC-123 缺料嗎？`
   - 測試：庫存偏低時的缺料分析

9. **場景9：缺料分析並獲取建議**
   - 指令：`分析料號 ABC-123 的缺料情況`
   - 測試：缺料分析並生成建議

### 採購單生成場景（2個）

10. **場景10：生成採購單**
    - 指令：`為料號 ABC-123 生成採購單，數量 100 件`
    - 測試：基本採購單生成功能

11. **場景11：缺料檢查後生成採購單**
    - 指令：`檢查料號 ABC-123 是否缺料，如果缺料就生成採購單 100 件`
    - 測試：條件式採購單生成

### 上下文和多輪對話場景（3個）

12. **場景12：上下文指代解析（多輪對話）**
    - 第一輪：`查詢料號 ABC-123 的庫存`
    - 第二輪：`剛才查的那個料號，幫我生成採購單，數量 50 件`
    - 測試：上下文管理和指代解析

13. **場景13：多輪對話完整流程**
    - 第一輪：`查詢料號 ABC-123 的庫存`
    - 第二輪：`它缺料嗎？`
    - 第三輪：`幫我生成採購單，數量 100 件`
    - 測試：完整的多輪對話流程

14. **場景14：查詢多個料號（連續查詢）**
    - 第一輪：`查詢料號 ABC-123 的信息`
    - 第二輪：`查詢料號 XYZ-456 的信息`
    - 測試：連續查詢不同料號

### 複雜場景（3個）

15. **場景15：複雜指令（包含多個動作）**
    - 指令：`查詢料號 ABC-123 的庫存，如果缺料就告訴我缺多少`
    - 測試：複雜指令的語義理解

16. **場景16：查詢不存在的料號**
    - 指令：`查詢料號 ABC-999 的信息`
    - 測試：錯誤處理（料號不存在）

17. **場景17：生成採購單但未指定數量**
    - 指令：`為料號 ABC-123 生成採購單`
    - 測試：錯誤處理（缺少必需參數）

### 邊界情況（2個）

18. **場景18：查詢零庫存**
    - 指令：`查詢料號 ABC-123 的庫存`
    - 測試：零庫存情況的處理

19. **場景19：不同格式的料號查詢**
    - 測試多種指令格式：
      - `查詢料號 ABC-123`
      - `查詢料號：ABC-123`
      - `query part ABC-123`
    - 測試：不同格式的指令解析

### 完整工作流程（1個）

20. **場景20：完整工作流程（查詢→分析→採購）**
    - 步驟1：`查詢料號 ABC-123 的信息`
    - 步驟2：`查詢它的庫存`
    - 步驟3：`分析缺料情況`
    - 步驟4：`生成採購單，數量 150 件`
    - 測試：完整的工作流程

## 運行測試

### 方法1：使用測試腳本（推薦）

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
./tests/mm_agent/run_integration_tests.sh
```

### 方法2：直接運行Python腳本

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
python3 tests/mm_agent/test_integration_scenarios.py
```

### 方法3：使用pytest

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
pytest tests/mm_agent/test_integration.py -v
```

## 測試前準備

### 1. 確保服務運行

- ✅ **Data-Agent服務**：運行在端口 8004
- ✅ **SeaweedFS Datalake**：運行正常
- ✅ **AI-Box Orchestrator**：運行在端口 8000（可選，如果使用真實調用）

### 2. 環境配置

確保`.env`文件包含：

```bash
# Data Agent Service 配置
DATA_AGENT_SERVICE_HOST=localhost
DATA_AGENT_SERVICE_PORT=8004

# Warehouse Manager Agent Service 配置
WAREHOUSE_MANAGER_AGENT_SERVICE_HOST=localhost
WAREHOUSE_MANAGER_AGENT_SERVICE_PORT=8003

# AI-Box 配置
AI_BOX_API_URL=http://localhost:8000
AI_BOX_API_KEY=your-api-key

# Datalake SeaweedFS 配置
DATALAKE_SEAWEEDFS_S3_ENDPOINT=http://localhost:8334
DATALAKE_SEAWEEDFS_S3_ACCESS_KEY=admin
DATALAKE_SEAWEEDFS_S3_SECRET_KEY=admin123
```

### 3. 測試數據準備

確保Datalake中有測試數據：

- `bucket-datalake-assets/parts/ABC-123.json` - 物料信息
- `bucket-datalake-assets/stock/ABC-123.json` - 庫存信息

## 測試結果

測試完成後，結果會保存在：

```
tests/mm_agent/integration_test_results.json
```

查看結果：

```bash
cat tests/mm_agent/integration_test_results.json | python3 -m json.tool
```

## 測試覆蓋範圍

### 功能覆蓋

- ✅ 料號查詢（多種格式）
- ✅ 庫存查詢（數量、位置）
- ✅ 缺料分析（充足、偏低、缺料）
- ✅ 採購單生成
- ✅ 上下文管理
- ✅ 指代解析
- ✅ 多輪對話

### 錯誤處理覆蓋

- ✅ 料號不存在
- ✅ 缺少必需參數
- ✅ 零庫存處理

### 邊界情況覆蓋

- ✅ 不同指令格式
- ✅ 複雜指令
- ✅ 多輪對話

## 注意事項

1. **測試依賴**：
   - 某些測試依賴於Data-Agent服務
   - 某些測試依賴於Datalake中的測試數據
   - 如果服務未運行或數據不存在，測試可能失敗

2. **測試順序**：
   - 多輪對話測試需要按順序執行
   - 上下文測試需要保持相同的session_id

3. **預期結果**：
   - 某些測試可能因為環境配置而失敗
   - 這是正常的，重點是測試錯誤處理是否正確

## 自定義測試

可以修改 `test_integration_scenarios.py` 添加更多測試場景：

```python
async def test_21_custom_test(self):
    """場景21：自定義測試"""
    return await self.run_test(
        "場景21：自定義測試",
        "你的測試指令",
        expected_success=True,
    )
```

然後在 `run_all_tests()` 方法中添加：

```python
self.test_21_custom_test,
```
