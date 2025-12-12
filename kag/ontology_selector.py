"""
Ontology 選擇器服務
功能：根據文件內容和元數據自動選擇合適的 domain 和 major ontology
創建日期：2025-12-10
創建人：Daniel Chung
最後修改日期：2025-12-10
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import structlog

logger = structlog.get_logger(__name__)


class OntologySelector:
    """Ontology 選擇器，用於根據文件特徵自動選擇合適的 Ontology"""

    def __init__(self, ontology_list_path: Optional[str] = None):
        """
        初始化 Ontology 選擇器

        :param ontology_list_path: ontology_list.json 文件路徑，如果為 None 則使用默認路徑
        """
        if ontology_list_path is None:
            # 獲取當前文件所在目錄，然後指向 ontology_list.json
            current_file = Path(__file__).resolve()
            ontology_list_path = str(
                current_file.parent / "ontology" / "ontology_list.json"
            )

        self.ontology_list_path = ontology_list_path
        self._ontology_list: Optional[Dict[str, Any]] = None
        self._load_ontology_list()

    def _load_ontology_list(self) -> None:
        """載入 ontology_list.json"""
        try:
            with open(self.ontology_list_path, "r", encoding="utf-8") as f:
                self._ontology_list = json.load(f)
            logger.info("Ontology list loaded", path=self.ontology_list_path)
        except FileNotFoundError:
            logger.error("Ontology list file not found", path=self.ontology_list_path)
            raise
        except json.JSONDecodeError as e:
            logger.error("Failed to parse ontology list", error=str(e))
            raise

    def select_by_keywords(
        self,
        keywords: List[str],
        file_name: Optional[str] = None,
        file_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        根據關鍵字選擇 Ontology

        :param keywords: 關鍵字列表（從文件名、內容等提取）
        :param file_name: 文件名（可選，用於額外匹配）
        :param file_content: 文件內容預覽（可選，用於額外匹配）
        :return: 選擇結果，包含 base, domain, major 文件列表
        """
        if not self._ontology_list:
            raise RuntimeError("Ontology list not loaded")

        selected_domains: Set[str] = set()
        selected_majors: Set[str] = set()

        # 從 quick_index.by_keywords 查找
        quick_index = self._ontology_list.get("quick_index", {}).get("by_keywords", {})

        for keyword in keywords:
            keyword_lower = keyword.lower()
            # 直接匹配
            if keyword_lower in quick_index:
                for file in quick_index[keyword_lower]:
                    if "domain" in file:
                        selected_domains.add(file)
                    elif "major" in file:
                        selected_majors.add(file)

            # 部分匹配（關鍵字包含在索引關鍵字中，或索引關鍵字包含在關鍵字中）
            for index_keyword, files in quick_index.items():
                # 檢查關鍵字是否匹配索引關鍵字（雙向匹配）
                if (
                    keyword_lower in index_keyword
                    or index_keyword in keyword_lower
                    or keyword_lower.startswith(index_keyword)
                    or index_keyword.startswith(keyword_lower)
                ):
                    for file in files:
                        if "domain" in file:
                            selected_domains.add(file)
                        elif "major" in file:
                            selected_majors.add(file)

        # 從文件名和內容中提取關鍵字進行匹配
        if file_name:
            file_name_lower = file_name.lower()
            for index_keyword, files in quick_index.items():
                if index_keyword in file_name_lower:
                    for file in files:
                        if "domain" in file:
                            selected_domains.add(file)
                        elif "major" in file:
                            selected_majors.add(file)

        if file_content:
            content_lower = file_content[:500].lower()  # 只檢查前500字符
            for index_keyword, files in quick_index.items():
                if index_keyword in content_lower:
                    for file in files:
                        if "domain" in file:
                            selected_domains.add(file)
                        elif "major" in file:
                            selected_majors.add(file)

        # 驗證 major 與 domain 的兼容性
        selected_domains_list = list(selected_domains)
        selected_majors_list = list(selected_majors)

        # 過濾不兼容的 major
        compatible_majors = []
        for major_file in selected_majors_list:
            # 查找 major 的兼容 domain
            for major_info in self._ontology_list.get("major_ontologies", []):
                if major_info["file_name"] == major_file:
                    compatible_domains = major_info.get("compatible_domains", [])
                    # 如果選中的 domain 中有兼容的，則保留此 major
                    if any(d in selected_domains_list for d in compatible_domains):
                        compatible_majors.append(major_file)
                    elif not compatible_domains:  # 如果沒有指定兼容性，則允許
                        compatible_majors.append(major_file)
                    break

        result = {
            "base": self._ontology_list["base_ontology"]["file_name"],
            "domain": selected_domains_list if selected_domains_list else [],
            "major": compatible_majors,
            "selection_method": "keywords",
            "matched_keywords": keywords,
        }

        logger.info(
            "Selected ontologies by keywords",
            base=result["base"],
            domains=result["domain"],
            majors=result["major"],
            keywords=keywords,
        )

        return result

    def select_by_document_type(self, document_type: str) -> Dict[str, Any]:
        """
        根據文檔類型選擇 Ontology

        :param document_type: 文檔類型（如 "生產報告", "財務報表"）
        :return: 選擇結果
        """
        if not self._ontology_list:
            raise RuntimeError("Ontology list not loaded")

        doc_type_index = self._ontology_list.get("quick_index", {}).get(
            "by_document_type", {}
        )

        if document_type in doc_type_index:
            config = doc_type_index[document_type]
            result = {
                "base": self._ontology_list["base_ontology"]["file_name"],
                "domain": config.get("domain", []),
                "major": config.get("major", []),
                "selection_method": "document_type",
                "document_type": document_type,
            }
        else:
            # 如果找不到匹配的文檔類型，返回默認配置（只有 base）
            result = {
                "base": self._ontology_list["base_ontology"]["file_name"],
                "domain": [],
                "major": [],
                "selection_method": "default",
                "document_type": document_type,
            }

        logger.info(
            "Selected ontologies by document type",
            base=result["base"],
            domains=result["domain"],
            majors=result["major"],
            document_type=document_type,
        )

        return result

    def select_auto(
        self,
        file_name: Optional[str] = None,
        file_content: Optional[str] = None,
        file_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        自動選擇 Ontology（綜合多種方法）

        :param file_name: 文件名
        :param file_content: 文件內容預覽（前1000字符）
        :param file_metadata: 文件元數據（可包含 document_type 等）
        :return: 選擇結果
        """
        keywords: List[str] = []

        # 從文件名提取關鍵字
        if file_name:
            # 移除文件擴展名，分割關鍵字
            name_without_ext = Path(file_name).stem
            keywords.extend(name_without_ext.split("_"))
            keywords.extend(name_without_ext.split("-"))
            keywords.append(name_without_ext)

        # 從文件內容提取關鍵字（簡單實現：取前1000字符中的常見關鍵字）
        if file_content:
            content_preview = file_content[:1000].lower()
            # 檢查是否包含關鍵字索引中的詞
            quick_index = self._ontology_list.get("quick_index", {}).get(
                "by_keywords", {}
            )
            for keyword in quick_index.keys():
                if keyword in content_preview:
                    keywords.append(keyword)

        # 從元數據提取
        if file_metadata:
            doc_type = file_metadata.get("document_type")
            if doc_type:
                return self.select_by_document_type(doc_type)

            # 從元數據的其他字段提取關鍵字
            for key, value in file_metadata.items():
                if isinstance(value, str) and len(value) < 100:
                    keywords.append(value.lower())

        # 使用關鍵字選擇
        if keywords:
            return self.select_by_keywords(keywords, file_name, file_content)

        # 默認：只返回 base
        return {
            "base": self._ontology_list["base_ontology"]["file_name"],
            "domain": [],
            "major": [],
            "selection_method": "default",
            "reason": "No keywords or document type found",
        }

    def get_ontology_paths(self, selection: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        獲取 Ontology 文件的完整路徑

        :param selection: select_auto 或 select_by_keywords 返回的選擇結果
        :return: 包含完整路徑的字典
        """
        base_path = self._ontology_list["metadata"]["base_path"]

        paths = {
            "base": f"{base_path}{selection['base']}",
            "domain": [f"{base_path}{d}" for d in selection["domain"]],
            "major": (
                [f"{base_path}{m}" for m in selection["major"]]
                if selection.get("major")
                else []
            ),
        }

        return paths
