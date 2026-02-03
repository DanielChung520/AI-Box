import boto3
import pandas as pd
from io import BytesIO
from typing import Optional, List, Dict
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataLakeAccess")


class DataLakeClient:
    def __init__(self, endpoint="http://localhost:8334", bucket="tiptop-raw"):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id="admin",
            aws_secret_access_key="admin123",
            region_name="us-east-1",
        )
        self.bucket = bucket

    def query_table(
        self, table_name: str, filters: Optional[Dict] = None, is_large=False
    ) -> pd.DataFrame:
        """
        從 DataLake 讀取資料表（支援單一檔案或多分片目錄）
        """
        if is_large:
            prefix = f"raw/v1/{table_name}/year=2024_2025/month=00/"
        else:
            prefix = f"raw/v1/{table_name}/year=2026/month=01/"

        try:
            # 1. 列出目錄下所有物件
            paginator = self.s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

            dataframes = []
            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        if obj["Key"].endswith(".parquet"):
                            resp = self.s3.get_object(Bucket=self.bucket, Key=obj["Key"])
                            df = pd.read_parquet(BytesIO(resp["Body"].read()))
                            dataframes.append(df)

            if not dataframes:
                logger.warning(f"在 {prefix} 找不到數據")
                return pd.DataFrame()

            full_df = pd.concat(dataframes, ignore_index=True)

            if filters:
                for col, val in filters.items():
                    if col in full_df.columns:
                        full_df = full_df[full_df[col] == val]

            return full_df
        except Exception as e:
            logger.error(f"讀取 {table_name} 失敗: {e}")
            return pd.DataFrame()

    def get_inventory_status(self, item_id: Optional[str] = None) -> pd.DataFrame:
        """
        【物料管理員工具】獲取當前庫存狀態
        """
        # 嘗試多個路徑查找 img_file
        prefixes_to_try = [
            f"raw/v1/img_file/year=2026/month=01/",
            f"raw/v1/img_file/year=2025/month=12/",
        ]

        df = pd.DataFrame()
        for prefix in prefixes_to_try:
            df = self._query_by_prefix(prefix, "img_file")
            if not df.empty:
                break

        if df.empty:
            logger.warning("img_file 在所有路徑都找不到")
            return df

        if item_id:
            df = df[df["img01"] == item_id]

        # 關聯品名與單位資訊
        items_df = self.query_table("ima_file")
        if items_df.empty:
            return df

        result = pd.merge(
            df,
            items_df[["ima01", "ima02", "ima021", "ima25"]],
            left_on="img01",
            right_on="ima01",
            how="left",
        )
        return result

    def _query_by_prefix(self, prefix: str, table_name: str) -> pd.DataFrame:
        """根據前綴查詢數據"""
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

            dataframes = []
            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        if obj["Key"].endswith(".parquet"):
                            resp = self.s3.get_object(Bucket=self.bucket, Key=obj["Key"])
                            df = pd.read_parquet(BytesIO(resp["Body"].read()))
                            dataframes.append(df)

            if not dataframes:
                return pd.DataFrame()

            return pd.concat(dataframes, ignore_index=True)
        except Exception as e:
            logger.error(f"讀取 {table_name} 失敗 (prefix: {prefix}): {e}")
            return pd.DataFrame()

    def get_purchase_history(self, vendor_id: Optional[str] = None) -> pd.DataFrame:
        """
        【採購管理員工具】獲取採購歷史
        """
        pmn = self.query_table("pmn_file")
        pmm = self.query_table("pmm_file")

        # 關聯單頭單身
        po_full = pd.merge(pmn, pmm, left_on="pmn01", right_on="pmm01", how="left")

        if vendor_id:
            po_full = po_full[po_full["pmm04"] == vendor_id]

        return po_full


if __name__ == "__main__":
    # 簡單測試
    client = DataLakeClient()
    print("測試：查詢庫存總覽...")
    inv = client.get_inventory_status()
    print(inv.head())
