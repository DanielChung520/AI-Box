-- mart_shipping_wide.sql
-- 代碼功能說明: 出貨寬表 - 合併出貨頭檔、出貨明細、客戶主檔
-- 創建日期: 2026-02-13
-- 創建人: Daniel Chung

{{
    config(
        materialized='table',
        alias='mart_shipping_wide',
        pre_hook="CREATE SEQUENCE IF NOT EXISTS seq_mart_shipping"
    )
}}

-- 從 S3 Parquet 讀取出貨資料
WITH source_shipping AS (
    SELECT
        -- XMDG_T 出貨頭檔欄位
        XMDGENT AS ent,
        XMDGSITE AS site,
        XMDGDOCNO AS doc_no,
        XMDGDOCDT AS doc_date,
        XMDGSTUS AS status,
        XMDG002 AS sales_person,
        XMDG003 AS sales_dept,
        XMDG005 AS customer_no,
        XMDG028 AS expected_date,
        XMDG027 AS sales_category,

        -- XMDH_T 出貨明細欄位
        XMDHSEQ AS seq,
        XMDH001 AS order_no,
        XMDH002 AS so_line,
        XMDH003 AS order_line_sn,
        XMDH004 AS order_batch_seq,
        XMDHUD001 AS customer_po_no,
        XMDH006 AS item_no,
        XMDH016 AS request_qty,
        XMDH017 AS actual_qty,
        XMDH023 AS unit_price,

        -- OOEFT_T 客戶主檔欄位 (LEFT JOIN)
        ooef001 AS oo_customer_no,
        ooef011 AS customer_name,
        ooef017 AS customer_short_name,

        -- MA_T 物料主檔欄位 (LEFT JOIN)
        ma001 AS ma_item_no,
        ma002 AS item_name,
        ma003 AS item_spec
    FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/XMDG_T/year=*/month=*/data.parquet', hive_partitioning=true)
    INNER JOIN read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/XMDH_T/year=*/month=*/data.parquet', hive_partitioning=true)
        ON XMDGDOCNO = XMDHDOCNO
    LEFT JOIN (
        SELECT
            ooef001,
            ooef011,
            ooef017
        FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/OEEF_T/year=*/month=*/data.parquet', hive_partitioning=true)
    ) ON XMDG005 = ooef001
    LEFT JOIN (
        SELECT
            ma001,
            ma002,
            ma003
        FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/MA_T/year=*/month=*/data.parquet', hive_partitioning=true)
    ) ON XMDH006 = ma001
),

shipping_with_ranking AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY doc_no, seq ORDER BY actual_qty DESC) AS rn
    FROM source_shipping
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['doc_no', 'seq']) }} AS shipping_key,
    doc_no,
    doc_date,
    status,
    sales_person,
    sales_dept,
    customer_no,
    customer_name,
    customer_short_name,
    expected_date,
    sales_category,
    seq,
    order_no,
    so_line,
    customer_po_no,
    item_no,
    ma_item_no,
    item_name,
    item_spec,
    request_qty,
    actual_qty,
    unit_price,
    request_qty * unit_price AS total_amount,
    CURRENT_TIMESTAMP() AS _dbtloadedat
FROM shipping_with_ranking
WHERE rn = 1

{% if is_incremental() %}
WHERE _dbtloadedat > (SELECT MAX(_dbtloadedat) FROM {{ this }})
{% endif %}
