-- mart_work_order_wide.sql
-- 代碼功能說明: 工單寬表 - 合併工單頭檔、客戶主檔、物料主檔
-- 創建日期: 2026-02-13
-- 創建人: Daniel Chung



-- 從 S3 Parquet 讀取工單資料
WITH source_work_order AS (
    SELECT
        -- SFAA_T 工單頭檔欄位
        SFAAENT AS ent,
        SFAASITE AS site,
        SFAA010 AS item_no,
        SFAA056 AS scrap_qty,
        SFAA022 AS so_order,
        SFAA023 AS so_line,
        SFAA024 AS order_line_sn,
        SFAA025 AS order_batch_seq,
        SFAA009 AS customer_no,
        SFAA034 AS location_no,
        SFAA035 AS warehouse_no,
        SFAASTUS AS status,

        -- OOEFT_T 客戶主檔欄位 (LEFT JOIN)
        ooef001 AS oo_customer_no,
        ooef011 AS customer_name,
        ooef017 AS customer_short_name,

        -- MA_T 物料主檔欄位 (LEFT JOIN)
        ma001 AS ma_item_no,
        ma002 AS item_name,
        ma003 AS item_spec
    FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/SFAA_T/year=*/month=*/data.parquet', hive_partitioning=true)
    LEFT JOIN (
        SELECT
            ooef001,
            ooef011,
            ooef017
        FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/OEEF_T/year=*/month=*/data.parquet', hive_partitioning=true)
    ) ON SFAA009 = ooef001
    LEFT JOIN (
        SELECT
            ma001,
            ma002,
            ma003
        FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/MA_T/year=*/month=*/data.parquet', hive_partitioning=true)
    ) ON SFAA010 = ma001
),

work_order_with_ranking AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY item_no ORDER BY status DESC) AS rn
    FROM source_work_order
)

SELECT
    md5(cast(coalesce(cast(item_no as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(customer_no as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(status as TEXT), '_dbt_utils_surrogate_key_null_') as TEXT)) AS work_order_key,
    item_no,
    customer_no,
    customer_name,
    customer_short_name,
    ma_item_no,
    item_name,
    item_spec,
    warehouse_no,
    location_no,
    status,
    scrap_qty,
    so_order,
    so_line,
    CURRENT_TIMESTAMP() AS _dbtloadedat
FROM work_order_with_ranking
WHERE rn = 1

