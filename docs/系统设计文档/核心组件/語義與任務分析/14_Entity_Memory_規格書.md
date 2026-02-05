# Entity Memory 規格書

**文件編號**: AI-Box-DOC-014
**版本**: 1.0
**創建日期**: 2026-02-04
**最後修改日期**: 2026-02-04
**狀態**: 草稿

---

## 1. 概述

### 1.1 文件目的

本規格書定義 AI-Box 系統中 **Entity Memory（實體記憶）** 模組的功能需求、數據模型、存儲設計、檢索策略以及與現有系統的整合方式。

Entity Memory 是 AI-Box 記憶系統的核心組件之一，專門用於長期追蹤和管理對話中出現的重要實體名詞，為指代消解（Coreference Resolution）提供基礎設施支持。

### 1.2 設計背景

AI-Box 系統面臨以下挑戰：

1. **指代消解困難**：用戶使用「它」「這個」「上次說的」等指代詞時，系統無法正確消解
2. **實體遺忘**：跨會話時，系統忘記用戶曾經提到的重要實體
3. **知識碎片化**：系統實體名稱散落在各處，缺乏統一管理

Entity Memory 的目標是提供一個統一、持久、可擴展的實體記憶層，解決上述問題。

### 1.3 設計原則

| 原則               | 說明                                              |
| ------------------ | ------------------------------------------------- |
| **分層存儲** | 長期實體（名詞）與會話上下文（事件/時間）分層管理 |
| **自動學習** | 從對話中自動識別和記憶新實體，無需手動配置        |
| **混合存儲** | 同時使用向量庫（語義搜索）和圖譜（關係追蹤）      |
| **檢索優先** | 支援多種檢索策略，根據查詢特點動態選擇最優策略    |
| **用戶隔離** | 基於 user_id 隔離實體記憶，確保數據安全           |

### 1.4 術語定義

| 術語                                     | 定義                                             |
| ---------------------------------------- | ------------------------------------------------ |
| **Entity（實體）**                 | 對話中出現的重要名詞（人、地、物、組織、系統等） |
| **Session Entity**                 | 會話內的實體上下文，會話結束後失效               |
| **Long-term Entity**               | 需要長期記憶的實體，永久保存                     |
| **Coreference（指代）**            | 指代詞（如「它」「這個」）與其指向實體的映射關係 |
| **Entity Extraction（實體提取）**  | 從文本中自動識別和提取實體的過程                 |
| **Retrieval Strategy（檢索策略）** | 根據查詢特點選擇最優檢索方法的策略層             |

---

## 2. 系統架構

### 2.1 整體架構圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AI-Box 應用層                                  │
│                                                                          │
│   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐             │
│   │  Task Agent   │   │  Chat API     │   │  RAG System   │             │
│   │  (mm-agent)   │   │  (chat.py)    │   │  (Knowledge)  │             │
│   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘             │
│           │                   │                   │                     │
│           └───────────────────┼───────────────────┘                     │
│                               │                                         │
│                               ▼                                         │
│              ┌─────────────────────────────────┐                        │
│              │     Entity Memory Service       │                        │
│              │     (統一實體記憶服務)            │                        │
│              └────────────────┬────────────────┘                        │
│                               │                                         │
│           ┌───────────────────┼───────────────────┐                     │
│           │                   │                   │                     │
│           ▼                   ▼                   ▼                     │
│   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐             │
│   │ Coreference   │   │   Entity      │   │   Retrieval   │             │
│   │   Resolver    │◄──│   Extractor   │──►│   Strategy    │             │
│   │   (指代消解)   │   │   (實體提取)   │   │   (檢索策略)   │             │
│   └───────────────┘   └───────────────┘   └───────────────┘             │
│                               │                                         │
│           ┌───────────────────┼───────────────────┐                     │
│           │                   │                   │                     │
│           ▼                   ▼                   ▼                     │
│   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐             │
│   │    Qdrant     │   │   ArangoDB    │   │     Redis     │             │
│   │  (向量庫)      │   │   (圖譜)      │   │  (會話緩存)    │             │
│   └───────────────┘   └───────────────┘   └───────────────┘             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 組件職責

