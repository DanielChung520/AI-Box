# 代碼功能說明: Ontology 管理器 V2 - 使用 ArangoDB Store Service（檔案系統轉結構遷移）
# 創建日期: 2025-12-18 19:39:14 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18 19:39:14 (UTC+8)

"""Ontology Manager V2

使用 OntologyStoreService 從 ArangoDB 載入 Ontology，替代文件系統讀取。
保持與原有 OntologyManager 相同的接口以確保向後兼容。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.api.services.ontology_store_service import get_ontology_store_service

# 保持全局變量以兼容現有代碼
ONTOLOGY_RULES: Dict[str, Any] = {
    "entity_classes": [],
    "relationship_types": [],
    "owl_domain_range": {},
}


class OntologyManager:
    """
    負責載入、合併 Ontology，並建立運行時驗證規則。
    使用 ArangoDB Store Service 替代文件系統讀取。
    """

    def __init__(self, base_path: Optional[str] = None, tenant_id: Optional[str] = None):
        """
        初始化 Ontology 管理器

        Args:
            base_path: 保留參數以兼容舊接口（已棄用，不再使用）
            tenant_id: 租戶 ID，用於查詢租戶專屬 Ontology
        """
        self.base_path = base_path  # 保留以兼容，但不再使用
        self.tenant_id = tenant_id
        self.store_service = get_ontology_store_service()
        self.loaded_ontologies: Dict[str, Any] = {}

    def merge_ontologies(
        self, domain_files: List[str], task_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        核心合併邏輯：載入 Base, Domain, Task 層次，並更新全局規則容器。

        Args:
            domain_files: 領域層 Ontology 檔案列表 (e.g., ['domain-enterprise.json'])
            task_file: 專業層 Ontology 檔案 (e.g., 'major-manufacture.json')

        Returns:
            合併後的規則字典
        """
        global ONTOLOGY_RULES

        # 使用 Store Service 的 merge_ontologies 方法
        merged_rules = self.store_service.merge_ontologies(
            domain_files=domain_files, major_file=task_file, tenant_id=self.tenant_id
        )

        # 更新全局規則容器（保持兼容性）
        ONTOLOGY_RULES = merged_rules

        return ONTOLOGY_RULES

    def load_prompt_template(self) -> Dict[str, Any]:
        """
        載入 Prompt-Template.json 模板文件

        Note: 此功能暫時保持從文件系統讀取，未來可遷移到 ArangoDB

        Returns:
            提示詞模板字典
        """
        # TODO: 未來可以將 Prompt-Template 也遷移到 ArangoDB
        import json
        from pathlib import Path

        current_file = Path(__file__).resolve()
        template_path = current_file.parent / "ontology" / "Prompt-Template.json"

        if not template_path.exists():
            raise FileNotFoundError(f"Prompt-Template.json not found at {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_prompt(
        self,
        text_chunk: str,
        ontology_rules: Optional[Dict[str, Any]] = None,
        include_owl_constraints: bool = True,
    ) -> str:
        """
        根據合併後的 Ontology 規則生成提示詞

        Args:
            text_chunk: 待分析的文本片段
            ontology_rules: 合併後的 Ontology 規則（如果為 None，使用全局 ONTOLOGY_RULES）
            include_owl_constraints: 是否包含 OWL Domain/Range 約束說明

        Returns:
            生成的提示詞字符串
        """
        # 使用現有的實現邏輯（從原 kag_schema_manager.py）
        # 這裡簡化處理，實際應該重用原實現
        if ontology_rules is None:
            global ONTOLOGY_RULES
            ontology_rules = ONTOLOGY_RULES

        entity_classes = ontology_rules.get("entity_classes")
        relationship_types = ontology_rules.get("relationship_types")
        if not entity_classes or not relationship_types:
            raise RuntimeError("Ontology 規則未初始化。請先調用 merge_ontologies() 方法載入並合併 Ontology。")

        # 載入提示詞模板
        template = self.load_prompt_template()

        # 生成提示詞（簡化實現，實際應該重用原邏輯）
        # TODO: 重用原 kag_schema_manager.py 中的 _format_entity_list 等方法
        prompt_lines = []
        prompt_lines.append("實體類別:")
        for entity in sorted(entity_classes):
            prompt_lines.append(f"- {entity}")

        prompt_lines.append("\n關係類型:")
        for rel in sorted(relationship_types):
            prompt_lines.append(f"- {rel}")

        prompt_lines.append(f"\n文本片段:\n{text_chunk}")

        return "\n".join(prompt_lines)
