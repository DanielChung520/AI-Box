#!/usr/bin/env python3
# 代碼功能說明: 圖譜提取模板驗證腳本
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""圖譜提取模板驗證腳本

功能：
1. 使用系統服務檢查 Ontology 選擇
2. 使用系統服務檢查 Ontology 加載
3. 使用系統服務檢查 Prompt 模板生成
4. 驗證 JSON Schema
5. 生成驗證報告

使用方法:
    python scripts/verify_kg_templates.py <file_id>
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

import importlib.util
from pathlib import Path as PathLib

from kag.kag_schema_manager import OntologyManager
from kag.ontology_selector import OntologySelector
from services.api.processors.parser_factory import ParserFactory
from services.api.services.file_metadata_service import get_metadata_service
from services.api.services.ontology_store_service import get_ontology_store_service

# 直接导入 LocalFileStorage，绕过 __init__.py 中的 boto3 依赖
project_root_storage = PathLib(__file__).parent.parent
spec_storage = importlib.util.spec_from_file_location(
    "local_file_storage", project_root_storage / "storage" / "file_storage.py"
)
module_storage = importlib.util.module_from_spec(spec_storage)
spec_storage.loader.exec_module(module_storage)
LocalFileStorage = module_storage.LocalFileStorage
from system.infra.config.config import get_config_section


def get_file_content_preview(file_id: str, max_chars: int = 1000) -> str:
    """獲取文件內容預覽（使用系統服務）"""
    try:
        metadata_service = get_metadata_service()
        file_metadata = metadata_service.get(file_id)
        if not file_metadata:
            return ""

        config = get_config_section("file_upload", default={}) or {}
        storage_path = config.get("storage_path", "./data/datasets/files")
        storage = LocalFileStorage(storage_path=storage_path, enable_encryption=False)
        file_content_bytes = storage.read_file(
            file_id=file_id,
            task_id=file_metadata.task_id,
            metadata_storage_path=file_metadata.storage_path,
        )

        if file_content_bytes is None:
            return ""

        parser_factory = ParserFactory()
        parser = parser_factory.get_parser(
            mime_type=file_metadata.file_type,
            file_path=file_metadata.filename,
        )

        if file_metadata.file_type == "application/pdf":
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file_content_bytes)
                tmp_path = tmp_file.name

            try:
                parse_result = parser.parse(tmp_path)
                text = parse_result.get("text", "")
                return text[:max_chars]
            finally:
                Path(tmp_path).unlink()
        else:
            text = file_content_bytes.decode("utf-8", errors="ignore")
            return text[:max_chars]

    except Exception as e:
        print(f"⚠️  獲取文件內容預覽失敗: {e}")
        return ""


def verify_ontology_selection(file_id: str) -> Dict[str, Any]:
    """驗證 Ontology 選擇（使用系統服務）"""
    print("\n[1] 驗證 Ontology 選擇...")

    result: Dict[str, Any] = {
        "verified": False,
        "selection_result": {},
        "errors": [],
    }

    try:
        metadata_service = get_metadata_service()
        file_metadata = metadata_service.get(file_id)
        if not file_metadata:
            result["errors"].append("無法獲取文件元數據")
            return result

        file_content_preview = get_file_content_preview(file_id, max_chars=1000)

        selector = OntologySelector()
        selection = selector.select_auto(
            file_name=file_metadata.filename,
            file_content=file_content_preview,
            file_metadata={"file_type": file_metadata.file_type},
        )

        result["selection_result"] = selection
        result["verified"] = True

        print("  ✅ Ontology 選擇成功")
        print(f"     Base: {selection.get('base', 'N/A')}")
        print(f"     Domain: {selection.get('domain', [])}")
        print(f"     Major: {selection.get('major', [])}")
        print(f"     選擇方法: {selection.get('selection_method', 'N/A')}")

    except Exception as e:
        result["errors"].append(f"Ontology 選擇驗證失敗: {str(e)}")
        print(f"  ❌ Ontology 選擇驗證失敗: {e}")

    return result