| 組件名稱                      | 職責                     | 主要方法                                                    |
| ----------------------------- | ------------------------ | ----------------------------------------------------------- |
| **EntityMemoryService** | 統一入口，協調各子模組   | `resolve()`, `store()`, `extract()`                   |
| **EntityExtractor**     | 從對話中提取實體         | `extract_from_text()`, `detect_remember_intent()`       |
| **EntityStorage**       | 實體數據的持久化         | `store_entity()`, `get_entity()`, `search_entities()` |
| **RetrievalStrategy**   | 動態選擇最優檢索策略     | `search()`, `fuse_results()`                            |
| **CoreferenceResolver** | 指代消解（整合長期實體） | `resolve()`                                               |

### 2.3 數據流向

```
會話開始
    │
    ▼
┌─────────────────────┐
│  讀取會話實體上下文   │ ← Redis (session_context)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  讀取長期實體記憶    │ ← Qdrant + ArangoDB (entity_memory)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   指代消解處理       │ ← CoreferenceResolver
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  返回消解後查詢      │ → Task Analyzer / mm-agent
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  提取並學習新實體    │ ← EntityExtractor
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  存儲新實體到長期記憶 │ → Qdrant + ArangoDB
└─────────────────────┘
```

---

## 3. 記憶層級定義

### 3.1 記憶層級分類

AI-Box 系統中的記憶分為以下幾個層級：

| 層級         | 名稱         | 存儲位置          | 有效期 | 內容類型                 | 範例                          |
| ------------ | ------------ | ----------------- | ------ | ------------------------ | ----------------------------- |
| **L1** | 會話實體     | Redis             | 會話內 | 事件、時間指示           | 「上次說的」「今天」「這個」  |
| **L2** | 長期實體     | Qdrant + ArangoDB | 永久   | 名詞（人、地、物、組織） | 「宏康 HCI」「AI-Box」「IBM」 |
| **L3** | 對話歷史     | Redis             | 1 小時 | 完整對話記錄             | user/assistant 消息歷史       |
| **L4** | AAM 長期記憶 | Qdrant            | 永久   | 經驗、偏好、知識         | 用戶偏好、系統知識            |

### 3.2 實體層級判定規則

```
輸入文本 → 實體提取 → 層級判定

判定邏輯：
├── 事件指示詞 → L1（會話實體）
│   「上次」「之前」「這次」「今天」「這週」
│
├── 時間指示詞 → L1（會話實體）
│   「明天」「上週」「下個月」「最近」
│
├── 代詞指示 → L1（會話實體）+ 引用 L2
│   「這個」「那個」「它」「他」「她」
│
├── 名詞實體 → L2（長期實體）
│   （組織名、產品名、地名、人名、系統名等）
│
└── 用戶明確指示 → L2（長期實體）
    「幫我記住」「記住這個」「這很重要」
```

### 3.3 實體類型定義

根據需求，所有名詞實體統一歸類為 `entity_noun`：

| 類型代碼        | 類型名稱 | 說明                   | 範例                  |
| --------------- | -------- | ---------------------- | --------------------- |
| `entity_noun` | 名詞實體 | 所有需要長期記憶的名詞 | AI-Box、宏康 HCI、IBM |

> **注意**：未來可根據實際需求迭代細分為 `org_name`、`person_name`、`product_name` 等。

---

## 4. 數據模型

### 4.1 實體數據模型（Qdrant）

