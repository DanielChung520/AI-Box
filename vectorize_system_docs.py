# 代碼功能說明: 系統設計文檔向量化腳本
# 創建日期: 2025-12-31
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-31

"""將系統設計文檔向量化並存儲到 ChromaDB collection='system'"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

import structlog

from database.chromadb import ChromaCollection, ChromaDBClient
from services.api.processors.chunk_processor import ChunkConfig, ChunkProcessor, ChunkStrategy
from services.api.services.embedding_service import get_embedding_service

logger = structlog.get_logger(__name__)


async def vectorize_system_docs(
    docs_dir: str = "docs/系统设计文档",
    collection_name: str = "system",
    chunk_strategy: ChunkStrategy = ChunkStrategy.SEMANTIC,
    chunk_size: int = 768,
) -> None:
    """
    將系統設計文檔向量化並存儲到 ChromaDB

    Args:
        docs_dir: 文檔目錄路徑
        collection_name: ChromaDB collection 名稱
        chunk_strategy: 分塊策略
        chunk_size: 分塊大小（字符數）
    """
    # 獲取項目根目錄
    project_root = Path(__file__).parent
    docs_path = project_root / docs_dir

    if not docs_path.exists():
        raise ValueError(f"文檔目錄不存在: {docs_path}")

    logger.info("開始向量化系統設計文檔", docs_dir=str(docs_path), collection_name=collection_name)

    # 初始化服務
    chroma_client = ChromaDBClient()
    embedding_service = get_embedding_service()

    # 使用 ChunkConfig 配置（長期可配置策略）
    chunk_config = ChunkConfig(
        chunk_size=chunk_size,
        min_chunk_size=50,
        max_chunk_size=2000,
        max_code_block_size=2000,
        table_context_lines=3,
        combine_text_paragraphs=True,
        separate_code_blocks=True,
        separate_tables=True,
        enable_quality_check=True,
        enable_adaptive_size=True,
    )
    chunk_processor = ChunkProcessor(
        chunk_size=chunk_size,
        strategy=chunk_strategy,
        overlap=0.2,
        config=chunk_config,
    )

    # 創建或獲取 collection
    collection_obj = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"source": "system_docs", "docs_dir": str(docs_path)},
    )
    collection = ChromaCollection(collection_obj)

    # 統計信息
    total_files = 0
    total_chunks = 0
    total_vectors = 0

    # 遍歷所有 Markdown 文件
    md_files = list(docs_path.rglob("*.md"))
    logger.info(f"找到 {len(md_files)} 個 Markdown 文件")

    for md_file in md_files:
        try:
            # 跳過某些文件（如 README、臨時文件等）
            if md_file.name.startswith(".") or md_file.name.lower() == "readme.md":
                continue

            logger.info(f"處理文件: {md_file.relative_to(project_root)}")

            # 讀取文件內容
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                logger.warning(f"文件為空，跳過: {md_file.name}")
                continue

            # 生成文件 ID（使用相對路徑）
            relative_path = md_file.relative_to(project_root)
            file_id = str(relative_path).replace("/", "_").replace("\\", "_").replace(".md", "")

            # 準備文件元數據
            file_metadata = {
                "source_file": str(relative_path),
                "file_name": md_file.name,
                "file_path": str(relative_path),
                "content_type": "text/markdown",
            }

            # 分塊
            chunks = chunk_processor.process(
                text=content,
                file_id=file_id,
                metadata=file_metadata,
            )

            if not chunks:
                logger.warning(f"文件分塊為空，跳過: {md_file.name}")
                continue

            logger.info(f"文件分塊完成: {len(chunks)} 個分塊", file=md_file.name)

            # 生成向量
            chunk_texts = [chunk.get("text", "") for chunk in chunks]
            embeddings = await embedding_service.generate_embeddings_batch(chunk_texts)

            if len(embeddings) != len(chunks):
                raise ValueError(f"向量數量 ({len(embeddings)}) 與分塊數量 ({len(chunks)}) 不匹配")

            # 準備存儲數據
            ids: List[str] = []
            documents: List[str] = []
            metadatas: List[Dict[str, Any]] = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_id}_chunk_{i}"
                ids.append(chunk_id)
                documents.append(chunk.get("text", ""))

                # 準備元數據
                chunk_metadata = chunk.get("metadata", {}).copy()
                metadata: Dict[str, Any] = {
                    **chunk_metadata,
                    "file_id": file_id,
                    "chunk_index": i,
                    "chunk_text": chunk.get("text", "")[:200],  # 前200字符用於索引
                    "source_file": file_metadata["source_file"],
                    "file_name": file_metadata["file_name"],
                    "file_path": file_metadata["file_path"],
                }

                # 將列表和字典轉換為 JSON 字符串（ChromaDB 不支持）
                for k, v in metadata.items():
                    if isinstance(v, (list, dict)):
                        metadata[k] = json.dumps(v, ensure_ascii=False)

                metadatas.append(metadata)

            # 批量存儲到 ChromaDB
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            total_files += 1
            total_chunks += len(chunks)
            total_vectors += len(embeddings)

            logger.info(
                f"文件向量化完成: {md_file.name}",
                chunks=len(chunks),
                vectors=len(embeddings),
            )

        except Exception as e:
            logger.error(f"處理文件失敗: {md_file.name}", error=str(e))
            continue

    # 輸出統計信息
    logger.info(
        "系統設計文檔向量化完成",
        total_files=total_files,
        total_chunks=total_chunks,
        total_vectors=total_vectors,
        collection_name=collection_name,
    )

    # 獲取 collection 統計
    try:
        count = collection.count()
        logger.info(f"Collection '{collection_name}' 總向量數: {count}")
    except Exception as e:
        logger.warning(f"無法獲取 collection 統計信息: {e}")


def main() -> None:
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="向量化系統設計文檔")
    parser.add_argument(
        "--docs-dir",
        type=str,
        default="docs/系统设计文档",
        help="文檔目錄路徑（相對項目根目錄）",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="system",
        help="ChromaDB collection 名稱",
    )
    parser.add_argument(
        "--chunk-strategy",
        type=str,
        choices=["fixed_size", "sliding_window", "semantic", "ast_driven"],
        default="semantic",
        help="分塊策略（推薦：semantic 用於 Markdown 文檔，支持代碼塊和表格保護）",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=768,
        help="分塊大小（字符數，默認 768）",
    )

    args = parser.parse_args()

    # 轉換分塊策略
    strategy_map = {
        "fixed_size": ChunkStrategy.FIXED_SIZE,
        "sliding_window": ChunkStrategy.SLIDING_WINDOW,
        "semantic": ChunkStrategy.SEMANTIC,
        "ast_driven": ChunkStrategy.AST_DRIVEN,
    }
    chunk_strategy = strategy_map[args.chunk_strategy]

    # 運行向量化
    asyncio.run(
        vectorize_system_docs(
            docs_dir=args.docs_dir,
            collection_name=args.collection,
            chunk_strategy=chunk_strategy,
            chunk_size=args.chunk_size,
        )
    )


if __name__ == "__main__":
    main()
