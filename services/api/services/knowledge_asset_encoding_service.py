# 代碼功能說明: 知識資產編碼服務（Ontology 對齊 + KNW-Code 生成）
# 創建日期: 2026-01-25 19:32 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-25 19:32 UTC+8

"""知識資產編碼服務 - 封裝 Ontology 對齊與 KNW-Code 生成，供上傳 pipeline 與 KA-Agent 共用。"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from kag.ontology_selector import OntologySelector

logger = logging.getLogger(__name__)

# 默認回退值（規格 13.6.3）
_DEFAULT_DOMAIN = "domain-enterprise"
_DEFAULT_VERSION = "1.0.0"
_DEFAULT_LIFECYCLE = "Draft"
_KA_ID_PREFIX = "KA-"
_KNW_PREFIX = "KNW-"


class KnowledgeAssetEncodingService:
    """知識資產編碼服務：Ontology 對齊 + KNW-Code 生成"""

    def __init__(self, ontology_selector: Optional[OntologySelector] = None):
        self._selector = ontology_selector or OntologySelector()

    async def encode_file(
        self,
        file_id: str,
        filename: str,
        file_content_preview: Optional[str] = None,
        file_metadata: Optional[Dict[str, Any]] = None,
        use_semantic_match: bool = True,
        fallback_on_error: bool = True,
    ) -> Dict[str, Any]:
        """
        對文件進行知識資產編碼。

        Args:
            file_id: 文件 ID
            filename: 文件名
            file_content_preview: 文件內容預覽（前 2000 字，用於語義匹配）
            file_metadata: 文件元數據（可含 file_type、user_id、task_id 等）
            use_semantic_match: 是否使用語義匹配
            fallback_on_error: Ontology 失敗時是否使用默認值

        Returns:
            {
                "knw_code": "KNW-...",
                "ka_id": "KA-...",
                "domain": "domain-enterprise",
                "major": "major-manufacture" | None,
                "lifecycle_state": "Draft",
                "version": "1.0.0",
            }
        """
        file_metadata = file_metadata or {}
        domain = _DEFAULT_DOMAIN
        major: Optional[str] = None
        version = _DEFAULT_VERSION
        lifecycle_state = _DEFAULT_LIFECYCLE

        try:
            sel = await self._selector.select_auto_async(
                file_name=filename,
                file_content=file_content_preview,
                file_metadata=file_metadata,
                use_semantic_match=use_semantic_match,
            )
            dom_list = sel.get("domain") or []
            maj_list = sel.get("major") or []
            if isinstance(dom_list, list) and len(dom_list) > 0:
                domain = dom_list[0] if isinstance(dom_list[0], str) else str(dom_list[0])
            if isinstance(maj_list, list) and len(maj_list) > 0:
                major = maj_list[0] if isinstance(maj_list[0], str) else str(maj_list[0])
        except Exception as e:
            logger.warning(
                f"Ontology 選擇失敗，使用默認值: file_id={file_id}, error={str(e)}",
                exc_info=True,
            )
            if not fallback_on_error:
                raise
            domain = _DEFAULT_DOMAIN
            major = None

        ka_id = self._generate_ka_id(file_id=file_id, domain=domain, major=major)
        knw_code = self._generate_knw_code(
            domain=domain, major=major, version=version, file_id=file_id
        )

        result = {
            "knw_code": knw_code,
            "ka_id": ka_id,
            "domain": domain,
            "major": major,
            "lifecycle_state": lifecycle_state,
            "version": version,
        }
        logger.info(f"知識資產編碼完成: file_id={file_id}, knw_code={knw_code}, domain={domain}")
        return result

    def _generate_ka_id(self, file_id: str, domain: str, major: Optional[str]) -> str:
        """生成 ka_id：KA-{domain_slug}-{major_slug}-{short_id}"""
        d = re.sub(r"[^a-zA-Z0-9]", "_", domain).strip("_") or "GENERAL"
        m = re.sub(r"[^a-zA-Z0-9]", "_", major).strip("_") if major else "GENERAL"
        short = (file_id or "")[:8].replace("-", "") or "0"
        return f"{_KA_ID_PREFIX}{d}-{m}-{short}"

    def _generate_knw_code(
        self,
        domain: str,
        major: Optional[str],
        version: str,
        file_id: str,
    ) -> str:
        """
        生成 KNW-Code：KNW-{DOMAIN}-{TYPE}-{SUBDOMAIN}-{OBJECT}-{SCOPE}-v{MAJOR.MINOR}
        簡化版：KNW-{DOMAIN}-SPEC-{MAJOR}-FILE-v{version}
        """
        d = re.sub(r"[^a-zA-Z0-9]", "_", domain).upper().strip("_") or "GENERAL"
        m = re.sub(r"[^a-zA-Z0-9]", "_", (major or "GENERAL")).upper().strip("_") or "GENERAL"
        v = version or _DEFAULT_VERSION
        if not re.match(r"^\d+\.\d+(\.\d+)?$", v):
            v = _DEFAULT_VERSION
        return f"{_KNW_PREFIX}{d}-SPEC-{m}-FILE-v{v}"