```python
# agents/services/entity_memory/models.py

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class EntityType(str, Enum):
    ENTITY_NOUN = "entity_noun"  # 名詞實體

class EntityStatus(str, Enum):
    ACTIVE = "active"     # 活躍
    ARCHIVED = "archived" # 歸檔
    REVIEW = "review"     # 待審核

class EntityMemory(BaseModel):
    """
    實體記憶數據模型（存儲到 Qdrant）
    """
    # 基本信息
    entity_id: str                    # 實體唯一標識 (UUID)
    entity_value: str                 # 實體名稱（如 "AI-Box"）
    entity_type: EntityType           # 實體類型
  
    # 元數據
    user_id: str                      # 所屬用戶 ID
    confidence: float = 1.0           # 置信度 (0.0 - 1.0)
    status: EntityStatus = EntityStatus.ACTIVE
  
    # 時間戳
    first_mentioned: datetime         # 首次提及時間
    last_mentioned: datetime          # 最近提及時間
    mention_count: int = 0            # 提及次數
  
    # 向量表示（Qdrant 使用）
    vector: Optional[List[float]] = None
  
    # 額外屬性（JSON）
    attributes: dict = {}
  
    # 關係標記
    related_entities: List[str] = []  # 關聯的實體 ID 列表
```

### 4.2 實體關係模型（ArangoDB）

```python
class EntityRelation(BaseModel):
    """
    實體關係數據模型（存儲到 ArangoDB）
    """
    # 基本信息
    relation_id: str                  # 關係唯一標識
    source_entity_id: str             # 源實體 ID
    target_entity_id: str             # 目標實體 ID
    relation_type: str                # 關係類型
  
    # 關係描述
    description: Optional[str] = None # 關係描述
  
    # 元數據
    user_id: str                      # 所屬用戶 ID
    created_at: datetime              # 創建時間
    updated_at: datetime              # 更新時間
    confidence: float = 1.0           # 置信度
```

### 4.3 會話實體模型（Redis）

```python
class SessionContext(BaseModel):
    """
    會話上下文數據模型（存儲到 Redis）
    """
    session_id: str                   # 會話 ID
    user_id: str                      # 用戶 ID
  
    # 會話內的實體引用
    mentioned_entities: List[str] = []    # 會話中提到的實體 ID 列表
    last_referred_entity: Optional[str] = None  # 最後被指代詞引用的實體
  
    # 指代消解歷史
    coreference_history: List[dict] = []  # 指代消解歷史記錄
  
    # 時間範圍
    started_at: datetime              # 會話開始時間
    last_activity: datetime           # 最後活動時間
```

### 4.4 指代消解結果模型

```python
class CoreferenceResolution(BaseModel):
    """
    指代消解結果數據模型
    """
    original_text: str                # 原始指代詞（如 "它"）
    resolved_text: str                # 消解後的實體（如 "AI-Box"）
    entity_id: Optional[str] = None   # 實體 ID（如果存在）
    source: str                       # 來源: "session" | "long_term" | "inference"
    confidence: float                 # 置信度
  
class CoreferenceResult(BaseModel):
    """
    指代消解完整結果
    """
    original_query: str               # 原始查詢
    resolved_query: str               # 消解後的查詢
    resolutions: List[CoreferenceResolution]  # 指代消解列表
    confidence: float                 # 整體置信度
    entities_found: List[str] = []    # 找到的實體 ID 列表
```

---

## 5. 存儲設計

### 5.1 Qdrant Collection 配置

```yaml
# Collection 名稱: ai_box_entity_memory

collection_name: ai_box_entity_memory
vector_size: 384  # nomic-embed-text 維度
distance_metric: Cosine

# Payload 字段索引
payload_schema:
  entity_value:
    type: keyword  # 精確匹配
  entity_type:
    type: keyword  # 類型過濾
  user_id:
    type: keyword  # 用戶隔離
  status:
    type: keyword  # 狀態過濾
  first_mentioned:
    type: datetime # 時間範圍查詢
  last_mentioned:
    type: datetime # 時間範圍查詢
  mention_count:
    type: integer  # 次數過濾
```

### 5.2 ArangoDB Collection 配置

```json
{
  "collections": {
    "entity_relations": {
      "name": "entity_relations",
      "type": 2,  // 邊集合
      "fields": [
        {"field": "relation_id", "type": "string"},
        {"field": "source_entity_id", "type": "string"},
        {"field": "target_entity_id", "type": "string"},
        {"field": "relation_type", "type": "string"},
        {"field": "user_id", "type": "string"},
        {"field": "created_at", "type": "string"},
        {"field": "confidence", "type": "number"}
      ]
    }
  }
}
```

