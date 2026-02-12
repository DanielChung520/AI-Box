#!/usr/bin/env python3
import duckdb

conn = duckdb.connect(
    database=":memory:",
    config={
        "s3_access_key_id": "admin",
        "s3_secret_access_key": "admin123",
        "s3_endpoint": "localhost:8334",
        "s3_region": "us-east-1",
        "s3_use_ssl": "false",
        "s3_url_style": "path",
    },
)

# 查詢 SFCB_T 的 schema
try:
    result = conn.execute("""
        SELECT column_name, column_type 
        FROM information_schema.columns 
        WHERE table_name = 'sfcb_t'
        ORDER BY ordinal_position
    """)
    print("SFCB_T columns from information_schema:")
    for row in result.fetchall():
        print(f"  {row[0]}: {row[1]}")
except Exception as e:
    print(f"Error: {e}")

# 嘗試直接查詢 Parquet
try:
    result = conn.execute("""
        SELECT * FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/SFCB_T/year=*/month=*/data.parquet') LIMIT 1
    """)
    print("\nActual Parquet columns:")
    for col in result.description:
        print(f"  {col[0]}")
except Exception as e:
    print(f"\nParquet read error: {e}")
