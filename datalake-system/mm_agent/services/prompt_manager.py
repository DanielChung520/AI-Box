# 代碼功能說明: 提示詞管理服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""提示詞管理服務 - 管理LLM提示詞"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 添加 AI-Box 根目錄到 Python 路徑
_ai_box_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_ai_box_root) not in sys.path:
    sys.path.insert(0, str(_ai_box_root))

# System Prompt定義
WAREHOUSE_AGENT_SYSTEM_PROMPT = """你是一個庫存管理助手（庫管員 Agent），專門負責處理庫存管理相關的業務邏輯。

你的職責：
1. 理解用戶的庫存管理指令
2. 識別用戶要執行的操作類型（查詢料號、查詢庫存、缺料分析、生成採購單等）
3. 提取業務參數（料號、數量等）
4. 理解上下文中的指代（如「剛才查的那個料號」）

支持的操作類型：
- query_part: 查詢物料基本信息
- query_stock: 查詢庫存信息
- analyze_shortage: 缺料分析
- generate_purchase_order: 生成採購單
- adjust_stock: 調整庫存（虛擬）

輸出要求：
- 必須返回有效的 JSON 格式
- 包含識別的意圖（intent）、置信度（confidence）、提取的參數（parameters）
- 如果指令不明確，標記需要澄清（clarification_needed）並提供澄清問題
"""


class PromptManager:
    """提示詞管理服務"""

    def __init__(self) -> None:
        """初始化提示詞管理器"""
        self._logger = logger
        self._system_prompt = WAREHOUSE_AGENT_SYSTEM_PROMPT

    def get_system_prompt(self) -> str:
        """獲取System Prompt

        Returns:
            System Prompt字符串
        """
        return self._system_prompt

    def build_semantic_analysis_prompt(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """構建語義分析提示詞

        Args:
            instruction: 用戶指令
            context: 上下文信息（可選）

        Returns:
            構建好的提示詞
        """
        prompt = f"""分析以下用戶指令，識別意圖並提取參數。

用戶指令：
{instruction}

"""

        # 添加上下文信息（如果提供）
        if context:
            context_str = json.dumps(context, ensure_ascii=False, indent=2)
            prompt += f"""上下文信息：
{context_str}

注意：如果指令中包含指代（如「剛才查的那個料號」），請從上下文中獲取對應的值。

"""

        prompt += """請返回以下 JSON 格式：
{
    "intent": "query_part|query_stock|query_stock_history|analyze_shortage|generate_purchase_order|adjust_stock",
    "confidence": 0.0-1.0,
    "parameters": {
        "part_number": "料號（如果可提取）",
        "quantity": 數量（如果可提取）,
        "location": "庫存位置（如果可提取）",
        "start_date": "開始日期（如果可提取，如 YYYY-MM-DD）",
        "end_date": "結束日期（如果可提取，如 YYYY-MM-DD）"
    },
    "clarification_needed": false,
    "clarification_questions": []
}

如果指令包含模糊的時間詞彙（如「最近」、「這幾天」），且意圖是查詢歷史記錄，請設置 clarification_needed 為 true，並提供時間範圍澄清問題。

時間範圍澄清選項：
- 今天
- 最近一週
- 最近一個月
- 最近三個月
- 最近六個月
- 指定日期範圍"""

        return prompt

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> str:
        """調用LLM生成響應

        Args:
            system_prompt: System Prompt
            user_prompt: User Prompt
            temperature: 溫度參數（0-1）
            max_tokens: 最大token數

        Returns:
            LLM響應文本
        """
        try:
            from llm.clients.ollama import OllamaClient

            client = OllamaClient()

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            result = await client.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                purpose="mm_agent_semantic_analysis",
            )

            content = result.get("content", "")
            if not content:
                self._logger.warning("LLM返回空響應")
                return ""

            return content

        except ImportError as e:
            self._logger.warning(f"無法導入AI-Box LLM客戶端，回退到正則表達式: {e}")
            return ""
        except Exception as e:
            self._logger.warning(f"LLM調用失敗，回退到正則表達式: {e}")
            return ""

    def parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM響應為JSON

        Args:
            response: LLM響應文本

        Returns:
            解析後的JSON字典

        Raises:
            ValueError: 解析失敗時拋出異常
        """
        try:
            # 嘗試直接解析JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果直接解析失敗，嘗試提取JSON部分
            # 移除可能的代碼塊標記
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            try:
                return json.loads(cleaned_response)
            except json.JSONDecodeError as e:
                self._logger.error(f"無法解析LLM響應為JSON: {e}, 響應內容: {response}")
                raise ValueError(f"無法解析LLM響應為JSON: {e}") from e

    async def generate_stock_response(
        self,
        warehouse: str,
        stock_list: list,
        count: int,
        user_instruction: str = "",
    ) -> str:
        """使用 LLM 生成庫存查詢回覆

        Args:
            warehouse: 倉庫代碼
            stock_list: 庫存資料列表
            count: 總筆數
            user_instruction: 用戶原始指令

        Returns:
            LLM 生成的格式化回覆
        """
        system_prompt = """你是一個專業的庫存管理助手，專門將查詢結果整理成對用户友善的回覆。

