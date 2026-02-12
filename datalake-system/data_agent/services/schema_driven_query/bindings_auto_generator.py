# 代碼功能說明: Bindings 自動生成器
# 創建日期: 2026-02-12
# 創建人: Daniel Chung
# 用途: 自動生成 DUCKDB dialect mappings

"""Bindings Auto Generator

功能：
- 讀取現有 ORACLE bindings
- 自動生成 DUCKDB dialect mappings
- 更新 bindings.json
"""

import json
from pathlib import Path
from typing import Dict, Any


class BindingsAutoGenerator:
    """Bindings 自動生成器"""

    TABLE_S3_PATH = {
        "INAG_T": "s3://tiptop-raw/raw/v1/tiptop_jp/INAG_T/year=*/month=*/data.parquet",
        "SFAA_T": "s3://tiptop-raw/raw/v1/tiptop_jp/SFAA_T/year=*/month=*/data.parquet",
        "SFCA_T": "s3://tiptop-raw/raw/v1/tiptop_jp/SFCA_T/year=*/month=*/data.parquet",
        "SFCB_T": "s3://tiptop-raw/raw/v1/tiptop_jp/SFCB_T/year=*/month=*/data.parquet",
        "XMDG_T": "s3://tiptop-raw/raw/v1/tiptop_jp/XMDG_T/year=*/month=*/data.parquet",
        "XMDH_T": "s3://tiptop-raw/raw/v1/tiptop_jp/XMDH_T/year=*/month=*/data.parquet",
        "XMDT_T": "s3://tiptop-raw/raw/v1/tiptop_jp/XMDT_T/year=*/month=*/data.parquet",
        "XMDU_T": "s3://tiptop-raw/raw/v1/tiptop_jp/XMDU_T/year=*/month=*/data.parquet",
    }

    def __init__(self, bindings_path: str):
        self.bindings_path = Path(bindings_path)
        self.bindings_data = {}

    def load(self):
        """載入現有 bindings.json"""
        if self.bindings_path.exists():
            with open(self.bindings_path, "r", encoding="utf-8") as f:
                self.bindings_data = json.load(f)
        else:
            raise FileNotFoundError(f"Bindings file not found: {self.bindings_path}")

    def generate_duckdb_bindings(self) -> Dict[str, Any]:
        """生成 DUCKDB bindings"""
        if "bindings" not in self.bindings_data:
            raise ValueError("No bindings found in file")

        duckdb_bindings = {}

        for concept, mapping in self.bindings_data["bindings"].items():
            if "ORACLE" in mapping or "JP_TIPTOP_ERP" in mapping:
                oracle_mapping = mapping.get("ORACLE") or mapping.get("JP_TIPTOP_ERP")
                table = oracle_mapping.get("table", "")

                duckdb_bindings[concept] = {
                    "DUCKDB": {
                        "table": table,
                        "column": oracle_mapping.get("column", ""),
                        "aggregation": oracle_mapping.get("aggregation", "NONE"),
                        "operator": oracle_mapping.get("operator", "="),
                        "s3_path": self.TABLE_S3_PATH.get(table, ""),
                    }
                }

        return duckdb_bindings

    def update_bindings(self, output_path: str = None):
        """更新 bindings.json，新增 DUCKDB dialect"""
        duckdb_bindings = self.generate_duckdb_bindings()

        for concept, duckdb_mapping in duckdb_bindings.items():
            if concept in self.bindings_data["bindings"]:
                self.bindings_data["bindings"][concept]["DUCKDB"] = duckdb_mapping["DUCKDB"]
            else:
                self.bindings_data["bindings"][concept] = {"DUCKDB": duckdb_mapping["DUCKDB"]}

        self.bindings_data["datasource"]["dialect"] = "DUCKDB"

        output_path = output_path or str(self.bindings_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.bindings_data, f, ensure_ascii=False, indent=2)

        print(f"Bindings updated: {output_path}")

    def generate_report(self) -> Dict[str, Any]:
        """生成報告"""
        duckdb_bindings = self.generate_duckdb_bindings()

        report = {
            "total_concepts": len(self.bindings_data.get("bindings", {})),
            "duckdb_bindings": len(duckdb_bindings),
            "tables": {},
        }

        for concept, mapping in duckdb_bindings.items():
            table = mapping["DUCKDB"]["table"]
            if table not in report["tables"]:
                report["tables"][table] = []
            report["tables"][table].append(concept)

        return report


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description="Bindings Auto Generator")
    parser.add_argument("--input", "-i", required=True, help="Input bindings.json path")
    parser.add_argument("--output", "-o", help="Output path (default: overwrite input)")
    parser.add_argument("--report", action="store_true", help="Generate report only")

    args = parser.parse_args()

    generator = BindingsAutoGenerator(args.input)
    generator.load()

    if args.report:
        report = generator.generate_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        generator.update_bindings(args.output)
        report = generator.generate_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