def verify_ontology_loading(selection_result: Dict[str, Any]) -> Dict[str, Any]:
    """驗證 Ontology 加載（使用系統服務）"""
    print("\n[2] 驗證 Ontology 加載...")

    result: Dict[str, Any] = {
        "verified": False,
        "base_ontology": None,
        "domain_ontologies": [],
        "major_ontology": None,
        "merged_ontology": None,
        "errors": [],
    }

    try:
        store_service = get_ontology_store_service()

        base_name = selection_result.get("base", "")
        if base_name:
            base_ontology = store_service.get_ontology_with_priority(
                name=base_name, type="base", tenant_id=None
            )
            if base_ontology:
                result["base_ontology"] = {
                    "name": base_ontology.name,
                    "type": base_ontology.type,
                    "entity_classes_count": len(base_ontology.entity_classes or []),
                    "object_properties_count": len(base_ontology.object_properties or []),
                }
                print(f"  ✅ Base Ontology 加載成功: {base_name}")
                print(f"     實體類數量: {result['base_ontology']['entity_classes_count']}")
                print(f"     關係類型數量: {result['base_ontology']['object_properties_count']}")

        domain_files = selection_result.get("domain", [])
        for domain_file in domain_files:
            try:
                domain_ontology = store_service.get_ontology_with_priority(
                    name=domain_file, type="domain", tenant_id=None
                )
                if domain_ontology:
                    result["domain_ontologies"].append(
                        {
                            "name": domain_ontology.name,
                            "type": domain_ontology.type,
                            "entity_classes_count": len(domain_ontology.entity_classes or []),
                            "object_properties_count": len(domain_ontology.object_properties or []),
                        }
                    )
                    print(f"  ✅ Domain Ontology 加載成功: {domain_file}")
            except Exception as e:
                result["errors"].append(f"加載 Domain Ontology {domain_file} 失敗: {str(e)}")

        major_file = (
            selection_result.get("major", [None])[0] if selection_result.get("major") else None
        )
        if major_file:
            try:
                major_ontology = store_service.get_ontology_with_priority(
                    name=major_file, type="major", tenant_id=None
                )
                if major_ontology:
                    result["major_ontology"] = {
                        "name": major_ontology.name,
                        "type": major_ontology.type,
                        "entity_classes_count": len(major_ontology.entity_classes or []),
                        "object_properties_count": len(major_ontology.object_properties or []),
                    }
                    print(f"  ✅ Major Ontology 加載成功: {major_file}")
            except Exception as e:
                result["errors"].append(f"加載 Major Ontology {major_file} 失敗: {str(e)}")

        # 合併 Ontology
        manager = OntologyManager(tenant_id=None)
        if base_name:
            base_ont = store_service.get_ontology_with_priority(
                name=base_name, type="base", tenant_id=None
            )
            if base_ont:
                domain_onts = []
                for d in domain_files:
                    dom_ont = store_service.get_ontology_with_priority(
                        name=d, type="domain", tenant_id=None
                    )
                    if dom_ont:
                        domain_onts.append(dom_ont)

                major_ont = None
                if major_file:
                    major_ont = store_service.get_ontology_with_priority(
                        name=major_file, type="major", tenant_id=None
                    )

                if domain_onts or major_ont:
                    # 使用 store_service 的 merge_ontologies 方法
                    merged_rules = store_service.merge_ontologies(
                        domain_files=domain_files,
                        major_file=major_file,
                        tenant_id=None,
                    )

                    if merged_rules:
                        result["merged_ontology"] = {
                            "entity_classes_count": len(merged_rules.get("entity_classes", [])),
                            "object_properties_count": len(
                                merged_rules.get("object_properties", [])
                            ),
                        }
                        result["verified"] = True
                        print("  ✅ Ontology 合併成功")
                        print(f"     合併後實體類數量: {result['merged_ontology']['entity_classes_count']}")
                        print(
                            f"     合併後關係類型數量: {result['merged_ontology']['object_properties_count']}"
                        )

    except Exception as e:
        result["errors"].append(f"Ontology 加載驗證失敗: {str(e)}")
        print(f"  ❌ Ontology 加載驗證失敗: {e}")

    return result


