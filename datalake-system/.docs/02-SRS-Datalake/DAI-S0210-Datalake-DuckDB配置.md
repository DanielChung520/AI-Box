# DAI-S0210 Datalake DuckDB 配置規格書

**文件編號**: DAI-S0210  
**版本**: 1.0  
**日期**: 2026-02-27  
**依據代碼**: `datalake-system/dbt/`, `datalake-system/data/`

---

## 1. 產品目的 (Product Purpose)

### 1.1 核心聲明

Datalake DuckDB 配置負責管理 DuckDB 數據庫的配置、Schema 定義和數據模型。

### 1.2 解決問題

- 數據模型定義
- Schema 管理
- 數據轉換

### 1.3 服務對象

- Data-Agent
- 數據工程師

---

## 2. 產品概覽 (Product Overview)

### 2.1 目標用戶

| 用戶類型 | 使用場景 | 需求 |
|----------|----------|------|
| Data-Agent | 數據查詢 | Schema 訪問 |
| 工程師 | 模型維護 | 配置管理 |

### 2.2 技術棧

| 層級 | 技術 | 版本 | 用途 |
|------|------|------|------|
| DB | DuckDB | 1.4.4 | 數據庫引擎 |
| Model | dbt | - | 數據模型管理 |
| Storage | Parquet | - | 列式存儲 |

---

## 3. 功能需求 (Functional Requirements)

### 3.1 Schema 管理

| 功能 ID | 功能名稱 | 說明 |
|---------|----------|------|
| F-DL-021-001 | Mart 定義 | 寬表模型定義 |
| F-DL-021-002 | 字段映射 | 字段類型映射 |
| F-DL-021-003 | 視圖管理 | 數據庫視圖 |

### 3.2 數據模型

| 功能 ID | 功能名稱 | 說明 |
|---------|----------|------|
| F-DL-021-010 | mart_inventory_wide | 庫存寬表 |
| F-DL-021-011 | mart_work_order_wide | 工單寬表 |
| F-DL-021-012 | mart_shipping_wide | 出貨寬表 |

---

## 4. 性能要求 (Performance Requirements)

| 指標 | 目標值 | 說明 |
|------|--------|------|
| 查詢時間 | ≤ 5s | 單表查詢 |
| 數據加載 | ≤ 10s | 全量加載 |

---

## 5. 錯誤碼詳細定義

| 錯誤碼 | 名稱 | 描述 |
|--------|------|------|
| E210-001 | SCHEMA_NOT_FOUND | Schema 不存在 |
| E210-002 | TABLE_NOT_FOUND | 表不存在 |

---

*文件結束*
