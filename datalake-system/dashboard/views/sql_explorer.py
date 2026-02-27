# -*- coding: utf-8 -*-
"""
代碼功能說明: SQL Explorer - JP TiTop 資料庫查詢界面
創建日期: 2026-02-18
創建人: AI Assistant
最後修改日期: 2026-02-18

專注於 JP TiTop ERP 資料（/jp/execute 端點對應的資料）
S3 路徑: s3://tiptop-raw/raw/v1/tiptop_jp/{TABLE}/year=*/month=*/data.parquet
"""

import streamlit as st
import duckdb
import pandas as pd
from typing import Optional, Dict, List, Any

# 配置路徑（來自 /jp/execute bindings.json）
JP_DUCKDB_PATH = "/home/daniel/ai-box/datalake-system/data/warehouse/tiptop_jp.duckdb"
S3_BUCKET = "tiptop-raw"
S3_BASE_PATH = "raw/v1/tiptop_jp"

# JP 表格定義（來自 tiptop_jp/bindings.json）
# Mart 表格來自 DuckDB本地倉庫
JP_TABLES: Dict[str, Dict[str, Any]] = {
    # ========== S3 Parquet 表格 ==========
    "INAG_T": {
        "name": "INAG_T",
        "name_cn": "在庫明細",
        "description": "日本 TiTop 在庫明細表",
        "source": "S3 Parquet",
        "columns": [
            {"id": "INAGENT", "name": "企業編號", "type": "NUMBER"},
            {"id": "INAGSITE", "name": "營運據點", "type": "VARCHAR2"},
            {"id": "INAG001", "name": "料件編號", "type": "VARCHAR2"},
            {"id": "INAG004", "name": "倉庫編號", "type": "VARCHAR2"},
            {"id": "INAG005", "name": "儲位編號", "type": "VARCHAR2"},
            {"id": "INAG007", "name": "單位", "type": "VARCHAR2"},
            {"id": "INAG008", "name": "現有庫存", "type": "NUMBER(15,3)"},
        ],
    },
    "SFAA_T": {
        "name": "SFAA_T",
        "name_cn": "工單頭檔",
        "description": "日本 TiTop 工單頭檔",
        "source": "S3 Parquet",
        "columns": [
            {"id": "SFAAENT", "name": "企業編號", "type": "NUMBER"},
            {"id": "SFAASITE", "name": "營運據點", "type": "VARCHAR2"},
            {"id": "SFAA010", "name": "料件編號", "type": "VARCHAR2"},
            {"id": "SFAA056", "name": "報廢數量", "type": "NUMBER(15,3)"},
            {"id": "SFAA022", "name": "訂單編號", "type": "VARCHAR2"},
            {"id": "SFAA023", "name": "訂單項次", "type": "VARCHAR2"},
            {"id": "SFAA009", "name": "客戶編號", "type": "VARCHAR2"},
            {"id": "SFAASTUS", "name": "狀態", "type": "VARCHAR2"},
        ],
    },
    "SFCA_T": {
        "name": "SFCA_T",
        "name_cn": "工單製造頭檔",
        "description": "日本 TiTop 工單製造頭檔",
        "source": "S3 Parquet",
        "columns": [
            {"id": "SFCAENT", "name": "企業編號", "type": "NUMBER"},
            {"id": "SFCADocNo", "name": "工單編號", "type": "VARCHAR2"},
            {"id": "SFCA002", "name": "項次", "type": "VARCHAR2"},
            {"id": "SFCA001", "name": "序号", "type": "NUMBER"},
            {"id": "SFCA003", "name": "計劃數量", "type": "NUMBER"},
            {"id": "SFCA004", "name": "完工數量", "type": "NUMBER"},
            {"id": "month", "name": "月份", "type": "VARCHAR"},
            {"id": "year", "name": "年份", "type": "NUMBER"},
        ],
    },
    "SFCB_T": {
        "name": "SFCB_T",
        "name_cn": "工單製造明細檔",
        "description": "日本 TiTop 工單製造明細檔",
        "source": "S3 Parquet",
        "columns": [
            {"id": "SFCBENT", "name": "企業編號", "type": "NUMBER"},
            {"id": "SFCBDocNo", "name": "工單編號", "type": "VARCHAR2"},
            {"id": "SFCBSeq", "name": "項次", "type": "VARCHAR2"},
            {"id": "SFCBItem", "name": "料件", "type": "VARCHAR2"},
            {"id": "SFCBQty", "name": "數量", "type": "NUMBER"},
            {"id": "SFCBWIPQty", "name": "WIP數量", "type": "NUMBER"},
            {"id": "SFCBStatus", "name": "狀態", "type": "VARCHAR2"},
        ],
    },
    "XMDG_T": {
        "name": "XMDG_T",
        "name_cn": "出貨通知頭檔",
        "description": "日本 TiTop 出貨通知頭檔",
        "source": "S3 Parquet",
        "columns": [
            {"id": "XMDGENT", "name": "企業編號", "type": "NUMBER"},
            {"id": "XMDGDOCNO", "name": "出貨通知單號", "type": "VARCHAR2"},
            {"id": "XMDGDOCDT", "name": "出貨日期", "type": "DATE"},
            {"id": "XMDGCustID", "name": "客戶編號", "type": "VARCHAR2"},
            {"id": "XMDG005", "name": "業務人員", "type": "VARCHAR2"},
            {"id": "XMDGSTUS", "name": "狀態", "type": "VARCHAR2"},
            {"id": "XMDGTotalAmt", "name": "總金額", "type": "NUMBER"},
        ],
    },
    "XMDH_T": {
        "name": "XMDH_T",
        "name_cn": "出貨通知明細檔",
        "description": "日本 TiTop 出貨通知明細檔",
        "source": "S3 Parquet",
        "columns": [
            {"id": "XMDHENT", "name": "企業編號", "type": "NUMBER"},
            {"id": "XMDHDOCNO", "name": "出貨通知單號", "type": "VARCHAR2"},
            {"id": "XMDHSEQ", "name": "項次", "type": "VARCHAR2"},
            {"id": "XMDH006", "name": "料號", "type": "VARCHAR2"},
            {"id": "XMDH016", "name": "預交數量", "type": "NUMBER"},
            {"id": "XMDH017", "name": "實際數量", "type": "NUMBER"},
            {"id": "XMDH023", "name": "單價", "type": "NUMBER"},
        ],
    },
    # ========== Mart 寬表 (DuckDB 本地) ==========
    "mart_work_order_wide": {
        "name": "mart_work_order_wide",
        "name_cn": "工單寬表",
        "description": "工單數據寬表（已整合）",
        "source": "DuckDB 本地",
        "columns": [
            {"id": "item_no", "name": "料件編號", "type": "VARCHAR"},
            {"id": "customer_no", "name": "客戶編號", "type": "VARCHAR"},
            {"id": "status", "name": "狀態", "type": "VARCHAR"},
            {"id": "scrap_qty", "name": "報廢數量", "type": "DOUBLE"},
            {"id": "workstation", "name": "工作站", "type": "VARCHAR"},
        ],
    },
    "mart_inventory_wide": {
        "name": "mart_inventory_wide",
        "name_cn": "庫存寬表",
        "description": "庫存數據寬表（已整合）",
        "source": "DuckDB 本地",
        "columns": [
            {"id": "item_no", "name": "料件編號", "type": "VARCHAR"},
            {"id": "warehouse_no", "name": "倉庫編號", "type": "VARCHAR"},
            {"id": "location_no", "name": "儲位編號", "type": "VARCHAR"},
            {"id": "unit", "name": "單位", "type": "VARCHAR"},
            {"id": "existing_stocks", "name": "現有庫存", "type": "DOUBLE"},
        ],
    },
    "mart_shipping_wide": {
        "name": "mart_shipping_wide",
        "name_cn": "出貨寬表",
        "description": "出貨數據寬表（已整合）",
        "source": "DuckDB 本地",
        "columns": [
            {"id": "doc_no", "name": "出貨單號", "type": "VARCHAR"},
            {"id": "doc_date", "name": "出貨日期", "type": "VARCHAR"},
            {"id": "status", "name": "狀態", "type": "VARCHAR"},
            {"id": "customer_no", "name": "客戶編號", "type": "VARCHAR"},
            {"id": "seq", "name": "項次", "type": "DOUBLE"},
            {"id": "item_no", "name": "料件編號", "type": "VARCHAR"},
            {"id": "actual_qty", "name": "實際數量", "type": "DOUBLE"},
            {"id": "unit_price", "name": "單價", "type": "DOUBLE"},
        ],
    },
}


