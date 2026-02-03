import json
import pandas as pd
import numpy as np
from faker import Faker
import boto3
from io import BytesIO
from datetime import datetime, timedelta
import random

fake = Faker(["zh_TW"])


class TiptopTransactionGenerator:
    def __init__(self, schema_path, s3_endpoint="http://localhost:8334"):
        with open(schema_path, "r", encoding="utf-8") as f:
            self.schemas = json.load(f)

        self.s3 = boto3.client(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id="admin",
            aws_secret_access_key="admin123",
            region_name="us-east-1",
        )
        self.bucket = "tiptop-raw"

        # 讀取主數據以供關聯
        self.items = self._read_from_s3("ima_file")
        self.vendors = self._read_from_s3("pmc_file")
        self.locations = self._read_from_s3("ime_file")

        self.start_date = datetime(2024, 1, 1)
        self.end_date = datetime(2025, 12, 31)

    def _read_from_s3(self, table_name):
        # 讀取主數據
        key = f"raw/v1/{table_name}/year=2026/month=01/data.parquet"
        resp = self.s3.get_object(Bucket=self.bucket, Key=key)
        return pd.read_parquet(BytesIO(resp["Body"].read()))

    def _push_to_s3(self, df, table_name, year=2025, month=12, batch_idx=None):
        buffer = BytesIO()
        df.to_parquet(buffer, index=False, compression="snappy")

        filename = "data.parquet" if batch_idx is None else f"data_batch_{batch_idx}.parquet"
        month_str = f"{month:02d}" if isinstance(month, int) else month
        key = f"raw/v1/{table_name}/year={year}/month={month_str}/{filename}"

        self.s3.put_object(Bucket=self.bucket, Key=key, Body=buffer.getvalue())
        print(f"✅ 已上傳 {table_name} 至 S3: {key} (共 {len(df)} 筆)")

    def generate_all(self, target_count=1000000):
        print(
            f"🚀 開始模擬大規模交易數據 (目標: {target_count} 筆, 跨距 {self.start_date.date()} ~ {self.end_date.date()})..."
        )

        total_generated = 0
        batch_size = 100000
        batch_counter = 1

        rms = self.items[self.items["ima08"] == "P"]
        fgs = self.items[self.items["ima08"] == "M"]
        vendor_ids = self.vendors["pmc01"].tolist()

        days_diff = (self.end_date - self.start_date).days

        while total_generated < target_count:
            transactions = []
            for _ in range(batch_size):
                curr_date = self.start_date + timedelta(days=random.randint(0, days_diff))
                scenario = random.random()
                if scenario < 0.3:
                    item = rms.sample(n=1).iloc[0]
                    transactions.append(
                        {
                            "tlf01": item["ima01"],
                            "tlf06": curr_date,
                            "tlf10": random.randint(100, 1000),
                            "tlf13": f"RC-{fake.bothify('??####')}",
                            "tlf061": "W01",
                            "tlf062": "L01",
                            "tlf19": "101",
                        }
                    )
                elif scenario < 0.8:
                    if random.random() > 0.5:
                        item = rms.sample(n=1).iloc[0]
                        transactions.append(
                            {
                                "tlf01": item["ima01"],
                                "tlf06": curr_date,
                                "tlf10": -random.randint(10, 50),
                                "tlf13": f"WO-{fake.bothify('??####')}",
                                "tlf061": "W01",
                                "tlf062": "L01",
                                "tlf19": "201",
                            }
                        )
                    else:
                        fg = fgs.sample(n=1).iloc[0]
                        transactions.append(
                            {
                                "tlf01": fg["ima01"],
                                "tlf06": curr_date,
                                "tlf10": random.randint(5, 20),
                                "tlf13": f"WO-{fake.bothify('??####')}",
                                "tlf061": "W03",
                                "tlf062": "L01",
                                "tlf19": "102",
                            }
                        )
                else:
                    fg = fgs.sample(n=1).iloc[0]
                    transactions.append(
                        {
                            "tlf01": fg["ima01"],
                            "tlf06": curr_date,
                            "tlf10": -random.randint(1, 10),
                            "tlf13": f"SO-{fake.bothify('??####')}",
                            "tlf061": "W03",
                            "tlf062": "L01",
                            "tlf19": "202",
                        }
                    )

            df_batch = pd.DataFrame(transactions)
            self._push_to_s3(
                df_batch, "tlf_file_large", year="2024_2025", month=0, batch_idx=batch_counter
            )

            total_generated += len(df_batch)
            batch_counter += 1
            print(f"進度: {total_generated}/{target_count}")

        return total_generated

        return total_generated

    def generate_balance(self, tlf_df):
        print("📊 正在結算最終庫存 (img_file)...")

        # 從 S3 讀取所有批次數據
        all_tlf = []
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix="raw/v1/tlf_file_large/"):
            if "Contents" in page:
                for obj in page["Contents"]:
                    if obj["Key"].endswith(".parquet"):
                        resp = self.s3.get_object(Bucket=self.bucket, Key=obj["Key"])
                        df = pd.read_parquet(BytesIO(resp["Body"].read()))
                        all_tlf.append(df)

        tlf_df = pd.concat(all_tlf, ignore_index=True)

        # 按料號、倉庫、儲位加總
        balance = tlf_df.groupby(["tlf01", "tlf061", "tlf062"])["tlf10"].sum().reset_index()
        balance.columns = ["img01", "img02", "img03", "img10"]
        balance["img04"] = "BATCH-001"  # 預設批號

        # 移除數量為 0 的記錄
        balance = balance[balance["img10"] != 0]

        self._push_to_s3(balance, "img_file")


if __name__ == "__main__":
    METADATA_PATH = "/home/daniel/ai-box/datalake-system/metadata/schema_registry.json"
    gen = TiptopTransactionGenerator(METADATA_PATH)
    gen.generate_all()
    gen.generate_balance(None)
    print("\n🎉 交易數據與庫存結算完成！")