## 格式化規則

### 數值格式
- 數量使用千分位分隔（如：100,416）
- 金額保留小數點兩位（如：1,234.56）
- 比例顯示為百分比（如：25.30%）

### 日期格式
- 所有日期使用 yyyy-mm-dd 格式（如：2026-02-09）

### 欄位名稱
- 使用有意義的中文欄位名稱
- 不要使用資料庫欄位名（如 img01, img02）
- 範例：
  - img01 → 料號
  - img02 → 倉庫
  - img04 → 批次
  - img10 → 庫存數量

### 回覆格式選擇
1. **單筆資料**：用簡潔的摘要格式
2. **多筆資料（<10筆）**：用列表格式
3. **多筆資料（>=10筆）**：用 Markdown 表格

### 標題規則
- 使用有意義的標題
- 標題要包含查詢結果的關鍵資訊
- 範例：「W03 倉庫庫存清單（共 15 筆）」

## 請將以下庫存資料整理成對用户友善的回覆："""

        # 構建庫存數據摘要
        stock_data = []
        for i, item in enumerate(stock_list[:50], 1):
            part_no = item.get("part_number", "-")
            batch = item.get("batch_no", "-")
            qty = item.get("quantity", 0)
            stock_data.append(f"{i}. 料號: {part_no}, 批次: {batch}, 數量: {qty:,}")

        data_summary = "\n".join(stock_data)
        if len(stock_list) > 50:
            data_summary += f"\n... 還有 {len(stock_list) - 50} 筆資料"

        # 計算總數量
        total_quantity = sum(item.get("quantity", 0) for item in stock_list)

        user_prompt = f"""用戶指令：{user_instruction}

倉庫代碼：{warehouse}
資料筆數：{count}

庫存數據：
{data_summary}

庫存總數量：{total_quantity:,} 件

請將上述庫存數據整理成專業、易讀的回覆。"""

        try:
            response = await self.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=2000,
            )
            if response and response.strip():
                return response.strip()
        except Exception as e:
            self._logger.warning(f"LLM 生成庫存回覆失敗: {e}")

        # 回退到手動格式（簡單表格）
        if warehouse == "所有倉庫":
            explanation = f"### 📦 所有倉庫庫存清單（共 {count} 筆）\n\n"
        else:
            explanation = f"### 📦 {warehouse} 倉庫庫存清單（共 {count} 筆）\n\n"
        explanation += "| 序號 | 料號 | 批次 | 數量 |\n"
        explanation += "|------|------|------|------|\n"
        for i, item in enumerate(stock_list[:30], 1):
            part_no = item.get("part_number", "-")
            batch = item.get("batch_no", "-")
            qty = item.get("quantity", 0)
            explanation += f"| {i} | {part_no} | {batch} | {qty:,} |\n"
        if count > 30:
            explanation += f"\n*... 還有 {count - 30} 筆，請縮小查詢範圍*\n"
        return explanation

    async def generate_transaction_response(
        self,
        part_number: str,
        transactions: list,
        count: int,
        start_date: str = "",
        end_date: str = "",
        user_instruction: str = "",
    ) -> str:
        """使用 LLM 生成交易歷史回覆

        Args:
            part_number: 料號
            transactions: 交易記錄列表
            count: 總筆數
            start_date: 開始日期
            end_date: 結束日期
            user_instruction: 用戶原始指令

        Returns:
            LLM 生成的格式化回覆
        """
        # 交易類型說明
        transaction_types = {
            "101": "採購進貨",
            "102": "退貨入庫",
            "201": "銷售出庫",
            "202": "退貨出庫",
            "301": "調撥出庫",
        }

        system_prompt = """你是一個專業的庫存管理助手，專門將交易記錄整理成對用户友善的回覆。

## 格式化規則

### 日期格式
- 所有日期使用 yyyy-mm-dd 格式（如：2024-10-23）

### 數值格式
- 數量使用千分位分隔（如：-46, 1,234）
- 正數表示入庫，負數表示出庫

### 交易類型
- 101：採購進貨
- 102：退貨入庫
- 201：銷售出庫
- 202：退貨出庫
- 301：調撥出庫

### 回覆格式
- 使用 Markdown 表格呈現交易記錄
- 標題要包含料號和時間範圍
- 適當說明交易類型（入庫/出庫）

## 請將以下交易記錄整理成對用户友善的回覆："""

        # 構建交易數據摘要
        tx_data = []
        for i, tx in enumerate(transactions[:30], 1):
            tx_type = tx.get("transaction_type", "-")
            tx_date = tx.get("trans_date", "-")
            qty = tx.get("quantity", 0)
            unit = tx.get("unit", "件")
            warehouse = tx.get("warehouse", "-")
            tx_type_name = transaction_types.get(tx_type, f"類型{tx_type}")
            tx_data.append(
                f"{i}. 日期: {tx_date}, {tx_type_name}, 數量: {qty:,} {unit}, 倉庫: {warehouse}"
            )

        data_summary = "\n".join(tx_data)
        if len(transactions) > 30:
            data_summary += f"\n... 還有 {len(transactions) - 30} 筆交易記錄"

        # 計算入庫和出庫總數
        inbound_qty = sum(tx.get("quantity", 0) for tx in transactions if tx.get("quantity", 0) > 0)
        outbound_qty = sum(
            abs(tx.get("quantity", 0)) for tx in transactions if tx.get("quantity", 0) < 0
        )

        time_range = f"{start_date} ~ {end_date}" if start_date and end_date else "全部時間"

        user_prompt = f"""用戶指令：{user_instruction}

料號：{part_number}
時間範圍：{time_range}
資料筆數：{count}

交易記錄：
{data_summary}

入庫總數量：{inbound_qty:,} 件
出庫總數量：{outbound_qty:,} 件

請將上述交易記錄整理成專業、易讀的回覆。"""

        try:
            response = await self.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=2000,
            )
            if response and response.strip():
                return response.strip()
        except Exception as e:
            self._logger.warning(f"LLM 生成交易回覆失敗: {e}")

        # 回退到手動格式
        if count == 0:
            return f"料號 {part_number} 在 {time_range} 期間沒有交易記錄。"

        explanation = f"### 📋 {part_number} 交易記錄（{time_range}，共 {count} 筆）\n\n"
        explanation += "| 日期 | 交易類型 | 數量 | 單位 | 倉庫 |\n"
        explanation += "|------|----------|------|------|------|\n"
        for tx in transactions[:30]:
            tx_type = tx.get("transaction_type", "-")
            tx_date = tx.get("trans_date", "-")
            qty = tx.get("quantity", 0)
            unit = tx.get("unit", "件")
            warehouse = tx.get("warehouse", "-")
            tx_type_name = transaction_types.get(tx_type, f"類型{tx_type}")
            explanation += f"| {tx_date} | {tx_type_name} | {qty:,} | {unit} | {warehouse} |\n"
        if count > 30:
            explanation += f"\n*... 還有 {count - 30} 筆，請縮小查詢範圍*\n"
        return explanation

    async def generate_no_data_response(
        self,
        query: str,
        user_instruction: str = "",
    ) -> str:
        """使用 LLM 生成「查無資料」回覆

        Args:
            query: 查詢條件
            user_instruction: 用戶原始指令

        Returns:
            LLM 生成的格式化回覆
        """
        system_prompt = """你是一個專業的庫存管理助手。當查詢結果為空時，需要以友善、專業的方式告知用戶，並提供建議。

## 回覆規則
1. 先確認用戶的查詢條件
2. 明確告知「查無資料」
3. 提供可能的原因和建議
4. 語氣要誠懇、專業

## 範例回覆
「根據您的查詢條件，系統中沒有找到符合的資料。可能的原因：
- 該料號尚未建立
- 查詢條件設定過於嚴格
- 該倉庫/儲位沒有存貨

建議：請確認料號是否正確，或嘗試擴大查詢範圍。」"""

        user_prompt = f"""用戶查詢：{user_instruction}
解析後的查詢條件：{query}

請生成查無資料的回覆。"""

        try:
            response = await self.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=500,
            )
            if response and response.strip():
                return response.strip()
        except Exception as e:
            self._logger.warning(f"LLM 生成查無資料回覆失敗: {e}")

        # 回退
        return f"抱歉，根據您的查詢條件「{user_instruction}」，系統中沒有找到符合的資料。\n\n請確認：\n- 料號是否正確\n- 倉庫編號是否存在\n- 是否需要擴大查詢範圍"

    async def generate_clarification_response(
        self,
        clarification_type: str,
        message: str,
        suggestions: list,
        user_instruction: str = "",
    ) -> str:
        """使用 LLM 生成「需要確認」的回覆

        Args:
            clarification_type: 確認類型（QUERY_SCOPE_TOO_LARGE, INTENT_UNCLEAR 等）
            message: 系統訊息
            suggestions: 建議列表
            user_instruction: 用戶原始指令

        Returns:
            LLM 生成的格式化回覆
        """
        system_prompt = """你是一個專業的庫存管理助手。當需要用戶提供更多資訊時，需要以友善的方式詢問。

## 回覆規則
1. 清楚說明需要什麼資訊
2. 提供具體的建議
3. 語氣要禮貌、明確

## 確認類型說明
- QUERY_SCOPE_TOO_LARGE: 查詢範圍過大，需要更多篩選條件
- INTENT_UNCLEAR: 無法理解查詢意圖，需要用戶重新描述"""

        type_hints = {
            "QUERY_SCOPE_TOO_LARGE": "此查詢範圍過大，請提供更多篩選條件（如：料號、倉庫、特定時間範圍）以縮小查詢範圍。",
            "INTENT_UNCLEAR": "無法理解您的查詢意圖，請重新描述您的需求。",
        }

        user_prompt = f"""用戶查詢：{user_instruction}
系統訊息：{message}
確認類型：{clarification_type}

類型說明：{type_hints.get(clarification_type, "")}

建議：{", ".join(suggestions) if suggestions else "無"}

請生成需要確認的回覆。"""

        try:
            response = await self.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=500,
            )
            if response and response.strip():
                return response.strip()
        except Exception as e:
            self._logger.warning(f"LLM 生成確認回覆失敗: {e}")

        # 回退
        fallback_msgs = {
            "QUERY_SCOPE_TOO_LARGE": f"⚠️ {message}\n\n請提供更多篩選條件（如料號、倉庫）以縮小查詢範圍。",
            "INTENT_UNCLEAR": f"⚠️ {message}\n\n請重新描述您的查詢需求。",
        }
        return fallback_msgs.get(clarification_type, f"⚠️ {message}")

    async def generate_error_response(
        self,
        error_type: str,
        message: str,
        original_query: str = "",
    ) -> str:
        """使用 LLM 生成「執行錯誤」回覆

        Args:
            error_type: 錯誤類型
            message: 錯誤訊息
            original_query: 原始查詢

        Returns:
            LLM 生成的格式化回覆
        """
        system_prompt = """你是一個專業的庫存管理助手。當發生錯誤時，需要以友善的方式告知用戶，並提供解決建議。

## 回覆規則
1. 先表達歉意
2. 說明錯誤原因
3. 提供解決建議
4. 語氣要誠懇、積極

## 錯誤類型說明
- SCHEMA_ERROR: 資料庫結構錯誤
- CONNECTION_ERROR: 連線錯誤（資料庫服務無法連接）
- TIMEOUT: 查詢超時
- INTERNAL_ERROR: 系統內部錯誤"""

        user_prompt = f"""原始查詢：{original_query}
錯誤類型：{error_type}
錯誤訊息：{message}

請生成錯誤回覆。"""

        try:
            response = await self.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=500,
            )
            if response and response.strip():
                return response.strip()
        except Exception as e:
            self._logger.warning(f"LLM 生成錯誤回覆失敗: {e}")

        # 回退
        fallback_msgs = {
            "SCHEMA_ERROR": f"❌ 資料庫結構錯誤：{message}",
            "CONNECTION_ERROR": "❌ 連線錯誤：無法連接到資料庫服務，請稍後再試。",
            "TIMEOUT": f"❌ 查詢超時：{message}，請嘗試更明確的查詢條件。",
            "INTERNAL_ERROR": f"❌ 系統錯誤：{message}，請聯繫系統管理員。",
        }
        return fallback_msgs.get(error_type, f"❌ 錯誤：{message}")
