# 代碼功能說明: MM-Agent 語義與任務分析測試場景
# 創建日期: 2026-02-21
# 創建人: Daniel Chung
# 測試目的: 驗證 MM-Agent 的語義理解與任務分發能力

"""
MM-Agent 語義與任務分析測試場景

本測試文件包含 100 個測試場景，用於驗證 MM-Agent 對以下意圖的分類能力：

第一層 (GAI Intent) - API Router 處理:
- GREETING: 問候/打招呼
- THANKS: 感謝回覆
- COMPLAIN: 道歉處理
- CANCEL: 取消任務
- CONTINUE: 繼續執行
- MODIFY: 重新處理
- HISTORY: 顯示歷史
- EXPORT: 導出結果
- CONFIRM: 請求確認
- FEEDBACK: 記錄反饋
- CLARIFICATION: 請求澄清
- BUSINESS: 業務請求（轉發 BPA）

第二層 (BPA Intent) - MM-Agent 處理:
- KNOWLEDGE_QUERY: 業務知識問題 → KA-Agent
- SIMPLE_QUERY: 簡單數據查詢 → Data-Agent
- COMPLEX_TASK: 複雜任務 → ReAct Planner
- CLARIFICATION: 需要澄清
- CONTINUE_WORKFLOW: 繼續執行工作流

場景分類:
1. 與知識、數據無關的互動 (打招呼、不完整等)
2. 與知識有關的查詢
3. 與數據有關的查詢
4. 複雜任務 (綜合知識與數據，需要編排)
"""

import pytest
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class GAIIntentType(str, Enum):
    """第一層 GAI 意圖類型"""

    GREETING = "GREETING"
    THANKS = "THANKS"
    COMPLAIN = "COMPLAIN"
    CANCEL = "CANCEL"
    CONTINUE = "CONTINUE"
    MODIFY = "MODIFY"
    HISTORY = "HISTORY"
    EXPORT = "EXPORT"
    CONFIRM = "CONFIRM"
    FEEDBACK = "FEEDBACK"
    CLARIFICATION = "CLARIFICATION"
    BUSINESS = "BUSINESS"


class BPAIntentType(str, Enum):
    """第二層 BPA 意圖類型"""

    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
    SIMPLE_QUERY = "SIMPLE_QUERY"
    COMPLEX_TASK = "COMPLEX_TASK"
    CLARIFICATION = "CLARIFICATION"
    CONTINUE_WORKFLOW = "CONTINUE_WORKFLOW"


class KnowledgeSourceType(str, Enum):
    """知識來源類型"""

    INTERNAL = "internal"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


@dataclass
class IntentTestCase:
    """意圖測試案例"""

    id: int
    category: str  # 場景分類
    user_input: str  # 用戶輸入
    expected_gai_intent: GAIIntentType  # 第一層預期意圖
    expected_bpa_intent: Optional[BPAIntentType] = None  # 第二層預期意圖
    expected_knowledge_source: Optional[KnowledgeSourceType] = None
    description: str = ""  # 場景描述
    needs_clarification: bool = False  # 是否需要澄清
    is_complex_task: bool = False  # 是否為複雜任務


# =============================================================================
# 第一部分：與知識、數據無關的互動 (15 個場景)
# =============================================================================

