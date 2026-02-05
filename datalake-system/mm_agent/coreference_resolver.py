# 代碼功能說明: 指代消解器 - 規則基礎 + LLM + AAM 長期記憶混合
# 創建日期: 2026-02-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-02

"""指代消解器 - 規則基礎 + LLM + AAM 長期記憶混合方案"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 嘗試導入 AAM 模塊
_AAM_AVAILABLE = False
try:
    import sys

    sys.path.insert(0, "/home/daniel/ai-box")
    from agents.infra.memory.aam.models import Memory, MemoryType, MemoryPriority
    from agents.infra.memory.aam.qdrant_adapter import QdrantAdapter

    _AAM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AAM 模塊不可用: {e}")
    Memory = None
    MemoryType = None
    MemoryPriority = None
    QdrantAdapter = None


class ResolutionResult(BaseModel):
    """指代消解結果"""

    resolved: bool  # 是否成功消解
    resolved_query: str  # 消解後的查詢
    entities: Dict[str, Any]  # 解析出的實體
    method: str  # 使用的方法（'rule', 'llm', 'aam'）
    confidence: float  # 置信度（0-1）


class CoreferenceResolver:
    """指代消解器 - 規則基礎 + LLM + AAM 長期記憶混合"""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen3:32b",
        user_id: str = "default",
        enable_aam: bool = True,
    ):
        """
        初始化指代消解器

        Args:
            ollama_url: Ollama 服務 URL
            model: LLM 模型名稱（推薦：qwen3:32b）
            user_id: 用戶 ID（用於 AAM User Isolation）
            enable_aam: 是否啟用 AAM 長期記憶
        """
        self._ollama_url = ollama_url
        self._model = model
        self._user_id = user_id
        self._enable_aam = False  # 暫時禁用 AAM，避免每次請求載入 embedding model
        self._llm_available = self._check_llm_available()

        # AAM Qdrant 適配器（禁用）
        self._qdrant_adapter = None

        # 繁體中文代詞列表
        self._pronouns = {
            "近程": ["這個", "那個", "它", "此", "是"],
            "遠程": ["那個", "那", "是"],
            "人稱": ["他", "她", "它"],
        }

        # 物料管理專業詞彙表
        self._domain_vocab = {
            "料號": ["料號", "品號", "型號", "編號"],
            "庫存": ["庫存", "存量", "剩餘", "結存", "還有多少", "總共有多少", "存貨"],
            "採購": ["採購", "買", "買進", "進貨", "收料"],
            "銷售": ["銷售", "賣", "賣出", "出貨", "出庫"],
            "領料": ["領料", "領用", "生產領料"],
            "報廢": ["報廢", "報損", "損耗"],
            "時間": ["上月", "上個月", "最近", "今年", "去年", "本週", "本季"],
        }

    def _check_llm_available(self) -> bool:
        """檢查 LLM 是否可用"""
        try:
            import requests

            response = requests.get(f"{self._ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"LLM 不可用，將僅使用規則基礎方法: {e}")
            return False

    def resolve(
        self,
        current_query: str,
        context_entities: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        user_id: Optional[str] = None,  # 新增：支援動態 user_id
    ) -> ResolutionResult:
        """
        指代消解主方法

        Args:
            current_query: 當前查詢
            context_entities: 上下文實體（料號、tlf19、意圖等）
            conversation_history: 對話歷史
            user_id: 用戶 ID（用於 AAM，覆蓋建構時的 user_id）

        Returns:
            指代消解結果
        """
        effective_user_id = user_id or self._user_id

        # Step 0: 檢查是否需要指代消解
        if not self._needs_resolution(current_query):
            return ResolutionResult(
                resolved=False,
                resolved_query=current_query,
                entities={},
                method="none",
                confidence=1.0,
            )

        # Step 0.5: AAM 長期記憶查詢（新增）
        aam_entities = {}
        if self._qdrant_adapter and effective_user_id:
            aam_entities = self._query_aam_memory(
                user_id=effective_user_id,
                query=current_query,
            )
            if aam_entities:
                logger.info(f"AAM 長期記憶查詢結果: {aam_entities}")

        # 合併上下文實體和 AAM 實體（AAM 優先）
        merged_entities = {**context_entities, **aam_entities}

        # Step 1: 嘗試 AAM 消解（新增 - 最高優先級）
        if aam_entities:
            aam_result = self._resolve_by_aam(current_query, aam_entities)
            if aam_result.resolved and aam_result.confidence >= 0.85:
                # 存儲到 AAM
                self._store_to_aam(effective_user_id, current_query, aam_result)
                logger.info(f"AAM 消解成功: {current_query} -> {aam_result.resolved_query}")
                return aam_result

        # Step 2: 嘗試規則基礎消解（快速）
        rule_result = self._resolve_by_rules(current_query, merged_entities)
        if rule_result.resolved and rule_result.confidence >= 0.8:
            # 存儲到 AAM
            self._store_to_aam(effective_user_id, current_query, rule_result)
            logger.info(f"規則基礎消解成功: {current_query} -> {rule_result.resolved_query}")
            return rule_result

        # Step 3: 如果規則基礎不確定，使用 LLM（高精度）
        if self._llm_available:
            llm_result = self._resolve_by_llm(current_query, merged_entities, conversation_history)
            logger.info(f"LLM 消解成功: {current_query} -> {llm_result.resolved_query}")
            # 存儲到 AAM
            self._store_to_aam(effective_user_id, current_query, llm_result)
            return llm_result

        # Step 4: LLM 不可用，返回規則基礎結果（即使置信度低）
        logger.info(
            f"LLM 不可用，使用規則基礎消解: {current_query} -> {rule_result.resolved_query}"
        )
        # 存儲到 AAM
        self._store_to_aam(effective_user_id, current_query, rule_result)
        return rule_result

    def _query_aam_memory(
        self,
        user_id: str,
        query: str,
    ) -> Dict[str, Any]:
        """
        從 AAM 長期記憶查詢相關實體

        Args:
            user_id: 用戶 ID
            query: 當前查詢

        Returns:
            查詢到的實體字典
        """
        if not self._qdrant_adapter:
            return {}

        try:
            # 查詢料號相關記憶
            part_memories = self._qdrant_adapter.search(
                query=query,
                user_id=user_id,
                entity_type="part_number",
                min_confidence=0.7,
                limit=3,
            )

            # 查詢 tlf19 相關記憶
            tlf19_memories = self._qdrant_adapter.search(
                query=query,
                user_id=user_id,
                entity_type="tlf19",
                min_confidence=0.7,
                limit=3,
            )

            # 構建實體字典
            entities = {}

            # 取置信度最高的料號
            if part_memories:
                best_part = max(part_memories, key=lambda m: m.confidence)
                entities["part_number"] = best_part.entity_value
                # 更新訪問計數
                self._qdrant_adapter.update_access(best_part.memory_id)

            # 取置信度最高的 tlf19
            if tlf19_memories:
                best_tlf19 = max(tlf19_memories, key=lambda m: m.confidence)
                entities["tlf19"] = best_tlf19.entity_value
                # 更新訪問計數
                self._qdrant_adapter.update_access(best_tlf19.memory_id)

            return entities

        except Exception as e:
            logger.error(f"AAM 查詢失敗: {e}")
            return {}

    def _store_to_aam(
        self,
        user_id: str,
        query: str,
        result: ResolutionResult,
    ) -> None:
        """
        將消解結果存儲到 AAM 長期記憶

        Args:
            user_id: 用戶 ID
            query: 原始查詢
            result: 消解結果
        """
        if not self._qdrant_adapter or not user_id:
            return

        try:
            from agents.infra.memory.aam.models import Memory, MemoryType, MemoryPriority

            # 存儲料號實體
            if result.entities.get("part_number"):
                part_number = result.entities["part_number"]

                # 檢查是否已存在
                existing = self._qdrant_adapter.find_by_exact_match(
                    user_id=user_id,
                    entity_type="part_number",
                    entity_value=part_number,
                )

                if existing:
                    # 更新置信度
                    self._qdrant_adapter.update(
                        Memory(
                            memory_id=existing.memory_id,
                            content=f"料號: {part_number}",
                            memory_type=MemoryType.LONG_TERM,
                            priority=MemoryPriority.HIGH,
                            user_id=user_id,
                            entity_type="part_number",
                            entity_value=part_number,
                            confidence=result.confidence,
                            status="active",
                        )
                    )
                else:
                    # 新建記憶
                    memory = Memory(
                        memory_id=f"part_{user_id}_{part_number}_{int(datetime.now().timestamp())}",
                        content=f"料號: {part_number}",
                        memory_type=MemoryType.LONG_TERM,
                        priority=MemoryPriority.HIGH,
                        user_id=user_id,
                        entity_type="part_number",
                        entity_value=part_number,
                        confidence=result.confidence,
                        status="active",
                    )
                    self._qdrant_adapter.store(memory)

            # 存儲 tlf19 實體
            if result.entities.get("tlf19"):
                tlf19 = result.entities["tlf19"]

                existing = self._qdrant_adapter.find_by_exact_match(
                    user_id=user_id,
                    entity_type="tlf19",
                    entity_value=tlf19,
                )

                if not existing:
                    memory = Memory(
                        memory_id=f"tlf19_{user_id}_{tlf19}_{int(datetime.now().timestamp())}",
                        content=f"動作代碼: {tlf19}",
                        memory_type=MemoryType.LONG_TERM,
                        priority=MemoryPriority.MEDIUM,
                        user_id=user_id,
                        entity_type="tlf19",
                        entity_value=tlf19,
                        confidence=result.confidence,
                        status="active",
                    )
                    self._qdrant_adapter.store(memory)

            logger.debug(f"已存儲到 AAM: user={user_id}, entities={result.entities}")

        except Exception as e:
            logger.error(f"存儲到 AAM 失敗: {e}")

    def _resolve_by_aam(
        self,
        current_query: str,
        aam_entities: Dict[str, Any],
    ) -> ResolutionResult:
        """
        AAM 消解（使用長期記憶）

        Args:
            current_query: 當前查詢
            aam_entities: 從 AAM 查詢到的實體

        Returns:
            消解結果
        """
        resolved_query = current_query
        resolved_entities = {}
        confidence = 0.0

        part_number = aam_entities.get("part_number")
        tlf19 = aam_entities.get("tlf19")

        # 處理代詞替換
        for pronoun_type, pronouns in self._pronouns.items():
            for pronoun in pronouns:
                if pronoun in resolved_query and part_number:
                    resolved_query = resolved_query.replace(pronoun, part_number)
                    resolved_entities["part_number"] = part_number
                    confidence += 0.35
                    break

        # 處理省略
        has_action = any(
            action in resolved_query
            for action in ["庫存", "存貨", "採購", "買", "賣", "領料", "報廢"]
        )
        has_part_number = any(kw in resolved_query for kw in ["RM05", "ABC-", "10-", "料號"])

        if has_action and not has_part_number and part_number:
            resolved_query = f"{part_number} {resolved_query}"
            resolved_entities["part_number"] = part_number
            confidence += 0.4

        if tlf19:
            resolved_entities["tlf19"] = tlf19
            confidence += 0.15

        confidence = min(confidence, 0.95)

        return ResolutionResult(
            resolved=len(resolved_entities) > 0,
            resolved_query=resolved_query,
            entities=resolved_entities,
            method="aam",
            confidence=confidence,
        )

    def _needs_resolution(self, query: str) -> bool:
        """檢查是否需要指代消解"""
        # 檢查代詞
        for pronoun_list in self._pronouns.values():
            for pronoun in pronoun_list:
                if pronoun in query:
                    return True

        # 檢查省略情況（沒有料號但有動作詞）
        has_action = any(
            action in query for vocab in self._domain_vocab.values() for action in vocab
        )
        has_part_number = any(keyword in query for keyword in ["RM05", "ABC-", "10-", "料號"])

        # 有動作但沒有料號，可能是省略
        if has_action and not has_part_number:
            return True

        return False

    def _resolve_by_rules(
        self, current_query: str, context_entities: Dict[str, Any]
    ) -> ResolutionResult:
        """
        規則基礎消解（快速）

        處理簡單的代詞替換，例如：
        - "這個料號" → "RM05-008"
        - "那個" → "ABC-123"
        - "它" → "RM05-008"
        """
        resolved_query = current_query
        resolved_entities = {}
        confidence = 0.0

        # 優先從上下文獲取實體
        part_number = context_entities.get("part_number")
        tlf19 = context_entities.get("tlf19")
        last_intent = context_entities.get("intent")

        # 1. 處理近程代詞（這個、這）
        for pronoun in self._pronouns["近程"]:
            if pronoun in resolved_query:
                if part_number:
                    resolved_query = resolved_query.replace(pronoun, part_number)
                    resolved_entities["part_number"] = part_number
                    confidence += 0.3
                    break

        # 2. 處理遠程代詞（那個、那）
        for pronoun in self._pronouns["遠程"]:
            if pronoun in resolved_query:
                if part_number:
                    resolved_query = resolved_query.replace(pronoun, part_number)
                    resolved_entities["part_number"] = part_number
                    confidence += 0.3
                    break

        # 3. 處理人稱代詞（他、她、它）
        for pronoun in self._pronouns["人稱"]:
            if pronoun in resolved_query:
                if part_number:
                    resolved_query = resolved_query.replace(pronoun, part_number)
                    resolved_entities["part_number"] = part_number
                    confidence += 0.2
                    break

        # 4. 處理省略（沒有料號但有動作）
        # 檢查是否有動作詞但沒有料號
        has_action = any(
            action in resolved_query
            for action in ["庫存", "存貨", "採購", "買", "賣", "領料", "報廢"]
        )
        has_part_number_in_query = any(
            kw in resolved_query for kw in ["RM05", "ABC-", "10-", "料號"]
        )

        if has_action and not has_part_number_in_query and part_number:
            # 在查詢開頭插入料號
            resolved_query = f"{part_number} {resolved_query}"
            resolved_entities["part_number"] = part_number
            confidence += 0.4

        # 5. 添加其他實體
        if tlf19 and not any(
            kw in resolved_query for kw in ["採購", "買進", "銷售", "賣出", "領料", "報廢"]
        ):
            # 如果查詢中沒有明確動作，使用上下文的 tlf19
            resolved_entities["tlf19"] = tlf19
            confidence += 0.1

        if last_intent:
            resolved_entities["intent"] = last_intent

        # 計算最終置信度（最高 0.9，因為規則基礎方法有局限性）
        confidence = min(confidence, 0.9)

        return ResolutionResult(
            resolved=len(resolved_entities) > 0,
            resolved_query=resolved_query,
            entities=resolved_entities,
            method="rule",
            confidence=confidence,
        )

    def _resolve_by_llm(
        self,
        current_query: str,
        context_entities: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
    ) -> ResolutionResult:
        """
        LLM 消解（高精度）

        使用 qwen3:32b 處理複雜的指代和省略
        """
        # 構建提示詞
        prompt = self._build_llm_prompt(current_query, context_entities, conversation_history)

        try:
            import requests

            # 調用 Ollama API
            response = requests.post(
                f"{self._ollama_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,  # 低溫度，確保精確
                        "max_tokens": 256,
                        "num_predict": 256,
                    },
                },
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                llm_output = result.get("response", "").strip()

                # 解析 LLM 輸出
                parsed = self._parse_llm_output(llm_output, current_query)

                return ResolutionResult(
                    resolved=parsed["resolved"],
                    resolved_query=parsed["resolved_query"],
                    entities=parsed["entities"],
                    method="llm",
                    confidence=0.95,  # LLM 置信度高
                )
            else:
                logger.error(f"LLM 請求失敗: {response.status_code}")
                raise Exception("LLM request failed")

        except Exception as e:
            logger.error(f"LLM 消解失敗: {e}")
            # 回退到規則基礎方法
            return self._resolve_by_rules(current_query, context_entities)

    def _build_llm_prompt(
        self,
        current_query: str,
        context_entities: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
    ) -> str:
        """構建 LLM 提示詞"""
        # 構建上下文信息
        context_info = []
        if context_entities.get("part_number"):
            context_info.append(f"料號: {context_entities['part_number']}")
        if context_entities.get("tlf19"):
            context_info.append(f"動作代碼: {context_entities['tlf19']}")
        if context_entities.get("intent"):
            context_info.append(f"上次意圖: {context_entities['intent']}")

        context_str = "\n".join(context_info) if context_info else "無"

        # 構建對話歷史
        history_str = ""
        if conversation_history:
            last_msgs = conversation_history[-3:]  # 只取最近 3 條
            history_lines = []
            for msg in last_msgs:
                role = "用戶" if msg["role"] == "user" else "助手"
                history_lines.append(f"{role}: {msg['content']}")
            history_str = "\n".join(history_lines)
        else:
            history_str = "無對話歷史"

        prompt = f"""你是一個專業的中文指代消解助手，專注於物料管理領域。

