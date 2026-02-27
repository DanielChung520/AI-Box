-- Mart: 出貨彙總表
-- 按客戶、時間預先聚合
-- 建立日期: 2026-02-14

CREATE TABLE IF NOT EXISTS mart_shipping_summary AS
SELECT 
    SUBSTR(XMDGDOCDT, 1, 6) AS year_month,
    XMDG001 AS customer_id,
    XMDG002 AS sales_id,
    XMDG003 AS dept_id,
    XMDGSTUS AS status,
    COUNT(*) AS shipping_count,
    SUM(XMDH016) AS total_qty
FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/XMDG_T/year=*/month=*/data.parquet')
LEFT JOIN read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/XMDH_T/year=*/month=*/data.parquet')
    ON XMDGDOCNO = XMDH001
GROUP BY SUBSTR(XMDGDOCDT, 1, 6), XMDG001, XMDG002, XMDG003, XMDGSTUS;

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_mart_shp_ym ON mart_shipping_summary(year_month);
CREATE INDEX IF NOT EXISTS idx_mart_shp_cust ON mart_shipping_summary(customer_id);