# 代碼功能說明: NER 性能測試腳本
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""NER 性能測試腳本 - 測試實體識別速度和準確率"""

import asyncio
import time
import json
from typing import List, Dict, Optional
import argparse

from services.api.services.ner_service import NERService


async def test_ner_performance(
    texts: List[str], model_type: Optional[str] = None, batch_size: int = 32
) -> Dict:
    """測試 NER 性能"""
    service = NERService()

    # 單文本測試
    single_start = time.time()
    single_results = []
    for text in texts[:10]:  # 測試前10個文本
        try:
            entities = await service.extract_entities(text, model_type)
            single_results.append(len(entities))
        except Exception as e:
            print(f"單文本提取失敗: {e}")
            single_results.append(0)
    single_time = time.time() - single_start
    single_avg_time = single_time / len(texts[:10]) if texts[:10] else 0

    # 批量測試
    batch_start = time.time()
    try:
        batch_results = await service.extract_entities_batch(texts, model_type)
        batch_time = time.time() - batch_start
        batch_avg_time = batch_time / len(texts) if texts else 0
        batch_total_entities = sum(len(r) for r in batch_results)
    except Exception as e:
        print(f"批量提取失敗: {e}")
        batch_time = 0
        batch_avg_time = 0
        batch_total_entities = 0

    # 計算 tokens（簡單估算：中文字符數）
    total_chars = sum(len(text) for text in texts)
    tokens_per_second = total_chars / batch_time if batch_time > 0 else 0

    return {
        "model_type": model_type or service.model_type,
        "total_texts": len(texts),
        "single_text": {
            "total_time": single_time,
            "avg_time": single_avg_time,
            "texts_processed": len(texts[:10]),
        },
        "batch": {
            "total_time": batch_time,
            "avg_time": batch_avg_time,
            "total_entities": batch_total_entities,
        },
        "performance": {
            "tokens_per_second": tokens_per_second,
            "target_met": tokens_per_second > 1000,
        },
    }


def generate_test_texts(count: int = 100) -> List[str]:
    """生成測試文本"""
    base_texts = [
        "張三在北京的微軟公司工作，他是一名軟件工程師。",
        "李四和王五在2024年1月1日創建了一家新公司。",
        "蘋果公司發布了新的iPhone產品，售價為999美元。",
        "上海是中國最大的城市之一，位於長江三角洲。",
        "馬雲創立了阿里巴巴集團，總部位於杭州。",
    ]

    texts = []
    for i in range(count):
        texts.append(base_texts[i % len(base_texts)])

    return texts


async def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="NER 性能測試")
    parser.add_argument("--texts", type=int, default=100, help="測試文本數量（默認：100）")
    parser.add_argument(
        "--model-type", type=str, default=None, help="模型類型（spacy/ollama）"
    )
    parser.add_argument("--output", type=str, default=None, help="輸出結果文件路徑（JSON）")

    args = parser.parse_args()

    print(f"生成 {args.texts} 個測試文本...")
    texts = generate_test_texts(args.texts)

    print(f"開始性能測試（模型類型: {args.model_type or '默認'}）...")
    results = await test_ner_performance(texts, args.model_type)

    print("\n=== 性能測試結果 ===")
    print(f"模型類型: {results['model_type']}")
    print(f"總文本數: {results['total_texts']}")
    print("\n單文本處理:")
    print(f"  總時間: {results['single_text']['total_time']:.2f} 秒")
    print(f"  平均時間: {results['single_text']['avg_time']:.3f} 秒/文本")
    print("\n批量處理:")
    print(f"  總時間: {results['batch']['total_time']:.2f} 秒")
    print(f"  平均時間: {results['batch']['avg_time']:.3f} 秒/文本")
    print(f"  識別實體總數: {results['batch']['total_entities']}")
    print("\n性能指標:")
    print(f"  處理速度: {results['performance']['tokens_per_second']:.2f} tokens/秒")
    print(
        f"  目標達成: {'✓' if results['performance']['target_met'] else '✗'} (> 1000 tokens/秒)"
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n結果已保存到: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
