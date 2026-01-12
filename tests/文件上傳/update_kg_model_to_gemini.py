#!/usr/bin/env python3
# 代碼功能說明: 將 KG 提取模型配置更新為 Gemini
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""將 KG 提取模型配置更新為 Gemini"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加載環境變數
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

# 設置環境變數（臨時）
os.environ["NER_MODEL_TYPE"] = "gemini"
os.environ["OLLAMA_NER_MODEL"] = "gemini-pro"
os.environ["RE_MODEL_TYPE"] = "gemini"
os.environ["OLLAMA_RE_MODEL"] = "gemini-pro"
os.environ["RT_MODEL_TYPE"] = "gemini"
os.environ["OLLAMA_RT_MODEL"] = "gemini-pro"

from database.arangodb.client import ArangoDBClient
from services.api.models.config import ConfigUpdate
from services.api.services.config_store_service import ConfigStoreService


def update_config():
    """更新 KG 提取模型配置為 Gemini"""
    try:
        client = ArangoDBClient()
        if client.db is None:
            print("❌ ArangoDB 連接失敗")
            return False

        service = ConfigStoreService()

        # 獲取當前配置
        kg_config = service.get_config("kg_extraction", tenant_id=None)

        if kg_config:
            # 更新配置
            config_data = kg_config.config_data.copy()
            config_data["ner_model_type"] = "gemini"
            config_data["ner_model"] = "gemini-pro"
            config_data["re_model_type"] = "gemini"
            config_data["re_model"] = "gemini-pro"
            config_data["rt_model_type"] = "gemini"
            config_data["rt_model"] = "gemini-pro"

            update = ConfigUpdate(config_data=config_data, is_active=True)

            service.update_config("kg_extraction", update, tenant_id=None)
            print("✅ 已更新 KG 提取模型配置為 Gemini")
            print(f'  NER: {config_data["ner_model_type"]} - {config_data["ner_model"]}')
            print(f'  RE: {config_data["re_model_type"]} - {config_data["re_model"]}')
            print(f'  RT: {config_data["rt_model_type"]} - {config_data["rt_model"]}')
            return True
        else:
            # 創建新配置
            from services.api.models.config import ConfigCreate

            config_data = {
                "enabled": True,
                "mode": "all_chunks",
                "min_confidence": 0.5,
                "ner_model_type": "gemini",
                "ner_model": "gemini-pro",
                "re_model_type": "gemini",
                "re_model": "gemini-pro",
                "rt_model_type": "gemini",
                "rt_model": "gemini-pro",
            }

            create = ConfigCreate(
                scope="kg_extraction", config_data=config_data, is_active=True, tenant_id=None
            )

            service.create_config(create)
            print("✅ 已創建 KG 提取模型配置（Gemini）")
            return True
    except Exception as e:
        print(f"❌ 更新配置失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("更新 KG 提取模型配置為 Gemini")
    print("=" * 60)

    if update_config():
        print("\n✅ 配置更新成功")
        print("請重新啟動 RQ Worker 以使配置生效")
    else:
        print("\n❌ 配置更新失敗")
        sys.exit(1)
