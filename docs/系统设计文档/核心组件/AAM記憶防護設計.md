# AAM 記憶防護設計文檔

**文件編號**: SYS-DESIGN-AAM-001  
**版本**: 1.0.0  
**創建日期**: 2026-02-02  
**最後修改日期**: 2026-02-02  
**負責人**: AI-Box Team

---

## 1. 概述

### 1.1 文件目的

本文檔描述 AAM (Agent Assistant Memory) 記憶防護系統的設計架構，實現長期記憶的持久化存儲、User Isolation 防護、去重檢測、衝突處理和定期檢討機制。

### 1.2 設計目標

| 目標 | 說明 |
|------|------|
| **User Isolation** | 按 user_id 隔離記憶，防止跨用戶污染 |
| **長期持久化** | 使用 Qdrant 向量資料庫存儲記憶 |
| **記憶防護** | 去重檢測、衝突處理、自動覆寫 |
| **定期檢討** | 低熱度記憶歸檔、過時記憶審核 |
| **可追溯性** | 記憶來源、使用次數、版本控制 |

### 1.3 系統架構

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AAM 記憶防護架構                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     應用層 (Application Layer)                       │   │
│  │                                                                      │   │
│  │   ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐ │   │
│  │   │ MM-Agent          │  │ Chat Service      │  │ Memory Review   │ │   │
│  │   │ CoreferenceResolver│  │ HybridRAGService  │  │ Job            │ │   │
│  │   └─────────┬─────────┘  └─────────┬─────────┘  └───────┬─────────┘ │   │
│  │            │                       │                    │           │   │
│  └────────────┼───────────────────────┼────────────────────┼───────────┘   │
│               │                       │                    │               │
│               ▼                       ▼                    ▼               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AAM Manager (aam_core.py)                        │   │
│  │                                                                      │   │
│  │   ┌─────────────────────────────────────────────────────────────┐   │   │
│  │   │  Core Functions:                                            │   │   │
│  │   │  - store_entity()  存儲實體（含去重、衝突檢測）               │   │   │
│  │   │  - retrieve_entities() 檢索實體（含熱度排序）                │   │   │
│  │   │  - detect_conflicts() 衝突檢測                              │   │   │
│  │   │  - get_user_entities() 按用戶查詢                           │   │   │
│  │   └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  QdrantAdapter (qdrant_adapter.py)                  │   │
│  │                                                                      │   │
│  │   功能:                                                              │   │
│  │   - User Isolation: 按 user_id 隔離查詢                            │   │
│  │   - 向量存儲: 使用 all-mpnet-base-v2 (768維)                       │   │
│  │   - 去重檢測: find_by_exact_match()                                │   │
│  │   - 衝突檢測: detect_conflicts()                                   │   │
│  │   - 熱度追蹤: access_count, accessed_at                            │   │
│  │   - 時效管理: archive_memory(), mark_for_review()                  │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Qdrant Vector DB                            │   │
│  │                                                                      │   │
│  │   Collection: aam_entities                                          │   │
│  │   - vectors: 768維 (all-mpnet-base-v2)                             │   │
│  │   - payload: user_id, entity_type, entity_value, confidence, etc.  │   │
│  │   - indexes: user_id, entity_type, status, created_at              │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 數據模型

### 2.1 Memory 擴展

```python
@dataclass
class Memory:
    """記憶數據模型（擴展版）"""

    # 基礎欄位
    memory_id: str
    content: str
    memory_type: MemoryType  # SHORT_TERM / LONG_TERM
    priority: MemoryPriority = MEDIUM

    # 元數據
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime
 datetime
    accessed_at: Optional[datetime] = None    updated_at:
    access_count: int = 0
    relevance_score: float = 0.0

    # === Qdrant 擴展欄位 ===
    user_id: str = ""              # User Isolation Key
    entity_type: str = ""          # part_number / tlf19 / intent / preference
    entity_value: str = ""         # RM05-008 / 101 / purchase
    confidence: float = 0.5        # 置信度 (0.0-1.0)
    status: str = "active"         # active / archived / review
```

### 2.2 Qdrant Collection 配置

```json
{
  "name": "aam_entities",
  "vectors": {
    "size": 768,
    "distance": "Cosine"
  },
  "payload_schema": {
    "user_id": {"type": "keyword", "index": true},
    "entity_type": {"type": "keyword", "index": true},
    "entity_value": {"type": "text", "index": true},
    "confidence": {"type": "float", "range": true},
    "access_count": {"type": "integer", "range": true},
    "status": {"type": "keyword", "index": true},
    "created_at": {"type": "datetime", "index": true},
    "updated_at": {"type": "datetime", "index": true}
  }
}
```

---

## 3. 核心功能

### 3.1 User Isolation

**目的**: 防止不同用戶的記憶相互污染

```python
def search(
    query: str,
    user_id: str,  # 必填參數
    entity_type: Optional[str] = None,
    ...
) -> List[Memory]:
    """
    搜索時強制添加 user_id 過濾器
    """
    must_conditions = [
        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
        # ...
    ]
```

**效果**:
```
用戶 A 查詢 → 只能返回 user_id="A" 的記憶
用戶 B 查詢 → 只能返回 user_id="B" 的記憶
```

### 3.2 去重檢測

**目的**: 防止同一實體重複存儲