def get_s3_path(table_name: str) -> str:
    """取得 S3 Parquet 路徑"""
    return f"s3://{S3_BUCKET}/{S3_BASE_PATH}/{table_name}/year=*/month=*/data.parquet"


def is_mart_table(table_name: str) -> bool:
    """檢查是否為本地 DuckDB Mart 表格"""
    return table_name in ["mart_work_order_wide", "mart_inventory_wide", "mart_shipping_wide"]


def execute_query_local(query: str, max_rows: int = 100) -> dict:
    """執行本地 DuckDB 查詢（Mart 表格）"""
    conn = duckdb.connect(JP_DUCKDB_PATH, read_only=True)
    try:
        query_with_limit = query.strip()
        if query_with_limit.upper().startswith("SELECT") and "LIMIT" not in query.upper():
            query_with_limit = f"{query_with_limit} LIMIT {max_rows}"

        result = conn.execute(query_with_limit)

        if query.strip().upper().startswith("SELECT"):
            columns = [desc[0] for desc in conn.description]
            rows = result.fetchall()
            row_count = len(rows)
            error = None
        else:
            columns = []
            rows = []
            row_count = result.rowcount
            error = None

        conn.close()
        return {"columns": columns, "rows": rows, "row_count": row_count, "error": error}
    except Exception as e:
        conn.close()
        return {"columns": None, "rows": None, "row_count": 0, "error": str(e)}


