
  
    
    

    create  table
      "tiptop_jp"."main_mart"."mart_inventory_summary__dbt_tmp"
  
    as (
      -- Mart: 庫存彙總表
-- 按倉庫、料號、儲位預先聚合
-- 建立日期: 2026-02-14

CREATE TABLE IF NOT EXISTS mart_inventory_summary AS
SELECT 
    INAG004 AS warehouse_no,
    INAG001 AS item_no,
    INAG005 AS location_no,
    INAG007 AS unit,
    INAGSITE AS site,
    SUM(INAG008) AS total_qty,
    COUNT(*) AS record_count
FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/INAG_T/year=*/month=*/data.parquet')
GROUP BY INAG004, INAG001, INAG005, INAG007, INAGSITE;

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_mart_inv_warehouse ON mart_inventory_summary(warehouse_no);
CREATE INDEX IF NOT EXISTS idx_mart_inv_item ON mart_inventory_summary(item_no);
CREATE INDEX IF NOT EXISTS idx_mart_inv_warehouse_item ON mart_inventory_summary(warehouse_no, item_no);
    );
  
  