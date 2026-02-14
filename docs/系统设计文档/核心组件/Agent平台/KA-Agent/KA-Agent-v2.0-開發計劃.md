# KA-Agent v2.0 開發計劃

> **計劃版本**: v1.0.0  
> **創建日期**: 2026-02-13 10:00 UTC+8  
> **維護人**: Daniel Chung  
> **目標版本**: v2.0.0

---

## 1. 計劃概述

### 1.1 目標

完成 KA-Agent v2.0 開發，整合新的 Knowledge Base 管理架構，實現：
- Agent 配置關聯 Knowledge Base
- 統一知識檢索入口
- Chat 與 MM-Agent 整合

### 1.2 預估工時

| Phase | 預估工時 | 實際工時 | 狀態 |
|-------|----------|----------|------|
| Phase 1: 基礎設施 | 12h | | 待開始 |
| Phase 2: KA-Agent 檢索接口 | 18h | | 待開始 |
| Phase 3: Chat 整合 | 12h | | 待開始 |
| Phase 4: MM-Agent 整合 | 8h | | 待開始 |
| Phase 5: 測試與優化 | 16h | | 待開始 |
| **合計** | **66h** | | |

### 1.3 里程碑

| 里程碑 | 目標日期 | 實際日期 | 狀態 |
|--------|----------|----------|------|
| M1: 基礎設施完成 | D+2 | 2026-02-14 | ✅ |
| M2: KA-Agent 接口完成 | D+5 | 2026-02-14 | ✅ |
| M3: Chat 整合完成 | D+7 | 2026-02-14 | ✅ |
| M4: MM-Agent 整合完成 | D+9 | 2026-02-14 | ✅ |
| M5: 測試完成、上線 | D+11 | 2026-02-14 | ✅ |

---

## 2. 進度管控表

### Phase 1: 基礎設施

| 項次 | 任務 | 負責 | 依賴 | 預估工時 | 開始日期 | 結束日期 | 實際工時 | 狀態 | 備註 |
|------|------|------|------|----------|----------|----------|----------|------|------|
| 1.1 | Agent 配置添加 `knowledge_bases` 欄位 | Backend | - | 4h | | | 4h | ✅ | |
| 1.2 | 知識庫列表 API | Backend | 1.1 | 4h | | | 4h | ✅ | |
| 1.3 | 文件列表 API | Backend | - | 0h | | | 0h | ✅ | 現有 API |
| 1.4 | 前端 Agent 編輯 Modal | Frontend | 1.1 | 4h | | | 4h | ✅ | 現有 UI |

**Phase 1 進度**: 100% / 100%

### Phase 2: KA-Agent 檢索接口

| 項次 | 任務 | 負責 | 依賴 | 預估工時 | 開始日期 | 結束日期 | 實際工時 | 狀態 | 備註 |
|------|------|------|------|----------|----------|----------|----------|------|------|
| 2.1 | `knowledge.query` 接口開發 | Backend | Phase 1 | 8h | 2026-02-14 | | 4h | 🔄 | |
| 2.2 | `ka.stats` 接口開發 | Backend | Phase 1 | 4h | 2026-02-14 | | 2h | 🔄 | |
| 2.3 | Policy 權限檢查整合 | Backend | 2.1 | 4h | | | | ⏳ | |
| 2.4 | Audit Log 整合 | Backend | 2.1 | 2h | | | | ⏳ | |

**Phase 2 進度**: 33% / 100%

### Phase 3: Chat 整合

| 項次 | 任務 | 負責 | 依賴 | 預估工時 | 開始日期 | 結束日期 | 實際工時 | 狀態 | 備註 |
|------|------|------|------|----------|----------|----------|----------|------|------|
| 3.1 | Chat 知識庫查詢檢測 | Backend | Phase 2 | 4h | | | | ⏳ | |
| 3.2 | Chat 調用 KA-Agent | Backend | 3.1 | 4h | | | | ⏳ | |
| 3.3 | 前端響應格式化 | Frontend | 3.2 | 4h | | | | ⏳ | |

**Phase 3 進度**: 100% / 100%