GAITING_SCENARIOS = [
    # 問候類 (GREETING)
    IntentTestCase(
        id=1,
        category="打招呼-基本問候",
        user_input="你好",
        expected_gai_intent=GAIIntentType.GREETING,
        description="基本問候語",
    ),
    IntentTestCase(
        id=2,
        category="打招呼-早安",
        user_input="早安",
        expected_gai_intent=GAIIntentType.GREETING,
        description="早晨問候",
    ),
    IntentTestCase(
        id=3,
        category="打招呼-晚安",
        user_input="晚安，辛苦了",
        expected_gai_intent=GAIIntentType.GREETING,
        description="晚間問候",
    ),
    IntentTestCase(
        id=4,
        category="打招呼-Hi",
        user_input="Hi there",
        expected_gai_intent=GAIIntentType.GREETING,
        description="英文問候",
    ),
    IntentTestCase(
        id=5,
        category="打招呼-在嗎",
        user_input="在嗎？",
        expected_gai_intent=GAIIntentType.GREETING,
        description="確認在線",
    ),
    # 感謝類 (THANKS)
    IntentTestCase(
        id=6,
        category="感謝-基本感謝",
        user_input="謝謝你",
        expected_gai_intent=GAIIntentType.THANKS,
        description="基本感謝",
    ),
    IntentTestCase(
        id=7,
        category="感謝-多謝",
        user_input="多謝幫忙",
        expected_gai_intent=GAIIntentType.THANKS,
        description="書面感謝",
    ),
    # 道歉類 (COMPLAIN)
    IntentTestCase(
        id=8,
        category="道歉-抱歉",
        user_input="對不起，麻煩你了",
        expected_gai_intent=GAIIntentType.COMPLAIN,
        description="道歉語",
    ),
    # 取消類 (CANCEL)
    IntentTestCase(
        id=9,
        category="取消-取消任務",
        user_input="算了，不要做了",
        expected_gai_intent=GAIIntentType.CANCEL,
        description="取消任務",
    ),
    IntentTestCase(
        id=10,
        category="取消-停止",
        user_input="停止這個操作",
        expected_gai_intent=GAIIntentType.CANCEL,
        description="停止操作",
    ),
    # 確認類 (CONFIRM)
    IntentTestCase(
        id=11,
        category="確認-請求確認",
        user_input="請確認這筆採購單的資訊",
        expected_gai_intent=GAIIntentType.CONFIRM,
        description="請求確認資訊",
    ),
    IntentTestCase(
        id=12,
        category="確認-是否正確",
        user_input="這個數據是對的嗎？",
        expected_gai_intent=GAIIntentType.CONFIRM,
        description="詢問是否正確",
    ),
    # 歷史類 (HISTORY)
    IntentTestCase(
        id=13,
        category="歷史-顯示歷史",
        user_input="顯示之前的查詢記錄",
        expected_gai_intent=GAIIntentType.HISTORY,
        description="請求顯示歷史",
    ),
    # 導出類 (EXPORT)
    IntentTestCase(
        id=14,
        category="導出-導出結果",
        user_input="把結果匯出成Excel",
        expected_gai_intent=GAIIntentType.EXPORT,
        description="導出數據",
    ),
    # 反饋類 (FEEDBACK)
    IntentTestCase(
        id=15,
        category="反饋-記錄反饋",
        user_input="這個功能很好用",
        expected_gai_intent=GAIIntentType.FEEDBACK,
        description="給予反饋",
    ),
]


# =============================================================================
# 第二部分：需要澄清的場景 (15 個場景)
# =============================================================================

