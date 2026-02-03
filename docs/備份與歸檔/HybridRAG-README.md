# Hybrid RAG 檔案整合存檔

## 整合說明

此目錄包含已整合的 Hybrid RAG 相關檔案。為了簡化專案結構和減少重複代碼，相關的 Hybrid RAG 實現已被整合到主文件：

**主要實現位置**: `genai/workflows/rag/hybrid_rag.py`

## 存檔文件說明

### 核心實現文件
- `hybrid_rag.py` - AAM 內的簡化 Hybrid RAG 實現（已整合到主文件）
- `hybrid_factory.py` - Hybrid RAG 工廠類（功能已整合）
- `hybrid_orchestrator.py` - Hybrid RAG 協調器（功能已整合）

### 工具與演示
- `hybrid_mode_demo.py` - Hybrid 模式演示腳本

### 測試文件
- `tests/test_hybrid_orchestrator.py` - 協調器測試
- `tests/test_hybrid_integration.py` - 整合測試
- `tests/test_hybrid_mode.py` - Phase3 混合模式測試

### 文檔
- `docs/hybrid_mode.md` - Hybrid 模式說明文檔
- `docs/wbs-3.4-hybrid-mode.md` - WBS 3.4 Hybrid 模式計劃

## 整合決策

1. **保留主文件**: `genai/workflows/rag/hybrid_rag.py` 包含最完整的實現
2. **移除重複**: 多個簡化的 Hybrid RAG 實現已被整合
3. **保留歷史**: 將相關文件存檔以供參考

## 使用說明

如果需要使用 Hybrid RAG 功能，請直接使用：

```python
from genai.workflows.rag.hybrid_rag import HybridRAGService
```

---

**整合日期**: 2026-01-23
**整合人**: Daniel Chung