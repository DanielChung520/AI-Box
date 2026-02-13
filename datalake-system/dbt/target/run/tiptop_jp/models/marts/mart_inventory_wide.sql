
  
    
    

    create  table
      "tiptop_jp"."main_mart"."mart_inventory_wide__dbt_tmp"
  
    as (
      -- mart_inventory_wide.sql
-- 代碼功能說明: 庫存寬表 - 合併庫存明細與物料主檔
-- 創建日期: 2026-02-13
-- 創建人: Daniel Chung



-- 從 S3 Parquet 讀取庫存資料，關聯 MA 物料主檔
WITH source_inventory AS (
    SELECT
        -- INAG_T 庫存明細欄位
        ent,
        site,
        INAG001 AS item_no,
        INAG004 AS warehouse_no,
        INAG005 AS location_no,
        INAG007 AS unit,
        INAG008 AS existing_stocks,

        -- MA_T 物料主檔欄位 (LEFT JOIN)
        ma001 AS ma_item_no,
        ma002 AS item_name,
        ma003 AS item_spec,
        ma025 AS item_type,
        ma026 AS item_category,
        ma027 AS stock_unit
    FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/INAG_T/year=*/month=*/data.parquet', hive_partitioning=true)
    LEFT JOIN (
        SELECT
            ma001,
            ma002,
            ma003,
            ma025,
            ma026,
            ma027
        FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/MA_T/year=*/month=*/data.parquet', hive_partitioning=true)
    ) ON INAG001 = ma001
),

inventory_with_ranking AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY item_no ORDER BY existing_stocks DESC) AS rn
    FROM source_inventory
)

SELECT
    md5(cast(coalesce(cast(item_no as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(warehouse_no as TEXT), '_dbt_utils_surrogate_key_null_') as TEXT)) AS inventory_key,
    item_no,
    warehouse_no,
    location_no,
    unit,
    existing_stocks,
    ma_item_no,
    item_name,
    item_spec,
    item_type,
    item_category,
    stock_unit,
    CURRENT_TIMESTAMP() AS _dbtloadedat
FROM inventory_with_ranking
WHERE rn = 1  -- 去重，每個料號只保留一筆記錄


    );
  
  