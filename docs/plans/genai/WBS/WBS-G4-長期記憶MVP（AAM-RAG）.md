<!--
代碼功能說明: WBS-G4 長期記憶 MVP（AAM/RAG）
創建日期: 2025-12-13 13:55 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 13:55 (UTC+8)
-->

# WBS-G4：長期記憶 MVP（AAM/RAG）

## 目標

在不做大重構前提下，先交付「可用的長期記憶」：

- 根據 user query 檢索長期記憶（向量/圖譜至少一種）
- 把檢索結果注入到 MoE Chat 的上下文

## 工作項

- **G4.1 Retrieval 管線**
  - MVP：向量檢索（ChromaDB）
  - 可選：圖譜檢索（ArangoDB）

- **G4.2 注入策略**
  - 以 system message 或 tool-context 方式注入
  - 控制 top-k、總字數、引用格式

- **G4.3 Memory 寫入策略（MVP）**
  - 先以「對話摘要/關鍵片段」寫入 long-term
  - 後續再加異步 knowledge extraction

- **G4.4 指標**
  - memory_hit_count、memory_sources、retrieval_latency

## 驗收

- 同一 user 連續對話可以看到「長期記憶」對回覆的影響
- memory hit 的指標可觀測