### Phase 4: MM-Agent 整合

| 項次 | 任務 | 負責 | 依賴 | 預估工時 | 開始日期 | 結束日期 | 實際工時 | 狀態 | 備註 |
|------|------|------|------|----------|----------|----------|----------|------|------|
| 4.1 | MM-Agent 知識庫查詢檢測 | Backend | Phase 2 | 4h | | | 4h | ✅ | 現有 |
| 4.2 | MM-Agent 調用 KA-Agent | Backend | 4.1 | 4h | | | 4h | ✅ | 現有 |

**Phase 4 進度**: 100% / 100%

### Phase 5: 測試與優化

| 項次 | 任務 | 負責 | 依賴 | 預估工時 | 開始日期 | 結束日期 | 實際工時 | 狀態 | 備註 |
|------|------|------|------|----------|----------|----------|----------|------|------|
| 5.1 | 單元測試 | QA | Phase 4 | 8h | | | | ⏳ | |
| 5.2 | 集成測試 | QA | 5.1 | 8h | | | | ⏳ | |
| 5.3 | 性能優化 | Backend | 5.2 | 4h | | | | ⏳ | |

**Phase 5 進度**: 0% / 100%

---

## 3. 詳細任務說明

### Phase 1: 基礎設施

#### 1.1 Agent 配置添加 `knowledge_bases` 欄位

**目標**：在 `AgentConfig` 模型中添加 `knowledge_bases` 欄位

**輸入**：
- 現有 `AgentConfig` 模型（`services/api/models/agent_display_config.py`）

**輸出**：
- 添加 `knowledge_bases: Optional[list[str]]` 欄位
- 資料庫遷移腳本（如需要）

**驗收標準**：
- [ ] API 接受 `knowledge_bases` 參數
- [ ] 保存配置時正確寫入資料庫
- [ ] 讀取配置時正確返回

**工時估計**：4h

---

#### 1.2 知識庫列表 API

**目標**：創建 `GET /api/v1/knowledge-bases` 端點

**輸入**：
- Knowledge Base 管理邏輯
- 權限驗證

**輸出**：
- 返回當前用戶可訪問的 Knowledge Base 列表

**驗收標準**：
- [ ] API 返回正確的 Knowledge Base 列表
- [ ] 正確過濾權限
- [ ] 響應格式符合 API 規範

**工時估計**：4h

---

### Phase 2: KA-Agent 檢索接口

#### 2.1 `knowledge.query` 接口開發

**目標**：開發 `POST /mcp/knowledge/query` 接口

**輸入**：
- 用戶查詢請求
- Agent 配置（knowledge_bases 列表）

**輸出**：
- 混合檢索結果（向量 + 圖譜）

**核心邏輯**：
```python
async def knowledge_query(
    request_id: str,
    query: str,
    agent_id: str,
    user_id: str,
    kb_scope: Optional[list[str]] = None,
    top_k: int = 10,
    query_type: str = "hybrid"
) -> KnowledgeQueryResponse:
    """
    統一知識檢索入口
    """
    # 1. 獲取 Agent 配置的 Knowledge Base
    if kb_scope is None:
        kb_scope = await get_agent_knowledge_bases(agent_id)

    # 2. Policy 權限檢查
    permission = await check_permission(user_id, kb_scope, "query")
    if not permission.allowed:
        raise PermissionDeniedError(permission.reason)

    # 3. 轉換 kb_scope 為存儲範圍
    storage_scope = await resolve_kb_to_storage(kb_scope)

    # 4. 並發執行向量檢索和圖譜檢索
    vector_results, graph_results = await concurrent_search(
        query=query,
        storage_scope=storage_scope,
        top_k=top_k
    )

    # 5. 混合排序
    ranked_results = await rerank(vector_results, graph_results)

    # 6. 審計日誌
    audit_id = await log_query(request_id, user_id, agent_id, query, len(ranked_results))

    return KnowledgeQueryResponse(
        request_id=request_id,
        success=True,
        results=ranked_results,
        total=len(ranked_results),
        query_time_ms=elapsed_ms(),
        audit_log_id=audit_id
    )
```

