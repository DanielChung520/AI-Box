# 代碼功能說明: 後台為指定用戶或全部用戶寫入 AI 處理同意（data_consents）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28 12:00 UTC+8

"""後台授予 AI 處理同意腳本。

用法:
  python scripts/grant_ai_consent.py --user-id <user_id>   # 為單一用戶寫入
  python scripts/grant_ai_consent.py --all                 # 為 user_tasks 中所有 user_id 寫入

從專案根目錄執行。
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 將專案根目錄加入 path，以便 import services
_root = Path(__file__).resolve().parent.parent  # 專案根目錄（腳本在 scripts/）
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# 顯式加載 .env（依 .cursorrules 規範）；腳本需先設定 path 再 import 專案模組
from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=_root / ".env")

from database.arangodb import ArangoDBClient  # noqa: E402
from services.api.models.data_consent import ConsentType, DataConsentCreate  # noqa: E402
from services.api.services.data_consent_service import get_consent_service  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _collect_user_ids_from_tasks(client: ArangoDBClient) -> list[str]:
    """從 user_tasks 取得不重複的 user_id 列表。"""
    if client.db is None or client.db.aql is None:
        raise RuntimeError("ArangoDB AQL is not available")
    aql = (
        "FOR doc IN user_tasks COLLECT user_id = doc.user_id FILTER user_id != null RETURN user_id"
    )
    cursor = client.db.aql.execute(aql)
    return list(cursor)


def main() -> int:
    parser = argparse.ArgumentParser(description="後台為用戶寫入 AI 處理同意（data_consents）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-id", type=str, help="要授予同意的單一 user_id")
    group.add_argument("--all", action="store_true", help="為 user_tasks 中所有 user_id 授予同意")
    args = parser.parse_args()

    user_ids: list[str] = []
    if args.user_id:
        user_ids = [args.user_id]
    else:
        client = ArangoDBClient()
        try:
            user_ids = _collect_user_ids_from_tasks(client)
        except Exception as e:
            logger.error(f"從 user_tasks 取得 user_id 失敗: {e}")
            return 1
        if not user_ids:
            logger.warning("user_tasks 中無任何 user_id，不執行寫入")
            return 0

    consent_service = get_consent_service()
    create = DataConsentCreate(
        consent_type=ConsentType.AI_PROCESSING,
        purpose="後台授予 AI 處理同意",
        granted=True,
        expires_at=None,
    )
    ok = 0
    for uid in user_ids:
        try:
            consent_service.record_consent(uid, create)
            logger.info(f"已寫入 AI 處理同意: user_id={uid}")
            ok += 1
        except Exception as e:
            logger.warning(f"寫入失敗 user_id={uid}: {e}")
    logger.info(f"完成: 成功 {ok}/{len(user_ids)}")
    return 0 if ok == len(user_ids) else 1


if __name__ == "__main__":
    sys.exit(main())
