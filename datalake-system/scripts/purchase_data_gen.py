#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
採購單據模擬數據生成腳本

功能：
- 生成採購單頭檔 (pmm_file)
- 生成採購單身檔 (pmn_file)
- 生成收料單身檔 (rvb_file)
- 使用 Faker 模擬 2 年數據（2024-2025）
- 料號使用現有 ima_file 主檔
- 供應商使用現有 pmc_file 主檔

使用方式：
    python scripts/purchase_data_gen.py
    python scripts/purchase_data_gen.py --tables pmm,pmn,rvb --year 2025
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


class PurchaseDataGenerator:
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
        self.vendors = None
        self.load_master_data()

    def load_master_data(self):
        """從 S3 讀取主數據"""
        try:
            items_key = "raw/v1/ima_file/year=2026/month=01/data.parquet"
            resp = self.s3.get_object(Bucket=self.bucket, Key=items_key)
            self.items = pd.read_parquet(BytesIO(resp["Body"].read()))
            print(f"✅ 已載入料號主檔: {len(self.items)} 筆")

            vendors_key = "raw/v1/pmc_file/year=2026/month=01/data.parquet"
            resp = self.s3.get_object(Bucket=self.bucket, Key=vendors_key)
            self.vendors = pd.read_parquet(BytesIO(resp["Body"].read()))
            print(f"✅ 已載入供應商主檔: {len(self.vendors)} 筆")
        except Exception as e:
            print(f"❌ 無法載入主數據: {e}")
            sys.exit(1)

    def _push_to_s3(self, df, table_name, year=2025, month=12):
        """上傳 Parquet 到 S3"""
        buffer = BytesIO()
        df.to_parquet(buffer, index=False, compression="snappy")

        month_str = f"{month:02d}"
        key = f"raw/v1/{table_name}/year={year}/month={month_str}/data.parquet"

        self.s3.put_object(Bucket=self.bucket, Key=key, Body=buffer.getvalue())
        print(f"✅ 已上傳 {table_name} 至 S3: {key} (共 {len(df)} 筆)")

    def generate_purchase_orders(self, start_year=2024, end_year=2025):
        """生成採購單頭 + 單身，按月分區

        Args:
            start_year: 起始年份
            end_year: 結束年份
        """
        schema_pmm = self.schemas["pmm_file"]
        schema_pmn = self.schemas["pmn_file"]

        vendor_ids = self.vendors["pmc01"].tolist() if not self.vendors.empty else []
        item_ids = self.items["ima01"].tolist() if not self.items.empty else []

        if not vendor_ids:
            print("❌ 無供應商數據，無法生成採購單")
            return None, None

        if not item_ids:
            print("❌ 無料號數據，無法生成採購單")
            return None, None

        orders_per_month = 15
        total_generated = 0

        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                order_date_base = datetime(year, month, 1)

                if month == 12:
                    month_end = min(datetime(year + 1, 1, 1) - timedelta(days=1), self.end_date)
                else:
                    month_end = min(datetime(year, month + 1, 1) - timedelta(days=1), self.end_date)

                if year == 2025 and month == 12:
                    month_end = self.end_date

                pmm_data = []
                pmn_data = []
                batch_orders = []

                for _ in range(orders_per_month):
                    order_no = f"PO-{year}{month:02d}{random.randint(1000, 9999)}"
                    order_date = order_date_base + timedelta(
                        days=random.randint(0, (month_end - order_date_base).days)
                    )
                    expected_date = order_date + timedelta(days=random.randint(7, 30))

                    pmm_row = {col["id"]: "" for col in schema_pmm["columns"]}
                    pmm_row["pmm01"] = order_no
                    pmm_row["pmm02"] = order_date.strftime("%Y-%m-%d")
                    pmm_row["pmm04"] = random.choice(vendor_ids)
                    pmm_row["pmm09"] = fake.name()
                    pmm_data.append(pmm_row)
                    batch_orders.append(order_no)

                    num_lines = random.randint(2, 6)

                    selected_items = random.sample(item_ids, min(num_lines, len(item_ids)))

                    for line_no, item_id in enumerate(selected_items, 1):
                        qty = random.randint(50, 500)
                        received_qty = random.randint(0, qty)

                        pmn_row = {col["id"]: "" for col in schema_pmn["columns"]}
                        pmn_row["pmn01"] = order_no
                        pmn_row["pmn02"] = line_no
                        pmn_row["pmn04"] = item_id
                        pmn_row["pmn20"] = qty
                        pmn_row["pmn31"] = received_qty
                        pmn_row["pmn33"] = expected_date.strftime("%Y-%m-%d")
                        pmn_data.append(pmn_row)

                pmm_df = pd.DataFrame(pmm_data)
                pmn_df = pd.DataFrame(pmn_data)

                self._push_to_s3(pmm_df, "pmm_file", year=year, month=month)
                self._push_to_s3(pmn_df, "pmn_file", year=year, month=month)

                total_generated += len(pmm_data)
                print(f"  {year}-{month:02d}: {len(pmm_data)} 筆採購單")

        print(f"\n✅ 採購單生成完成: {total_generated} 筆")
        return pmm_df, pmn_df

    def generate_receiving_reports(self, start_year=2024, end_year=2025):
        """生成收料單身檔 (rvb_file)，基於已生成的採購單

        Args:
            start_year: 起始年份
            end_year: 結束年份
        """
        schema_rvb = self.schemas["rvb_file"]

        all_pmn_data = []

        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                try:
                    key = f"raw/v1/pmn_file/year={year}/month={month:02d}/data.parquet"
                    resp = self.s3.get_object(Bucket=self.bucket, Key=key)
                    df = pd.read_parquet(BytesIO(resp["Body"].read()))
                    all_pmn_data.append(df)
                except Exception:
                    continue

        if not all_pmn_data:
            print("❌ 無採購單身數據，無法生成收料單")
            return None

        pmn_all = pd.concat(all_pmn_data, ignore_index=True)
        rvb_data = []

        for _, row in pmn_all.iterrows():
            if random.random() < 0.7:
                received_qty = row.get("pmn31", 0) or 0
                if received_qty > 0:
                    rvb_row = {col["id"]: "" for col in schema_rvb["columns"]}
                    rvb_row["rvb01"] = f"RC-{row['pmn01'][3:]}"
                    rvb_row["rvb05"] = row["pmn04"]
                    rvb_row["rvb07"] = row["pmn01"]
                    rvb_row["rvb33"] = received_qty
                    rvb_data.append(rvb_row)

        rvb_df = pd.DataFrame(rvb_data)

        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                month_data = rvb_df.copy()
                month_data["year"] = pd.to_datetime(pmn_all["pmn33"], errors="coerce").dt.year
                month_data["month"] = pd.to_datetime(pmn_all["pmn33"], errors="coerce").dt.month

                month_rvb = month_data[
                    (month_data["year"] == year) & (month_data["month"] == month)
                ].drop(columns=["year", "month"])

                if not month_rvb.empty:
                    self._push_to_s3(month_rvb, "rvb_file", year=year, month=month)

        print(f"\n✅ 收料單生成完成: {len(rvb_df)} 筆")
        return rvb_df

    def generate_all(self):
        """生成所有採購相關數據"""
        print("🚀 開始生成採購單據模擬數據（2 年）...")
        print(f"   時間範圍: {self.start_date.date()} ~ {self.end_date.date()}")
        print()

        print("📦 生成採購單數據 (pmm_file, pmn_file)...")
        self.generate_purchase_orders(2024, 2025)
        print()

        print("📦 生成收料單數據 (rvb_file)...")
        self.generate_receiving_reports(2024, 2025)
        print()

        print("🎉 採購單據模擬數據生成完成！")


def main():
    parser = argparse.ArgumentParser(description="生成採購單據模擬數據")
    parser.add_argument("--tables", type=str, help="指定生成的表，用逗號分隔，如: pmm,pmn,rvb")
    parser.add_argument("--year", type=int, help="指定生成年份（用於 pmm, pmn, rvb）")

    args = parser.parse_args()

    gen = PurchaseDataGenerator(METADATA_PATH, S3_ENDPOINT)

    if args.tables:
        tables = [t.strip() for t in args.tables.split(",")]
        start_year = args.year if args.year else 2024
        end_year = args.year if args.year else 2025

        if "pmm" in tables or "pmn" in tables:
            if "pmm" in tables and "pmn" not in tables:
                print("⚠️  pmm 需要 pmn，同時生成...")
            print(f"📦 生成採購單數據 ({start_year}-{end_year})...")
            gen.generate_purchase_orders(start_year, end_year)

        if "rvb" in tables:
            print(f"📦 生成收料單數據 ({start_year}-{end_year})...")
            gen.generate_receiving_reports(start_year, end_year)
    else:
        gen.generate_all()


if __name__ == "__main__":
    main()
