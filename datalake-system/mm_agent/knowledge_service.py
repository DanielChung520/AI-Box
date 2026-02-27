# 代碼功能說明: 知識檢索服務
# 創建日期: 2026-02-09
# 創建人: AI-Box Development
# 最後修改日期: 2026-02-09

"""
知識檢索服務 - Knowledge Retrieval Service

整合 KA-Agent 進行知識查詢，支援：
1. 內部知識檢索（公司規定、ERP 操作流程等）
2. 外部知識檢索（產業最佳實踐、專業術語等）
3. LLM 回退機制（KA-Agent 不可用時）

使用方式：
- knowledge_service.query(query, source_type="internal")
- knowledge_service.query(query, source_type="external")
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
from enum import Enum
from pydantic import BaseModel

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class KnowledgeSourceType(str, Enum):
    """知識來源類型"""

    INTERNAL = "internal"  # 公司內部知識
    EXTERNAL = "external"  # 外部專業知識
    UNKNOWN = "unknown"


class KnowledgeQueryResult(BaseModel):
    """知識查詢結果"""

    success: bool
    answer: str = ""
    sources: list = []
    source_type: KnowledgeSourceType = KnowledgeSourceType.UNKNOWN
    error: Optional[str] = None
    query_time_ms: int = 0


class KnowledgeService:
    """知識檢索服務"""

    def __init__(self) -> None:
        """初始化知識檢索服務"""
        self._ai_box_api_url = os.getenv("AI_BOX_API_URL", "http://localhost:8000")
        self._api_key = os.getenv("AI_BOX_API_KEY", "")
        self._timeout = 60.0

        # LLM 配置（用於回退）
        self._llm_model = os.getenv("KNOWLEDGE_LLM_MODEL", "gpt-oss:120b")
        self._llm_timeout = 120.0

        logger.info(f"[KnowledgeService] 初始化完成，API URL: {self._ai_box_api_url}")

    async def query(
        self,
        query: str,
        source_type: KnowledgeSourceType = KnowledgeSourceType.UNKNOWN,
        session_id: str = "",
    ) -> KnowledgeQueryResult:
        """
        執行知識查詢

        Args:
            query: 查詢問題
            source_type: 知識來源類型（internal/external）
            session_id: 會話 ID

        Returns:
            KnowledgeQueryResult: 查詢結果
        """
        import time

        start_time = time.time()
        query_time_ms = 0

        logger.info(
            f"[KnowledgeService] 執行知識查詢: {query[:50]}..., source_type={source_type.value}"
        )

        try:
            # 1. 嘗試調用 KA-Agent
            ka_result = await self._call_ka_agent(query, source_type, session_id)
            query_time_ms = int((time.time() - start_time) * 1000)

            if ka_result["success"]:
                logger.info(f"[KnowledgeService] KA-Agent 查詢成功: {query_time_ms}ms")
                return KnowledgeQueryResult(
                    success=True,
                    answer=ka_result.get("answer", ""),
                    sources=ka_result.get("sources", []),
                    source_type=source_type,
                    query_time_ms=query_time_ms,
                )

            logger.warning(
                f"[KnowledgeService] KA-Agent 查詢失敗，回退到 LLM: {ka_result.get('error')}"
            )

        except Exception as e:
            logger.warning(f"[KnowledgeService] KA-Agent 調用異常，回退到 LLM: {e}")

        # 2. 回退到 LLM
        try:
            llm_result = await self._call_llm_knowledge(query, source_type)
            query_time_ms = int((time.time() - start_time) * 1000)

            logger.info(f"[KnowledgeService] LLM 回退查詢成功: {query_time_ms}ms")

            # 標註來源
            source_label = (
                "公司內部知識庫" if source_type == KnowledgeSourceType.INTERNAL else "網路搜尋"
            )
            sources = [{"type": source_type.value, "source": source_label}]

            return KnowledgeQueryResult(
                success=True,
                answer=llm_result,
                sources=sources,
                source_type=source_type,
                query_time_ms=query_time_ms,
            )

        except Exception as e:
            query_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[KnowledgeService] LLM 回退也失敗: {e}")

            return KnowledgeQueryResult(
                success=False,
                error=str(e),
                source_type=source_type,
                query_time_ms=query_time_ms,
            )

    async def _call_ka_agent(
        self,
        query: str,
        source_type: KnowledgeSourceType,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        調用 KA-Agent 執行知識查詢

        根據 KA-Agent 規格書，支援：
        - knowledge.query: 混合檢索
        - ka.retrieve: 資產檢索
        - ka.list: 資產列表
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._ai_box_api_url}/api/v1/knowledge/query",
                    json={
                        "request_id": f"mm_knowledge_{session_id or 'unknown'}",
                        "query": query,
                        "agent_id": "ka-agent",
                        "user_id": session_id,
                        "metadata": {
                            "caller_agent_id": "mm-agent",
                            "caller_agent_key": "-h0tjyh",
                        },
                        "options": {
                            "query_type": "hybrid",
                            "top_k": 10,
                            "include_graph": True,
                        },
                    },
                    headers={"Authorization": f"Bearer {self._api_key}"} if self._api_key else {},
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                    }

                result = response.json()

                # 解析 KA-Agent 響應
                if not result.get("success", False):
                    return {"success": False, "error": result.get("message", "Unknown error")}

                # 提取答案和來源
                answer = ""
                sources = []

                results = result.get("results", [])
                for r in results[:5]:
                    sources.append(
                        {
                            "filename": r.get("filename", ""),
                            "content": r.get("content", "")[:200],
                            "confidence": r.get("confidence", 0),
                        }
                    )
                    if not answer:
                        answer = r.get("content", "")
                return {"success": True, "answer": answer, "sources": sources}

        except httpx.TimeoutException:
            return {"success": False, "error": "KA-Agent 調用超時"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _call_llm_knowledge(
        self,
        query: str,
        source_type: KnowledgeSourceType,
    ) -> str:
        """
        調用 LLM 生成知識回答（回退機制）

        當 KA-Agent 不可用時，使用 LLM 回答知識問題
        """
        import httpx

        # 根據來源類型生成不同的 system prompt
        if source_type == KnowledgeSourceType.INTERNAL:
            system_prompt = """你是一位專業的企業管理顧問，負責回答公司內部管理相關問題。

            回答原則：
            1. 基於最佳實踐和通用管理原則回答
            2. 如果涉及具體公司流程，說明「一般企業做法如下...」
            3. 保持專業、簡潔
            4. 不編造具體的公司規定或文件

            如果無法確定具體答案，誠實說明需要查閱公司內部文件。
            """
        else:
            system_prompt = """你是一位專業的庫存管理和供應鏈管理顧問，負責回答專業知識問題。

            回答原則：
            1. 提供準確、專業的知識解答
            2. 引用相關領域的最佳實踐
            3. 保持簡潔明瞭
            4. 如有不確定的地方，誠實說明

            目標：幫助用戶理解專業概念和最佳實踐。
            """

        try:
            async with httpx.AsyncClient(timeout=self._llm_timeout) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self._llm_model,
                        "prompt": f"{system_prompt}\n\n用戶問題：{query}",
                        "stream": False,
                    },
                )

                if response.status_code != 200:
                    raise Exception(f"LLM 調用失敗: HTTP {response.status_code}")

                data = response.json()
                answer = data.get("response", "") or data.get("thinking", "")

                # 標註這是 LLM 生成的回答
                source_note = "\n\n---\n*以上回答由 AI 根據專業知識生成，如需準確的公司內部規定，請查閱相關文件。*"
                if source_type == KnowledgeSourceType.INTERNAL:
                    source_note = (
                        "\n\n---\n*回答來源：一般企業管理實踐，具體規定請參考公司內部文件。*"
                    )

                return answer + source_note

        except Exception as e:
            logger.error(f"[KnowledgeService] LLM 調用失敗: {e}")
            raise

    async def list_knowledge_assets(
        self,
        domain: Optional[str] = None,
        major: Optional[str] = None,
        lifecycle_state: str = "Active",
    ) -> Dict[str, Any]:
        """
        列出知識資產

        Args:
            domain: 知識領域
            major: 專業層
            lifecycle_state: 生命週期狀態

        Returns:
            知識資產列表
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._ai_box_api_url}/api/v1/agents/execute",
                    json={
                        "agent_id": "ka-agent",
                        "task": {
                            "task_id": f"mm_list_{id(self)}",
                            "task_data": {
                                "action": "ka.list",
                                "domain": domain,
                                "major": major,
                                "lifecycle_state": lifecycle_state,
                            },
                            "metadata": {
                                "caller_agent_id": "mm-agent",
                                "caller_agent_key": "-h0tjyh",
                            },
                        },
                    },
                    headers={"Authorization": f"Bearer {self._api_key}"} if self._api_key else {},
                )

                if response.status_code != 200:
                    return {"success": False, "error": response.text}

                return response.json()

        except Exception as e:
            return {"success": False, "error": str(e)}


# 全域知識服務實例
_knowledge_service: Optional[KnowledgeService] = None


def get_knowledge_service() -> KnowledgeService:
    """取得全域知識服務實例"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
