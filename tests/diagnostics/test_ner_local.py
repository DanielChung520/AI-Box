import asyncio
import logging
import sys
from pathlib import Path

# 設置路徑
base_dir = Path(__file__).resolve().parent
sys.path.append(str(base_dir))

from genai.api.services.ner_service import NERService

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_ner():
    print("Initializing NERService...")
    service = NERService()
    service.model_name = "qwen3-coder:30b"
    service._init_models()
    print(f"Using model: {service.model_name} (type: {service.model_type})")

    text = "中央廚房採用真空包裝技術生產預製菜產品，保質期可達 30 天。生產線使用自動化設備，每日產能約 5000 份。"
    print(f"\nTesting NER with text: {text}")

    try:
        entities = await service.extract_entities(text)
        # 獲取最後一個請求的原始響應
        print(f"\nExtracted {len(entities)} entities:")
        for ent in entities:
            print(f"- {ent.text} ({ent.label}) [conf: {ent.confidence}]")

        if not entities:
            print("\nWARNING: No entities extracted!")

    except Exception as e:
        print(f"\nError during extraction: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ner())
