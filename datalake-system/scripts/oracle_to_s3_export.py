# 代碼功能說明: Oracle → S3 直接轉換腳本
# 創建日期: 2026-02-12
# 創建人: Daniel Chung
# 用途: 將 TiTop JP Oracle 數據直接導出到 S3 (Parquet)

"""
Oracle → S3 直接轉換腳本

使用方式:
    # 導出所有表格
    python oracle_to_s3_export.py --all

    # 導出指定表格
    python oracle_to_s3_export.py --tables INAG_T,SFAA_T

    # 只導出不存在的表格
    python oracle_to_s3_export.py --only-missing
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import duckdb
import oracledb

# ============== 配置 ==============
ORACLE_CONFIG = {
    "host": "192.168.5.16",
    "port": 1521,
    "service": "ORCL",
    "user": "appuser",
    "password": "app123",
    "lib_path": "/home/daniel/instantclient_23_26",
}

S3_CONFIG = {
    "endpoint": "localhost:8334",
    "access_key": "admin",
    "secret_key": "admin123",
    "bucket": "tiptop-raw",
    "path_prefix": "raw/v1/tiptop_jp",
}

# 要導出的表格清單
TABLES = [
    ("INAG_T", "在庫明細"),
    ("SFAA_T", "工單頭檔"),
    ("SFCA_T", "工單製造頭檔"),
    ("SFCB_T", "工單製造明細檔"),
    ("XMDG_T", "出貨通知頭檔"),
    ("XMDH_T", "出貨通知明細檔"),
    ("XMDT_T", "售價審核頭檔"),
    ("XMDU_T", "售價審核明細檔"),
]


def get_oracle_connection():
    """建立 Oracle 連接 (Thick Mode)"""
    os.environ["LD_LIBRARY_PATH"] = (
        f"{ORACLE_CONFIG['lib_path']}:/home/daniel/oracle_libs:"
        + os.environ.get("LD_LIBRARY_PATH", "")
    )
    oracledb.init_oracle_client(lib_dir=ORACLE_CONFIG["lib_path"])

    dsn = f"{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}/{ORACLE_CONFIG['service']}"
    return oracledb.connect(
        user=ORACLE_CONFIG["user"],
        password=ORACLE_CONFIG["password"],
        dsn=dsn,
    )


def get_s3_path(table_name: str) -> str:
    """生成 S3 路徑"""
    return f"s3://{S3_CONFIG['bucket']}/{S3_CONFIG['path_prefix']}/{table_name}/year=*/month=*/data.parquet"


def check_s3_exists(duckdb_conn, table_name: str) -> bool:
    """檢查 S3 上是否已有數據"""
    s3_path = get_s3_path(table_name)
    try:
        result = duckdb_conn.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{s3_path}')
        """).fetchone()
        return result[0] > 0 if result else False
    except:
        return False