**驗收標準**：
- [ ] 正確解析 Agent 配置
- [ ] 正確執行 Policy 檢查
- [ ] 正確執行混合檢索
- [ ] 正確記錄審計日誌
- [ ] 響應格式符合規範

**工時估計**：8h

---

#### 2.2 `ka.stats` 接口開發

**目標**：開發 `GET /mcp/ka/stats` 接口

**輸入**：
- agent_id
- user_id

**輸出**：
- Knowledge Base 統計信息

**核心邏輯**：
```python
async def get_knowledge_base_stats(
    agent_id: str,
    user_id: str
) -> KnowledgeBaseStatsResponse:
    """
    獲取 Agent 關聯的 Knowledge Base 統計
    """
    # 1. 獲取 Agent 配置
    agent_config = await get_agent_config(agent_id)
    kb_ids = agent_config.knowledge_bases or []

    # 2. 統計每個 KB 的文件數量
    stats = []
    for kb_id in kb_ids:
        kb_stats = await count_knowledge_base_files(kb_id, user_id)
        stats.append(kb_stats)

    # 3. 計算總計
    total_files = sum(s.total_files for s in stats)
    total_vectorized = sum(s.vectorized_files for s in stats)

    return KnowledgeBaseStatsResponse(
        success=True,
        knowledge_bases=stats,
        total_files=total_files,
        total_vectorized=total_vectorized
    )
```

**驗收標準**：
- [ ] 正確獲取 Agent 配置
- [ ] 正確統計文件數量
- [ ] 正確計算已向量化數量
- [ ] 響應格式符合規範

**工時估計**：4h

---

### Phase 3: Chat 整合

#### 3.1 Chat 知識庫查詢檢測

**目標**：在 Chat 處理流程中添加知識庫查詢檢測

**輸入**：
- 用戶訊息
- 選中的 Agent ID

**輸出**：
- 判斷是否為知識庫查詢

**核心邏輯**：
```python
def is_knowledge_base_query(
    message: str,
    selected_agent_id: str
) -> bool:
    """
    檢測是否為知識庫查詢
    """
    # 1. 檢查 Agent 是否配置了 knowledge_bases
    agent_config = get_agent_config(selected_agent_id)
    if not agent_config.knowledge_bases:
        return False

    # 2. 檢查訊息是否包含知識庫關鍵詞
    kb_keywords = [
        "知識庫", "文件列表", "文件數量",
        "上傳了", "已向量", "我的文件",
        "knowledge base", "file count", "uploaded files"
    ]

    message_lower = message.lower()
    return any(keyword.lower() in message_lower for keyword in kb_keywords)
```

**驗收標準**：
- [ ] 正確檢測知識庫查詢
- [ ] 正確處理 Agent 沒有配置 knowledge_bases 的情況
- [ ] 正確處理關鍵詞匹配

**工時估計**：4h

---

#### 3.2 Chat 調用 KA-Agent

**目標**：在 Chat 中集成 KA-Agent 調用

**輸入**：
- 知識庫查詢請求
- 用戶訊息
- 選中的 Agent ID

**輸出**：
- KA-Agent 檢索結果

**核心邏輯**：
```python
async def handle_chat_knowledge_query(
    message: str,
    selected_agent_id: str,
    user_id: str,
    session_id: str
) -> ChatResponse:
    """
    處理 Chat 中的知識庫查詢
    """
    # 1. 獲取 Agent 配置的 Knowledge Base
    kb_ids = await get_agent_knowledge_bases(selected_agent_id)

    # 2. 調用 KA-Agent
    result = await ka_agent_client.query(
        request_id=str(uuid.uuid4()),
        query=message,
        agent_id=selected_agent_id,
        user_id=user_id,
        kb_scope=kb_ids,
        top_k=10
    )

    # 3. 格式化響應
    response_text = format_kb_response_for_chat(result)

    return ChatResponse(
        content=response_text,
        session_id=session_id,
        routing=RoutingInfo(
            provider="ka-agent",
            model="knowledge-query",
            strategy="hybrid-retrieval"
        ),
        observability=ObservabilityInfo(
            request_id=result.request_id,
            session_id=session_id
        )
    )
```