```python
def store_entity(
    user_id: str,
    entity_type: str,
    entity_value: str,
    metadata: Dict
) -> str:
    """
    存儲前進行精確匹配檢查
    """
    # 1. 精確匹配查詢
    existing = qdrant.find_by_exact_match(
        user_id=user_id,
        entity_type=entity_type,
        entity_value=entity_value
    )

    if existing:
        # 2. 已存在 → 更新置信度
        return update_memory(existing.memory_id, metadata)
    else:
        # 3. 新實體 → 存入
        return create_memory(user_id, entity_type, entity_value, metadata)
```

### 3.3 衝突處理

**目的**: 處理高相似度記憶的衝突

```python
def detect_conflicts(
    user_id: str,
    entity_type: str,
    new_value: str,
    new_confidence: float,
) -> List[MemoryConflict]:
    """
    檢測新值是否與現有記憶衝突
    """
    # 1. 獲取同類型實體
    existing = qdrant.get_user_entities(user_id, entity_type)

    # 2. 計算語義相似度
    for entity in existing:
        similarity = cosine_similarity(new_value, entity.content)

        # 3. 0.85 < similarity < 1.0 表示高度相似
        if 0.85 < similarity < 1.0:
            # 4. 自動覆寫策略
            if new_confidence > entity.confidence:
                overwrite(entity, new_value, new_confidence)
```

### 3.4 熱度排序

**目的**: 返回最相關、最常訪問的記憶

```python
def retrieve_entities(
    user_id: str,
    query: str,
    min_confidence: float = 0.7,
    limit: int = 5
) -> List[Memory]:
    """
    取出高質量記憶
    """
    # 1. 向量搜尋
    results = qdrant.search(query, user_id, limit=limit*2)

    # 2. 置信度過濾
    filtered = [m for m in results if m.confidence >= min_confidence]

    # 3. 熱度排序
    scored = [
        {**m, "final_score": compute_score(m)}
        for m in filtered
    ]

    # 4. 返回 top N
    return sorted(scored, key=lambda m: m.final_score, reverse=True)[:limit]

def compute_score(memory: Memory) -> float:
    """計算最終分數"""
    return (
        memory.relevance_score * 0.4 +   # 相關度
        (memory.access_count / 100) * 0.3 +  # 熱度
        (1 - days_since_update / 365) * 0.3  # 時效性
    )
```

---

## 4. 定期檢討機制

### 4.1 檢討策略

| 記憶類型 | 處理方式 | 觸發條件 |
|---------|---------|---------|
| **低熱度記憶** | 歸檔 | access_count ≤ 3 且創建 > 90 天 |
| **可能過時記憶** | 標記審核 | 長期未更新但持續訪問 |
| **高價值記憶** | 保留 | access_count > 10 |

### 4.2 檢討流程

```python
async def weekly_review_job():
    """
    每週執行 - 低熱度記憶歸檔
    """
    for user_id in all_users:
        # 1. 查找低熱度記憶
        low_hotness = qdrant.find_low_hotness(
            user_id=user_id,
            max_access=3,
            older_than_days=90
        )

        # 2. 歸檔低熱度記憶
        for memory in low_hotness:
            qdrant.archive_memory(memory.memory_id)
            logger.info(f"[AAM REVIEW] 歸檔: {memory.memory_id}")

        # 3. 標記可能過時記憶
        stale = find_potentially_stale(user_id, days=180)
        for memory in stale:
            qdrant.mark_for_review(
                memory.memory_id,
                reason="長期未更新但持續訪問"
            )
```

### 4.3 Cron 配置

```bash
# /etc/cron.d/aam-memory-review
# 每週日凌晨 2 點執行
0 2 * * 0 root cd /home/daniel/ai-box && python3 jobs/memory_review_job.py >> /var/log/aam_review.log 2>&1
```

---

## 5. 記憶流程

### 5.1 存儲流程

```
用戶輸入 → Translator 提取實體
                    │
                    ▼
         ┌──────────────────────┐
         │  AAMManager.store_entity() │
         └──────────────────────┘
                    │
                    ├─► 1. 去重檢查 (find_by_exact_match)
                    │
                    ├─► 2. 衝突檢測 (detect_conflicts)
                    │
                    └─► 3. 存入 Qdrant (含 user_id 隔離)
```

### 5.2 檢索流程

```
用戶輸入 → 指代消解請求
                    │
                    ▼
         ┌──────────────────────┐
         │ AAMManager.retrieve_entities() │
         └──────────────────────┘
                    │
                    ├─► 1. 向量搜尋 (user_id 隔離)
                    │
                    ├─► 2. 置信度過濾 (≥ 0.7)
                    │
                    └─► 3. 熱度排序返回
```

---

## 6. 文檔變更歷史

| 版本 | 日期 | 變更內容 |
|------|------|---------|
| 1.0.0 | 2026-02-02 | 初始版本 |

---

## 7. 相關文件

- [系統管理作業規範](系統管理/系統管理作業規範.md)
- [Memory 模型](../memory/aam/models.py)
- [Qdrant Adapter](../memory/aam/qdrant_adapter.py)
- [定期檢討 Job](../jobs/memory_review_job.py)
- [單元測試](../../tests/test_aam_qdrant.py)

---

**文件結束**
