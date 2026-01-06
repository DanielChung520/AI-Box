"""
Ontology 選擇器服務
功能：根據文件內容和元數據自動選擇合適的 domain 和 major ontology
創建日期：2025-12-10
創建人：Daniel Chung
最後修改日期：2026-01-04 22:59 (UTC+8)
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

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
            ontology_list_path = str(current_file.parent / "ontology" / "ontology_list.json")

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
                # 雙向匹配：索引關鍵字在文件名中，或文件名關鍵字在索引中
                if index_keyword in file_name_lower or file_name_lower in index_keyword:
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

        # 驗證 major 與 domain 的兼容性，並自動添加推薦的 domain
        selected_domains_list = list(selected_domains)
        selected_majors_list = list(selected_majors)

        # 過濾不兼容的 major，並自動添加推薦的 domain
        compatible_majors = []
        for major_file in selected_majors_list:
            # 查找 major 的兼容 domain
            compatible_domains_found = False
            for major_info in self._ontology_list.get("major_ontologies", []):
                if major_info["file_name"] == major_file:
                    compatible_domains = major_info.get("compatible_domains", [])
                    if compatible_domains:
                        # 如果選中的 domain 中有兼容的，則保留此 major
                        if any(d in selected_domains_list for d in compatible_domains):
                            compatible_domains_found = True
                            compatible_majors.append(major_file)
                        else:
                            # 如果沒有匹配到兼容的 domain，自動添加第一個推薦的 domain
                            recommended_domain = compatible_domains[0]
                            if recommended_domain not in selected_domains_list:
                                selected_domains_list.append(recommended_domain)
                                logger.info(
                                    "Auto-added recommended domain for major",
                                    major=major_file,
                                    recommended_domain=recommended_domain,
                                )
                            compatible_majors.append(major_file)
                            compatible_domains_found = True
                    else:
                        # 如果沒有指定兼容性，則允許
                        compatible_majors.append(major_file)
                        compatible_domains_found = True
                    break

            # 如果沒有在 major_ontologies 中找到，也允許（兼容舊版本）
            if not compatible_domains_found:
                compatible_majors.append(major_file)

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

        doc_type_index = self._ontology_list.get("quick_index", {}).get("by_document_type", {})

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
            quick_index_dict = (
                self._ontology_list.get("quick_index") if self._ontology_list else None
            )
            quick_index = (
                quick_index_dict.get("by_keywords", {})  # type: ignore[union-attr]  # 已檢查為 dict
                if quick_index_dict and isinstance(quick_index_dict, dict)
                else {}
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
        if not self._ontology_list:
            return {
                "base": "",
                "domain": [],
                "major": [],
                "selection_method": "default",
                "reason": "No ontology list loaded",
            }
        base_ontology = self._ontology_list.get("base_ontology")
        if not base_ontology or not isinstance(base_ontology, dict):
            return {
                "base": "",
                "domain": [],
                "major": [],
                "selection_method": "default",
                "reason": "No base ontology found",
            }
        return {
            "base": base_ontology.get("file_name", ""),  # type: ignore[index]  # 已檢查為 dict
            "domain": [],
            "major": [],
            "selection_method": "default",
            "reason": "No keywords or document type found",
        }

    def get_ontology_paths(
        self, selection: Dict[str, Any]
    ) -> Dict[str, Any]:  # 返回類型改為 Any，因為 base 可能是字符串
        """
        獲取 Ontology 文件的完整路徑

        :param selection: select_auto 或 select_by_keywords 返回的選擇結果
        :return: 包含完整路徑的字典
        """
        if not self._ontology_list:
            return {"base": "", "domain": [], "major": []}
        metadata = self._ontology_list.get("metadata")
        if not metadata or not isinstance(metadata, dict):
            return {"base": "", "domain": [], "major": []}
        base_path = metadata.get("base_path", "")  # type: ignore[index]  # 已檢查為 dict

        base_value = selection.get("base", "")
        domain_list = selection.get("domain", [])
        major_list = selection.get("major", [])

        # 確保類型正確
        if not isinstance(base_value, str):
            base_value = ""
        if not isinstance(domain_list, list):
            domain_list = []
        if not isinstance(major_list, list):
            major_list = []

        paths: Dict[str, Any] = {
            "base": f"{base_path}{base_value}",  # base 是字符串，不是列表
            "domain": [f"{base_path}{d}" for d in domain_list],
            "major": [f"{base_path}{m}" for m in major_list],
        }

        return paths

    async def select_by_semantic_match(
        self,
        file_name: Optional[str] = None,
        file_content: Optional[str] = None,
        file_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 進行語義匹配選擇 Ontology

        策略：
        1. 使用 LLM 生成文件摘要和理解領域
        2. 使用 LLM 理解每個 Ontology 的能力
        3. 進行語義匹配，選擇最合適的 Ontology

        :param file_name: 文件名
        :param file_content: 文件內容預覽（前2000字符）
        :param file_metadata: 文件元數據
        :return: 選擇結果，如果失敗返回 None
        """
        try:
            from llm.moe.moe_manager import LLMMoEManager  # noqa: F401
        except ImportError:
            logger.warning("LLM service not available, semantic matching disabled")
            return None

        # 1. 構建文件摘要和理解（優先使用預存的摘要）
        file_summary = None

        # 優先使用預存的摘要（如果存在）
        if file_metadata:
            custom_metadata = file_metadata.get("custom_metadata", {})
            file_summary = custom_metadata.get("file_summary")
            if file_summary:
                logger.info(
                    "使用預存的文件摘要",
                    file_name=file_name,
                    summary_length=len(file_summary),
                )

        # 如果沒有預存摘要，才生成新的
        if not file_summary:
            file_summary = await self._generate_file_summary(file_name, file_content, file_metadata)

        if not file_summary:
            logger.warning("Failed to generate file summary, falling back to keyword matching")
            return None

        # 2. 獲取所有可用的 Ontology 候選
        available_ontologies = self._get_available_ontologies()

        # 3. 使用 LLM 進行語義匹配
        matched_ontologies = await self._semantic_match_ontologies(
            file_summary, available_ontologies
        )

        if (
            not matched_ontologies
            or not matched_ontologies.get("domain")
            and not matched_ontologies.get("major")
        ):
            logger.warning(
                "Semantic matching returned no results, falling back to keyword matching"
            )
            return None

        # 4. 構建選擇結果
        return {
            "base": self._ontology_list["base_ontology"]["file_name"],
            "domain": matched_ontologies.get("domain", []),
            "major": matched_ontologies.get("major", []),
            "selection_method": "semantic_match",
            "file_summary": file_summary,
            "reasoning": matched_ontologies.get("reasoning", ""),
            "confidence": matched_ontologies.get("confidence", 0.0),
        }

    async def _generate_file_summary(
        self,
        file_name: Optional[str],
        file_content: Optional[str],
        file_metadata: Optional[Dict[str, Any]],
    ) -> str:
        """使用 LLM 生成文件摘要和領域理解"""
        try:
            from llm.moe.moe_manager import LLMMoEManager
        except ImportError:
            return ""

        # 構建 prompt
        content_preview = file_content[:2000] if file_content else "無內容"
        metadata_str = (
            json.dumps(file_metadata, ensure_ascii=False, indent=2) if file_metadata else "無"
        )

        prompt = f"""請分析以下文件的領域和主題，生成簡潔的摘要和理解。

文件名：{file_name or "未知"}

文件內容預覽（前2000字符）：
{content_preview}

文件元數據：
{metadata_str}

請提供：
1. 文件的主要領域（例如：食品產業、製造業、能源、企業管理、行政等）
2. 文件的核心主題和內容（50字以內）
3. 文件涉及的專業術語和關鍵概念（5-10個）
4. 文件的應用場景（例如：生產報告、技術文檔、政策文件等）

請以 JSON 格式返回：
{{
    "domain": "領域名稱",
    "summary": "核心主題摘要",
    "key_concepts": ["概念1", "概念2", ...],
    "application_scenarios": ["場景1", "場景2", ...]
}}"""

        try:
            moe = LLMMoEManager()
            result = await moe.generate(
                prompt,
                temperature=0.3,  # 降低隨機性，提高穩定性
                max_tokens=500,
            )

            summary_text = result.get("text") or result.get("content", "")

            # 嘗試解析 JSON
            try:
                # 嘗試提取 JSON（可能包含 markdown 代碼塊）
                json_match = re.search(r"\{[\s\S]*\}", summary_text)
                if json_match:
                    summary_text = json_match.group(0)

                summary_json = json.loads(summary_text)
                return json.dumps(summary_json, ensure_ascii=False)
            except json.JSONDecodeError:
                # 如果不是 JSON，返回原始文本
                logger.warning(
                    f"Failed to parse JSON from file summary, using raw text: {summary_text[:200]}"
                )
                return summary_text

        except Exception as e:
            logger.error(f"Failed to generate file summary: {e}", exc_info=True)
            return ""

    def _get_available_ontologies(self) -> Dict[str, List[Dict[str, Any]]]:
        """獲取所有可用的 Ontology 列表（含描述、標籤、用例）"""
        if not self._ontology_list:
            return {"domain": [], "major": []}

        ontologies: Dict[str, List[Dict[str, Any]]] = {
            "domain": [],
            "major": [],
        }

        # 獲取 Domain Ontologies
        for domain in self._ontology_list.get("domain_ontologies", []):
            ontologies["domain"].append(
                {
                    "file_name": domain["file_name"],
                    "ontology_name": domain.get("ontology_name", ""),
                    "description": domain.get("description", ""),
                    "tags": domain.get("tags", []),
                    "use_cases": domain.get("use_cases", []),
                }
            )

        # 獲取 Major Ontologies
        for major in self._ontology_list.get("major_ontologies", []):
            ontologies["major"].append(
                {
                    "file_name": major["file_name"],
                    "ontology_name": major.get("ontology_name", ""),
                    "description": major.get("description", ""),
                    "tags": major.get("tags", []),
                    "use_cases": major.get("use_cases", []),
                    "compatible_domains": major.get("compatible_domains", []),
                }
            )

        return ontologies

    async def _semantic_match_ontologies(
        self,
        file_summary: str,
        available_ontologies: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """使用 LLM 進行語義匹配，選擇最合適的 Ontology"""
        try:
            from llm.moe.moe_manager import LLMMoEManager
        except ImportError:
            return {"domain": [], "major": [], "reasoning": "", "confidence": 0.0}

        # 構建 Ontology 候選描述
        domain_descriptions = []
        for domain in available_ontologies["domain"]:
            desc = f"""
- 文件名：{domain['file_name']}
- 名稱：{domain['ontology_name']}
- 描述：{domain['description']}
- 標籤：{', '.join(domain['tags'])}
- 適用場景：{', '.join(domain['use_cases'])}
"""
            domain_descriptions.append(desc)

        major_descriptions = []
        for major in available_ontologies["major"]:
            desc = f"""
- 文件名：{major['file_name']}
- 名稱：{major['ontology_name']}
- 描述：{major['description']}
- 標籤：{', '.join(major['tags'])}
- 適用場景：{', '.join(major['use_cases'])}
- 兼容的 Domain：{', '.join(major.get('compatible_domains', []))}
"""
            major_descriptions.append(desc)

        # 構建匹配 prompt
        prompt = f"""你是一個 Ontology 選擇專家。根據文件摘要，選擇最合適的 Domain 和 Major Ontology。

文件摘要和理解：
{file_summary}

可用的 Domain Ontologies：
{chr(10).join(domain_descriptions)}

可用的 Major Ontologies：
{chr(10).join(major_descriptions)}

請根據文件的領域、主題、應用場景，選擇最匹配的 Ontology。考慮以下因素：
1. 領域匹配度（Domain Ontology）
2. 專業匹配度（Major Ontology）
3. 應用場景匹配度
4. 關鍵概念匹配度

請以 JSON 格式返回：
{{
    "selected_domains": ["domain-xxx.json", "domain-yyy.json"],
    "selected_majors": ["major-xxx.json"],
    "reasoning": "選擇理由（100字以內）",
    "confidence": 0.95
}}"""

        try:
            moe = LLMMoEManager()
            result = await moe.generate(
                prompt,
                temperature=0.2,  # 降低隨機性
                max_tokens=800,
            )

            result_text = result.get("text") or result.get("content", "")

            # 解析 JSON 響應
            try:
                # 嘗試提取 JSON（可能包含 markdown 代碼塊）
                json_match = re.search(r"\{[\s\S]*\}", result_text)
                if json_match:
                    result_text = json_match.group(0)

                matched = json.loads(result_text)

                return {
                    "domain": matched.get("selected_domains", []),
                    "major": matched.get("selected_majors", []),
                    "reasoning": matched.get("reasoning", ""),
                    "confidence": matched.get("confidence", 0.0),
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response: {e}, response: {result_text[:500]}")
                return {"domain": [], "major": [], "reasoning": "", "confidence": 0.0}

        except Exception as e:
            logger.error(f"Failed to perform semantic matching: {e}", exc_info=True)
            return {"domain": [], "major": [], "reasoning": "", "confidence": 0.0}

    async def select_auto_async(
        self,
        file_name: Optional[str] = None,
        file_content: Optional[str] = None,
        file_metadata: Optional[Dict[str, Any]] = None,
        use_semantic_match: bool = True,
    ) -> Dict[str, Any]:
        """
        自動選擇 Ontology（綜合多種方法，優先使用語義匹配）

        :param file_name: 文件名
        :param file_content: 文件內容預覽（前2000字符，用於語義匹配）
        :param file_metadata: 文件元數據
        :param use_semantic_match: 是否使用語義匹配（默認 True）
        :return: 選擇結果
        """
        # 策略 1：優先使用語義匹配（如果啟用且內容足夠）
        if use_semantic_match and file_content and len(file_content) > 100:
            try:
                semantic_result = await self.select_by_semantic_match(
                    file_name=file_name,
                    file_content=file_content[:2000],  # 使用前2000字符
                    file_metadata=file_metadata,
                )

                if semantic_result and (
                    semantic_result.get("domain") or semantic_result.get("major")
                ):
                    logger.info(
                        "Ontology selected by semantic match",
                        domains=semantic_result.get("domain"),
                        majors=semantic_result.get("major"),
                        confidence=semantic_result.get("confidence", 0.0),
                    )
                    return semantic_result
            except Exception as e:
                logger.warning(
                    f"Semantic matching failed, falling back to keyword matching: {e}",
                    exc_info=True,
                )

        # 策略 2：降級到關鍵字匹配（原有邏輯）
        return self.select_auto(file_name, file_content, file_metadata)