CLARIFICATION_SCENARIOS = [
    # 輸入過短
    IntentTestCase(
        id=16,
        category="澄清-過短輸入",
        user_input="倉庫",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="輸入過短，信息不足",
    ),
    IntentTestCase(
        id=17,
        category="澄清-過短輸入",
        user_input="料號",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="只有關鍵詞，無完整語義",
    ),
    IntentTestCase(
        id=18,
        category="澄清-代詞指代",
        user_input="那個料號的庫存",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="使用代詞指代，不明確",
    ),
    IntentTestCase(
        id=19,
        category="澄清-代詞指代",
        user_input="它有多少庫存？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="使用「它」但無前文",
    ),
    IntentTestCase(
        id=20,
        category="澄清-缺少對象",
        user_input="查詢庫存",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="缺少具體查詢對象",
    ),
    IntentTestCase(
        id=21,
        category="澄清-缺少時間",
        user_input="採購量",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="缺少時間範圍",
    ),
    IntentTestCase(
        id=22,
        category="澄清-缺少倉庫",
        user_input="庫存多少",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="未指定倉庫",
    ),
    IntentTestCase(
        id=23,
        category="澄清-模糊需求",
        user_input="給我一些資料",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="需求太過模糊",
    ),
    IntentTestCase(
        id=24,
        category="澄清-模糊需求",
        user_input="相關資訊",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="沒有具體說明要什麼",
    ),
    IntentTestCase(
        id=25,
        category="澄清-矛盾表達",
        user_input="幫我查詢但是不要查詢庫存",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="表達矛盾，無法執行",
    ),
    IntentTestCase(
        id=26,
        category="澄清-單一字符",
        user_input="?",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="僅有符號，無實義",
    ),
    IntentTestCase(
        id=27,
        category="澄清-無意義輸入",
        user_input="aaa",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="無意義字符",
    ),
    IntentTestCase(
        id=28,
        category="澄清-混合語言",
        user_input="查詢 abc",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="混合語言，語義不清",
    ),
    IntentTestCase(
        id=29,
        category="澄清-不完整命令",
        user_input="幫我",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="命令不完整",
    ),
    IntentTestCase(
        id=30,
        category="澄清-重複字符",
        user_input=".........",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.CLARIFICATION,
        needs_clarification=True,
        description="僅有重複符號",
    ),
]


# =============================================================================
# 第三部分：與知識有關的查詢 (25 個場景)
# =============================================================================

KNOWLEDGE_QUERY_SCENARIOS = [
    # 公司內部知識 (INTERNAL)
    IntentTestCase(
        id=31,
        category="知識查詢-內部知識",
        user_input="ERP收料操作步驟是什麼？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.INTERNAL,
        description="詢問ERP操作流程",
    ),
    IntentTestCase(
        id=32,
        category="知識查詢-內部知識",
        user_input="公司的採購審批流程是怎樣的？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.INTERNAL,
        description="詢問公司內部流程",
    ),
    IntentTestCase(
        id=33,
        category="知識查詢-內部知識",
        user_input="如何建立採購單？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.INTERNAL,
        description="詢問建立採購單方法",
    ),
    IntentTestCase(
        id=34,
        category="知識查詢-內部知識",
        user_input="入庫作業的標準流程",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.INTERNAL,
        description="詢問入庫流程",
    ),
    IntentTestCase(
        id=35,
        category="知識查詢-內部知識",
        user_input="我們公司的庫存盤點週期是多久？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.INTERNAL,
        description="詢問公司規定",
    ),
    # 專業術語/外部知識 (EXTERNAL)
    IntentTestCase(
        id=36,
        category="知識查詢-外部知識",
        user_input="什麼是ABC庫存分類法？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問專業術語定義",
    ),
    IntentTestCase(
        id=37,
        category="知識查詢-外部知識",
        user_input="什麼是安全庫存 (Safety Stock)？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問庫存管理術語",
    ),
    IntentTestCase(
        id=38,
        category="知識查詢-外部知識",
        user_input="如何做好庫存管理？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問最佳實踐",
    ),
    IntentTestCase(
        id=39,
        category="知識查詢-外部知識",
        user_input="存貨週轉率的計算公式",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問計算公式",
    ),
    IntentTestCase(
        id=40,
        category="知識查詢-外部知識",
        user_input="什麼是VMI庫存管理？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問專業概念",
    ),
    IntentTestCase(
        id=41,
        category="知識查詢-外部知識",
        user_input="JIT和JIC庫存策略的比較",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問專業比較",
    ),
    IntentTestCase(
        id=42,
        category="知識查詢-外部知識",
        user_input="倉庫管理的5S原則",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問管理原則",
    ),
    IntentTestCase(
        id=43,
        category="知識查詢-外部知識",
        user_input="什麼是經濟訂購量 (EOQ)？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問專業術語",
    ),
    IntentTestCase(
        id=44,
        category="知識查詢-外部知識",
        user_input="供應商管理庫存的優缺點",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問專業知識",
    ),
    IntentTestCase(
        id=45,
        category="知識查詢-外部知識",
        user_input="庫存準確率如何提升？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問改善方法",
    ),
    # 知識庫文件查詢
    IntentTestCase(
        id=46,
        category="知識查詢-知識庫",
        user_input="知識庫裡有哪些文件？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.INTERNAL,
        description="列出知識庫文件",
    ),
    IntentTestCase(
        id=47,
        category="知識查詢-知識庫",
        user_input="查詢我的文件",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.INTERNAL,
        description="查詢個人文件",
    ),
    IntentTestCase(
        id=48,
        category="知識查詢-知識庫",
        user_input="關於採購流程的文件",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.INTERNAL,
        description="搜尋相關文件",
    ),
    # Agent職責詢問
    IntentTestCase(
        id=49,
        category="知識查詢-職責",
        user_input="你是做什麼的？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.INTERNAL,
        description="詢問Agent職責",
    ),
    IntentTestCase(
        id=50,
        category="知識查詢-職責",
        user_input="你的功能有哪些？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.INTERNAL,
        description="詢問Agent能力",
    ),
    # 法規遵循
    IntentTestCase(
        id=51,
        category="知識查詢-法規",
        user_input="存貨盤點的法規要求",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問法規要求",
    ),
    IntentTestCase(
        id=52,
        category="知識查詢-法規",
        user_input="ISO庫存管理標準",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問國際標準",
    ),
    IntentTestCase(
        id=53,
        category="知識查詢-法規",
        user_input="存貨評價方法有哪些？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問專業知識",
    ),
    IntentTestCase(
        id=54,
        category="知識查詢-理論",
        user_input="MRP和MRPII的差異",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問理論差異",
    ),
    IntentTestCase(
        id=55,
        category="知識查詢-理論",
        user_input="什麼是供應鏈庫存管理？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.KNOWLEDGE_QUERY,
        expected_knowledge_source=KnowledgeSourceType.EXTERNAL,
        description="詢問理論概念",
    ),
]


