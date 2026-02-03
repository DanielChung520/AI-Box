#!/usr/bin/env python3
# 代碼功能說明: 對 KA-Agent 任務下的文件觸發完整處理（分塊+向量+圖譜）
# 創建日期: 2026-01-25 21:15 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-25 21:15 UTC+8

"""對已上傳但未產生 Qdrant 向量/圖譜的 KA-Agent 文件進行補跑

使用方式:
    SYSTEADMIN_PASSWORD=xxx python scripts/reprocess_ka_agent_knowledge.py
    或 python scripts/reprocess_ka_agent_knowledge.py --password xxx

前置：已執行 scripts/upload_ka_agent_knowledge.py 上架；API 與 RQ Worker 須運行。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv

    _env = _project_root / ".env"
    if _env.exists():
        load_dotenv(_env)
except ImportError:
    pass

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    import requests
except ImportError:
    print("需要安裝 requests: pip install requests")
    sys.exit(1)

TASK_ID = "KA-Agent"
USER_ID = "systemAdmin"


def login(api_base: str, password: str) -> str:
    r = requests.post(
        f"{api_base}/api/v1/auth/login",
        json={"username": USER_ID, "password": password},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("data", {}).get("access_token"):
        raise RuntimeError("登入成功但未返回 access_token")
    return data["data"]["access_token"]


def list_files(api_base: str, token: str) -> list[dict]:
    r = requests.get(
        f"{api_base}/api/v1/files",
        params={"task_id": TASK_ID, "limit": 100},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    files = data.get("data", {}).get("files", [])
    return files if isinstance(files, list) else []


def regenerate_full(api_base: str, token: str, file_id: str, filename: str) -> tuple[bool, str]:
    r = requests.post(
        f"{api_base}/api/v1/files/{file_id}/regenerate",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"type": "full"},
        timeout=30,
    )
    if r.status_code in (200, 201):
        j = r.json()
        job_id = (j.get("data") or {}).get("job_id", "?")
        return True, job_id
    return False, r.text[:200]


def main() -> int:
    ap = argparse.ArgumentParser(description="對 KA-Agent 任務文件觸發完整處理（分塊+向量+圖譜）")
    ap.add_argument("--api-base", default="http://localhost:8000", help="API 基底 URL")
    pw = os.environ.get("SYSTEADMIN_PASSWORD") or os.environ.get("SYSTEM_ADMIN_PASSWORD")
    ap.add_argument("--password", default=pw, help="systemAdmin 密碼")
    args = ap.parse_args()
    if not args.password:
        args.password = "systemAdmin@2026"
        print("使用 auth fallback 密碼")
    token = login(args.api_base, args.password)
    files = list_files(args.api_base, token)
    if not files:
        print("任務 KA-Agent 下無文件，請先執行上架腳本")
        return 1
    ok = 0
    for f in files:
        fid = f.get("file_id") or f.get("id")
        fn = f.get("filename", "?")
        if not fid:
            continue
        success, msg = regenerate_full(args.api_base, token, fid, fn)
        if success:
            print(f"已提交: {fn} (job_id={msg})")
            ok += 1
        else:
            print(f"失敗: {fn} -> {msg}")
    print(f"補跑完成: {ok} / {len(files)}")
    return 0 if ok == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())
