# 代碼功能說明: DT-Agent Mart 表 ETL 腳本 — 從 S3 parquet 重建所有 mart 寬表到 DuckDB
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

"""
Mart ETL 腳本：從 S3 (SeaweedFS) 上的 Oracle 原始 parquet 重建 4 張 mart 寬表

用法：
    cd /home/daniel/ai-box/datalake-system
    PYTHONPATH=. python3 dt_agent/scripts/rebuild_marts.py [--mart NAME] [--dry-run]

    --mart NAME     只重建指定的 mart 表（inventory, work_order, shipping, price）
    --dry-run       只顯示 SQL 不執行
    --drop-first    先 DROP 再 CREATE（預設行為）
    --no-drop       不 DROP，使用 CREATE OR REPLACE

Mart 表清單：
    1. mart_inventory_wide    (INAG_T)                    → 7 欄
    2. mart_work_order_wide   (SFCA_T + SFCB_T + SFAA_T)  → ~30 欄
    3. mart_shipping_wide     (XMDG_T + XMDH_T)           → ~20 欄
    4. mart_price_wide        (XMDT_T + XMDU_T)           → ~13 欄
"""

import argparse
import sys
import time
from pathlib import Path

import duckdb

# ===== S3 連線設定 =====
S3_CONFIG = {
    "endpoint": "localhost:8334",
    "access_key": "admin",
    "secret_key": "admin123",
    "url_style": "path",
    "use_ssl": False,
    "bucket": "tiptop-raw",
    "prefix": "raw/v1/tiptop_jp",
}

DUCKDB_PATH = str(Path(__file__).resolve().parents[2] / "data" / "warehouse" / "tiptop_jp.duckdb")


def s3_table(table_name: str) -> str:
    """生成 S3 parquet 讀取表達式（含 Hive partitioning）"""
    return (
        f"read_parquet("
        f"'s3://{S3_CONFIG['bucket']}/{S3_CONFIG['prefix']}/{table_name}"
        f"/year=*/month=*/data.parquet', hive_partitioning=true)"
    )


# ===== Mart 定義 =====


def sql_mart_inventory_wide() -> str:
    """mart_inventory_wide: 庫存明細（7 欄，來源 INAG_T）"""
    return f"""
CREATE OR REPLACE TABLE mart_inventory_wide AS
SELECT
    CAST(INAGENT AS VARCHAR)    AS ent,
    CAST(INAGSITE AS VARCHAR)   AS site,
    CAST(INAG001 AS VARCHAR)    AS item_no,
    CAST(INAG004 AS VARCHAR)    AS warehouse_no,
    CAST(INAG005 AS VARCHAR)    AS location_no,
    CAST(INAG007 AS VARCHAR)    AS unit,
    CAST(INAG008 AS DOUBLE)     AS existing_stocks
FROM {s3_table("INAG_T")}
"""


def sql_mart_work_order_wide() -> str:
    """mart_work_order_wide: 工單寬表（SFCA_T LEFT JOIN SFCB_T）

    主體：SFCA_T（製令單頭）LEFT JOIN SFCB_T（工序明細）
    
    注意：SFAA_T 與 SFCA_T 沒有直接 FK 關聯（SFAA 是品項工單基本資料，
    SFCA 是製令單），且 SFAA_T 是 snapshot 匯出有大量重複行，因此不 JOIN SFAA_T
    """
    return f"""
CREATE OR REPLACE TABLE mart_work_order_wide AS
SELECT
    -- SFCA 製令單頭
    CAST(ca.SFCAENT AS VARCHAR)     AS ent,
    CAST(ca.SFCASITE AS VARCHAR)    AS site,
    CAST(ca.SFCADOCNO AS VARCHAR)   AS mo_doc_no,
    CAST(ca.SFCA002 AS DOUBLE)      AS mo_doc_seq,
    CAST(ca.SFCA001 AS DOUBLE)      AS run_card_no,
    CAST(ca.SFCA003 AS DOUBLE)      AS production_qty,
    CAST(ca.SFCA004 AS DOUBLE)      AS completion_qty,
    -- SFCB 工序明細
    CAST(cb.SFCB002 AS VARCHAR)     AS ln,
    CAST(cb.SFCB003 AS VARCHAR)     AS current_operation,
    CAST(cb.SFCB004 AS INTEGER)     AS operation_seq,
    CAST(cb.SFCB011 AS VARCHAR)     AS workstation,
    CAST(cb.SFCB027 AS DOUBLE)      AS standard_output,
    CAST(cb.SFCB028 AS DOUBLE)      AS good_items_in,
    CAST(cb.SFCB033 AS DOUBLE)      AS good_items_out,
    CAST(cb.SFCB029 AS DOUBLE)      AS rework_in,
    CAST(cb.SFCB034 AS DOUBLE)      AS rework_out,
    CAST(cb.SFCB050 AS DOUBLE)      AS wip_qty,
    CAST(cb.SFCB036 AS DOUBLE)      AS scrap_in_station,
    CAST(cb.SFCB051 AS DOUBLE)      AS pending_pqc_qty,
    CAST(cb.SFCB041 AS DOUBLE)      AS outsourced_qty,
    CAST(cb.SFCB042 AS DOUBLE)      AS outsourced_finish_qty
FROM {s3_table("SFCA_T")} ca
LEFT JOIN {s3_table("SFCB_T")} cb
    ON ca.SFCAENT = cb.SFCBENT
    AND ca.SFCASITE = cb.SFCBSITE
    AND ca.SFCADOCNO = cb.SFCBDOCNO
"""


