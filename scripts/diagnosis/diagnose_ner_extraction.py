#!/usr/bin/env python3
# 代碼功能說明: 診斷 NER 提取問題
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""診斷 NER 提取問題 - 測試實際的 NER 提取結果"""

import asyncio
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加載環境變數
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

from genai.api.services.ner_service import NERService
from services.api.services.vector_store_service import VectorStoreService
import structlog

logger = structlog.get_logger(__name__)


async def diagnose_ner():
    """診斷 NER 提取問題"""
    print("=" * 70)
    print("NER 提取問題診斷")
    print("=" * 70)
    print()
    
    file_id = "149aee1a-89da-4b07-a83c-634fb29246e2"
    
    # 1. 獲取 chunks
    print("1. 獲取文件 chunks")
    print("-" * 70)
    vector_service = VectorStoreService()
    vectors = vector_service.get_vectors_by_file_id(file_id)
    print(f"  總 chunks 數: {len(vectors)}")
    print()
    
    # 2. 初始化 NER 服務
    print("2. 初始化 NER 服務")
    print("-" * 70)
    ner_service = NERService()
    print(f"  Model type: {ner_service.model_type}")
    print(f"  Model name: {ner_service.model_name}")
    print()
    
    # 3. 測試每個 chunk 的 NER 提取
    print("3. 測試每個 chunk 的 NER 提取")
    print("-" * 70)
    
    for i, vector in enumerate(vectors[:4], 1):
        metadata = vector.get("metadata", {})
        chunk_text = metadata.get("text", "")
        
        print(f"\nChunk {i}:")
        print(f"  文本長度: {len(chunk_text)} 字符")
        print(f"  前200字符: {repr(chunk_text[:200])}")
        
        # 提取實體
        try:
            entities = await ner_service.extract_entities(
                chunk_text,
                user_id="daniel@test.com",
                file_id=file_id,
            )
            
            print(f"  提取到的實體數: {len(entities)}")
            
            if entities:
                print(f"  實體列表:")
                for j, entity in enumerate(entities, 1):
                    print(f"    {j}. {entity.text} ({entity.label}) - confidence: {entity.confidence}")
            else:
                print(f"  ⚠️ 未提取到任何實體")
                
        except Exception as e:
            print(f"  ❌ 提取失敗: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 70)
    print("診斷完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(diagnose_ner())