# =============================================================================
# 第四部分：與數據有關的查詢 (25 個場景)
# =============================================================================

SIMPLE_QUERY_SCENARIOS = [
    # 庫存查詢
    IntentTestCase(
        id=56,
        category="數據查詢-庫存",
        user_input="查詢料號 10-0001 的庫存",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢指定料號庫存",
    ),
    IntentTestCase(
        id=57,
        category="數據查詢-庫存",
        user_input="W03 倉庫的庫存是多少？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢倉庫庫存",
    ),
    IntentTestCase(
        id=58,
        category="數據查詢-庫存",
        user_input="查詢 8802 倉庫的庫存",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢倉庫庫存",
    ),
    IntentTestCase(
        id=59,
        category="數據查詢-庫存",
        user_input="料號 20-5001 現有庫存數量",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢現有庫存",
    ),
    IntentTestCase(
        id=60,
        category="數據查詢-庫存",
        user_input="有哪些料號的庫存數量大於1000？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="條件查詢庫存",
    ),
    # 料號查詢
    IntentTestCase(
        id=61,
        category="數據查詢-料號",
        user_input="查詢料號 10-0001 的品名",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢料號基本資訊",
    ),
    IntentTestCase(
        id=62,
        category="數據查詢-料號",
        user_input="RM05-008 的規格是什麼？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢料號規格",
    ),
    IntentTestCase(
        id=63,
        category="數據查詢-料號",
        user_input="料號 AB12-3456 的單位",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢料號單位",
    ),
    # 庫存明細查詢
    IntentTestCase(
        id=64,
        category="數據查詢-明細",
        user_input="查詢料號在哪些倉庫有庫存",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢庫存分布",
    ),
    IntentTestCase(
        id=65,
        category="數據查詢-明細",
        user_input="查詢庫存數量等於0的料號",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢零庫存料號",
    ),
    IntentTestCase(
        id=66,
        category="數據查詢-明細",
        user_input="查詢沒有儲位資訊的庫存記錄",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢缺失儲位記錄",
    ),
    # 採購查詢
    IntentTestCase(
        id=67,
        category="數據查詢-採購",
        user_input="料號 10-0001 上月採購多少？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢採購數量",
    ),
    IntentTestCase(
        id=68,
        category="數據查詢-採購",
        user_input="RM05-008 上月買進多少？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢採購入庫",
    ),
    IntentTestCase(
        id=69,
        category="數據查詢-採購",
        user_input="本月採購筆數統計",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="統計採購筆數",
    ),
    IntentTestCase(
        id=70,
        category="數據查詢-採購",
        user_input="查詢供應商 A001 的採購記錄",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="按供應商查詢",
    ),
    # 銷售查詢
    IntentTestCase(
        id=71,
        category="數據查詢-銷售",
        user_input="料號 10-0001 上月賣出多少？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢銷售數量",
    ),
    IntentTestCase(
        id=72,
        category="數據查詢-銷售",
        user_input="RM06-010 上月銷售額",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢銷售額",
    ),
    # 簡單統計
    IntentTestCase(
        id=73,
        category="數據查詢-統計",
        user_input="各倉庫的總庫存量",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="統計倉庫庫存總量",
    ),
    IntentTestCase(
        id=74,
        category="數據查詢-統計",
        user_input="目前有多少料號？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="統計料號數量",
    ),
    IntentTestCase(
        id=75,
        category="數據查詢-統計",
        user_input="W01 倉庫庫存金額",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="計算庫存金額",
    ),
    # 其他簡單查詢
    IntentTestCase(
        id=76,
        category="數據查詢-其他",
        user_input="查詢成品倉的庫存",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="按倉庫類型查詢",
    ),
    IntentTestCase(
        id=77,
        category="數據查詢-其他",
        user_input="原料倉庫存數量",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢原料庫存",
    ),
    IntentTestCase(
        id=78,
        category="數據查詢-其他",
        user_input="查詢最近入庫的10筆資料",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢最新入庫記錄",
    ),
    IntentTestCase(
        id=79,
        category="數據查詢-其他",
        user_input="這個料號的庫存位置",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢庫存位置（需指代）",
    ),
    IntentTestCase(
        id=80,
        category="數據查詢-其他",
        user_input="顯示庫存低於安全庫存的料號",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.SIMPLE_QUERY,
        description="查詢低庫存料號",
    ),
]