def sql_mart_shipping_wide() -> str:
    """mart_shipping_wide: 出貨寬表（XMDG_T LEFT JOIN XMDH_T，~20 欄）"""
    return f"""
CREATE OR REPLACE TABLE mart_shipping_wide AS
SELECT
    -- XMDG 出貨通知頭
    CAST(g.XMDGENT AS VARCHAR)      AS ent,
    CAST(g.XMDGSITE AS VARCHAR)     AS site,
    CAST(g.XMDGDOCNO AS VARCHAR)    AS doc_no,
    CAST(g.XMDGDOCDT AS VARCHAR)    AS doc_date,
    CAST(g.XMDGSTUS AS VARCHAR)     AS status,
    CAST(g.XMDG002 AS VARCHAR)      AS sales_person,
    CAST(g.XMDG003 AS VARCHAR)      AS sales_department,
    CAST(g.XMDG005 AS VARCHAR)      AS customer_no,
    CAST(g.XMDG028 AS VARCHAR)      AS expected_shipping_date,
    CAST(g.XMDG027 AS VARCHAR)      AS sales_category,
    -- XMDH 出貨通知明細
    CAST(h.XMDHSEQ AS DOUBLE)       AS seq,
    CAST(h.XMDH001 AS VARCHAR)      AS order_no,
    CAST(h.XMDH002 AS VARCHAR)      AS so_line,
    CAST(h.XMDH003 AS VARCHAR)      AS order_line_sn,
    CAST(h.XMDH004 AS VARCHAR)      AS order_batch_seq,
    CAST(h.XMDHUD001 AS VARCHAR)    AS customer_po_no,
    CAST(h.XMDH006 AS VARCHAR)      AS item_no,
    CAST(h.XMDH016 AS DOUBLE)       AS request_qty,
    CAST(h.XMDH017 AS DOUBLE)       AS actual_qty,
    CAST(h.XMDH023 AS DOUBLE)       AS unit_price
FROM {s3_table("XMDG_T")} g
LEFT JOIN {s3_table("XMDH_T")} h
    ON g.XMDGENT = h.XMDHENT
    AND g.XMDGSITE = h.XMDHSITE
    AND g.XMDGDOCNO = h.XMDHDOCNO
"""


def sql_mart_price_wide() -> str:
    """mart_price_wide: 售價審核寬表（XMDT_T LEFT JOIN XMDU_T，~13 欄）"""
    return f"""
CREATE OR REPLACE TABLE mart_price_wide AS
SELECT
    -- XMDT 售價審核頭
    CAST(t.XMDTENT AS VARCHAR)      AS ent,
    CAST(t.XMDTSITE AS VARCHAR)     AS site,
    CAST(t.XMDTDOCNO AS VARCHAR)    AS doc_no,
    CAST(t.XMDTDOCDT AS VARCHAR)    AS doc_date,
    CAST(t.XMDT004 AS VARCHAR)      AS customer_no,
    CAST(t.XMDT002 AS VARCHAR)      AS applicant,
    CAST(t.XMDT003 AS VARCHAR)      AS department,
    CAST(t.XMDTSTUS AS VARCHAR)     AS status,
    CAST(t.XMDT015 AS VARCHAR)      AS valid_date,
    -- XMDU 售價審核明細
    CAST(u.XMDUSEQ AS DOUBLE)       AS seq,
    CAST(u.XMDU002 AS VARCHAR)      AS item_no,
    CAST(u.XMDU008 AS VARCHAR)      AS unit,
    CAST(u.XMDU011 AS DOUBLE)       AS unit_price
FROM {s3_table("XMDT_T")} t
LEFT JOIN {s3_table("XMDU_T")} u
    ON t.XMDTENT = u.XMDUENT
    AND t.XMDTSITE = u.XMDUSITE
    AND t.XMDTDOCNO = u.XMDUDOCNO
"""


