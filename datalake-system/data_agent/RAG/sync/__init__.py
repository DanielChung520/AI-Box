# Schema 同步腳本
# 代碼功能說明: 同步腳本初始化模組
# 創建日期: 2026-02-13
# 創建人: Daniel Chung

"""Schema 同步腳本

職責：
- sync_jp_schema.py: 同步 Schema (Concepts/Intents/Bindings) 到 Qdrant/ArangoDB
- sync_mmMaster.py: 同步 Master Data (料號/倉庫/工作站) 到 Qdrant/ArangoDB

使用示例：
    # 同步 Schema
    from data_agent.RAG.sync.sync_jp_schema import main
    main()

    # 同步 Master Data
    from data_agent.RAG.sync.sync_mmMaster import MasterDataSync
    sync = MasterDataSync()
    sync.sync_all()
"""

from .sync_jp_schema import main as sync_jp_schema
from .sync_mmMaster import MasterDataSync, main as sync_mmMaster

__all__ = ["sync_jp_schema", "MasterDataSync", "sync_mmMaster"]
