# 文件編輯 Agent v2.0 模組設計文檔

**代碼功能說明**: 文件編輯 Agent v2.0 模組設計文檔
**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11

---

## 概述

本文檔詳細說明文件編輯 Agent v2.0 的模組設計，包括各模組的職責、接口、實現細節和模組之間的交互關係。

---

## 模組架構

```
agents/builtin/document_editing_v2/
├── agent.py              # DocumentEditingAgentV2 主類
├── models.py             # 數據模型（DocumentContext, EditIntent, PatchResponse）
└── __init__.py

agents/core/editing_v2/
├── intent_validator.py       # Intent DSL 驗證
├── markdown_parser.py        # Markdown AST 解析
├── target_locator.py         # Target Selector 定位（支持模糊匹配）
├── fuzzy_matcher.py          # 模糊匹配器（新增）
├── context_assembler.py      # 最小上下文裝配（性能優化）
├── content_generator.py      # LLM 內容生成
├── patch_generator.py        # Block Patch 生成
├── validator_linter.py       # 驗證與 Linter（支持進階驗證）
├── style_checker.py          # 樣式檢查器（新增）
├── semantic_drift_checker.py # 語義漂移檢查器（新增）
├── external_reference_checker.py # 外部參照檢查器（新增）
├── audit_logger.py           # 審計日誌服務（性能優化）
├── audit_models.py           # 審計事件模型（新增）
├── workspace_integration.py  # 任務工作區整合
├── error_handler.py          # 錯誤處理
└── schemas.py                # JSON Schema 定義
```

---

## 核心模組設計

### 1. DocumentEditingAgentV2

**位置**: `agents/builtin/document_editing_v2/agent.py`

**職責**:

- 實現 `AgentServiceProtocol` 接口
- 協調各個核心服務模組
- 處理請求驗證和錯誤處理
- 集成審計日誌記錄

**主要方法**:

- `execute(request: AgentServiceRequest) -> AgentServiceResponse`: 執行編輯任務
- `health_check() -> AgentServiceStatus`: 健康檢查
- `get_capabilities() -> Dict[str, Any]`: 獲取服務能力

**依賴關係**:

- `IntentValidator`: Intent DSL 驗證
- `WorkspaceIntegration`: 文件讀取
- `MarkdownParser`: Markdown 解析
- `TargetLocator`: 目標定位（支持模糊匹配）
- `ContextAssembler`: 上下文裝配
- `ContentGenerator`: 內容生成
- `ValidatorLinter`: 驗證（支持進階驗證）
- `PatchGenerator`: Patch 生成
- `AuditLogger`: 審計日誌記錄

---

### 2. FuzzyMatcher（模糊匹配器）

**位置**: `agents/core/editing_v2/fuzzy_matcher.py`

**職責**:

- 實現模糊匹配算法（Levenshtein Distance）
- 支持 Heading、Anchor、Block 的模糊匹配
- 性能優化：結果緩存、搜索範圍限制、早期退出

**主要方法**:

- `fuzzy_match_heading(target_text, target_level, blocks) -> List[Tuple[Block, float]]`: Heading 模糊匹配
- `fuzzy_match_anchor(target_anchor_id, blocks) -> List[Tuple[Block, float]]`: Anchor 模糊匹配
- `fuzzy_match_block(target_content, blocks) -> List[Tuple[Block, float]]`: Block 模糊匹配
- `calculate_similarity(text1, text2) -> float`: 計算相似度
- `normalize_text(text) -> str`: 標準化文本

**性能優化**:

- **結果緩存**: 標準化文本緩存（限制緩存大小）
- **搜索範圍限制**: `max_search_blocks` 參數（默認 100）
- **早期退出**: 如果找到高相似度匹配（> 0.95），提前返回

**配置參數**:

- `similarity_threshold`: 相似度閾值（0-1），默認 0.7
- `max_search_blocks`: 最大搜索 Block 數量，默認 100

---

### 3. TargetLocator（目標定位器）

**位置**: `agents/core/editing_v2/target_locator.py`

**職責**:

- 定位目標 Block（根據 Target Selector）
- 精確匹配失敗時自動嘗試模糊匹配
- 返回結構化的候選列表（多個匹配時）

**主要方法**:

- `locate(target_selector: TargetSelector) -> MarkdownBlock`: 定位目標 Block

**集成模糊匹配**:

- 精確匹配失敗時，自動調用 `FuzzyMatcher` 進行模糊匹配
- 如果只有一個高相似度匹配（> 0.9），直接返回
- 如果有多個匹配，返回候選列表（最多 5 個）

**配置參數**:

- `fuzzy_threshold`: 模糊匹配相似度閾值，默認 0.7
- `enable_fuzzy`: 是否啟用模糊匹配，默認 True

---

### 4. StyleChecker（樣式檢查器）

**位置**: `agents/core/editing_v2/style_checker.py`

**職責**:

- 實現樣式檢查（語氣、術語、格式）
- 支持多種樣式指南（如 "enterprise-tech-v1"）
- 返回結構化的違規列表

**主要方法**:

- `check(content: str) -> List[Dict[str, Any]]`: 檢查樣式違規
- `_check_tone(content) -> List[Dict]`: 檢查語氣
- `_check_terminology(content) -> List[Dict]`: 檢查術語
- `_check_format(content) -> List[Dict]`: 檢查格式

**支持的檢查**:

- **語氣檢查**: 禁止第一人稱、禁止命令式
- **術語檢查**: 必需術語、禁止術語
- **格式檢查**: 表格標頭、列表格式

---

### 5. SemanticDriftChecker（語義漂移檢查器）

**位置**: `agents/core/editing_v2/semantic_drift_checker.py`

**職責**:

- 實現語義漂移檢查（NER 變更率、關鍵詞交集比例）
- 比較原始內容和新內容的語義差異
- 返回結構化的違規信息

**主要方法**:

- `check(original_content: str, new_content: str) -> List[Dict[str, Any]]`: 檢查語義漂移
- `_check_ner_change_rate(original, new) -> Optional[Dict]`: 檢查 NER 變更率
- `_check_keywords_overlap(original, new) -> Optional[Dict]`: 檢查關鍵詞交集比例
- `_extract_entities(content) -> Set[str]`: 提取命名實體
- `_extract_keywords(content, top_n) -> Set[str]`: 提取關鍵詞

**配置參數**:

- `ner_change_rate_max`: NER 變更率最大值（0-1），默認 0.3
- `keywords_overlap_min`: 關鍵詞交集比例最小值（0-1），默認 0.5

---

### 6. ExternalReferenceChecker（外部參照檢查器）

**位置**: `agents/core/editing_v2/external_reference_checker.py`

**職責**:

- 實現外部參照檢查（外部 URL、未在上下文中的事實）
- 檢測外部 URL 鏈接
- 檢測未在上下文中的引用

**主要方法**:

- `check(content: str, no_external_reference: bool) -> List[Dict[str, Any]]`: 檢查外部參照
- `_check_external_urls(content) -> List[Dict]`: 檢查外部 URL
- `_check_facts_not_in_context(content) -> List[Dict]`: 檢查未在上下文中的事實

---

### 7. ValidatorLinter（驗證器）

**位置**: `agents/core/editing_v2/validator_linter.py`

**職責**:

- 實現基本驗證（結構檢查、長度檢查）
- 集成進階驗證（樣式檢查、語義漂移檢查、外部參照檢查）
- 返回結構化的驗證錯誤

**主要方法**:

- `validate(content: str, constraints: Optional[Constraints]) -> None`: 驗證內容
- `_validate_structure(content) -> None`: 結構檢查
- `_validate_length(content, constraints) -> None`: 長度檢查
- `_validate_style(content, style_guide) -> None`: 樣式檢查（新增）
- `_validate_semantic_drift(content) -> None`: 語義漂移檢查（新增）
- `_validate_external_reference(content) -> None`: 外部參照檢查（新增）

**驗證流程**:

1. 結構檢查（標題階層、Markdown 語法）
2. 長度檢查（max_tokens、max_chars）
3. 樣式檢查（如果配置了 `style_guide`）
4. 語義漂移檢查（如果提供了原始內容）
5. 外部參照檢查（如果 `no_external_reference` 為 true）

---

### 8. AuditLogger（審計日誌服務）

**位置**: `agents/core/editing_v2/audit_logger.py`

**職責**:

- 記錄審計事件（9 個事件類型）
- 存儲 Patch 和 Intent（不可變存儲）
- 支持事件查詢
- 性能優化：異步寫入、批量寫入

**主要方法**:

- `log_event(...) -> AuditEvent`: 記錄審計事件
- `store_patch(...) -> PatchStorage`: 存儲 Patch
- `store_intent(...) -> IntentStorage`: 存儲 Intent
- `query_events(...) -> List[AuditEvent]`: 查詢審計事件
- `get_patch(patch_id) -> Optional[PatchStorage]`: 獲取 Patch
- `get_intent(intent_id) -> Optional[IntentStorage]`: 獲取 Intent
- `flush() -> None`: 刷新所有隊列

**性能優化**:

- **異步寫入**: 使用隊列，不阻塞主流程
- **批量寫入**: 收集多個事件後一次性寫入（`batch_size` 默認 10）
- **寫入降級**: 如果數據庫寫入失敗，降級到內存存儲

**配置參數**:

- `async_write`: 是否使用異步寫入，默認 True
- `batch_size`: 批量寫入大小，默認 10

---

### 9. ContextAssembler（上下文裝配器）

**位置**: `agents/core/editing_v2/context_assembler.py`

**職責**:

- 裝配最小上下文（目標 Block + 相鄰 Block）
- 計算上下文摘要（SHA-256）
- 格式化上下文為 LLM 輸入格式
- 性能優化：上下文緩存

**主要方法**:

- `assemble_context(target_block: MarkdownBlock) -> List[MarkdownBlock]`: 裝配上下文
- `compute_context_digest(context_blocks) -> str`: 計算上下文摘要
- `format_context_for_llm(context_blocks) -> str`: 格式化上下文
- `clear_cache() -> None`: 清除緩存

**性能優化**:

- **上下文緩存**: 緩存已計算的上下文（基於 block_id 和 max_context_blocks）
- **緩存大小限制**: 限制緩存大小（默認 100 個條目）

**配置參數**:

- `max_context_blocks`: 最大上下文 Block 數量，默認 5
- `enable_cache`: 是否啟用緩存，默認 True

---

## 數據模型

### AuditEvent（審計事件）

**位置**: `agents/core/editing_v2/audit_models.py`

```python
class AuditEvent(BaseModel):
    event_id: str
    event_type: AuditEventType
    intent_id: Optional[str]
    patch_id: Optional[str]
    doc_id: Optional[str]
    timestamp: datetime
    duration: Optional[float]
    metadata: Dict[str, Any]
    user_id: Optional[str]
    tenant_id: Optional[str]
```

**事件類型**:

1. `INTENT_RECEIVED` - Intent 接收
2. `INTENT_VALIDATED` - Intent 驗證
3. `TARGET_LOCATED` - 目標定位
4. `CONTEXT_ASSEMBLED` - 上下文裝配
5. `CONTENT_GENERATED` - 內容生成
6. `PATCH_GENERATED` - Patch 生成
7. `VALIDATION_PASSED` - 驗證通過
8. `VALIDATION_FAILED` - 驗證失敗
9. `PATCH_APPLIED` - Patch 應用

---

### PatchStorage / IntentStorage

**位置**: `agents/core/editing_v2/audit_models.py`

```python
class PatchStorage(BaseModel):
    patch_id: str
    intent_id: str
    doc_id: str
    block_patch: Dict[str, Any]
    text_patch: str
    content_hash: str  # SHA-256
    created_at: datetime
    created_by: str

class IntentStorage(BaseModel):
    intent_id: str
    doc_id: str
    intent_data: Dict[str, Any]
    content_hash: str  # SHA-256
    created_at: datetime
    created_by: str
```

---

## 模組交互流程

### 完整編輯流程

```
DocumentEditingAgentV2.execute()
    ↓
1. IntentValidator.parse_intent() [記錄 INTENT_RECEIVED, INTENT_VALIDATED]
    ↓
2. WorkspaceIntegration.get_file_content()
    ↓
3. MarkdownParser.parse()
    ↓
4. TargetLocator.locate() [記錄 TARGET_LOCATED]
    ├─→ 精確匹配成功 → 返回 Block
    └─→ 精確匹配失敗 → FuzzyMatcher.fuzzy_match_*() → 返回 Block 或候選列表
    ↓
5. ContextAssembler.assemble_context() [記錄 CONTEXT_ASSEMBLED]
    ↓
6. ContentGenerator.generate_content() [記錄 CONTENT_GENERATED]
    ↓
7. ValidatorLinter.validate() [記錄 VALIDATION_PASSED/FAILED]
    ├─→ StyleChecker.check() (如果配置了 style_guide)
    ├─→ SemanticDriftChecker.check() (如果提供了原始內容)
    └─→ ExternalReferenceChecker.check() (如果 no_external_reference = true)
    ↓
8. PatchGenerator.generate_block_patch() [記錄 PATCH_GENERATED]
    ↓
9. AuditLogger.store_patch() / store_intent()
    ↓
10. 返回 PatchResponse
```

---

## 性能優化策略

### 1. 模糊匹配性能優化

- **結果緩存**: 標準化文本緩存
- **搜索範圍限制**: 限制搜索 Block 數量（`max_search_blocks`）
- **早期退出**: 高相似度匹配提前返回

### 2. 審計日誌性能優化

- **異步寫入**: 使用隊列，不阻塞主流程
- **批量寫入**: 收集多個事件後一次性寫入
- **寫入降級**: 數據庫失敗時降級到內存存儲

### 3. 上下文裝配性能優化

- **上下文緩存**: 緩存已計算的上下文
- **上下文大小限制**: 限制上下文 Block 數量

---

## 擴展性設計

### 新增樣式指南

1. 在 `StyleChecker._load_style_rules()` 中添加新的規則集
2. 實現對應的檢查邏輯
3. 在 `constraints.style_guide` 中指定樣式指南名稱

### 新增驗證器

1. 實現驗證器類（繼承或實現統一的接口）
2. 在 `ValidatorLinter` 中集成新驗證器
3. 在 `constraints` 中添加對應的配置選項

### 新增審計事件類型

1. 在 `AuditEventType` 枚舉中添加新類型
2. 在 `DocumentEditingAgentV2.execute()` 中添加事件記錄點
3. 更新審計日誌查詢邏輯（如需要）

---

## 測試策略

### 單元測試

- 每個模組都有對應的單元測試
- 測試覆蓋率目標：> 80%

### 集成測試

- 測試完整編輯流程
- 測試模糊匹配集成
- 測試進階驗證集成
- 測試審計日誌集成

### 性能測試

- 測試各模組的性能指標
- 確保性能指標達標

---

## 參考文檔

- 《文件編輯-Agent-系統規格書-v2.0.md》
- 《文件編輯-Agent-v2-重構計劃書.md》
- API 文檔：`docs/api/document-editing-agent-v2-api.md`