def execute_query_s3(query: str, max_rows: int = 100) -> dict:
    """執行 S3 Parquet 查詢"""
    conn = duckdb.connect(JP_DUCKDB_PATH, read_only=True)

    try:
        # 配置 S3 連接（使用 path-style addressing）
        conn.execute("SET s3_endpoint='localhost:8334';")
        conn.execute("SET s3_access_key_id='admin';")
        conn.execute("SET s3_secret_access_key='admin123';")
        conn.execute("SET s3_use_ssl=false;")
        conn.execute("SET s3_region='us-east-1';")
        conn.execute("SET s3_url_style='path';")

        # 添加 LIMIT
        query_with_limit = query.strip()
        if query_with_limit.upper().startswith("SELECT") and "LIMIT" not in query.upper():
            query_with_limit = f"{query_with_limit} LIMIT {max_rows}"

        result = conn.execute(query_with_limit)

        # 獲取結果
        if query.strip().upper().startswith("SELECT"):
            columns = [desc[0] for desc in conn.description]
            rows = result.fetchall()
            row_count = len(rows)
            error = None
        else:
            columns = []
            rows = []
            row_count = result.rowcount
            error = None

        conn.close()
        return {"columns": columns, "rows": rows, "row_count": row_count, "error": error}
    except Exception as e:
        conn.close()
        return {"columns": None, "rows": None, "row_count": 0, "error": str(e)}


def preview_s3_table(
    table_name: str, max_rows: int = 100
) -> tuple[Optional[List[str]], Optional[List[tuple]]]:
    """預覽表格數據（支持 S3 Parquet 和本地 DuckDB）"""
    if table_name not in JP_TABLES:
        return None, None

    table_info = JP_TABLES[table_name]
    source = table_info.get("source", "S3 Parquet")

    if is_mart_table(table_name):
        query = f"SELECT * FROM {table_name} LIMIT {max_rows}"
        result = execute_query_local(query, max_rows)
    else:
        s3_path = get_s3_path(table_name)
        query = f"SELECT * FROM read_parquet('{s3_path}') LIMIT {max_rows}"
        result = execute_query_s3(query, max_rows)

    if result["error"]:
        st.error(f"查詢錯誤: {result['error']}")
        return None, None

    return result["columns"], result["rows"]


def get_table_list() -> List[str]:
    """取得可用表格列表"""
    return list(JP_TABLES.keys())


