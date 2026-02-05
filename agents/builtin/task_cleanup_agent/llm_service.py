# 代碼功能說明: Task Cleanup Agent LLM 服務
# 創建日期: 2026-01-23
# 創建人: Daniel Chung

"""LLM 服務，用於 Task Cleanup Agent 的分析和驗證。"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional

import httpx

from agents.builtin.task_cleanup_agent.prompts import (
    analyze_prompt,
    plan_prompt,
    verify_prompt,
)
from agents.builtin.task_cleanup_agent.models import CleanupStats

logger = logging.getLogger(__name__)


class CleanupLLMService:
    """清理任務的 LLM 服務"""
    def __init__(self):
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = "qwen3-coder:30b"

    async def _call_llm(self, prompt: str) -> str:
        """調用 LLM API"""
        url = f"{self.ollama_host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 2048,
            },
        },
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except Exception as e:
            logger.error(f"LLM API 調用失敗: {e}")
            raise

    async def analyze(
        self, user_id: str, task_id: Optional[str], stats: CleanupStats,
    ) -> Dict[str, str]:
        """分析清理數據"""
        stats_dict = {
            "user_tasks": stats.user_tasks,
            "file_metadata": stats.file_metadata,
            "entities": stats.entities,
            "relations": stats.relations,
            "qdrant_collections": stats.qdrant_collections,
            "seaweedfs_directories": stats.seaweedfs_directories,
        }
        prompt = analyze_prompt(user_id, task_id, stats_dict),
        try:
            content = await self._call_llm(prompt)
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(f"LLM 分析失敗: {e}")
            return {
                "urgency": "medium",
                "risk_level": "medium",
                "analysis": f"自動分析失敗: {str(e)}",
                "recommendation": "建議謹慎操作",
            }

    async def generate_plan(
        self, user_id: str, task_id: Optional[str], stats: CleanupStats, analysis: Dict[str, str]
    ) -> Dict[str, Any]:
        """生成清理計劃"""
        stats_dict = {
            "user_tasks": stats.user_tasks,
            "file_metadata": stats.file_metadata,
            "entities": stats.entities,
            "relations": stats.relations,
            "qdrant_collections": stats.qdrant_collections,
            "seaweedfs_directories": stats.seaweedfs_directories,
        }
        prompt = plan_prompt(user_id, task_id, stats_dict, analysis),
        try:
            content = await self._call_llm(prompt)
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(f"LLM 生成計劃失敗: {e}")
            return {
                "steps": ["執行標準清理流程"],
                "estimated_impact": "清理所有關聯數據",
                "warnings": [f"生成計劃失敗，使用默認計劃: {str(e)}"],
            }

    async def verify(
        self, user_id: str, task_id: Optional[str], stats: CleanupStats, result: CleanupStats,
    ) -> Dict[str, Any]:
        """驗證清理結果"""
        stats_dict = {
            "user_tasks": stats.user_tasks,
            "file_metadata": stats.file_metadata,
            "entities": stats.entities,
            "relations": stats.relations,
        }
        result_dict = {
            "user_tasks": result.user_tasks,
            "file_metadata": result.file_metadata,
            "entities": result.entities,
            "relations": result.relations,
        }
        prompt = verify_prompt(user_id, task_id, stats_dict, result_dict),
        try:
            content = await self._call_llm(prompt)
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(f"LLM 驗證失敗: {e}")
            return {
                "is_complete": False,
                "findings": f"驗證過程中出錯: {str(e)}",
                "suggestions": ["建議手動檢查清理結果"],
            }

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON 響應"""
        content = content.strip()
        # 嘗試直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        # 尋找 ```json ... ``` 區塊
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        # 尋找 ``` ... ``` 區塊
        json_match = re.search(r"```\s*([\s\S]*?)\s*```", content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        # 尋找 { ... } 區塊
        brace_match = re.search(r"\{[\s\S]*\}", content)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
        # 尋找 [ ... ] 區塊
        bracket_match = re.search(r"\[[\s\S]*\]", content)
        if bracket_match:
            try:
                return json.loads(bracket_match.group(0))
            except json.JSONDecodeError:
                pass
        logger.warning(f"無法解析 LLM 響應: {content[:100]}...")
        return {"error": "解析失敗", "raw_content": content[:200]}