def verify_prompt_generation(merged_ontology: Dict[str, Any], sample_text: str) -> Dict[str, Any]:
    """驗證 Prompt 模板生成（使用系統服務）"""
    print("\n[3] 驗證 Prompt 模板生成...")

    result: Dict[str, Any] = {
        "verified": False,
        "kg_extraction_prompt": "",
        "errors": [],
    }

    try:
        manager = OntologyManager(tenant_id=None)

        if merged_ontology:
            kg_prompt = manager.generate_prompt(
                text_chunk=sample_text,
                ontology_rules=merged_ontology,
                include_owl_constraints=True,
            )
            result["kg_extraction_prompt"] = kg_prompt
            result["verified"] = True
            print("  ✅ KG Extraction Prompt 生成成功")
            print(f"     Prompt 長度: {len(kg_prompt)} 字符")
            print(f"     Prompt 預覽: {kg_prompt[:200]}...")

            entity_classes_in_prompt = any(
                ec.get("name", "") in kg_prompt if isinstance(ec, dict) else str(ec) in kg_prompt
                for ec in merged_ontology.get("entity_classes", [])
            )
            relation_types_in_prompt = any(
                rt.get("name", "") in kg_prompt if isinstance(rt, dict) else str(rt) in kg_prompt
                for rt in merged_ontology.get("object_properties", [])
            ) or any(rt in kg_prompt for rt in merged_ontology.get("relationship_types", []))

            if entity_classes_in_prompt:
                print("  ✅ Prompt 包含實體類定義")
            else:
                print("  ⚠️  Prompt 可能未包含實體類定義")
                result["errors"].append("Prompt 可能未包含實體類定義")

            if relation_types_in_prompt:
                print("  ✅ Prompt 包含關係類型定義")
            else:
                print("  ⚠️  Prompt 可能未包含關係類型定義")
                result["errors"].append("Prompt 可能未包含關係類型定義")

    except Exception as e:
        result["errors"].append(f"Prompt 模板生成驗證失敗: {str(e)}")
        print(f"  ❌ Prompt 模板生成驗證失敗: {e}")

    return result


def verify_json_schema() -> Dict[str, Any]:
    """驗證 JSON Schema（檢查系統代碼）"""
    print("\n[4] 驗證 JSON Schema...")

    result: Dict[str, Any] = {
        "verified": False,
        "ner_schema": {},
        "re_schema": {},
        "rt_schema": {},
        "errors": [],
    }

    try:
        from genai.api.services.ner_service import OllamaNERModel
        from genai.api.services.re_service import OllamaREModel
        from genai.api.services.rt_service import OllamaRTModel

        ner_model = OllamaNERModel(model_name="test")
        ner_prompt = ner_model._prompt_template

        if "JSON" in ner_prompt or "json" in ner_prompt.lower():
            result["ner_schema"]["format_specified"] = True
            print("  ✅ NER Prompt 指定了 JSON 格式")
        else:
            result["ner_schema"]["format_specified"] = False
            result["errors"].append("NER Prompt 未指定 JSON 格式")

        re_model = OllamaREModel(model_name="test")
        re_prompt = re_model._prompt_template

        if "JSON" in re_prompt or "json" in re_prompt.lower():
            result["re_schema"]["format_specified"] = True
            print("  ✅ RE Prompt 指定了 JSON 格式")
        else:
            result["re_schema"]["format_specified"] = False
            result["errors"].append("RE Prompt 未指定 JSON 格式")

        rt_model = OllamaRTModel(model_name="test")
        rt_prompt = rt_model._prompt_template

        if "JSON" in rt_prompt or "json" in rt_prompt.lower():
            result["rt_schema"]["format_specified"] = True
            print("  ✅ RT Prompt 指定了 JSON 格式")
        else:
            result["rt_schema"]["format_specified"] = False
            result["errors"].append("RT Prompt 未指定 JSON 格式")

        ner_fields = ["text", "label", "confidence"]
        for field in ner_fields:
            if field in ner_prompt.lower():
                result["ner_schema"].setdefault("fields", []).append(field)

        re_fields = ["subject", "object", "relation", "confidence"]
        for field in re_fields:
            if field in re_prompt.lower():
                result["re_schema"].setdefault("fields", []).append(field)

        rt_fields = ["relation", "type", "confidence"]
        for field in rt_fields:
            if field in rt_prompt.lower():
                result["rt_schema"].setdefault("fields", []).append(field)

        result["verified"] = len(result["errors"]) == 0

    except Exception as e:
        result["errors"].append(f"JSON Schema 驗證失敗: {str(e)}")
        print(f"  ❌ JSON Schema 驗證失敗: {e}")

    return result