### 5.3 Redis 緩存配置

```python
# 會話實體緩存配置
SESSION_CONTEXT_TTL = 24 * 60 * 60  # 24 小時
SESSION_CONTEXT_PREFIX = "entity_session:"
```

### 5.4 存儲操作接口

```python
class EntityStorage:
    """實體存儲層"""
  
    # ========== 實體操作 ==========
  
    async def store_entity(self, entity: EntityMemory) -> bool:
        """
        存儲實體到長期記憶
      
        Args:
            entity: 實體數據對象
          
        Returns:
            是否存儲成功
        """
        pass
  
    async def get_entity(self, entity_id: str, user_id: str) -> Optional[EntityMemory]:
        """
        根據 ID 獲取實體
      
        Args:
            entity_id: 實體 ID
            user_id: 用戶 ID
          
        Returns:
            實體對象或 None
        """
        pass
  
    async def search_entities(
        self,
        query: str,
        user_id: str,
        limit: int = 10
    ) -> List[EntityMemory]:
        """
        搜索實體（向量搜索 + 關鍵詞匹配）
      
        Args:
            query: 搜索查詢
            user_id: 用戶 ID
            limit: 返回數量限制
          
        Returns:
            匹配的實體列表
        """
        pass
  
    async def get_entity_by_value(
        self,
        entity_value: str,
        user_id: str
    ) -> Optional[EntityMemory]:
        """
        根據實體名稱精確查找
      
        Args:
            entity_value: 實體名稱
            user_id: 用戶 ID
          
        Returns:
            實體對象或 None
        """
        pass
  
    async def update_entity_mention(
        self,
        entity_id: str,
        user_id: str
    ) -> bool:
        """
        更新實體提及時間和次數
      
        Args:
            entity_id: 實體 ID
            user_id: 用戶 ID
          
        Returns:
            是否更新成功
        """
        pass
  
    # ========== 關係操作 ==========
  
    async def store_relation(self, relation: EntityRelation) -> bool:
        """存儲實體關係"""
        pass
  
    async def get_related_entities(
        self,
        entity_id: str,
        user_id: str
    ) -> List[str]:
        """
        獲取關聯的實體 ID 列表
      
        Args:
            entity_id: 源實體 ID
            user_id: 用戶 ID
          
        Returns:
            關聯的實體 ID 列表
        """
        pass
  
    # ========== 會話上下文操作 ==========
  
    async def store_session_context(
        self,
        session_id: str,
        context: SessionContext
    ) -> bool:
        """存儲會話上下文"""
        pass
  
    async def get_session_context(
        self,
        session_id: str
    ) -> Optional[SessionContext]:
        """獲取會話上下文"""
        pass
  
    async def add_entity_to_session(
        self,
        session_id: str,
        entity_id: str
    ) -> bool:
        """將實體添加到會話"""
        pass
  
    async def set_last_referred_entity(
        self,
        session_id: str,
        entity_id: str
    ) -> bool:
        """設置最後被引用的實體"""
        pass
```

---

## 6. 檢索策略

### 6.1 檢索策略概述

Entity Memory 支援多種檢索策略，根據查詢特點動態選擇最優策略：

| 策略               | 適用場景                 | 優先級 |
| ------------------ | ------------------------ | ------ |
| **精確匹配** | 查詢包含完整實體名稱     | 最高   |
| **向量搜索** | 查詢是模糊描述或部分名稱 | 高     |
| **類型過濾** | 需要過濾特定類型實體     | 中     |
| **混合融合** | 多策略結果需要融合排序   | -      |

### 6.2 檢索流程