def generate_sql_template(table_name: str, template_type: str) -> str:
    """生成 SQL 模板"""
    if is_mart_table(table_name):
        templates = {
            "basic": f"-- 查詢 {JP_TABLES[table_name]['name_cn']} 基本資料\nSELECT * FROM {table_name} LIMIT 100",
            "count": f"-- 統計 {JP_TABLES[table_name]['name_cn']} 筆數\nSELECT COUNT(*) as total FROM {table_name}",
            "aggregate": f"-- 聚合查詢範例\nSELECT item_no, COUNT(*) as cnt FROM {table_name} GROUP BY item_no LIMIT 100",
            "join": f"-- JOIN 查詢範例\nSELECT a.*, b.* FROM {table_name} a\nLEFT JOIN mart_inventory_wide b ON a.item_no = b.item_no LIMIT 100",
        }
    else:
        s3_path = get_s3_path(table_name)
        templates = {
            "basic": f"-- 查詢 {JP_TABLES[table_name]['name_cn']} 基本資料\nSELECT * FROM read_parquet('{s3_path}') LIMIT 100",
            "count": f"-- 統計 {JP_TABLES[table_name]['name_cn']} 筆數\nSELECT COUNT(*) as total FROM read_parquet('{s3_path}')",
            "aggregate": f"-- 聚合查詢範例\nSELECT COUNT(*) as cnt, SUM(column) as total FROM read_parquet('{s3_path}') GROUP BY column",
            "join": f"-- JOIN 查詢範例\nSELECT a.*, b.* FROM read_parquet('{s3_path}') a\nLEFT JOIN read_parquet('s3://{S3_BUCKET}/{S3_BASE_PATH}/other_table/year=*/month=*/data.parquet') b ON a.key = b.key",
        }

    return templates.get(template_type, templates["basic"])


