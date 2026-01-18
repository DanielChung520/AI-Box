#!/usr/bin/env python3
# 代碼功能說明: 診斷圖譜提取問題
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""診斷圖譜提取問題 - 檢查配置、模型可用性和實際提取流程"""

import asyncio
import os
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

import structlog

from genai.api.services.ner_service import NERService
from genai.api.services.re_service import REService
from genai.api.services.rt_service import RTService
from genai.api.services.triple_extraction_service import TripleExtractionService
from services.api.services.config_store_service import ConfigStoreService

logger = structlog.get_logger(__name__)


async def diagnose():
    """診斷圖譜提取問題"""
    print("=" * 70)
    print("圖譜提取問題診斷")
    print("=" * 70)
    print()

    # 1. 檢查環境變數
    print("1. 檢查環境變數")
    print("-" * 70)
    env_vars = [
        "NER_MODEL_TYPE",
        "OLLAMA_NER_MODEL",
        "RE_MODEL_TYPE",
        "OLLAMA_RE_MODEL",
        "RT_MODEL_TYPE",
        "OLLAMA_RT_MODEL",
        "GEMINI_API_KEY",
    ]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"  {var} = {value} (⚠️  會覆蓋 ArangoDB 配置)")
        else:
            print(f"  {var} = (未設置)")
    print()

    # 2. 檢查 ArangoDB 配置
    print("2. 檢查 ArangoDB 配置")
    print("-" * 70)
    try:
        config_service = ConfigStoreService()
        kg_config = config_service.get_config("kg_extraction", tenant_id=None)
        if kg_config and kg_config.config_data:
            config_data = kg_config.config_data
            print(f"  NER model_type: {config_data.get('ner_model_type')}")
            print(f"  NER model: {config_data.get('ner_model')}")
            print(f"  RE model_type: {config_data.get('re_model_type')}")
            print(f"  RE model: {config_data.get('re_model')}")
            print(f"  RT model_type: {config_data.get('rt_model_type')}")
            print(f"  RT model: {config_data.get('rt_model')}")
        else:
            print("  ❌ 未找到 kg_extraction 配置")
    except Exception as e:
        print(f"  ❌ 讀取配置失敗: {e}")
    print()

    # 3. 檢查 NER 服務
    print("3. 檢查 NER 服務")
    print("-" * 70)
    try:
        ner_service = NERService()
        print(f"  Model type: {ner_service.model_type}")
        print(f"  Model name: {ner_service.model_name}")
        print(f"  Primary model available: {ner_service._primary_model is not None}")
        if ner_service._primary_model:
            if hasattr(ner_service._primary_model, "is_available"):
                print(f"  Primary model is_available: {ner_service._primary_model.is_available()}")
            print(f"  Primary model type: {type(ner_service._primary_model).__name__}")
        print(f"  Fallback model available: {ner_service._fallback_model is not None}")
    except Exception as e:
        print(f"  ❌ NER 服務初始化失敗: {e}")
        import traceback

        traceback.print_exc()
    print()

    # 4. 檢查 RE 服務
    print("4. 檢查 RE 服務")
    print("-" * 70)
    try:
        re_service = REService()
        print(f"  Model type: {re_service.model_type}")
        print(f"  Model name: {re_service.model_name}")
        print(f"  Primary model available: {re_service._primary_model is not None}")
        if re_service._primary_model:
            if hasattr(re_service._primary_model, "is_available"):
                print(f"  Primary model is_available: {re_service._primary_model.is_available()}")
            print(f"  Primary model type: {type(re_service._primary_model).__name__}")
    except Exception as e:
        print(f"  ❌ RE 服務初始化失敗: {e}")
        import traceback

        traceback.print_exc()
    print()

    # 5. 檢查 RT 服務
    print("5. 檢查 RT 服務")
    print("-" * 70)
    try:
        rt_service = RTService()
        print(f"  Model type: {rt_service.model_type}")
        print(f"  Model name: {rt_service.model_name}")
        print(f"  Primary model available: {rt_service._primary_model is not None}")
        if rt_service._primary_model:
            if hasattr(rt_service._primary_model, "is_available"):
                print(f"  Primary model is_available: {rt_service._primary_model.is_available()}")
            print(f"  Primary model type: {type(rt_service._primary_model).__name__}")
    except Exception as e:
        print(f"  ❌ RT 服務初始化失敗: {e}")
        import traceback

        traceback.print_exc()
    print()

    # 6. 測試實際提取（使用簡單文本）
    print("6. 測試實際提取（使用簡單文本）")
    print("-" * 70)
    test_text = "生質能源是一種可再生能源，通過氣化熱解技術可以將廢棄物轉化為合成氣。"
    print(f"  測試文本: {test_text}")
    print()

    try:
        triple_service = TripleExtractionService()
        print("  開始提取三元組...")
        triples = await triple_service.extract_triples(
            text=test_text,
            entities=None,
            enable_ner=True,
            ontology_rules=None,
        )
        print(f"  提取結果: {len(triples)} 個三元組")
        if triples:
            for i, triple in enumerate(triples[:3], 1):
                print(
                    f"    {i}. {triple.subject.text} - {triple.relation.type} - {triple.object.text}"
                )
        else:
            print("  ⚠️  未提取到任何三元組")
    except Exception as e:
        print(f"  ❌ 提取失敗: {e}")
        import traceback

        traceback.print_exc()
    print()

    # 7. 檢查 Gemini 客戶端（如果使用 Gemini）
    print("7. 檢查 Gemini 客戶端")
    print("-" * 70)
    try:
        from llm.clients.gemini import GeminiClient

        gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_api_key:
            print(f"  Gemini API Key: {gemini_api_key[:10]}... (已設置)")
            try:
                client = GeminiClient()
                print(f"  Gemini client available: {client.is_available()}")
            except Exception as e:
                print(f"  ❌ Gemini 客戶端初始化失敗: {e}")
        else:
            print("  ⚠️  Gemini API Key 未設置")
    except ImportError as e:
        print(f"  ⚠️  Gemini 客戶端不可用: {e}")
    except Exception as e:
        print(f"  ❌ 檢查 Gemini 客戶端時出錯: {e}")
    print()

    print("=" * 70)
    print("診斷完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(diagnose())