```
輸入查詢 → 策略選擇 → 並行檢索 → 結果融合 → 返回結果

Step 1: 策略選擇
├── 包含完整實體名稱？ → 精確匹配
├── 包含模糊描述？ → 向量搜索
├── 需要類型過濾？ → 類型過濾
└── 複雜查詢？ → 混合策略

Step 2: 並行檢索（可選）
├── 策略 A：向量搜索
├── 策略 B：精確匹配
└── 策略 C：類型過濾

Step 3: 結果融合
├── 分數標準化
├── 置信度加權
├── 新鮮度衰減
└── 去重 + 排序

Step 4: 返回結果
└── 返回 Top-K 實體
```

### 6.3 結果融合算法

```python
def fuse_results(
    vector_results: List[EntityMemory],
    exact_results: List[EntityMemory],
    type_filtered: List[EntityMemory]
) -> List[EntityMemory]:
    """
    融合多策略檢索結果
  
    融合公式:
    final_score = w1 * vector_score + w2 * exact_score + w3 * freshness_score
  
    Args:
        vector_results: 向量搜索結果
        exact_results: 精確匹配結果
        type_filtered: 類型過濾結果
      
    Returns:
        融合後排序的實體列表
    """
    # 權重配置
    WEIGHTS = {
        "vector": 0.4,
        "exact": 0.4,
        "freshness": 0.2
    }
  
    # 合併所有結果
    all_results = {e.entity_id: e for e in vector_results + exact_results + type_filtered}
  
    # 計算融合分數
    for entity_id, entity in all_results.items():
        final_score = (
            WEIGHTS["vector"] * entity.scores.get("vector", 0) +
            WEIGHTS["exact"] * entity.scores.get("exact", 0) +
            WEIGHTS["freshness"] * _calculate_freshness(entity.last_mentioned)
        )
        entity.final_score = final_score
  
    # 按分數排序
    sorted_entities = sorted(all_results.values(), key=lambda e: e.final_score, reverse=True)
  
    return sorted_entities

def _calculate_freshness(last_mentioned: datetime) -> float:
    """
    計算實體新近度分數（0.0 - 1.0）
  
    最近提及的實體獲得更高分數
    """
    now = datetime.utcnow()
    hours_diff = (now - last_mentioned).total_seconds() / 3600
  
    # 24 小時內為 1.0，每增加 24 小時衰減 0.1
    freshness = max(0.0, 1.0 - (hours_diff / 240))
    return freshness
```

### 6.4 檢索策略接口

```python
class RetrievalStrategy:
    """檢索策略層"""
  
    async def search(
        self,
        query: str,
        user_id: str,
        entity_type: Optional[EntityType] = None,
        limit: int = 10
    ) -> List[EntityMemory]:
        """
        統一的檢索接口
      
        Args:
            query: 搜索查詢
            user_id: 用戶 ID
            entity_type: 實體類型過濾（可選）
            limit: 返回數量限制
          
        Returns:
            檢索結果列表（已融合排序）
        """
        pass
  
    async def search_by_coreference(
        self,
        coreference_word: str,
        session_id: str,
        user_id: str,
        limit: int = 5
    ) -> List[EntityMemory]:
        """
        根據指代詞查找可能指向的實體
      
        Args:
            coreference_word: 指代詞（如 "它""這個"）
            session_id: 會話 ID
            user_id: 用戶 ID
            limit: 返回數量限制
          
        Returns:
            可能的實體列表
        """
        pass
```

---

## 7. API 接口

### 7.1 服務層接口