# =============================================================================
# 第五部分：複雜任務 (20 個場景)
# =============================================================================

COMPLEX_TASK_SCENARIOS = [
    # 比較分析類
    IntentTestCase(
        id=81,
        category="複雜任務-比較分析",
        user_input="比較近三個月採購金額",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="時間維度比較",
    ),
    IntentTestCase(
        id=82,
        category="複雜任務-比較分析",
        user_input="各倉庫庫存金額排行",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="倉庫維度排行",
    ),
    IntentTestCase(
        id=83,
        category="複雜任務-比較分析",
        user_input="成品倉與原料倉庫存對比",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="倉庫類型對比",
    ),
    IntentTestCase(
        id=84,
        category="複雜任務-比較分析",
        user_input="本月與上月庫存差異",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="月度庫存差異",
    ),
    IntentTestCase(
        id=85,
        category="複雜任務-比較分析",
        user_input="比較不同供應商的交貨品質",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="供應商維度比較",
    ),
    # 多維度總覽類
    IntentTestCase(
        id=86,
        category="複雜任務-多維度總覽",
        user_input="料號 10-0001 的採購與庫存總覽",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="多維度數據總覽",
    ),
    IntentTestCase(
        id=87,
        category="複雜任務-多維度總覽",
        user_input="提供完整的庫存狀況報告",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="完整庫存報告",
    ),
    IntentTestCase(
        id=88,
        category="複雜任務-多維度總覽",
        user_input="這個月的業務總覽",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="月度業務總覽",
    ),
    # 業務規則類
    IntentTestCase(
        id=89,
        category="複雜任務-業務規則",
        user_input="本月採購單未交貨明細",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="未完成交貨查詢",
    ),
    IntentTestCase(
        id=90,
        category="複雜任務-業務規則",
        user_input="查詢未出貨的訂單",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="未完成訂單查詢",
    ),
    IntentTestCase(
        id=91,
        category="複雜任務-業務規則",
        user_input="逾期未交的採購單",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="逾期交貨查詢",
    ),
    # 操作步驟類
    IntentTestCase(
        id=92,
        category="複雜任務-操作步驟",
        user_input="如何建立採購單？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="詢問操作步驟",
    ),
    IntentTestCase(
        id=93,
        category="複雜任務-操作步驟",
        user_input="怎麼做庫存盤點？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="詢問盤點流程",
    ),
    IntentTestCase(
        id=94,
        category="複雜任務-操作步驟",
        user_input="入庫作業要怎麼操作？",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="詢問入庫操作",
    ),
    # 分類分析類
    IntentTestCase(
        id=95,
        category="複雜任務-分類分析",
        user_input="ABC庫存分類分析",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="ABC分析",
    ),
    IntentTestCase(
        id=96,
        category="複雜任務-分類分析",
        user_input="依據週轉率分類庫存",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="週轉率分類",
    ),
    # 趨勢預測類
    IntentTestCase(
        id=97,
        category="複雜任務-趨勢預測",
        user_input="分析庫存趨勢",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="趨勢分析",
    ),
    IntentTestCase(
        id=98,
        category="複雜任務-趨勢預測",
        user_input="預測下個月需求",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="需求預測",
    ),
    IntentTestCase(
        id=99,
        category="複雜任務-報告生成",
        user_input="生成月度庫存報告",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="報告生成",
    ),
    IntentTestCase(
        id=100,
        category="複雜任務-報告生成",
        user_input="製作採購分析儀表板",
        expected_gai_intent=GAIIntentType.BUSINESS,
        expected_bpa_intent=BPAIntentType.COMPLEX_TASK,
        is_complex_task=True,
        description="儀表板製作",
    ),
]


