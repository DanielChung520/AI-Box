import pandas as pd
import boto3
from io import BytesIO
from datetime import datetime
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataIngestor")


class UniversalDataIngestor:
    """
    通用數據抽取與加載工具 (ETL)
    支援將客戶各類系統資料轉換為 Parquet 存入數據湖
    """

    def __init__(self, endpoint="http://localhost:8334", bucket="tiptop-raw"):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id="admin",
            aws_secret_access_key="admin123",
            region_name="us-east-1",
        )
        self.bucket = bucket

    def ingest_dataframe(self, df: pd.DataFrame, source_system: str, table_name: str):
        """
        核心方法：將任何 DataFrame 推送到數據湖
        """
        if df.empty:
            logger.warning(f"跳過空白數據: {table_name}")
            return

        now = datetime.now()
        # 建立結構化路徑：來源/版本/表名/時間分區
        key = f"raw/v1/{source_system}/{table_name}/year={now.year}/month={now.month:02d}/ingest_{now.strftime('%H%M%S')}.parquet"

        try:
            buffer = BytesIO()
            df.to_parquet(buffer, index=False, compression="snappy")
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=buffer.getvalue())
            logger.info(f"✅ [ETL 成功] 來源:{source_system} | 表:{table_name} | 路徑:{key}")
        except Exception as e:
            logger.error(f"❌ [ETL 失敗] {table_name}: {e}")

    def fetch_from_external_sql(self, connection_string, query):
        """
        【模擬功能】從客戶 SQL 數據庫抓取資料
        實際導入時會根據客戶 DB 類型 (Oracle, SQL Server, MySQL) 調用
        """
        logger.info(f"正在連線至外部系統抓取數據...")
        # 這裡未來會接 pd.read_sql(query, connection)
        pass


if __name__ == "__main__":
    ingestor = UniversalDataIngestor()

    # 範例：模擬從客戶 MES 系統抓取的即時工單狀態
    mes_data = pd.DataFrame(
        [
            {"wo_no": "WO-9901", "status": "Running", "progress": 85.5, "machine": "CNC-01"},
            {"wo_no": "WO-9902", "status": "Pending", "progress": 0, "machine": "CNC-02"},
        ]
    )

    print("🚀 啟動模擬 ETL 任務...")
    ingestor.ingest_dataframe(mes_data, "mes_system", "work_order_status")
