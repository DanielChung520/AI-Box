#!/usr/bin/env python3
# 代碼功能說明: 更新 KG 提取模型配置為 Gemini 最新模型
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""更新 KG 提取模型配置為 Gemini 最新模型

使用方法:
    python update_kg_model_to_gemini_latest.py [model_name]

默認使用: gemini-2.5-flash (推薦，速度快)
其他選項: gemini-pro-latest, gemini-2.5-pro
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.api.models.config import ConfigUpdate
from services.api.services.config_store_service import ConfigStoreService


def update_kg_model(model_name: str = "gemini-2.5-flash"):
    """更新 KG 提取模型配置"""
    service = ConfigStoreService()

    # 獲取當前配置
    kg_config = service.get_config("kg_extraction", tenant_id=None)

    if not kg_config:
        print("❌ 未找到 kg_extraction 配置")
        return False

    # 更新配置
    config_data = kg_config.config_data.copy()
    config_data["ner_model_type"] = "gemini"
    config_data["ner_model"] = model_name
    config_data["re_model_type"] = "gemini"
    config_data["re_model"] = model_name
    config_data["rt_model_type"] = "gemini"
    config_data["rt_model"] = model_name

    update = ConfigUpdate(config_data=config_data, is_active=True)

    service.update_config("kg_extraction", update, tenant_id=None)

    print("✅ 已更新 KG 提取模型配置")
    print(f"  NER: gemini - {model_name}")
    print(f"  RE: gemini - {model_name}")
    print(f"  RT: gemini - {model_name}")
    print()
    print("⚠️  請重啟 RQ Worker 以應用新配置:")
    print("  ./scripts/start_services.sh restart rq_worker")

    return True


if __name__ == "__main__":
    model_name = sys.argv[1] if len(sys.argv) > 1 else "gemini-2.5-flash"

    print("=" * 60)
    print("更新 KG 提取模型配置為 Gemini")
    print("=" * 60)
    print(f"模型名稱: {model_name}")
    print()

    if update_kg_model(model_name):
        print("=" * 60)
        print("更新完成")
        print("=" * 60)
    else:
        print("=" * 60)
        print("更新失敗")
        print("=" * 60)
        sys.exit(1)