```python
# agents/services/entity_memory/entity_memory_service.py

class EntityMemoryService:
    """Entity Memory 統一服務"""
  
    def __init__(
        self,
        storage: EntityStorage,
        extractor: EntityExtractor,
        strategy: RetrievalStrategy
    ):
        self.storage = storage
        self.extractor = extractor
        self.strategy = strategy
  
    async def resolve_coreference(
        self,
        query: str,
        session_id: str,
        user_id: str
    ) -> CoreferenceResult:
        """
        指代消解主接口
      
        Args:
            query: 用戶原始查詢
            session_id: 會話 ID
            user_id: 用戶 ID
          
        Returns:
            指代消解結果
        """
        pass
  
    async def extract_and_store(
        self,
        text: str,
        session_id: str,
        user_id: str,
        auto_learn: bool = True
    ) -> List[EntityMemory]:
        """
        從文本中提取並存儲實體
      
        Args:
            text: 輸入文本
            session_id: 會話 ID
            user_id: 用戶 ID
            auto_learn: 是否自動學習新實體
          
        Returns:
            提取的實體列表
        """
        pass
  
    async def get_entity(
        self,
        entity_value: str,
        user_id: str
    ) -> Optional[EntityMemory]:
        """
        獲取指定實體
      
        Args:
            entity_value: 實體名稱
            user_id: 用戶 ID
          
        Returns:
            實體對象或 None
        """
        pass
  
    async def search_entities(
        self,
        query: str,
        user_id: str,
        limit: int = 10
    ) -> List[EntityMemory]:
        """
        搜索實體
      
        Args:
            query: 搜索查詢
            user_id: 用戶 ID
            limit: 返回數量限制
          
        Returns:
            匹配的實體列表
        """
        pass
  
    async def remember_entity(
        self,
        entity_value: str,
        user_id: str,
        attributes: Optional[dict] = None
    ) -> EntityMemory:
        """
        手動記住實體（用戶明確指示）
      
        Args:
            entity_value: 實體名稱
            user_id: 用戶 ID
            attributes: 額外屬性
          
        Returns:
            創建的實體對象
        """
        pass
```

### 7.2 整合到 Chat API

```python
# api/routers/chat.py (pseudo-code)

class EntityMemoryService:
    entity_memory_service: EntityMemoryService

async def chat_message(request_body: ChatRequest):
    # ... 前置處理 ...
  
    # Step 1: 指代消解
    coreference_result = await entity_memory_service.resolve_coreference(
        query=last_user_text,
        session_id=session_id,
        user_id=current_user.user_id
    )
  
    resolved_query = coreference_result.resolved_query
  
    # Step 2: 實體提取與學習
    await entity_memory_service.extract_and_store(
        text=last_user_text,
        session_id=session_id,
        user_id=current_user.user_id,
        auto_learn=True
    )
  
    # Step 3: 使用消解後的查詢繼續處理
    # ...
```

---

## 8. 與現有系統整合

### 8.1 與 Chat API 整合

**整合點**: `api/routers/chat.py`

**整合時機**:

1. 收到用戶消息後（指代消解）
2. 發送回覆前（實體學習）

**整合方式**:

```python
# 在消息處理流程中添加
from agents.services.entity_memory.entity_memory_service import get_entity_memory_service

entity_service = get_entity_memory_service()

# 指代消解
resolved_query = await entity_service.resolve_coreference(
    query=user_message,
    session_id=session_id,
    user_id=user_id
)

# 實體提取與學習
await entity_service.extract_and_store(
    text=user_message,
    session_id=session_id,
    user_id=user_id
)
```

### 8.2 與 mm-agent 整合

**整合點**: `datalake-system/mm_agent/chain/context_manager.py`

**現有架構**:
mm-agent 已有 `ConversationContext` 和 `CoreferenceResolver`

**整合方式**:

```python
# 使用 EntityMemoryService 補充長期實體記憶
from agents.services.entity_memory.entity_memory_service import get_entity_memory_service

class MMConversationContext:
    async def load_long_term_entities(self, user_id: str):
        entity_service = get_entity_memory_service()
        entities = await entity_service.search_entities(
            query="",  # 獲取所有實體
            user_id=user_id,
            limit=100
        )
        self.extracted_entities.update({
            e.entity_value: {"entity_id": e.entity_id, "type": "long_term"}
            for e in entities
        })
```

### 8.3 與 AAM 系統整合

**整合點**: `agents/infra/memory/aam/aam_core.py`

**整合方式**:
Entity Memory 與 AAM 長期記憶是**互補關係**：

