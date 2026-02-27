-- Mart: 工單彙總表
-- 按時間、工作站預先聚合
-- 建立日期: 2026-02-14

CREATE TABLE IF NOT EXISTS mart_work_order_summary AS
SELECT 
    SUBSTR(SFCAENT, 1, 6) AS year_month,
    SFCA004 AS mo_doc_no,
    SFCA001 AS mo_line,
    SFCA003 AS plan_qty,
    SFCA004 AS complete_qty,
    SFCA005 AS status,
    SFCA006 AS workstation
FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/SFCA_T/year=*/month=*/data.parquet');

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_mart_wo_ym ON mart_work_order_summary(year_month);
CREATE INDEX IF NOT EXISTS idx_mart_wo_ws ON mart_work_order_summary(workstation);