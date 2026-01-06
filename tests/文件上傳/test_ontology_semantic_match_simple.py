# 代碼功能說明: 測試 Ontology 語義匹配選擇功能（簡化版，不依賴 LLM）
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""
簡化測試：驗證語義匹配方法的代碼邏輯和結構
即使 LLM 服務不可用，也能驗證方法是否可以正確調用
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

from kag.ontology_selector import OntologySelector


async def test_semantic_match_simple():
    """簡化測試：驗證方法結構和基本邏輯"""

    print("=" * 80)
    print("Ontology 語義匹配功能 - 代碼結構驗證測試")
    print("=" * 80)

    # 初始化選擇器
    selector = OntologySelector()
    print("✅ OntologySelector 初始化成功")

    # 測試 1: 驗證方法是否存在
    print("\n【測試 1】方法存在性檢查")
    print("-" * 80)
    assert hasattr(selector, "select_by_semantic_match"), "缺少 select_by_semantic_match 方法"
    print("✅ select_by_semantic_match 方法存在")

    assert hasattr(selector, "select_auto_async"), "缺少 select_auto_async 方法"
    print("✅ select_auto_async 方法存在")

    assert hasattr(selector, "_generate_file_summary"), "缺少 _generate_file_summary 方法"
    print("✅ _generate_file_summary 方法存在")

    assert hasattr(selector, "_get_available_ontologies"), "缺少 _get_available_ontologies 方法"
    print("✅ _get_available_ontologies 方法存在")

    assert hasattr(selector, "_semantic_match_ontologies"), "缺少 _semantic_match_ontologies 方法"
    print("✅ _semantic_match_ontologies 方法存在")

    # 測試 2: 測試 _get_available_ontologies（不依賴 LLM）
    print("\n【測試 2】獲取可用 Ontology 列表")
    print("-" * 80)
    try:
        ontologies = selector._get_available_ontologies()
        print(f"✅ 成功獲取 Ontology 列表")
        print(f"   Domain Ontologies 數量: {len(ontologies.get('domain', []))}")
        print(f"   Major Ontologies 數量: {len(ontologies.get('major', []))}")

        # 顯示前幾個 Domain Ontology
        if ontologies.get("domain"):
            print(f"\n   Domain Ontologies 示例:")
            for domain in ontologies["domain"][:3]:
                print(f"     - {domain['file_name']}: {domain['ontology_name']}")

        # 顯示前幾個 Major Ontology
        if ontologies.get("major"):
            print(f"\n   Major Ontologies 示例:")
            for major in ontologies["major"][:3]:
                print(f"     - {major['file_name']}: {major['ontology_name']}")
    except Exception as e:
        print(f"❌ 獲取 Ontology 列表失敗: {e}")
        import traceback
        traceback.print_exc()

    # 測試 3: 測試語義匹配方法調用（會因為 LLM 不可用而返回 None，但不會報錯）
    print("\n【測試 3】語義匹配方法調用（預期失敗但不報錯）")
    print("-" * 80)

    test_file_name = "东方伊厨-预制菜发展策略报告20250902.pdf"
    test_file_content = """
    預製菜產業概述
    預製菜是指經過洗、切、搭配等預處理，然後通過冷凍、真空包裝等方式保存，消費者購買後只需簡單加熱或調味即可食用的食品。
    
    市場發展趨勢：
    1. 消費升級：消費者對便利性和品質的要求提高
    2. 中央廚房模式興起：標準化生產，降低成本
    """

    try:
        result = await selector.select_by_semantic_match(
            file_name=test_file_name,
            file_content=test_file_content,
            file_metadata=None,
        )
        if result:
            print(f"✅ 語義匹配成功（如果 LLM 服務可用）")
            print(f"   選擇方法: {result.get('selection_method')}")
            print(f"   Domain: {result.get('domain', [])}")
            print(f"   Major: {result.get('major', [])}")
        else:
            print(f"⚠️  語義匹配返回 None（可能是 LLM 服務不可用，這是預期的）")
            print(f"   這是正常的，因為測試環境可能沒有配置 LLM 服務")
    except Exception as e:
        print(f"❌ 語義匹配調用異常: {e}")
        import traceback
        traceback.print_exc()

    # 測試 4: 測試自動選擇（會降級到關鍵字匹配）
    print("\n【測試 4】自動選擇（優先語義匹配，失敗時降級到關鍵字匹配）")
    print("-" * 80)

    try:
        result = await selector.select_auto_async(
            file_name=test_file_name,
            file_content=test_file_content,
            file_metadata=None,
            use_semantic_match=True,
        )
        print(f"✅ 自動選擇成功")
        print(f"   選擇方法: {result.get('selection_method')}")
        print(f"   Domain: {result.get('domain', [])}")
        print(f"   Major: {result.get('major', [])}")
        
        if result.get('selection_method') == 'semantic_match':
            print(f"   ✅ 使用了語義匹配")
        elif result.get('selection_method') == 'keywords':
            print(f"   ⚠️  降級到關鍵字匹配（可能是 LLM 服務不可用）")
    except Exception as e:
        print(f"❌ 自動選擇異常: {e}")
        import traceback
        traceback.print_exc()

    # 測試 5: 測試關鍵字匹配（對比）
    print("\n【測試 5】關鍵字匹配（對比測試）")
    print("-" * 80)

    try:
        result = selector.select_auto(
            file_name=test_file_name,
            file_content=test_file_content,
            file_metadata=None,
        )
        print(f"✅ 關鍵字匹配成功")
        print(f"   選擇方法: {result.get('selection_method')}")
        print(f"   Domain: {result.get('domain', [])}")
        print(f"   Major: {result.get('major', [])}")
        print(f"   匹配的關鍵字: {result.get('matched_keywords', [])}")
    except Exception as e:
        print(f"❌ 關鍵字匹配異常: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("代碼結構驗證測試完成")
    print("=" * 80)
    print("\n說明：")
    print("- 如果 LLM 服務可用，語義匹配會正常工作")
    print("- 如果 LLM 服務不可用，系統會自動降級到關鍵字匹配")
    print("- 這是設計的 fallback 機制，確保系統的穩定性")


if __name__ == "__main__":
    asyncio.run(test_semantic_match_simple())