- Entity Memory: 專注於實體名詞的追蹤
- AAM Memory: 專注於用戶偏好、經驗、知識的積累

兩者可共享 Qdrant 存儲，但使用不同的 Collection：

- Entity Memory: `ai_box_entity_memory`
- AAM Memory: `ai_box_aam_memory`

### 8.4 與 Task Analyzer 整合

**整合點**: `agents/task_analyzer/analyzer.py`

**整合方式**:
在 Task Analyzer 的 Router LLM Prompt 中注入長期實體上下文：

```python
# 在 router_llm.py 中
async def get_router_prompt(user_query: str, session_id: str, user_id: str):
    # 獲取長期實體
    entity_service = get_entity_memory_service()
    entities = await entity_service.search_entities(
        query=user_query,
        user_id=user_id,
        limit=5
    )
  
    # 注入到 System Prompt
    entity_context = "\n".join([
        f"- {e.entity_value} (最近提及: {e.last_mentioned})"
        for e in entities
    ])
  
    return f"""...
用戶提到的相關實體：
{entity_context}
..."""
```

---

## 9. 錯誤處理與監控

### 9.1 錯誤處理策略

| 錯誤類型          | 處理方式               | 用戶影響           |
| ----------------- | ---------------------- | ------------------ |
| Qdrant 連接失敗   | 使用內存回退           | 僅影響長期實體記憶 |
| ArangoDB 連接失敗 | 記錄警告，跳過關係存儲 | 僅影響實體關係追蹤 |
| Redis 連接失敗    | 使用內存回退           | 僅影響會話實體     |
| 實體提取失敗      | 記錄錯誤，跳過該次提取 | 無感知             |
| 指代消解失敗      | 返回原始查詢           | 無感知             |

### 9.2 監控指標

```python
# 監控指標定義

METRICS = {
    # 性能指標
    "entity_memory.resolve.latency_ms": "指代消解延遲",
    "entity_memory.extract.latency_ms": "實體提取延遲",
    "entity_memory.search.latency_ms": "實體搜索延遲",
  
    # 業務指標
    "entity_memory.resolutions.success": "指代消解成功次數",
    "entity_memory.resolutions.failed": "指代消解失敗次數",
    "entity_memory.extractions.count": "提取的新實體數量",
    "entity_memory.recall.hits": "實體召回命中次數",
    "entity_memory.recall.misses": "實體召回未命中次數",
  
    # 存儲指標
    "entity_memory.storage.count": "實體總數",
    "entity_memory.storage.size_bytes": "存儲大小",
}
```

### 9.3 日誌規範

```python
import logging

logger = logging.getLogger("entity_memory")

#  INFO 級別：主要操作
logger.info(f"Entity resolved: query='{query}', resolved='{resolved}', source='{source}'")

#  WARNING 級別：可恢復錯誤
logger.warning(f"Qdrant connection failed, using fallback: {error}")

#  ERROR 級別：不可恢復錯誤
logger.error(f"Entity extraction failed: {error}", exc_info=True)
```

---

## 10. 附錄

### 10.1 種子數據

系統預載入的實體種子數據：

| 實體名稱  | 類型        | 來源 |
| --------- | ----------- | ---- |
| AI-Box    | entity_noun | 系統 |
| 宏康 HCI  | entity_noun | 系統 |
| mm-agent  | entity_noun | 系統 |
| KA-Agent  | entity_noun | 系統 |
| ArangoDB  | entity_noun | 系統 |
| Qdrant    | entity_noun | 系統 |
| ChromaDB  | entity_noun | 系統 |
| SeaweedFS | entity_noun | 系統 |
| Redis     | entity_noun | 系統 |
| Ollama    | entity_noun | 系統 |
| FastAPI   | entity_noun | 系統 |
| MCP       | entity_noun | 系統 |

### 10.2 文件變更歷史

| 版本 | 日期       | 變更內容 | 作者   |
| ---- | ---------- | -------- | ------ |
| 1.0  | 2026-02-04 | 初版創建 | Daniel |

---

**文件結束**