def generate_report(
    file_id: str,
    ontology_selection: Dict[str, Any],
    ontology_loading: Dict[str, Any],
    prompt_generation: Dict[str, Any],
    json_schema: Dict[str, Any],
) -> Dict[str, Any]:
    """生成驗證報告"""
    timestamp = int(time.time())
    report_dir = project_root / "logs" / "kg_templates"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_data = {
        "file_id": file_id,
        "timestamp": timestamp,
        "verification_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ontology_selection": ontology_selection,
        "ontology_loading": ontology_loading,
        "prompt_generation": prompt_generation,
        "json_schema": json_schema,
        "summary": {
            "ontology_selection_verified": ontology_selection.get("verified", False),
            "ontology_loading_verified": ontology_loading.get("verified", False),
            "prompt_generation_verified": prompt_generation.get("verified", False),
            "json_schema_verified": json_schema.get("verified", False),
            "total_errors": len(ontology_selection.get("errors", []))
            + len(ontology_loading.get("errors", []))
            + len(prompt_generation.get("errors", []))
            + len(json_schema.get("errors", [])),
        },
    }

    json_file = report_dir / f"verify_report_{file_id}_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    markdown_file = report_dir / f"verify_report_{file_id}_{timestamp}.md"
    with open(markdown_file, "w", encoding="utf-8") as f:
        f.write("# 圖譜提取模板驗證報告\n\n")
        f.write(f"**文件 ID**: `{file_id}`\n")
        f.write(f"**驗證時間**: {report_data['verification_time']}\n\n")
        f.write("## 驗證摘要\n\n")
        summary = report_data["summary"]
        f.write(f"- Ontology 選擇: {'✅ 通過' if summary['ontology_selection_verified'] else '❌ 失敗'}\n")
        f.write(f"- Ontology 加載: {'✅ 通過' if summary['ontology_loading_verified'] else '❌ 失敗'}\n")
        f.write(f"- Prompt 模板生成: {'✅ 通過' if summary['prompt_generation_verified'] else '❌ 失敗'}\n")
        f.write(f"- JSON Schema: {'✅ 通過' if summary['json_schema_verified'] else '❌ 失敗'}\n")
        f.write(f"- 總錯誤數: {summary['total_errors']}\n\n")

    print(f"\n[報告] JSON 報告已保存到: {json_file}")
    print(f"[報告] Markdown 報告已保存到: {markdown_file}")

    return report_data


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("使用方法: python scripts/verify_kg_templates.py <file_id>")
        sys.exit(1)

    file_id = sys.argv[1]

    print("=" * 80)
    print("圖譜提取模板驗證")
    print("=" * 80)
    print(f"文件 ID: {file_id}\n")

    sample_text = get_file_content_preview(file_id, max_chars=500)
    if not sample_text:
        print("⚠️  無法獲取文件內容預覽，將使用空文本")
        sample_text = ""

    ontology_selection = verify_ontology_selection(file_id)
    selection_result = ontology_selection.get("selection_result", {})
    ontology_loading = verify_ontology_loading(selection_result)

    merged_ontology_rules = None
    if ontology_loading.get("verified"):
        try:
            store_service = get_ontology_store_service()
            base_name = selection_result.get("base", "")
            domain_files = selection_result.get("domain", [])
            major_file = (
                selection_result.get("major", [None])[0] if selection_result.get("major") else None
            )

            if base_name:
                merged_ontology_rules = store_service.merge_ontologies(
                    domain_files=domain_files,
                    major_file=major_file,
                    tenant_id=None,
                )
        except Exception as e:
            print(f"⚠️  獲取合併後 Ontology 規則失敗: {e}")

    prompt_generation = verify_prompt_generation(merged_ontology_rules or {}, sample_text)

    json_schema = verify_json_schema()
    report_data = generate_report(
        file_id, ontology_selection, ontology_loading, prompt_generation, json_schema
    )

    print("\n" + "=" * 80)
    print("驗證摘要")
    print("=" * 80)
    summary = report_data["summary"]
    print(f"Ontology 選擇: {'✅ 通過' if summary['ontology_selection_verified'] else '❌ 失敗'}")
    print(f"Ontology 加載: {'✅ 通過' if summary['ontology_loading_verified'] else '❌ 失敗'}")
    print(f"Prompt 模板生成: {'✅ 通過' if summary['prompt_generation_verified'] else '❌ 失敗'}")
    print(f"JSON Schema: {'✅ 通過' if summary['json_schema_verified'] else '❌ 失敗'}")
    print(f"總錯誤數: {summary['total_errors']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
