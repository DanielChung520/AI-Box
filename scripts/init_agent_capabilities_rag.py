# 代碼功能說明: Agent 能力 RAG 初始化腳本
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""初始化 Agent 能力 RAG 向量庫

將 Agent 相關文檔存儲到 RAG 向量數據庫，以便在 Agent 選擇時進行語義檢索。
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict

# 添加項目根目錄到 Python 路徑
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

logger = logging.getLogger(__name__)


def load_markdown_file(file_path: Path) -> str:
    """讀取 Markdown 文件內容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load file {file_path}: {e}")
        return ""


async def vectorize_and_store_document(
    chroma_client: Any,
    collection_name: str,
    content: str,
    metadata: Dict[str, Any],
    chunk_processor: Any,
    embedding_service: Any,
) -> bool:
    """將文檔向量化並存儲到 ChromaDB"""
    try:
        # 使用 ChunkProcessor 分割文檔
        chunks = chunk_processor.process(
            text=content,
            file_id=metadata.get("doc_id", "unknown"),
            metadata=metadata,
        )

        # 為每個塊生成嵌入向量
        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            # 生成嵌入向量
            # 提取文本（chunk 是字典，包含 text 字段）
            chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
            if not chunk_text:
                continue

            embedding = await embedding_service.generate_embedding(chunk_text)

            # 提取文本（chunk 是字典，包含 text 字段）
            chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
            if not chunk_text:
                continue

            documents.append(chunk_text)
            metadatas.append(
                {
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
            )
            ids.append(f"{metadata.get('doc_id', 'unknown')}_chunk_{i}")

        # 存儲到 ChromaDB
        collection = chroma_client.get_or_create_collection(collection_name)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=[
                e.tolist() if hasattr(e, "tolist") else e
                for e in [await embedding_service.generate_embedding(d) for d in documents]
            ],
        )

        logger.info(f"Successfully stored document {metadata.get('doc_id')} ({len(chunks)} chunks)")
        return True
    except Exception as e:
        logger.error(f"Failed to vectorize and store document: {e}", exc_info=True)
        return False


async def main():
    """主函數"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting Agent Capabilities RAG initialization...")

    try:
        from database.chromadb import ChromaDBClient
        from services.api.processors.chunk_processor import ChunkConfig, ChunkProcessor
        from services.api.services.embedding_service import get_embedding_service

        # 初始化服務
        chroma_client = ChromaDBClient()
        embedding_service = get_embedding_service()
        chunk_processor = ChunkProcessor(
            config=ChunkConfig(
                chunk_size=768,
            ),
            overlap=0.2,
        )

        collection_name = "agent_capabilities"

        # 1. 存儲設計文檔
        docs_dir = _project_root / "docs" / "系统设计文档" / "核心组件"

        # 文件編輯-Agent-模組設計-v2.md
        doc1_path = docs_dir / "IEE對話式開發文件編輯" / "文件編輯-Agent-模組設計-v2.md"
        if doc1_path.exists():
            content = load_markdown_file(doc1_path)
            if content:
                metadata = {
                    "doc_id": "file_editing_agent_module_design_v2",
                    "doc_type": "design_document",
                    "title": "文件編輯 Agent 模組設計 v2.0",
                    "category": "module_design",
                    "version": "2.0",
                }
                await vectorize_and_store_document(
                    chroma_client,
                    collection_name,
                    content,
                    metadata,
                    chunk_processor,
                    embedding_service,
                )

        # 文件編輯-Agent-系統規格書-v2.0.md
        doc2_path = docs_dir / "IEE對話式開發文件編輯" / "文件編輯-Agent-系統規格書-v2.0.md"
        if doc2_path.exists():
            content = load_markdown_file(doc2_path)
            if content:
                metadata = {
                    "doc_id": "file_editing_agent_spec_v2",
                    "doc_type": "specification",
                    "title": "文件編輯 Agent 系統規格書 v2.0",
                    "category": "specification",
                    "version": "2.0",
                }
                await vectorize_and_store_document(
                    chroma_client,
                    collection_name,
                    content,
                    metadata,
                    chunk_processor,
                    embedding_service,
                )

        # Agent-Platform-v3.md
        doc3_path = docs_dir / "Agent平台" / "Agent-Platform-v3.md"
        if doc3_path.exists():
            content = load_markdown_file(doc3_path)
            if content:
                metadata = {
                    "doc_id": "agent_platform_v3",
                    "doc_type": "architecture",
                    "title": "Agent Platform 架構文檔 v3",
                    "category": "architecture",
                    "version": "3.0",
                }
                await vectorize_and_store_document(
                    chroma_client,
                    collection_name,
                    content,
                    metadata,
                    chunk_processor,
                    embedding_service,
                )

        logger.info("Agent Capabilities RAG initialization completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Failed to initialize Agent Capabilities RAG: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
