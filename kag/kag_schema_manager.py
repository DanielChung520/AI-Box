"""
知識圖譜 Schema 管理器
功能：負責載入、合併 Ontology JSON 文件，並建立運行時驗證規則
創建日期：2025-01-27
創建人：Daniel Chung
最後修改日期：2025-12-10
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator

# 1. 儲存所有 Ontology 規則的動態容器 (全局變數)
# LangChain Agent 將在運行時填充這個容器
ONTOLOGY_RULES: Dict[str, Any] = {
    "entity_classes": [],  # 所有實體名稱的列表
    "relationship_types": [],  # 所有關係名稱的列表
    "owl_domain_range": {},  # 儲存 OWL (Domain, Range) 約束的字典
}


class OntologyManager:
    """
    負責載入、合併 Ontology JSON 文件，並建立運行時驗證規則。
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        初始化 Ontology 管理器

        :param base_path: Ontology 文件所在目錄路徑，如果為 None 則使用默認路徑 (kag/ontology/)
        """
        if base_path is None:
            # 獲取當前文件所在目錄，然後指向 ontology 子目錄
            current_file = Path(__file__).resolve()
            base_path = str(current_file.parent / "ontology")
        self.base_path = base_path
        self.loaded_ontologies: Dict[str, Any] = {}

    def _load_json(self, filename: str) -> Dict[str, Any]:
        """從指定路徑載入單一 JSON 檔案。"""
        file_path = os.path.join(self.base_path, filename)
        try:
            # 檢查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(
                    f"Ontology 文件未找到: {filename}. "
                    f"請確保您的 JSON 檔案存在於 {self.base_path} 目錄中。"
                )

            # 檢查文件是否為空
            if os.path.getsize(file_path) == 0:
                raise ValueError(
                    f"Ontology 文件為空: {filename}. "
                    f"請確保文件包含有效的 JSON 內容。"
                )

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not data:
                    raise ValueError(f"Ontology 文件 {filename} 解析後為空。")
                return data
        except FileNotFoundError:
            raise
        except ValueError:
            # 重新拋出 ValueError，保持原始異常類型
            raise
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Ontology 文件 {filename} JSON 格式錯誤: {e}. "
                f"請檢查文件格式是否正確。"
            )
        except Exception as e:
            raise RuntimeError(f"載入 Ontology 文件 {filename} 時發生錯誤: {e}")

    def merge_ontologies(
        self, domain_files: List[str], task_file: Optional[str] = None
    ):
        """
        核心合併邏輯：載入 Base, Domain, Task 層次，並更新全局規則容器。

        :param domain_files: 領域層 Ontology 檔案列表 (e.g., ['enterprise-otg.json'])
        :param task_file: 專業層 Ontology 檔案 (e.g., 'manufacture-otg.json')
        """

        # 清空容器，準備新的提取任務
        global ONTOLOGY_RULES
        ONTOLOGY_RULES = {
            "entity_classes": [],
            "relationship_types": [],
            "owl_domain_range": {},
        }

        # 步驟 1: 載入基礎 Ontology (Base Layer)
        base_ontology = self._load_json("base.json")
        all_modules = [base_ontology]

        # 步驟 2: 載入領域 Ontology (Domain Layer)
        for filename in domain_files:
            all_modules.append(self._load_json(filename))

        # 步驟 3: 載入專業 Ontology (Task Layer)
        if task_file:
            all_modules.append(self._load_json(task_file))

        # 步驟 4: 合併規則並填充全局容器
        all_entities = set()

        for module in all_modules:
            # 合併實體類別
            if "entity_classes" in module:
                for entity in module["entity_classes"]:
                    all_entities.add(entity["name"])

            # 合併物件屬性 (Object Properties) 和 OWL 約束
            if "object_properties" in module:
                for prop in module["object_properties"]:
                    rel_name = prop["name"]

                    # 加入關係名稱列表
                    ONTOLOGY_RULES["relationship_types"].append(rel_name)

                    # 建立 OWL Domain/Range 約束
                    if rel_name not in ONTOLOGY_RULES["owl_domain_range"]:
                        ONTOLOGY_RULES["owl_domain_range"][rel_name] = []

                    # 建立 (Domain Type, Range Type) 元組
                    for domain_type in prop["domain"]:
                        for range_type in prop["range"]:
                            ONTOLOGY_RULES["owl_domain_range"][rel_name].append(
                                (domain_type, range_type)
                            )

        # 最終填充實體列表
        ONTOLOGY_RULES["entity_classes"] = list(all_entities)
        ONTOLOGY_RULES["relationship_types"] = list(
            set(ONTOLOGY_RULES["relationship_types"])
        )  # 去重

        print(
            f"Ontology 合併完成。總實體數: {len(ONTOLOGY_RULES['entity_classes'])}，總關係數: {len(ONTOLOGY_RULES['relationship_types'])}"
        )
        return ONTOLOGY_RULES

    def load_prompt_template(self) -> Dict[str, Any]:
        """
        載入 Prompt-Template.json 模板文件

        :return: 提示詞模板字典
        """
        return self._load_json("Prompt-Template.json")

    def generate_prompt(
        self,
        text_chunk: str,
        ontology_rules: Optional[Dict[str, Any]] = None,
        include_owl_constraints: bool = True,
    ) -> str:
        """
        根據合併後的 Ontology 規則生成提示詞

        :param text_chunk: 待分析的文本片段
        :param ontology_rules: 合併後的 Ontology 規則（如果為 None，使用全局 ONTOLOGY_RULES）
        :param include_owl_constraints: 是否包含 OWL Domain/Range 約束說明
        :return: 生成的提示詞字符串
        """
        if ontology_rules is None:
            global ONTOLOGY_RULES
            ontology_rules = ONTOLOGY_RULES

        # 檢查 Ontology 規則是否已初始化
        # 使用 or 運算符：如果 entity_classes 或 relationship_types 任一為空，則報錯
        entity_classes = ontology_rules.get("entity_classes")
        relationship_types = ontology_rules.get("relationship_types")
        if not entity_classes or not relationship_types:
            raise RuntimeError(
                "Ontology 規則未初始化。請先調用 merge_ontologies() 方法載入並合併 Ontology。"
            )

        # 載入提示詞模板
        template = self.load_prompt_template()
        instruction = template.get("instruction_template", [])

        # 生成實體列表字符串
        entity_list = self._format_entity_list(ontology_rules["entity_classes"])

        # 生成關係列表字符串
        rel_list = self._format_relationship_list(ontology_rules["relationship_types"])

        # 生成 OWL Domain/Range 約束說明
        owl_constraints = ""
        if include_owl_constraints and ontology_rules.get("owl_domain_range"):
            owl_constraints = self._format_owl_constraints(
                ontology_rules["owl_domain_range"]
            )

        # 生成 JSON Schema
        json_schema = json.dumps(KnowledgeGraph.schema(), indent=2, ensure_ascii=False)

        # 組合提示詞模板
        prompt_lines = []
        for line in instruction:
            # 替換佔位符
            line = line.replace("[INJECT_ENTITY_LIST]", entity_list)
            line = line.replace("[INJECT_RELATIONSHIP_LIST]", rel_list)
            line = line.replace("[INJECT_JSON_SCHEMA]", json_schema)
            line = line.replace("[TEXT_CHUNK]", text_chunk)

            # 如果包含 OWL 約束，在相應位置插入
            if include_owl_constraints and "### 3. OWL Domain/Range 規則" in line:
                prompt_lines.append(line)
                if owl_constraints:
                    prompt_lines.append(owl_constraints)
                continue

            prompt_lines.append(line)

        return "\n".join(prompt_lines)

    def _format_entity_list(self, entity_classes: List[str]) -> str:
        """
        格式化實體列表為可讀字符串

        :param entity_classes: 實體類別列表
        :return: 格式化後的實體列表字符串
        """
        if not entity_classes:
            return "（無可用實體類型）"

        formatted = []
        for entity in sorted(entity_classes):
            formatted.append(f"- {entity}")
        return "\n".join(formatted)

    def _format_relationship_list(self, relationship_types: List[str]) -> str:
        """
        格式化關係列表為可讀字符串

        :param relationship_types: 關係類型列表
        :return: 格式化後的關係列表字符串
        """
        if not relationship_types:
            return "（無可用關係類型）"

        formatted = []
        for rel in sorted(relationship_types):
            formatted.append(f"- {rel}")
        return "\n".join(formatted)

    def _format_owl_constraints(self, owl_domain_range: Dict[str, List[tuple]]) -> str:
        """
        格式化 OWL Domain/Range 約束為可讀字符串

        :param owl_domain_range: OWL Domain/Range 約束字典
        :return: 格式化後的約束說明字符串
        """
        if not owl_domain_range:
            return ""

        constraints = []
        for rel_name, domain_range_pairs in sorted(owl_domain_range.items()):
            if not domain_range_pairs:
                continue

            # 收集所有有效的 (Domain, Range) 組合
            valid_combinations = []
            for domain_type, range_type in domain_range_pairs:
                valid_combinations.append(f"({domain_type}, {range_type})")

            if valid_combinations:
                constraints.append(
                    f"  - 關係 '{rel_name}' 的有效組合: {', '.join(valid_combinations)}"
                )

        if constraints:
            return "\n".join(constraints)
        return ""


# --- Pydantic 結構：動態使用全局規則 ---


class Triple(BaseModel):
    """定義單個知識三元組的結構，動態遵循運行時載入的 OWL 約束。"""

    subject: str = Field(description="三元組主體的實體名稱。")
    subject_type: str = Field(description="主體的實體類型。")
    relation: str = Field(description="主體與客體間的關係。")
    object: str = Field(description="客體的實體名稱。")
    object_type: str = Field(description="客體的實體類型。")

    @validator("subject_type", "object_type", pre=True)
    def validate_entity_types(cls, v):
        """驗證實體類型必須在當前載入的 Ontology 列表中。"""
        if v not in ONTOLOGY_RULES["entity_classes"]:
            raise ValueError(f"實體類型 '{v}' 未在當前載入的 Ontology 模組中定義。")
        return v

    @validator("relation", pre=True)
    def validate_relationship_type(cls, v):
        """驗證關係類型必須在當前載入的 Ontology 列表中。"""
        if v not in ONTOLOGY_RULES["relationship_types"]:
            raise ValueError(f"關係類型 '{v}' 未在當前載入的 Ontology 模組中定義。")
        return v

    @validator("object_type", pre=True, always=True)
    def validate_owl_domain_range(cls, v, values):
        """驗證三元組是否符合 OWL 的 Domain/Range 約束 (即: (主體類型, 客體類型) 必須是該關係的有效組合)。"""
        sub_type = values.get("subject_type")
        rel = values.get("relation")
        obj_type = v

        if rel in ONTOLOGY_RULES["owl_domain_range"]:
            # 檢查 (主體類型, 客體類型) 元組是否在允許的列表中
            if (sub_type, obj_type) not in ONTOLOGY_RULES["owl_domain_range"][rel]:
                raise ValueError(
                    f"OWL 約束失敗: 關係 '{rel}' 不允許連接 ({sub_type}, {obj_type})。"
                )
        return v


class KnowledgeGraph(BaseModel):
    """最終輸出結構：包含從文檔中提取的所有三元組。"""

    extracted_triples: List[Triple] = Field(
        description="從文本中提取出來的所有知識三元組列表。"
    )


# --- 範例 LangChain Agent 調用邏輯 ---

if __name__ == "__main__":
    # 使用默認路徑 (kag/ontology/) 或指定自定義路徑
    manager = OntologyManager()

    # 模擬 LangChain Agent 執行步驟：
    print("=" * 80)
    print("--- 1. 載入並合併 Manufacture 製造業相關的 Ontology ---")
    print("=" * 80)

    # 這裡假設已經分類文檔為 [企業] 領域和 [製造] 專業
    rules = manager.merge_ontologies(
        domain_files=["domain-enterprise.json"], task_file="major-manufacture.json"
    )

    print("\n" + "=" * 80)
    print("--- 2. 檢查合併後的規則 ---")
    print("=" * 80)
    print(f"合併後的實體類別 (部分): {rules['entity_classes'][:8]}...")
    print(f"合併後的關係類型 (部分): {rules['relationship_types'][:5]}...")

    # 測試動態 Pydantic 驗證
    print("\n" + "=" * 80)
    print("--- 3. 測試 Pydantic 驗證 ---")
    print("=" * 80)

    # 範例 1: 符合規則的三元組 (使用 Manufacture 專業層的規則)
    try:
        valid_triple_data = {
            "subject": "CNC 機床 G-100",
            "subject_type": "Machine_Asset",  # 來自 Manufacture-Ontology
            "relation": "produces",  # 來自 Manufacture-Ontology
            "object": "零件 R2-D2",
            "object_type": "Material",
        }
        Triple(**valid_triple_data)
        print("✅ 測試 1 (有效): 專業層三元組驗證成功。")
    except Exception as e:
        print(f"❌ 測試 1 失敗: {e}")

    # 範例 2: 違反 OWL Domain/Range 約束
    try:
        invalid_owl_data = {
            "subject": "李經理",
            "subject_type": "Person",
            "relation": "uses_method",  # 關係來自基礎層
            "object": "2025-10-26",
            "object_type": "TimePoint",
        }
        # 預期失敗：uses_method 的 Range 不包含 TimePoint，違反基礎層 OWL 約束
        Triple(**invalid_owl_data)
        print("❌ 測試 2 意外成功 (應失敗)。")
    except ValueError as e:
        print(f"✅ 測試 2 (無效): 驗證失敗成功。錯誤訊息: {e}")

    # 測試 Prompt 模板載入和生成
    print("\n" + "=" * 80)
    print("--- 4. 測試 Prompt 模板載入和生成 ---")
    print("=" * 80)

    try:
        # 載入模板
        template = manager.load_prompt_template()
        print(f"✅ 模板載入成功: {template.get('template_name', 'Unknown')}")
        print(f"   目標模型: {template.get('model_target', 'Unknown')}")
        print(f"   語言: {template.get('language', 'Unknown')}")

        # 生成提示詞
        sample_text = """
        2024年12月，李經理在台北工廠使用CNC機床G-100生產了零件R2-D2。
        該零件由供應商ABC公司提供原材料，並通過品質檢查。
        """

        prompt = manager.generate_prompt(
            text_chunk=sample_text, ontology_rules=rules, include_owl_constraints=True
        )

        print("\n✅ 提示詞生成成功！")
        print("\n生成的提示詞預覽（前500字符）:")
        print("-" * 80)
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        print("-" * 80)

        # 驗證佔位符是否已替換
        if "[INJECT_ENTITY_LIST]" in prompt:
            print("⚠️  警告: [INJECT_ENTITY_LIST] 佔位符未被替換")
        if "[INJECT_RELATIONSHIP_LIST]" in prompt:
            print("⚠️  警告: [INJECT_RELATIONSHIP_LIST] 佔位符未被替換")
        if "[INJECT_JSON_SCHEMA]" in prompt:
            print("⚠️  警告: [INJECT_JSON_SCHEMA] 佔位符未被替換")
        if "[TEXT_CHUNK]" in prompt:
            print("⚠️  警告: [TEXT_CHUNK] 佔位符未被替換")

        if all(
            placeholder not in prompt
            for placeholder in [
                "[INJECT_ENTITY_LIST]",
                "[INJECT_RELATIONSHIP_LIST]",
                "[INJECT_JSON_SCHEMA]",
                "[TEXT_CHUNK]",
            ]
        ):
            print("✅ 所有佔位符已成功替換！")

    except Exception as e:
        print(f"❌ Prompt 模板測試失敗: {e}")
        import traceback

        traceback.print_exc()
