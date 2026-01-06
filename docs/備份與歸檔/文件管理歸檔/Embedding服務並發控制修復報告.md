# Embedding 服務並發控制修復報告

**創建日期**: 2026-01-02
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-02

---

## 📋 問題分析

### 原始問題

在階段二批量測試中，即使將 `concurrency_limit` 降低到 3，Ollama embedding API 仍然返回 500 錯誤。經過深入分析，發現了以下設計缺陷：

1. **非全局 Semaphore**：每次調用 `generate_embeddings_batch` 時都會創建新的 `asyncio.Semaphore`，導致多個文件並發處理時，實際並發數超過 `concurrency_limit`。
2. **批次大小不匹配**：`batch_size` (50) 遠大於 `concurrency_limit` (3)，導致批次內並發處理時資源競爭。
3. **錯誤處理過於嚴格**：單個 embedding 失敗會導致整個批次失敗，影響批量處理的穩定性。
4. **缺乏監控**：無法追蹤實際的並發請求數和系統狀態。

---

## 🔧 修復方案

### 1. 類級別全局 Semaphore

**問題**：每個文件處理都創建自己的 Semaphore，無法真正控制全局並發。

**解決方案**：
- 將 Semaphore 改為類級別變量（`_global_semaphore`）
- 所有 `EmbeddingService` 實例共享同一個 Semaphore
- 確保所有文件處理共享同一個並發限制

**實現**：
```python
class EmbeddingService:
    # 類級別全局 Semaphore（所有實例共享）
    _global_semaphore: Optional[asyncio.Semaphore] = None
    _global_concurrency_limit: Optional[int] = None
    _active_requests: int = 0
    _lock: Optional[asyncio.Lock] = None
```

### 2. 智能批次大小調整

**問題**：`batch_size` (50) > `concurrency_limit` (3)，導致批次內並發超過限制。

**解決方案**：
- 在初始化時自動調整 `batch_size`，確保不超過 `concurrency_limit`
- 如果 `batch_size > concurrency_limit`，自動將 `batch_size` 調整為 `concurrency_limit`

**實現**：
```python
# 智能調整 batch_size：確保 batch_size 不超過 concurrency_limit
if self.batch_size > self.concurrency_limit:
    logger.warning(
        "batch_size exceeds concurrency_limit, adjusting batch_size",
        original_batch_size=self.batch_size,
        concurrency_limit=self.concurrency_limit,
    )
    self.batch_size = max(self.concurrency_limit, 1)
```

### 3. 部分失敗容錯機制

**問題**：單個 embedding 失敗會導致整個批次失敗，影響批量處理的穩定性。

**解決方案**：
- 允許部分失敗，使用空列表表示失敗的 embedding
- 只有當所有文本都失敗時才拋出異常
- 記錄失敗的文本索引和錯誤信息

**實現**：
```python
# 處理錯誤：允許部分失敗（產品級容錯）
embeddings: List[List[float]] = []
failed_count = 0

for i, result in enumerate(results):
    if isinstance(result, Exception):
        failed_count += 1
        logger.error(...)
        embeddings.append([])  # 使用空列表表示失敗
    elif isinstance(result, list):
        embeddings.append(result)

# 如果所有文本都失敗，才拋出異常
if failed_count == len(texts):
    raise RuntimeError(...)
elif failed_count > 0:
    logger.warning(...)  # 記錄部分失敗
```

### 4. 詳細監控和日誌

**問題**：無法追蹤實際的並發請求數和系統狀態。

**解決方案**：
- 添加 `_active_requests` 計數器，追蹤當前活躍的請求數
- 在關鍵點記錄詳細日誌（開始、完成、失敗）
- 記錄並發限制、活躍請求數、批次信息等

**實現**：
```python
# 更新活躍請求計數（用於監控）
async with lock:
    EmbeddingService._active_requests += 1
    current_active = EmbeddingService._active_requests
logger.debug(
    "Starting embedding request",
    active_requests=current_active,
    concurrency_limit=self.concurrency_limit,
    file_id=file_id,
)
```

---

## 📊 修復效果