# =============================================================================
# 測試類別組合
# =============================================================================

ALL_SCENARIOS = (
    GAITING_SCENARIOS
    + CLARIFICATION_SCENARIOS
    + KNOWLEDGE_QUERY_SCENARIOS
    + SIMPLE_QUERY_SCENARIOS
    + COMPLEX_TASK_SCENARIOS
)


# =============================================================================
# Pytest 測試類
# =============================================================================


class TestMMAgentIntentClassification:
    """MM-Agent 語義與任務分析測試類"""

    @pytest.fixture
    def scenarios(self):
        """提供所有測試場景"""
        return ALL_SCENARIOS

    def test_scenario_count(self, scenarios):
        """驗證場景數量"""
        assert len(scenarios) == 100, f"應有 100 個場景，實際有 {len(scenarios)} 個"

    def test_scenario_ids_unique(self, scenarios):
        """驗證場景 ID 唯一性"""
        ids = [s.id for s in scenarios]
        assert len(ids) == len(set(ids)), "場景 ID 必須唯一"

    # ========== 打招呼與基本互動測試 ==========

    @pytest.mark.parametrize("scenario", GAITING_SCENARIOS, ids=lambda s: f"greeting_{s.id}")
    def test_greeting_intents(self, scenario: IntentTestCase):
        """測試問候類意圖"""
        # 驗證預期 GAI Intent
        assert scenario.expected_gai_intent in [
            GAIIntentType.GREETING,
            GAIIntentType.THANKS,
            GAIIntentType.COMPLAIN,
            GAIIntentType.CANCEL,
            GAIIntentType.CONFIRM,
            GAIIntentType.HISTORY,
            GAIIntentType.EXPORT,
            GAIIntentType.FEEDBACK,
        ], f"場景 {scenario.id} 的預期意圖應該是問候/感謝/取消等非業務類型"

    # ========== 澄清測試 ==========

    @pytest.mark.parametrize("scenario", CLARIFICATION_SCENARIOS, ids=lambda s: f"clarify_{s.id}")
    def test_clarification_intents(self, scenario: IntentTestCase):
        """測試需要澄清的場景"""
        assert scenario.needs_clarification is True, f"場景 {scenario.id} 應該需要澄清"
        assert scenario.expected_bpa_intent == BPAIntentType.CLARIFICATION, (
            f"場景 {scenario.id} 應該分類為 CLARIFICATION"
        )

    # ========== 知識查詢測試 ==========

    @pytest.mark.parametrize(
        "scenario", KNOWLEDGE_QUERY_SCENARIOS, ids=lambda s: f"knowledge_{s.id}"
    )
    def test_knowledge_query_intents(self, scenario: IntentTestCase):
        """測試知識查詢意圖"""
        assert scenario.expected_bpa_intent == BPAIntentType.KNOWLEDGE_QUERY, (
            f"場景 {scenario.id} 應該分類為 KNOWLEDGE_QUERY"
        )
        assert scenario.expected_knowledge_source is not None, (
            f"場景 {scenario.id} 應該指定知識來源類型"
        )

    # ========== 簡單數據查詢測試 ==========

    @pytest.mark.parametrize("scenario", SIMPLE_QUERY_SCENARIOS, ids=lambda s: f"query_{s.id}")
    def test_simple_query_intents(self, scenario: IntentTestCase):
        """測試簡單數據查詢意圖"""
        assert scenario.expected_bpa_intent == BPAIntentType.SIMPLE_QUERY, (
            f"場景 {scenario.id} 應該分類為 SIMPLE_QUERY"
        )

    # ========== 複雜任務測試 ==========

    @pytest.mark.parametrize("scenario", COMPLEX_TASK_SCENARIOS, ids=lambda s: f"complex_{s.id}")
    def test_complex_task_intents(self, scenario: IntentTestCase):
        """測試複雜任務意圖"""
        assert scenario.expected_bpa_intent == BPAIntentType.COMPLEX_TASK, (
            f"場景 {scenario.id} 應該分類為 COMPLEX_TASK"
        )
        assert scenario.is_complex_task is True, f"場景 {scenario.id} 應該標記為複雜任務"

    # ========== 邊界情況測試 ==========

    def test_boundary_scenario_16(self):
        """測試最短輸入邊界"""
        scenario = next(s for s in ALL_SCENARIOS if s.id == 16)
        assert len(scenario.user_input) < 5, "輸入應該少於5個字符"

    def test_boundary_scenario_30(self):
        """測試重複字符邊界"""
        scenario = next(s for s in ALL_SCENARIOS if s.id == 30)
        assert scenario.needs_clarification is True