def export_table(table_name: str, description: str, duckdb_conn, oracle_conn) -> bool:
    """導出單個表格"""
    print(f"\n{'=' * 60}")
    print(f"導出表格: {table_name} ({description})")
    print(f"{'=' * 60}")

    # 檢查是否已存在
    if check_s3_exists(duckdb_conn, table_name):
        print(f"⚠️  表格 {table_name} 已存在於 S3，跳過")
        return True

    start_time = time.time()

    try:
        # 1. 從 Oracle 讀取數據
        print(f"1. 從 Oracle 讀取 {table_name}...")
        cursor = oracle_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        row_count = len(rows)
        print(f"   讀取完成: {row_count:,} rows")

        if row_count == 0:
            print(f"   ⚠️  表格為空，跳過")
            return True

        # 2. 建立臨時 DuckDB 表
        print(f"2. 建立臨時表...")
        temp_table_name = f"temp_{table_name}"

        # 建立欄位類型映射
        col_defs = []
        for col in cursor.description:
            col_name = col[0]
            oracle_type = str(col[1]).upper() if col[1] else "VARCHAR2"

            # 簡單類型映射
            if "VARCHAR2" in oracle_type or "CHAR" in oracle_type:
                duckdb_type = "VARCHAR"
            elif "NUMBER" in oracle_type:
                if col[4]:  # scale
                    duckdb_type = "DOUBLE"
                else:
                    duckdb_type = "BIGINT"
            elif "DATE" in oracle_type or "TIMESTAMP" in oracle_type:
                duckdb_type = "VARCHAR"
            elif "CLOB" in oracle_type or "BLOB" in oracle_type:
                duckdb_type = "VARCHAR"
            else:
                duckdb_type = "VARCHAR"

            col_defs.append(f'"{col_name}" {duckdb_type}')

        create_sql = f'CREATE TABLE "{temp_table_name}" ({", ".join(col_defs)})'
        duckdb_conn.execute(create_sql)

        # 插入數據
        print(f"3. 插入數據到臨時表...")
        placeholders = ", ".join([f"${i + 1}" for i in range(len(columns))])
        insert_sql = f'INSERT INTO "{temp_table_name}" VALUES ({placeholders})'

        # 分批插入
        batch_size = 10000
        for i in range(0, row_count, batch_size):
            batch = rows[i : i + batch_size]
            duckdb_conn.executemany(insert_sql, batch)
            progress = min(i + batch_size, row_count)
            print(f"   進度: {progress:,}/{row_count:,} ({progress * 100 // row_count}%)")

        # 3. 導出到 S3 Parquet
        print(f"4. 導出到 S3 Parquet...")
        s3_base_path = f"s3://{S3_CONFIG['bucket']}/{S3_CONFIG['path_prefix']}/{table_name}"
        year = datetime.now().year
        month = datetime.now().month

        duckdb_conn.execute(f"""
            COPY "{temp_table_name}"
            TO '{s3_base_path}/year={year}/month={month:02d}/data.parquet'
            (FORMAT PARQUET, ROW_GROUP_SIZE 100000)
        """)

        # 清理臨時表
        duckdb_conn.execute(f'DROP TABLE "{temp_table_name}"')

        execution_time = time.time() - start_time

        print(f"   ✅ 導出完成!")
        print(f"   - 筆數: {row_count:,}")
        print(f"   - 路徑: {s3_base_path}/year={year}/month={month:02d}/")
        print(f"   - 時間: {execution_time:.1f} 秒")
        print(f"   - 速度: {row_count / execution_time:,.0f} rows/sec")

        return True

    except Exception as e:
        print(f"   ❌ 導出失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_export(table_name: str, duckdb_conn, expected_rows: int = None) -> bool:
    """驗證導出的數據"""
    print(f"\n驗證 {table_name}...")

    s3_path = get_s3_path(table_name)
    try:
        result = duckdb_conn.execute(f"""
            SELECT COUNT(*) as cnt, MIN(year) as min_year, MAX(year) as max_year
            FROM read_parquet('{s3_path}')
        """).fetchone()

        print(f"   - 筆數: {result[0]:,}")
        print(f"   - 年份範圍: {result[1]} - {result[2]}")

        if expected_rows and result[0] != expected_rows:
            print(f"   ⚠️  筆數不符! 預期: {expected_rows:,}, 實際: {result[0]:,}")
            return False

        return True

    except Exception as e:
        print(f"   ❌ 驗證失敗: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Oracle → S3 數據導出工具")
    parser.add_argument("--all", action="store_true", help="導出所有表格")
    parser.add_argument("--tables", type=str, help="指定導出的表格 (逗號分隔)")
    parser.add_argument("--only-missing", action="store_true", help="只導出不存在的表格")
    parser.add_argument("--verify", action="store_true", help="驗證導出的數據")

    args = parser.parse_args()

    if not (args.all or args.tables or args.only_missing or args.verify):
        parser.print_help()
        print("\n範例:")
        print("  python oracle_to_s3_export.py --all                    # 導出所有表格")
        print("  python oracle_to_s3_export.py --tables INAG_T,SFAA_T  # 導出指定表格")
        print("  python oracle_to_s3_export.py --only-missing           # 只導出不存在的表格")
        print("  python oracle_to_s3_export.py --verify                 # 驗證已導出的數據")
        sys.exit(1)

    print("=" * 70)
    print("Oracle → S3 數據導出工具")
    print("=" * 70)
    print(f"Oracle: {ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}/{ORACLE_CONFIG['service']}")
    print(f"S3: {S3_CONFIG['endpoint']}/{S3_CONFIG['bucket']}/{S3_CONFIG['path_prefix']}")
    print("=" * 70)

    # 確定要導出的表格
    tables_to_export = []
    if args.tables:
        table_names = [t.strip() for t in args.tables.split(",")]
        tables_to_export = [(t, "") for t in table_names]
    elif args.all or args.only_missing:
        tables_to_export = TABLES

    # 建立連接
    print("\n建立連接...")
    oracle_conn = get_oracle_connection()
    duckdb_conn = duckdb.connect(":memory:")

    # 配置 S3
    duckdb_conn.execute(f"SET s3_endpoint = '{S3_CONFIG['endpoint']}'")
    duckdb_conn.execute(f"SET s3_access_key_id = '{S3_CONFIG['access_key']}'")
    duckdb_conn.execute(f"SET s3_secret_access_key = '{S3_CONFIG['secret_key']}'")
    duckdb_conn.execute("SET s3_use_ssl = false")
    duckdb_conn.execute("SET s3_url_style = 'path'")
    print("✅ 連接建立完成")

    try:
        if args.verify:
            # 只驗證
            print("\n驗證已導出的數據...")
            for table_name, desc in tables_to_export:
                if check_s3_exists(duckdb_conn, table_name):
                    verify_export(table_name, duckdb_conn)
                else:
                    print(f"⚠️  {table_name} 不存在於 S3")

        else:
            # 執行導出
            success_count = 0
            fail_count = 0

            for table_name, desc in tables_to_export:
                # 檢查是否只導出不存在的
                if args.only_missing and check_s3_exists(duckdb_conn, table_name):
                    print(f"\n跳過 {table_name} (已存在)")
                    continue

                if export_table(table_name, desc, duckdb_conn, oracle_conn):
                    success_count += 1
                else:
                    fail_count += 1

            # 總結
            print("\n" + "=" * 70)
            print("導出完成!")
            print(f"  - 成功: {success_count}/{len(tables_to_export)}")
            print(f"  - 失敗: {fail_count}/{len(tables_to_export)}")
            print("=" * 70)

    finally:
        oracle_conn.close()
        duckdb_conn.close()


if __name__ == "__main__":
    main()
