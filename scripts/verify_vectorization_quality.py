#!/usr/bin/env python3
# 代碼功能說明: 向量化質量檢驗腳本
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""向量化質量檢驗腳本

使用系統服務檢查向量化數據質量，包括：
1. 文本規範化情況（驗證無全角字符）
2. 向量質量（維度、數量、相似度）
3. 元數據完整性

使用方法:
    python scripts/verify_vectorization_quality.py <file_id> [--user-id <user_id>]

範例:
    python scripts/verify_vectorization_quality.py 149aee1a-89da-4b07-a83c-634fb29246e2
"""

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加載環境變數
from dotenv import load_dotenv

env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

# 導入系統服務
from services.api.services.vector_store_service import get_vector_store_service


def check_text_normalization(text: str) -> Dict[str, Any]:
    """檢查文本規範化情況

    Args:
        text: 文本內容

    Returns:
        規範化檢查結果
    """
    result = {
        "has_fullwidth_chars": False,
        "fullwidth_chars": [],
        "has_control_chars": False,
        "control_chars": [],
        "normalized": True,
    }

    # 檢查全角 ASCII 字符（字母、數字、空格）
    for char in text:
        # 檢查是否為全角 ASCII 字符
        if ord(char) >= 0xFF01 and ord(char) <= 0xFF5E:
            result["has_fullwidth_chars"] = True
            if char not in result["fullwidth_chars"]:
                result["fullwidth_chars"].append(char)

        # 檢查控制字符（除了換行符和制表符）
        if unicodedata.category(char)[0] == "C" and char not in ["\n", "\t", "\r"]:
            result["has_control_chars"] = True
            if char not in result["control_chars"]:
                result["control_chars"].append(repr(char))

    result["normalized"] = not (result["has_fullwidth_chars"] or result["has_control_chars"])

    return result


def verify_vectorization_quality(file_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """驗證向量化質量

    Args:
        file_id: 文件 ID
        user_id: 用戶 ID（可選）

    Returns:
        質量檢驗報告
    """
    print(f"[驗證] 開始檢驗文件向量化質量: {file_id}")

    # 使用系統服務獲取向量數據
    vector_store_service = get_vector_store_service()
    vectors = vector_store_service.get_vectors_by_file_id(
        file_id=file_id, user_id=user_id, limit=None
    )

    if not vectors:
        return {
            "file_id": file_id,
            "status": "error",
            "message": "未找到向量數據",
            "vector_count": 0,
        }

    print(f"[驗證] 找到 {len(vectors)} 個向量")

    # 檢驗結果
    report: Dict[str, Any] = {
        "file_id": file_id,
        "vector_count": len(vectors),
        "text_quality": {
            "total_chunks": 0,
            "normalized_count": 0,
            "not_normalized_count": 0,
            "issues": [],
        },
        "vector_quality": {
            "expected_dimension": 768,
            "dimensions": [],
            "missing_embeddings": 0,
        },
        "metadata_quality": {
            "missing_chunk_index": 0,
            "missing_file_id": 0,
            "missing_user_id": 0,
        },
    }

    # 檢驗每個向量
    for i, vector in enumerate(vectors):
        # 1. 文本規範化檢驗
        document = vector.get("document", "")
        if document:
            report["text_quality"]["total_chunks"] += 1
            normalization_check = check_text_normalization(document)
            if normalization_check["normalized"]:
                report["text_quality"]["normalized_count"] += 1
            else:
                report["text_quality"]["not_normalized_count"] += 1
                report["text_quality"]["issues"].append(
                    {
                        "chunk_index": i,
                        "file_id": file_id,
                        "issue": "未規範化",
                        "details": normalization_check,
                    }
                )

        # 2. 向量質量檢驗（如果有 embedding 數據）
        embedding = vector.get("embedding")
        if embedding:
            dim = len(embedding) if isinstance(embedding, list) else 0
            report["vector_quality"]["dimensions"].append(dim)
            if dim != report["vector_quality"]["expected_dimension"]:
                report["text_quality"]["issues"].append(
                    {
                        "chunk_index": i,
                        "file_id": file_id,
                        "issue": f"向量維度不正確: {dim} (期望: {report['vector_quality']['expected_dimension']})",
                    }
                )
        else:
            report["vector_quality"]["missing_embeddings"] += 1

        # 3. 元數據完整性檢驗
        metadata = vector.get("metadata", {})
        if "chunk_index" not in metadata:
            report["metadata_quality"]["missing_chunk_index"] += 1
        if "file_id" not in metadata:
            report["metadata_quality"]["missing_file_id"] += 1
        if user_id and "user_id" not in metadata:
            report["metadata_quality"]["missing_user_id"] += 1

    # 計算統計信息
    if report["vector_quality"]["dimensions"]:
        dimensions = report["vector_quality"]["dimensions"]
        report["vector_quality"]["min_dimension"] = min(dimensions)
        report["vector_quality"]["max_dimension"] = max(dimensions)
        report["vector_quality"]["avg_dimension"] = sum(dimensions) / len(dimensions)
        report["vector_quality"]["consistent_dimension"] = (
            min(dimensions) == max(dimensions) == report["vector_quality"]["expected_dimension"]
        )

    # 總體評估
    issues_count = len(report["text_quality"]["issues"])
    report["overall_quality"] = "good" if issues_count == 0 else "needs_attention"
    report["summary"] = {
        "vectors_found": len(vectors),
        "normalized_text_ratio": (
            report["text_quality"]["normalized_count"] / report["text_quality"]["total_chunks"]
            if report["text_quality"]["total_chunks"] > 0
            else 0
        ),
        "issues_count": issues_count,
    }

    return report


def generate_markdown_report(report: Dict[str, Any], output_file: Optional[str] = None) -> str:
    """生成 Markdown 格式報告

    Args:
        report: 檢驗報告
        output_file: 輸出文件路徑（可選）

    Returns:
        Markdown 報告內容
    """
    md_lines = [
        "# 向量化質量檢驗報告",
        "",
        f"**文件 ID**: `{report['file_id']}`",
        f"**檢驗時間**: {report.get('timestamp', 'N/A')}",
        "",
        "## 總體評估",
        "",
        f"- **狀態**: {report['overall_quality']}",
        f"- **向量數量**: {report['vector_count']}",
        f"- **文本規範化比例**: {report['summary']['normalized_text_ratio']:.2%}",
        f"- **問題數量**: {report['summary']['issues_count']}",
        "",
        "## 文本質量",
        "",
        f"- **總 chunks**: {report['text_quality']['total_chunks']}",
        f"- **已規範化**: {report['text_quality']['normalized_count']}",
        f"- **未規範化**: {report['text_quality']['not_normalized_count']}",
        "",
    ]

    if report["text_quality"]["issues"]:
        md_lines.extend(
            [
                "### 問題列表",
                "",
            ]
        )
        for issue in report["text_quality"]["issues"][:10]:  # 只顯示前 10 個
            md_lines.append(
                f"- Chunk {issue['chunk_index']}: {issue['issue']} - {issue.get('details', {})}"
            )
        if len(report["text_quality"]["issues"]) > 10:
            md_lines.append(f"\n*還有 {len(report['text_quality']['issues']) - 10} 個問題未顯示*")

    md_lines.extend(
        [
            "",
            "## 向量質量",
            "",
            f"- **期望維度**: {report['vector_quality']['expected_dimension']}",
        ]
    )

    if report["vector_quality"]["dimensions"]:
        md_lines.extend(
            [
                f"- **實際維度範圍**: {report['vector_quality']['min_dimension']} - {report['vector_quality']['max_dimension']}",
                f"- **平均維度**: {report['vector_quality']['avg_dimension']:.2f}",
                f"- **維度一致性**: {'✅ 是' if report['vector_quality']['consistent_dimension'] else '❌ 否'}",
            ]
        )
    else:
        md_lines.append("- **Embedding 數據**: 未包含在查詢結果中")

    md_lines.extend(
        [
            "",
            "## 元數據質量",
            "",
            f"- **缺少 chunk_index**: {report['metadata_quality']['missing_chunk_index']}",
            f"- **缺少 file_id**: {report['metadata_quality']['missing_file_id']}",
            f"- **缺少 user_id**: {report['metadata_quality']['missing_user_id']}",
            "",
        ]
    )

    md_content = "\n".join(md_lines)

    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"[報告] Markdown 報告已保存到: {output_file}")

    return md_content


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="向量化質量檢驗腳本")
    parser.add_argument("file_id", help="文件 ID")
    parser.add_argument("--user-id", help="用戶 ID（可選）")
    parser.add_argument(
        "--output-dir",
        default="logs/vectorization_quality",
        help="輸出目錄（默認: logs/vectorization_quality）",
    )

    args = parser.parse_args()

    # 執行檢驗
    report = verify_vectorization_quality(file_id=args.file_id, user_id=args.user_id)

    # 添加時間戳
    report["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 保存 JSON 報告
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_file = output_dir / f"quality_report_{args.file_id}_{int(datetime.now().timestamp())}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[報告] JSON 報告已保存到: {json_file}")

    # 生成 Markdown 報告
    md_file = output_dir / f"quality_report_{args.file_id}_{int(datetime.now().timestamp())}.md"
    generate_markdown_report(report, str(md_file))

    # 打印摘要
    print("\n" + "=" * 60)
    print("檢驗摘要")
    print("=" * 60)
    print(f"文件 ID: {report['file_id']}")
    print(f"向量數量: {report['vector_count']}")
    print(f"總體質量: {report['overall_quality']}")
    print(f"文本規範化比例: {report['summary']['normalized_text_ratio']:.2%}")
    print(f"問題數量: {report['summary']['issues_count']}")
    print("=" * 60)

    # 如果有問題，返回非零退出碼
    if report["overall_quality"] != "good":
        sys.exit(1)


if __name__ == "__main__":
    main()