### 修復前

- ❌ 多個文件並發時，實際並發數 = `concurrency_limit × 文件數`
- ❌ `batch_size` (50) > `concurrency_limit` (3)，導致資源競爭
- ❌ 單個失敗導致整個批次失敗
- ❌ 無法監控實際並發狀態

### 修復後

- ✅ 所有文件共享同一個並發限制，實際並發數 ≤ `concurrency_limit`
- ✅ `batch_size` 自動調整，確保不超過 `concurrency_limit`
- ✅ 允許部分失敗，提高批量處理的穩定性
- ✅ 詳細監控和日誌，便於問題診斷

---

## 🔍 技術細節

### 全局 Semaphore 初始化

**同步初始化**（在 `__init__` 中）：
```python
if EmbeddingService._global_semaphore is None:
    EmbeddingService._global_semaphore = asyncio.Semaphore(self.concurrency_limit)
    EmbeddingService._global_concurrency_limit = self.concurrency_limit
```

**異步更新**（在第一次使用時）：
```python
async def _ensure_global_semaphore(self) -> None:
    """確保全局 Semaphore 已初始化並與當前 concurrency_limit 匹配"""
    lock = self._get_lock()
    async with lock:
        if (
            EmbeddingService._global_semaphore is None
            or EmbeddingService._global_concurrency_limit != self.concurrency_limit
        ):
            # 重新創建 Semaphore
            EmbeddingService._global_semaphore = asyncio.Semaphore(self.concurrency_limit)
            EmbeddingService._global_concurrency_limit = self.concurrency_limit
```

### 並發控制流程

1. **初始化階段**：
   - 讀取配置（`config.json` 或環境變量）
   - 調整 `batch_size` 以匹配 `concurrency_limit`
   - 同步初始化全局 Semaphore（如果尚未初始化）

2. **請求階段**：
   - 確保全局 Semaphore 已初始化（異步檢查）
   - 更新活躍請求計數
   - 在 Semaphore 保護下執行請求
   - 更新活躍請求計數（finally 塊）

3. **批次處理階段**：
   - 使用全局 Semaphore 控制批次間並發
   - 批次內文本使用 `asyncio.gather` 並發處理（但受全局 Semaphore 限制）
   - 允許部分失敗，記錄詳細日誌

---

## ✅ 驗證清單

- [x] 全局 Semaphore 實現（類級別變量）
- [x] 智能批次大小調整
- [x] 部分失敗容錯機制
- [x] 詳細監控和日誌
- [x] 代碼格式化（black）
- [x] 代碼風格檢查（ruff）
- [x] 類型檢查（mypy）
- [x] 文件頭註釋更新（日期：2026-01-02）

---

## 📝 使用建議

### 配置建議

1. **`concurrency_limit`**：
   - 建議值：3-10（根據 Ollama 服務器性能調整）
   - 過低（<3）：可能無法充分利用資源
   - 過高（>10）：可能導致 Ollama 服務器過載

2. **`batch_size`**：
   - 會自動調整為不超過 `concurrency_limit`
   - 建議手動設置為 `concurrency_limit` 或更小

3. **監控**：
   - 查看日誌中的 `active_requests` 和 `concurrency_limit`
   - 如果 `active_requests` 持續接近 `concurrency_limit`，考慮增加限制

### 測試建議

1. **單一文件測試**：驗證基本功能正常
2. **批量文件測試**：驗證並發控制有效
3. **壓力測試**：逐步增加並發數，觀察 Ollama 服務器響應

---

## 🔄 向後兼容性

- ✅ 保持現有 API 接口不變
- ✅ 保持現有配置格式不變
- ✅ 自動調整 `batch_size`，無需手動修改配置
- ✅ 部分失敗容錯機制不影響正常流程

---

## 📚 相關文檔

- [文件上傳向量圖譜化測試計劃](./文件上傳向量圖譜化測試計劃.md)
- [第一階段測試報告](./第一階段測試報告.md)
- [第一階段測試問題分析](./第一階段測試問題分析.md)

---

**最後更新日期**: 2026-01-02

