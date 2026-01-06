#!/usr/bin/env python3
# 代碼功能說明: 直接更新 KG 提取模型配置
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""直接更新 KG 提取模型配置為 Gemini 最新模型"""

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

from services.api.services.config_store_service import ConfigStoreService
from services.api.models.config import ConfigUpdate


def main():
    model_name = sys.argv[1] if len(sys.argv) > 1 else "gemini-2.5-flash"
    
    print("=" * 60)
    print("直接更新 KG 提取模型配置")
    print("=" * 60)
    print(f"模型名稱: {model_name}")
    print()
    
    try:
        service = ConfigStoreService()
        kg_config = service.get_config("kg_extraction", tenant_id=None)
        
        if not kg_config:
            print("❌ 未找到 kg_extraction 配置")
            return 1
        
        config_data = kg_config.config_data.copy()
        print("當前配置:")
        print(f"  NER: {config_data.get('ner_model_type')} - {config_data.get('ner_model')}")
        print(f"  RE: {config_data.get('re_model_type')} - {config_data.get('re_model')}")
        print(f"  RT: {config_data.get('rt_model_type')} - {config_data.get('rt_model')}")
        print()
        
        # 更新為新模型
        config_data["ner_model"] = model_name
        config_data["re_model"] = model_name
        config_data["rt_model"] = model_name
        
        update = ConfigUpdate(config_data=config_data, is_active=True)
        service.update_config("kg_extraction", update, tenant_id=None)
        
        print("✅ 已更新配置")
        print(f"  NER: {config_data.get('ner_model_type')} - {config_data.get('ner_model')}")
        print(f"  RE: {config_data.get('re_model_type')} - {config_data.get('re_model')}")
        print(f"  RT: {config_data.get('rt_model_type')} - {config_data.get('rt_model')}")
        print()
        print("=" * 60)
        print("更新完成")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