# =============================================================================
# 測試場景摘要報告
# =============================================================================


def get_scenario_summary():
    """生成測試場景摘要"""
    categories = {}
    for scenario in ALL_SCENARIOS:
        if scenario.category not in categories:
            categories[scenario.category] = []
        categories[scenario.category].append(scenario.id)

    report = "測試場景摘要:\n"
    report += "=" * 60 + "\n"
    report += f"總場景數: {len(ALL_SCENARIOS)}\n\n"

    for category, ids in sorted(categories.items()):
        report += f"{category}: {len(ids)} 個\n"
        report += f"  IDs: {ids}\n\n"

    report += "=" * 60 + "\n"
    report += f"分類統計:\n"
    report += f"  打招呼/基本互動: {len(GAITING_SCENARIOS)} 個\n"
    report += f"  需要澄清: {len(CLARIFICATION_SCENARIOS)} 個\n"
    report += f"  知識查詢: {len(KNOWLEDGE_QUERY_SCENARIOS)} 個\n"
    report += f"  數據查詢: {len(SIMPLE_QUERY_SCENARIOS)} 個\n"
    report += f"  複雜任務: {len(COMPLEX_TASK_SCENARIOS)} 個\n"

    return report


if __name__ == "__main__":
    # 打印測試場景摘要
    print(get_scenario_summary())

    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
