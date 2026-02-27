-- mart_price_wide.sql
-- 代碼功能說明: 售價寬表 - 合併售價審核頭檔、明細檔、客戶主檔、料號主檔
-- 創建日期: 2026-02-15
-- 創建人: Daniel Chung



-- 從 S3 Parquet 讀取售價資料
WITH source_price AS (
    SELECT
        -- XMDT_T 售價審核頭檔欄位
        XMDTENT AS ent,
        XMDTSITE AS site,
        XMDTDOCNO AS price_doc_no,
        XMDTDOCDT AS price_doc_date,
        XMDTSTUS AS price_status,
        XMDT002 AS customer_no,
        XMDT003 AS currency,
        XMDT004 AS effective_date,
        XMDT005 AS expiration_date,

        -- XMDU_T 售價審核明細欄位
        XMDUSEQ AS price_seq,
        XMDU001 AS item_no,
        XMDU002 AS unit_price,
        XMDU003 AS minimum_qty,
        XMDU004 AS discount_rate,

        -- OOEFT_T 客戶主檔欄位 (LEFT JOIN)
        ooef001 AS oo_customer_no,
        ooef011 AS customer_name,

        -- MA_T 物料主檔欄位 (LEFT JOIN)
        ma001 AS ma_item_no,
        ma002 AS item_name,
        ma003 AS item_spec,
        ma025 AS item_category,
        ma026 AS item_unit
    FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/XMDT_T/year=*/month=*/data.parquet', hive_partitioning=true)
    INNER JOIN read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/XMDU_T/year=*/month=*/data.parquet', hive_partitioning=true)
        ON XMDTDOCNO = XMDUDOCNO
    LEFT JOIN (
        SELECT
            ooef001,
            ooef011
        FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/OEEF_T/year=*/month=*/data.parquet', hive_partitioning=true)
    ) ON XMDT002 = ooef001
    LEFT JOIN (
        SELECT
            ma001,
            ma002,
            ma003,
            ma025,
            ma026
        FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/MA_T/year=*/month=*/data.parquet', hive_partitioning=true)
    ) ON XMDU001 = ma001
),

price_with_ranking AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY item_no, customer_no ORDER BY price_doc_date DESC) AS rn
    FROM source_price
)

SELECT
    md5(cast(coalesce(cast(price_doc_no as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(price_seq as TEXT), '_dbt_utils_surrogate_key_null_') as TEXT)) AS price_key,
    price_doc_no,
    price_doc_date,
    price_status,
    customer_no,
    customer_name,
    currency,
    effective_date,
    expiration_date,
    price_seq,
    item_no,
    ma_item_no,
    item_name,
    item_spec,
    item_category,
    item_unit,
    unit_price,
    minimum_qty,
    discount_rate,
    -- Check if price is valid (not expired)
    CASE 
        WHEN expiration_date >= CURRENT_DATE THEN 'Y'
        WHEN expiration_date < CURRENT_DATE THEN 'N'
        ELSE 'U'
    END AS is_valid,
    CURRENT_TIMESTAMP() AS _dbtloadedat
FROM price_with_ranking
WHERE rn = 1

