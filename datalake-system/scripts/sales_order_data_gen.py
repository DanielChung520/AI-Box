#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
銷售訂單模擬數據生成腳本

功能：
- 生成客戶主檔 (cmc_file)
- 生成訂單單頭/單身 (coptc_file, coptd_file)
- 生成訂價單 (prc_file)
- 使用 Faker 模擬 2 年數據（2024-2025）
- 料號使用現有 ima_file 主檔

使用方式：
    python scripts/sales_order_data_gen.py
    python scripts/sales_order_data_gen.py --tables cmc
    python scripts/sales_order_data_gen.py --tables coptc,coptd --year 2025
"""

import json
import argparse
import pandas as pd
import numpy as np
from faker import Faker
import boto3
from io import BytesIO
from datetime import datetime, timedelta
from pathlib import Path
import random
import sys

fake = Faker(["zh_TW"])

S3_ENDPOINT = "http://localhost:8334"
S3_ACCESS_KEY = "admin"
S3_SECRET_KEY = "admin123"
BUCKET = "tiptop-raw"
METADATA_PATH = "/home/daniel/ai-box/datalake-system/metadata/schema_registry.json"


class SalesOrderGenerator:
    def __init__(self, schema_path=METADATA_PATH, s3_endpoint=S3_ENDPOINT):
        with open(schema_path, "r", encoding="utf-8") as f:
            self.schemas = json.load(f)

        self.s3 = boto3.client(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name="us-east-1",
        )
        self.bucket = BUCKET

        self.start_date = datetime(2024, 1, 1)
        self.end_date = datetime(2025, 12, 31)
        self.days_diff = (self.end_date - self.start_date).days

        self.items = None
        self.load_items()

    def load_items(self):
        """從 S3 讀取現有料號主檔"""
        try:
            key = "raw/v1/ima_file/year=2026/month=01/data.parquet"
            resp = self.s3.get_object(Bucket=self.bucket, Key=key)
            self.items = pd.read_parquet(BytesIO(resp["Body"].read()))
            print(f"✅ 已載入料號主檔: {len(self.items)} 筆")
        except Exception as e:
            print(f"❌ 無法載入料號主檔: {e}")
            sys.exit(1)

    def _read_from_s3(self, table_name, year=2026, month=1):
        """從 S3 讀取數據"""
        key = f"raw/v1/{table_name}/year={year}/month={month:02d}/data.parquet"
        resp = self.s3.get_object(Bucket=self.bucket, Key=key)
        return pd.read_parquet(BytesIO(resp["Body"].read()))

    def _push_to_s3(self, df, table_name, year=2025, month=12, batch_idx=None):
        """上傳 Parquet 到 S3"""
        buffer = BytesIO()
        df.to_parquet(buffer, index=False, compression="snappy")

        if batch_idx is not None:
            filename = f"data_batch_{batch_idx}.parquet"
        else:
            filename = "data.parquet"

        month_str = f"{month:02d}" if isinstance(month, int) else month
        key = f"raw/v1/{table_name}/year={year}/month={month_str}/{filename}"

        self.s3.put_object(Bucket=self.bucket, Key=key, Body=buffer.getvalue())
        print(f"✅ 已上傳 {table_name} 至 S3: {key} (共 {len(df)} 筆)")

    def generate_customers(self):
        """生成客戶主檔 (cmc_file)"""
        schema = self.schemas["cmc_file"]
        data = []

        jp_case_customers = ["D003", "D005", "D006", "D010", "D032", "D048", "D055"]
        extra_customers = [f"D{random.randint(100, 999)}" for _ in range(8)]
        all_customers = list(set(jp_case_customers + extra_customers))

        for i, cust_id in enumerate(sorted(all_customers), 1):
            row = {col["id"]: "" for col in schema["columns"]}
            row["cmc01"] = cust_id
            row["cmc02"] = (
                f"{fake.company()}{fake.random_element(['', '股份有限公司', '有限公司', '工業'])}"
            )
            row["cmc03"] = fake.name()
            row["cmc08"] = fake.phone_number()
            data.append(row)

        df = pd.DataFrame(data)
        self._push_to_s3(df, "cmc_file", year=2026, month=1)
        return df

    def generate_orders(self, start_year=2024, end_year=2025, no_price_ratio=0.2):
        """生成訂單單頭 + 單身 (coptc_file + coptd_file)，按月分區

        Args:
            start_year: 起始年份
            end_year: 結束年份
            no_price_ratio: 多少比例的料號故意不給訂價（模擬「尚未在訂價單中」情境）
        """
        schema_coptc = self.schemas["coptc_file"]
        schema_coptd = self.schemas["coptd_file"]

        customers = self._read_from_s3("cmc_file")
        customer_ids = customers["cmc01"].tolist()
        item_ids = self.items["ima01"].tolist()

        orders_per_month = 20
        total_generated = 0

        # 隨機選擇 20% 的料號不給訂價
        items_with_pricing = set(random.sample(item_ids, int(len(item_ids) * (1 - no_price_ratio))))
        items_without_pricing = set(item_ids) - items_with_pricing

        print(
            f"📊 料號分配: {len(items_with_pricing)} 個有訂價, {len(items_without_pricing)} 個無訂價"
        )

        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                order_date_base = datetime(year, month, 1)

                if month == 12:
                    month_end = min(datetime(year + 1, 1, 1) - timedelta(days=1), self.end_date)
                else:
                    month_end = min(datetime(year, month + 1, 1) - timedelta(days=1), self.end_date)

                if year == 2025 and month == 12:
                    month_end = self.end_date

                coptc_data = []
                coptd_data = []
                batch_orders = []

                for _ in range(orders_per_month):
                    order_no = f"SO-{year}{month:02d}{random.randint(1000, 9999)}"
                    order_date = order_date_base + timedelta(
                        days=random.randint(0, (month_end - order_date_base).days)
                    )
                    ship_date = order_date + timedelta(days=random.randint(3, 14))

                    status = random.choices(["10", "20", "30"], weights=[0.4, 0.3, 0.3])[0]

                    coptc_row = {col["id"]: "" for col in schema_coptc["columns"]}
                    coptc_row["coptc01"] = order_no
                    coptc_row["coptc02"] = random.choice(customer_ids)
                    coptc_row["coptc03"] = order_date.strftime("%Y-%m-%d")
                    coptc_row["coptc04"] = ship_date.strftime("%Y-%m-%d")
                    coptc_row["coptc05"] = status
                    coptc_row["coptc06"] = fake.name()
                    coptc_data.append(coptc_row)
                    batch_orders.append(order_no)

                    num_lines = random.randint(2, 5)

                    # 確保部分料號故意不使用有訂價的料號
                    use_no_price_ratio = random.random()
                    if use_no_price_ratio < no_price_ratio * 0.5:
                        # 30% 的訂單故意選無訂價的料號
                        available_items = (
                            list(items_without_pricing) if items_without_pricing else item_ids
                        )
                    else:
                        available_items = item_ids

                    selected_items = random.sample(
                        available_items, min(num_lines, len(available_items))
                    )

                    for line_no, item_id in enumerate(selected_items, 1):
                        qty = random.randint(10, 500)
                        shipped_qty = random.randint(0, qty) if status != "10" else 0

                        coptd_row = {col["id"]: "" for col in schema_coptd["columns"]}
                        coptd_row["coptd01"] = order_no
                        coptd_row["coptd02"] = line_no
                        coptd_row["coptd04"] = item_id
                        coptd_row["coptd20"] = qty
                        coptd_row["coptd30"] = self._get_item_price(item_id)
                        coptd_row["coptd31"] = shipped_qty
                        coptd_row["coptd32"] = fake.bothify("???-####")
                        coptd_data.append(coptd_row)

                coptc_df = pd.DataFrame(coptc_data)
                coptd_df = pd.DataFrame(coptd_data)

                self._push_to_s3(coptc_df, "coptc_file", year=year, month=month)
                self._push_to_s3(coptd_df, "coptd_file", year=year, month=month)

                total_generated += len(coptc_data)
                print(f"  {year}-{month:02d}: {len(coptc_data)} 筆訂單")

        print(f"\n✅ 訂單生成完成: {total_generated} 筆")
        return coptc_df, coptd_df

    def _get_item_price(self, item_id):
        """根據料號類型返回單價"""
        if item_id.startswith("10-"):
            return round(random.uniform(500, 5000), 2)
        elif item_id.startswith("RM01") or item_id.startswith("RM02"):
            return round(random.uniform(50, 200), 2)
        else:
            return round(random.uniform(10, 150), 2)

    def generate_pricing(self, force_no_price_ratio=0.2):
        """生成訂價單 (prc_file)

        Args:
            force_no_price_ratio: 多少比例的料號故意不給訂價
        """
        schema = self.schemas["prc_file"]
        item_ids = self.items["ima01"].tolist()

        data = []
        num_prices_per_item = {}

        # 選擇要給訂價的料號（80%）
        items_with_pricing = set(
            random.sample(item_ids, int(len(item_ids) * (1 - force_no_price_ratio)))
        )

        print(f"📊 訂價單生成: {len(items_with_pricing)}/{len(item_ids)} 個料號會有訂價")

        for item_id in item_ids:
            if item_id not in items_with_pricing:
                continue  # 跳過不給訂價的料號

            num_prices = random.randint(3, 8)
            num_prices_per_item[item_id] = num_prices

            base_price = self._get_item_price(item_id)

            for i in range(num_prices):
                price_date = self.start_date + timedelta(days=random.randint(0, self.days_diff))
                approved = random.random() < 0.8
                approved_date = (
                    price_date - timedelta(days=random.randint(1, 30)) if approved else None
                )

                row = {col["id"]: "" for col in schema["columns"]}
                row["prc01"] = item_id
                row["prc02"] = round(base_price * random.uniform(0.85, 1.15), 2)
                row["prc03"] = approved_date.strftime("%Y-%m-%d") if approved_date else ""
                row["prc04"] = "Y" if approved else "N"
                row["prc05"] = price_date.strftime("%Y-%m-%d")
                row["prc06"] = (price_date + timedelta(days=random.randint(180, 365))).strftime(
                    "%Y-%m-%d"
                )
                data.append(row)

        df = pd.DataFrame(data)
        self._push_to_s3(df, "prc_file", year=2026, month=1)

        return df, num_prices_per_item

    def generate_all(self):
        """生成所有數據"""
        print("🚀 開始生成銷售訂單模擬數據（2 年）...")
        print(f"   時間範圍: {self.start_date.date()} ~ {self.end_date.date()}")
        print()

        print("📦 生成客戶主檔 (cmc_file)...")
        self.generate_customers()
        print()

        print("📦 生成訂單數據 (coptc_file, coptd_file)...")
        self.generate_orders(2024, 2025)
        print()

        print("📦 生成訂價單 (prc_file)...")
        self.generate_pricing()
        print()

        print("🎉 銷售訂單模擬數據生成完成！")


def main():
    parser = argparse.ArgumentParser(description="生成銷售訂單模擬數據")
    parser.add_argument(
        "--tables", type=str, help="指定生成的表，用逗號分隔，如: cmc,coptc,coptd,prc"
    )
    parser.add_argument("--year", type=int, help="指定生成訂單的年份（用於 coptc, coptd）")

    args = parser.parse_args()

    gen = SalesOrderGenerator()

    if args.tables:
        tables = [t.strip() for t in args.tables.split(",")]

        if "cmc" in tables:
            print("📦 生成客戶主檔...")
            gen.generate_customers()

        if "coptc" in tables or "coptd" in tables:
            if "coptc" in tables and "coptd" not in tables:
                print("⚠️  coptc 需要 coptd，同時生成...")
            start_year = args.year if args.year else 2024
            end_year = args.year if args.year else 2025
            print(f"📦 生成訂單數據 ({start_year}-{end_year})...")
            gen.generate_orders(start_year, end_year)

        if "prc" in tables:
            print("📦 生成訂價單...")
            gen.generate_pricing()
    else:
        gen.generate_all()


if __name__ == "__main__":
    main()
