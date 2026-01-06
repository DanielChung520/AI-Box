# 代碼功能說明: 測試 Ontology 語義匹配選擇功能
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""
測試腳本：驗證 Ontology 語義匹配選擇功能

測試場景：
1. 測試文件摘要生成
2. 測試語義匹配選擇 Ontology
3. 比較關鍵字匹配與語義匹配的結果
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

from kag.ontology_selector import OntologySelector

logger = structlog.get_logger(__name__)


async def test_semantic_match():
    """測試語義匹配功能"""

    print("=" * 80)
    print("Ontology 語義匹配測試")
    print("=" * 80)

    # 初始化選擇器
    selector = OntologySelector()

    # 測試案例 1: 預製菜文件（應該匹配到 domain-food.json 和 major-prepared-food.json）
    print("\n【測試案例 1】預製菜發展策略報告")
    print("-" * 80)

    test_file_name = "东方伊厨-预制菜发展策略报告20250902.pdf"
    test_file_content = """
    預製菜產業概述
    預製菜是指經過洗、切、搭配等預處理，然後通過冷凍、真空包裝等方式保存，消費者購買後只需簡單加熱或調味即可食用的食品。
    
    市場發展趨勢：
    1. 消費升級：消費者對便利性和品質的要求提高
    2. 中央廚房模式興起：標準化生產，降低成本
    3. 冷鏈物流完善：保證食品新鮮度和安全性
    4. 技術創新：真空包裝、冷凍技術、保鮮技術不斷進步
    
    關鍵企業：
    - 東方伊廚：專業預製菜生產企業，擁有中央廚房和冷鏈物流系統
    - 主要產品：預製菜套餐、半成品食材、調理包
    
    食品安全標準：
    - HACCP 認證
    - ISO 22000 食品安全管理體系
    - 冷鏈溫度控制：-18°C 以下
    """

    print(f"文件名: {test_file_name}")
    print(f"文件內容預覽長度: {len(test_file_content)} 字符")

    # 方法 1: 語義匹配
    print("\n【方法 1】語義匹配（LLM）")
    print("-" * 80)
    try:
        semantic_result = await selector.select_by_semantic_match(
            file_name=test_file_name,
            file_content=test_file_content,
            file_metadata=None,
        )

        if semantic_result:
            print(f"✅ 語義匹配成功")
            print(f"選擇方法: {semantic_result.get('selection_method')}")
            print(f"Domain Ontologies: {semantic_result.get('domain', [])}")
            print(f"Major Ontologies: {semantic_result.get('major', [])}")
            print(f"置信度: {semantic_result.get('confidence', 0.0)}")
            print(f"選擇理由: {semantic_result.get('reasoning', '無')}")
            print(f"\n文件摘要:")
            try:
                summary = json.loads(semantic_result.get('file_summary', '{}'))
                print(json.dumps(summary, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                print(semantic_result.get('file_summary', '無摘要'))
        else:
            print("❌ 語義匹配失敗，返回 None")
    except Exception as e:
        print(f"❌ 語義匹配異常: {e}")
        import traceback
        traceback.print_exc()

    # 方法 2: 關鍵字匹配（對比）
    print("\n【方法 2】關鍵字匹配（傳統方法，對比）")
    print("-" * 80)
    try:
        keyword_result = selector.select_auto(
            file_name=test_file_name,
            file_content=test_file_content,
            file_metadata=None,
        )
        print(f"選擇方法: {keyword_result.get('selection_method')}")
        print(f"Domain Ontologies: {keyword_result.get('domain', [])}")
        print(f"Major Ontologies: {keyword_result.get('major', [])}")
        print(f"匹配的關鍵字: {keyword_result.get('matched_keywords', [])}")
    except Exception as e:
        print(f"❌ 關鍵字匹配異常: {e}")
        import traceback
        traceback.print_exc()

    # 方法 3: 自動選擇（優先語義匹配）
    print("\n【方法 3】自動選擇（優先語義匹配）")
    print("-" * 80)
    try:
        auto_result = await selector.select_auto_async(
            file_name=test_file_name,
            file_content=test_file_content,
            file_metadata=None,
            use_semantic_match=True,
        )
        print(f"選擇方法: {auto_result.get('selection_method')}")
        print(f"Domain Ontologies: {auto_result.get('domain', [])}")
        print(f"Major Ontologies: {auto_result.get('major', [])}")
        if auto_result.get('confidence'):
            print(f"置信度: {auto_result.get('confidence', 0.0)}")
    except Exception as e:
        print(f"❌ 自動選擇異常: {e}")
        import traceback
        traceback.print_exc()

    # 測試案例 2: 沒有明確關鍵字的文件（測試語義理解能力）
    print("\n" + "=" * 80)
    print("【測試案例 2】沒有明確關鍵字的文件")
    print("-" * 80)

    test_file_name_2 = "企業經營分析報告.pdf"
    test_file_content_2 = """
    本報告分析了公司過去一年的經營狀況。
    
    財務指標：
    - 營業收入增長 15%
    - 淨利潤率提升至 12%
    - 資產負債率控制在 60% 以下
    
    組織管理：
    - 完成組織架構調整，優化部門職能
    - 建立績效考核體系
    - 加強員工培訓和發展
    
    專案進展：
    - 新產品開發專案順利推進
    - 市場拓展專案取得初步成效
    - 數位化轉型專案正在規劃中
    """

    print(f"文件名: {test_file_name_2}")
    print(f"文件內容預覽長度: {len(test_file_content_2)} 字符")

    try:
        semantic_result_2 = await selector.select_by_semantic_match(
            file_name=test_file_name_2,
            file_content=test_file_content_2,
            file_metadata=None,
        )

        if semantic_result_2:
            print(f"\n✅ 語義匹配成功")
            print(f"選擇方法: {semantic_result_2.get('selection_method')}")
            print(f"Domain Ontologies: {semantic_result_2.get('domain', [])}")
            print(f"Major Ontologies: {semantic_result_2.get('major', [])}")
            print(f"置信度: {semantic_result_2.get('confidence', 0.0)}")
            print(f"選擇理由: {semantic_result_2.get('reasoning', '無')}")
        else:
            print("\n❌ 語義匹配失敗，返回 None")
    except Exception as e:
        print(f"\n❌ 語義匹配異常: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("測試完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_semantic_match())

