# 代碼功能說明: DataLake 數據存取服務
# 創建日期: 2026-01-29
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-29 UTC+8

"""DataLake 數據存取服務（DataLakeClient）"""

import logging
from io import BytesIO
from typing import Any, Dict, Optional

import boto3
import pandas as pd

from dashboard.config import DEFAULT_BUCKET, SEAWEEDFS_ENDPOINT

logger = logging.getLogger("DataLakeAccess")


class DataLakeClient:
    """DataLake 客戶端，從 SeaweedFS S3 讀取 Parquet 數據"""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        bucket: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint or SEAWEEDFS_ENDPOINT
        self.bucket = bucket or DEFAULT_BUCKET
        self.s3 = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id="admin",
            aws_secret_access_key="admin123",
            region_name="us-east-1",
        )

    def query_table(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        is_large: bool = False,
        years: Optional[list] = None,
    ) -> pd.DataFrame:
        """從 DataLake 讀取資料表（支援單一檔案或多分片目錄）"""
        if is_large:
            prefixes = [f"raw/v1/{table_name}/year=2024_2025/month=00/"]
        elif years:
            prefixes = [f"raw/v1/{table_name}/year={y}/month=01/" for y in years]
            prefixes.extend([f"raw/v1/{table_name}/year={y}/month=02/" for y in years])
            prefixes.extend([f"raw/v1/{table_name}/year={y}/month=03/" for y in years])
            prefixes.extend([f"raw/v1/{table_name}/year={y}/month=04/" for y in years])
            prefixes.extend([f"raw/v1/{table_name}/year={y}/month=05/" for y in years])
            prefixes.extend([f"raw/v1/{table_name}/year={y}/month=06/" for y in years])
            prefixes.extend([f"raw/v1/{table_name}/year={y}/month=07/" for y in years])
            prefixes.extend([f"raw/v1/{table_name}/year={y}/month=08/" for y in years])
            prefixes.extend([f"raw/v1/{table_name}/year={y}/month=09/" for y in years])
            prefixes.extend([f"raw/v1/{table_name}/year={y}/month=10/" for y in years])
            prefixes.extend([f"raw/v1/{table_name}/year={y}/month=11/" for y in years])
            prefixes.extend([f"raw/v1/{table_name}/year={y}/month=12/" for y in years])
        else:
            prefixes = [f"raw/v1/{table_name}/year=2026/month=01/"]

        try:
            dataframes: list[pd.DataFrame] = []
            for prefix in prefixes:
                try:
                    paginator = self.s3.get_paginator("list_objects_v2")
                    pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

                    for page in pages:
                        if "Contents" in page:
                            for obj in page["Contents"]:
                                if obj["Key"].endswith(".parquet"):
                                    resp = self.s3.get_object(Bucket=self.bucket, Key=obj["Key"])
                                    df = pd.read_parquet(BytesIO(resp["Body"].read()))
                                    dataframes.append(df)
                except Exception as e:
                    logger.warning(f"讀取 {prefix} 失敗: {e}")
                    continue

            if not dataframes:
                logger.warning(f"在所有路徑都找不到 {table_name} 的數據")
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
        """獲取當前庫存狀態（關聯品名與單位）"""
        prefixes = [
            "raw/v1/img_file/year=2026/month=01/",
            "raw/v1/img_file/year=2025/month=12/",
        ]

        df = pd.DataFrame()
        for prefix in prefixes:
            df = self._query_by_prefix(prefix, "img_file")
            if not df.empty:
                break

        if df.empty:
            logger.warning("img_file 在所有路徑都找不到")
            return df

        if item_id:
            df = df[df["img01"] == item_id]

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

            dataframes: list[pd.DataFrame] = []
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
        """獲取採購歷史（關聯單頭單身）"""
        pmn = self.query_table("pmn_file")
        pmm = self.query_table("pmm_file")

        po_full = pd.merge(pmn, pmm, left_on="pmn01", right_on="pmm01", how="left")

        if vendor_id:
            po_full = po_full[po_full["pmm04"] == vendor_id]

        return po_full

    def get_purchase_data(self) -> Dict[str, pd.DataFrame]:
        """獲取完整的採購相關數據"""
        pmm = self.query_table("pmm_file")
        pmn = self.query_table("pmn_file")
        rvb = self.query_table("rvb_file")
        vendors = self.query_table("pmc_file")

        return {
            "pmm_file": pmm,
            "pmn_file": pmn,
            "rvb_file": rvb,
            "pmc_file": vendors,
        }

    def get_order_data(self) -> Dict[str, pd.DataFrame]:
        """獲取完整的訂單相關數據"""
        coptc = self.query_table("coptc_file")
        coptd = self.query_table("coptd_file")
        prc = self.query_table("prc_file")
        customers = self.query_table("cmc_file")

        return {
            "coptc_file": coptc,
            "coptd_file": coptd,
            "prc_file": prc,
            "cmc_file": customers,
        }
