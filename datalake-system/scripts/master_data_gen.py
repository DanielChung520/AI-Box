import json
import pandas as pd
import numpy as np
from faker import Faker
import boto3
from io import BytesIO
from pathlib import Path
from datetime import datetime

# 初始化 Faker
fake = Faker(["zh_TW"])


class TiptopMasterGenerator:
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

    def _push_to_s3(self, df, table_name):
        buffer = BytesIO()
        df.to_parquet(buffer, index=False)
        key = f"raw/v1/{table_name}/year={datetime.now().year}/month={datetime.now().month:02d}/data.parquet"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=buffer.getvalue())
        print(f"✅ 已上傳 {table_name} 至 S3: {key} (共 {len(df)} 筆)")

    def generate_warehouses(self):
        schema = self.schemas["imd_file"]
        data = []
        wh_names = ["原料倉", "半成品倉", "成品倉", "報廢倉", "外協倉"]
        for i in range(1, 6):
            row = {col["id"]: "" for col in schema["columns"]}
            row["imd01"] = f"W{i:02d}"
            row["imd02"] = wh_names[i - 1]
            data.append(row)

        df = pd.DataFrame(data)
        self._push_to_s3(df, "imd_file")
        return df

    def generate_locations(self, wh_df):
        schema = self.schemas["ime_file"]
        data = []
        for wh_id in wh_df["imd01"]:
            for i in range(1, fake.random_int(min=5, max=10)):
                row = {col["id"]: "" for col in schema["columns"]}
                row["ime01"] = wh_id
                row["ime02"] = f"L{i:02d}"
                row["ime03"] = f"{wh_id}排-{i:02d}架"
                data.append(row)

        df = pd.DataFrame(data)
        self._push_to_s3(df, "ime_file")
        return df

    def generate_vendors(self):
        schema = self.schemas["pmc_file"]
        data = []
        v_types = ["模具廠", "沖壓廠", "壓鑄廠", "表面處理", "緊固件商"]
        for i in range(1, 16):
            row = {col["id"]: "" for col in schema["columns"]}
            row["pmc01"] = f"VND{i:03d}"
            row["pmc03"] = fake.company() + v_types[fake.random_int(0, 4)]
            row["pmc24"] = fake.name()
            row["pmc08"] = fake.phone_number()
            data.append(row)

        df = pd.DataFrame(data)
        self._push_to_s3(df, "pmc_file")
        return df

    def generate_items(self):
        schema = self.schemas["ima_file"]
        data = []

        fg_names = ["伺服器機殼", "工業電腦外殼", "壓鑄鋁散熱模組", "精密沖壓支架", "鈑金屏蔽罩"]
        rm_categories = {
            "RM01": "鋁合金錠",
            "RM02": "不鏽鋼板",
            "RM03": "鍍鋅鋼捲",
            "RM04": "精密螺絲",
            "RM05": "散熱膏",
            "RM06": "烤漆塗料",
            "RM07": "包裝紙箱",
            "RM08": "防震膠墊",
            "RM09": "銅質墊片",
            "RM10": "塑料件",
        }

        # 1. 生成成品 (20個)
        for i in range(1, 21):
            row = {col["id"]: "" for col in schema["columns"]}
            row["ima01"] = f"10-{i:04d}"
            row["ima02"] = fake.random_element(fg_names) + f"-{fake.bothify('??')}"
            row["ima021"] = f"SPEC-{fake.bothify('####')}"
            row["ima08"] = "M"
            row["ima25"] = "PCS"
            data.append(row)

        # 2. 生成原物料 (100個)
        for cat_code, cat_name in rm_categories.items():
            for i in range(1, 11):
                row = {col["id"]: "" for col in schema["columns"]}
                row["ima01"] = f"{cat_code}-{i:03d}"
                row["ima02"] = f"{cat_name}-{fake.word()}"
                row["ima021"] = f"TYPE-{fake.bothify('???')}"
                row["ima08"] = "P"
                row["ima25"] = fake.random_element(["KG", "PCS", "ROLL", "SET"])
                data.append(row)

        df = pd.DataFrame(data)
        self._push_to_s3(df, "ima_file")
        return df


if __name__ == "__main__":
    METADATA_PATH = "/home/daniel/ai-box/datalake-system/metadata/schema_registry.json"
    gen = TiptopMasterGenerator(METADATA_PATH)

    print("🚀 重新生成主數據 (標準 Tiptop 欄位)...")
    wh_df = gen.generate_warehouses()
    gen.generate_locations(wh_df)
    gen.generate_vendors()
    gen.generate_items()
    print("\n🎉 主數據更新完成！")