【上下文信息】
{context_str}

【對話歷史】
{history_str}

【當前查詢】
{current_query}

【任務】
1. 識別當前查詢中的指代詞（這個、那個、它、這、那）和省略信息
2. 從上下文中提取相關實體並填充到查詢中
3. 生成消解後的完整查詢

【輸出格式】（嚴格按照 JSON 格式輸出，不要有多餘文字）:
{{
  "resolved": true/false,
  "resolved_query": "消解後的查詢",
  "entities": {{
    "part_number": "料號（如果有）",
    "tlf19": "動作代碼（如果有）",
    "intent": "意圖（如果有）"
  }},
  "explanation": "消解說明"
}}

【示例】
查詢: "這個料號庫存還有多少"
上下文: 料號: RM05-008
輸出: {{"resolved": true, "resolved_query": "RM05-008庫存還有多少", "entities": {{"part_number": "RM05-008"}}, "explanation": "將'這個'替換為上下文中的料號'RM05-008'"}}

現在請輸出 JSON:"""

        return prompt

    def _parse_llm_output(self, llm_output: str, original_query: str) -> Dict[str, Any]:
        """解析 LLM 輸出"""
        try:
            # 嘗試提取 JSON
            import re

            json_match = re.search(r"\{.*\}", llm_output, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)

                return {
                    "resolved": parsed.get("resolved", False),
                    "resolved_query": parsed.get("resolved_query", original_query),
                    "entities": parsed.get("entities", {}),
                }
        except Exception as e:
            logger.error(f"解析 LLM 輸出失敗: {e}")

        # 解析失敗，返回原始查詢
        return {
            "resolved": False,
            "resolved_query": original_query,
            "entities": {},
        }


if __name__ == "__main__":
    # 測試指代消解器
    resolver = CoreferenceResolver(model="qwen3:32b")

    # 測試用例
    context_entities = {
        "part_number": "RM05-008",
        "tlf19": "101",
        "intent": "purchase",
        "table_name": "tlf_file",
    }

    conversation_history = [
        {"role": "user", "content": "RM05-008 上月買進多少"},
        {"role": "assistant", "content": "RM05-008 採購進貨共 5,000 KG"},
    ]

    test_queries = [
        "這個料號庫存還有多少",
        "庫存還有多少",  # 省略
        "那個賣出多少",
        "它最近有動靜嗎",
    ]

    print("=" * 70)
    print("指代消解測試")
    print("=" * 70)

    for query in test_queries:
        print(f"\n原始查詢: {query}")
        result = resolver.resolve(query, context_entities, conversation_history)
        print(f"消解結果: {result.resolved_query}")
        print(f"使用方法: {result.method}")
        print(f"置信度: {result.confidence:.2f}")
        print(f"實體: {result.entities}")
