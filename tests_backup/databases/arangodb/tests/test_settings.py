# 代碼功能說明: ArangoDB 設定載入測試
# 創建日期: 2025-11-25 22:58 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:58 (UTC+8)

"""測試設定載入與快取行為。"""

from __future__ import annotations

import json

from databases.arangodb.settings import (
    clear_arangodb_settings_cache,
    load_arangodb_settings,
)


def test_load_settings_from_custom_config(tmp_path):
    config = {
        "datastores": {
            "arangodb": {
                "host": "arangodb.internal",
                "port": 9000,
                "protocol": "https",
                "database": "kg",
                "request_timeout": 15,
            }
        }
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    clear_arangodb_settings_cache()
    settings = load_arangodb_settings(config_path)
    assert settings.host == "arangodb.internal"
    assert settings.port == 9000
    assert settings.protocol == "https"
    assert settings.request_timeout == 15


def test_settings_cache_can_be_cleared(tmp_path):
    config_a = {
        "datastores": {
            "arangodb": {
                "host": "host-a",
            }
        }
    }
    config_b = {
        "datastores": {
            "arangodb": {
                "host": "host-b",
            }
        }
    }
    path_a = tmp_path / "config_a.json"
    path_b = tmp_path / "config_b.json"
    path_a.write_text(json.dumps(config_a), encoding="utf-8")
    path_b.write_text(json.dumps(config_b), encoding="utf-8")

    clear_arangodb_settings_cache()
    settings_a = load_arangodb_settings(path_a)
    assert settings_a.host == "host-a"

    # 即使切換檔案，若未清空快取仍會回傳舊設定
    settings_cached = load_arangodb_settings(path_a)
    assert settings_cached.host == "host-a"

    clear_arangodb_settings_cache()
    settings_b = load_arangodb_settings(path_b)
    assert settings_b.host == "host-b"