# ===== Mart 註冊表 =====
MART_REGISTRY = {
    "inventory": {
        "table_name": "mart_inventory_wide",
        "sql_fn": sql_mart_inventory_wide,
        "description": "庫存明細（INAG_T → 7 欄）",
    },
    "work_order": {
        "table_name": "mart_work_order_wide",
        "sql_fn": sql_mart_work_order_wide,
        "description": "工單寬表（SFCA_T + SFCB_T → ~21 欄）",
    },
    "shipping": {
        "table_name": "mart_shipping_wide",
        "sql_fn": sql_mart_shipping_wide,
        "description": "出貨寬表（XMDG_T + XMDH_T → ~20 欄）",
    },
    "price": {
        "table_name": "mart_price_wide",
        "sql_fn": sql_mart_price_wide,
        "description": "售價審核寬表（XMDT_T + XMDU_T → ~13 欄）",
    },
}


def setup_s3(conn: duckdb.DuckDBPyConnection) -> None:
    """設定 DuckDB S3 連線參數"""
    conn.execute(f"SET s3_endpoint='{S3_CONFIG['endpoint']}'")
    conn.execute(f"SET s3_access_key_id='{S3_CONFIG['access_key']}'")
    conn.execute(f"SET s3_secret_access_key='{S3_CONFIG['secret_key']}'")
    conn.execute(f"SET s3_url_style='{S3_CONFIG['url_style']}'")
    conn.execute(f"SET s3_use_ssl={'true' if S3_CONFIG['use_ssl'] else 'false'}")


def rebuild_mart(
    conn: duckdb.DuckDBPyConnection,
    mart_key: str,
    dry_run: bool = False,
) -> dict:
    """重建單張 mart 表

    Returns:
        dict: {"table": str, "rows": int, "columns": int, "elapsed_s": float}
    """
    info = MART_REGISTRY[mart_key]
    table_name = info["table_name"]
    sql = info["sql_fn"]()

    print(f"\n{'=' * 60}")
    print(f"📦 {info['description']}")
    print(f"   表名: {table_name}")
    print(f"{'=' * 60}")

    if dry_run:
        print(f"\n[DRY-RUN] SQL:\n{sql}")
        return {"table": table_name, "rows": 0, "columns": 0, "elapsed_s": 0.0}

    # DROP + CREATE
    print(f"  ⏳ DROP TABLE IF EXISTS {table_name}...")
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")

    print(f"  ⏳ 從 S3 讀取並建立 {table_name}...")
    t0 = time.time()
    conn.execute(sql)
    elapsed = time.time() - t0

    # 驗證
    row_count = conn.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
    col_info = conn.execute(f"SELECT * FROM {table_name} LIMIT 0").description
    col_count = len(col_info)
    col_names = [c[0] for c in col_info]

    print(f"  ✅ 完成！{row_count:,} rows × {col_count} columns（{elapsed:.1f}s）")
    print(f"  📋 欄位: {', '.join(col_names)}")

    return {
        "table": table_name,
        "rows": row_count,
        "columns": col_count,
        "elapsed_s": elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="DT-Agent Mart ETL 腳本")
    parser.add_argument(
        "--mart",
        choices=list(MART_REGISTRY.keys()) + ["all"],
        default="all",
        help="要重建的 mart 表（預設: all）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只顯示 SQL 不執行",
    )
    parser.add_argument(
        "--db-path",
        default=DUCKDB_PATH,
        help=f"DuckDB 路徑（預設: {DUCKDB_PATH}）",
    )
    args = parser.parse_args()

    print("🚀 DT-Agent Mart ETL 腳本")
    print(f"   DuckDB: {args.db_path}")
    print(f"   S3: {S3_CONFIG['endpoint']} / {S3_CONFIG['bucket']}")
    print(f"   模式: {'DRY-RUN' if args.dry_run else 'EXECUTE'}")

    # 連線 DuckDB
    conn = duckdb.connect(args.db_path)
    setup_s3(conn)

    # 決定要重建的 mart
    mart_keys = list(MART_REGISTRY.keys()) if args.mart == "all" else [args.mart]

    results = []
    total_t0 = time.time()

    for key in mart_keys:
        try:
            result = rebuild_mart(conn, key, dry_run=args.dry_run)
            results.append(result)
        except Exception as e:
            print(f"\n  ❌ {MART_REGISTRY[key]['table_name']} 失敗: {e}")
            results.append(
                {
                    "table": MART_REGISTRY[key]["table_name"],
                    "rows": -1,
                    "columns": 0,
                    "elapsed_s": 0.0,
                    "error": str(e),
                }
            )

    total_elapsed = time.time() - total_t0

    # 總結
    print(f"\n{'=' * 60}")
    print(f"📊 ETL 總結（總耗時: {total_elapsed:.1f}s）")
    print(f"{'=' * 60}")
    for r in results:
        if r.get("error"):
            print(f"  ❌ {r['table']}: FAILED - {r['error']}")
        elif args.dry_run:
            print(f"  📝 {r['table']}: DRY-RUN")
        else:
            print(
                f"  ✅ {r['table']}: {r['rows']:,} rows × {r['columns']} cols ({r['elapsed_s']:.1f}s)"
            )

    conn.close()

    # 如果有失敗的 mart，exit code = 1
    if any(r.get("error") for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