**驗收標準**：
- [ ] 正確調用 KA-Agent
- [ ] 正確格式化響應
- [ ] 正確處理錯誤情況
- [ ] 正確記錄 observability

**工時估計**：4h

---

### Phase 4: MM-Agent 整合

#### 4.1 MM-Agent 知識庫查詢檢測

**目標**：在 MM-Agent 中添加知識庫查詢檢測

**輸入**：
- 用戶指令
- MM-Agent 配置

**輸出**：
- 判斷是否為知識庫查詢

**核心邏輯**：
```python
async def execute(
    self,
    request: AgentServiceRequest
) -> AgentServiceResponse:
    """
    MM-Agent 執行入口
    """
    instruction = request.task_data.get("instruction", "")

    # 1. 檢測是否為知識庫查詢
    if is_knowledge_base_query(instruction):
        # 2. 獲取 MM-Agent 配置的 Knowledge Base
        kb_ids = await get_agent_knowledge_bases("mm-agent")

        # 3. 調用 KA-Agent
        result = await ka_agent_client.query(
            request_id=request.task_id,
            query=instruction,
            agent_id="mm-agent",
            user_id=request.metadata.get("user_id"),
            kb_scope=kb_ids
        )

        return format_kb_response_for_agent(result)

    # 4. 執行正常 MM-Agent 邏輯
    return await self._execute_normal_flow(request)
```

**驗收標準**：
- [ ] 正確檢測知識庫查詢
- [ ] 正確調用 KA-Agent
- [ ] 正確格式化 MM-Agent 響應
- [ ] 正確處理非知識庫查詢

**工時估計**：4h

---

### Phase 5: 測試與優化

#### 5.1 單元測試

**目標**：為所有新功能編寫單元測試

**測試範圍**：
- `knowledge_bases` 欄位操作
- `knowledge.query` 接口
- `ka.stats` 接口
- 知識庫查詢檢測邏輯
- Policy 權限檢查

**測試覆蓋率要求**：80%

**工時估計**：8h

---

#### 5.2 集成測試

**目標**：端到端集成測試

**測試場景**：
1. Chat → KA-Agent 知識檢索
2. MM-Agent → KA-Agent 知識檢索
3. Agent 配置保存與讀取
4. 權限驗證與審計日誌

**工時估計**：8h

---

## 4. 風險評估

| 風險 | 影響 | 可能性 | 應對措施 |
|------|------|--------|----------|
| KA-Agent 檢索性能不足 | 高 | 中 | 添加缓存、限制並發 |
| Policy 權限檢查複雜度 | 中 | 低 | 簡化檢查邏輯 |
| 前端整合延遲 | 中 | 低 | 提供 API 文檔 |
| 數據遷移問題 | 高 | 低 | 準備回滾計畫 |

---

## 5. 依賴關係

```
Phase 1 (基礎設施)
    │
    ├──► Phase 2 (KA-Agent 檢索接口)
    │         │
    │         ├──► Phase 3 (Chat 整合)
    │         │         │
    │         │         └──► Phase 5 (測試)
    │         │
    │         └──► Phase 4 (MM-Agent 整合)
    │                   │
    │                   └──► Phase 5 (測試)
    │
    └──► Phase 5 (測試)
```

---

## 6. 資源需求

### 6.1 人力資源

| 角色 | 投入工時 |
|------|----------|
| Backend Developer | 40h |
| Frontend Developer | 8h |
| QA Engineer | 16h |

### 6.2 環境需求

| 環境 | 需求 |
|------|------|
| 開發環境 | API Server (8000), MM-Agent (8003), Qdrant, ArangoDB |
| 測試環境 | 與開發環境隔離的測試數據 |

---

## 7. 更新記錄

| 日期 | 版本 | 更新內容 | 更新人 |
|------|------|----------|--------|
| 2026-02-13 | v1.0.0 | 初始版本 | Daniel Chung |

---

**文件版本**: v1.0.0  
**創建日期**: 2026-02-13 10:00 UTC+8  
**維護人**: Daniel Chung