def render_sql_explorer() -> None:
    """渲染 SQL Explorer 頁面"""
    st.markdown("### 🗃️ SQL Explorer - JP Tiptop 數據庫")

    # 初始化 session state
    if "sql_query" not in st.session_state:
        st.session_state.sql_query = "-- 輸入您的 SQL 查詢\nSELECT * FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/INAG_T/year=*/month=*/data.parquet') LIMIT 100"
    if "query_result" not in st.session_state:
        st.session_state.query_result = None

    # 兩欄布局
    col1, col2 = st.columns([1, 2], gap="medium")

    with col1:
        st.markdown("#### 📋 表格瀏覽")

        # 表格選擇器
        selected_table = st.selectbox(
            "選擇表格",
            options=get_table_list(),
            index=0,
            format_func=lambda x: f"{x} - {JP_TABLES[x]['name_cn']}",
        )

        if selected_table:
            table_info = JP_TABLES[selected_table]

            # 顯示表格資訊
            with st.expander("📊 表格資訊", expanded=True):
                st.markdown(f"**表格名稱**: {table_info['name']}")
                st.markdown(f"**中文名稱**: {table_info['name_cn']}")
                st.markdown(f"**描述**: {table_info['description']}")
                st.markdown(f"**數據源**: {table_info.get('source', 'S3 Parquet')}")

            # 顯示欄位
            st.markdown("**欄位清單**:")
            columns = table_info.get("columns", [])
            for col in columns:
                st.markdown(f"- `{col['id']}` - {col['name']}")

            # 預覽按鈕
            if st.button("👁️ 預覽數據", use_container_width=True):
                with st.spinner("正在載入預覽數據..."):
                    cols, rows = preview_s3_table(selected_table)
                    if cols and rows:
                        st.success(f"成功載入 {len(rows)} 筆資料")
                        # 顯示預覽資料 - 確保 columns 和 data 長度一致
                        display_cols = cols[: len(rows[0])] if len(cols) > len(rows[0]) else cols
                        preview_df = pd.DataFrame(list(rows), columns=display_cols)
                        st.dataframe(preview_df, height=200, use_container_width=True)
                    else:
                        st.warning("無法載入預覽資料")

            # SQL 模板
            st.markdown("**SQL 模板**:")
            template_type = st.selectbox(
                "選擇模板",
                options=["basic", "count", "aggregate", "join"],
                format_func=lambda x: {
                    "basic": "基本查詢",
                    "count": "統計筆數",
                    "aggregate": "聚合查詢",
                    "join": "JOIN 查詢",
                }[x],
            )

            template_sql = generate_sql_template(selected_table, template_type)
            if st.button("📝 套用模板", use_container_width=True):
                st.session_state.sql_query = template_sql
                st.rerun()

    with col2:
        st.markdown("#### 📝 SQL 編輯器")

        # SQL 輸入區域
        sql_query = st.text_area(
            "輸入 SQL 查詢",
            value=st.session_state.sql_query,
            height=200,
            help="支援 DuckDB SQL 語法，可使用 read_parquet() 讀取 S3 Parquet 檔案",
        )

        # 查詢選項
        col_opts1, col_opts2 = st.columns(2)
        with col_opts1:
            max_rows = st.number_input(
                "最大筆數", min_value=10, max_value=10000, value=100, step=10
            )
        with col_opts2:
            show_sql_path = st.checkbox("顯示 S3 路徑範例", value=True)

        if show_sql_path:
            st.markdown("**S3 路徑格式**:")
            st.code(
                f"s3://{S3_BUCKET}/{S3_BASE_PATH}/{{TABLE}}/year=*/month=*/data.parquet",
                language="sql",
            )

        # 執行按鈕
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])
        with col_btn1:
            execute_btn = st.button("▶️ 執行查詢", type="primary", use_container_width=True)
        with col_btn2:
            clear_btn = st.button("🗑️ 清除", use_container_width=True)

        if clear_btn:
            st.session_state.sql_query = "-- 清除\nSELECT 1"
            st.session_state.query_result = None
            st.rerun()

        if execute_btn:
            if not sql_query.strip():
                st.warning("請輸入 SQL 查詢")
            else:
                with st.spinner("正在執行查詢..."):
                    query_lower = sql_query.lower()
                    is_local_query = any(
                        mart in query_lower
                        for mart in [
                            "mart_work_order_wide",
                            "mart_inventory_wide",
                            "mart_shipping_wide",
                        ]
                    )

                    if is_local_query:
                        result = execute_query_local(sql_query, max_rows)
                    else:
                        result = execute_query_s3(sql_query, max_rows)

                    if result["error"]:
                        st.error(f"❌ 查詢錯誤: {result['error']}")
                        st.session_state.query_result = None
                    else:
                        st.success(f"✅ 查詢成功，返回 {result['row_count']} 筆資料")
                        st.session_state.query_result = result

        # 顯示查詢結果
        if st.session_state.query_result:
            result = st.session_state.query_result

            if result["columns"] and result["rows"]:
                st.markdown("**查詢結果**:")
                try:
                    df = pd.DataFrame(result["rows"], columns=result["columns"])
                    st.dataframe(df, use_container_width=True, height=400)

                    # 匯出選項
                    col_exp1, col_exp2 = st.columns(2)
                    with col_exp1:
                        csv = df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "📥 下載 CSV",
                            data=csv,
                            file_name="query_result.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                except Exception as e:
                    st.error(f"顯示結果錯誤: {e}")
            elif result["row_count"] is not None:
                st.markdown(f"**執行結果**: 影響 {result['row_count']} 筆資料")
            else:
                st.info("查詢已執行，無返回資料")

    # 底部說明
    st.markdown("---")
    with st.expander("📖 SQL 查詢說明"):
        st.markdown("""
        **支援的查詢方式**:

        1. **直接查詢本地 Mart 寬表**:
        ```sql
        SELECT * FROM mart_work_order_wide LIMIT 100
        ```

        2. **直接查詢 S3 Parquet**:
        ```sql
        SELECT * FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/INAG_T/year=*/month=*/data.parquet') LIMIT 100
        ```

        3. **聚合查詢**:
        ```sql
        SELECT INAG001, COUNT(*) as cnt
        FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/INAG_T/year=*/month=*/data.parquet')
        GROUP BY INAG001
        LIMIT 100
        ```

        4. **JOIN 查詢 (Mart + S3)**:
        ```sql
        SELECT a.*, b.*
        FROM mart_work_order_wide a
        LEFT JOIN mart_inventory_wide b ON a.item_no = b.item_no
        LIMIT 100
        ```

        **注意事項**:
        - 查詢自動添加 LIMIT 限制
        - S3 路徑使用 path-style 格式
        - 支援標準 DuckDB SQL 語法
        - Mart 寬表可直接查詢本地 DuckDB
        """)
