#!/usr/bin/env python3
# 代碼功能說明: 以 systemAdmin 上架 MM-Agent 知識庫至 task MM-Agent
# 創建日期: 2026-01-25 23:51 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-25 23:51 UTC+8

"""上架 MM-Agent 知識庫（Ontology 須已導入）

使用方式:
    SYSTEADMIN_PASSWORD=xxx python scripts/upload_mm_agent_knowledge.py
    或
    python scripts/upload_mm_agent_knowledge.py --password xxx

須先執行: scripts/import_mm_agent_ontology.py
API 服務須運行於 --api-base（預設 http://localhost:8000）
知識庫目錄：docs/系统设计文档/核心组件/Agent平台/MM-Agent/知識庫
上傳時僅取根目錄檔案，略過 Ontology/ 等子目錄。

注意：MM 知識庫刻意包含 PDF 與大檔案，上傳使用 application/pdf、可調 --upload-timeout。
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

KNOWLEDGE_DIR = (
    _project_root / "docs" / "系统设计文档" / "核心组件" / "Agent平台" / "MM-Agent" / "知識庫"
)
TASK_ID = "MM-Agent"
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


def ensure_task(api_base: str, token: str) -> None:
    r = requests.post(
        f"{api_base}/api/v1/user-tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "task_id": TASK_ID,
            "title": TASK_ID,
            "user_id": USER_ID,
            "status": "pending",
            "messages": [],
            "fileTree": [],
        },
        timeout=30,
    )
    if r.status_code in (200, 201):
        print("Task MM-Agent 已就緒")
        return
    try:
        err = r.json()
        msg = err.get("message", err.get("detail", r.text))
    except Exception:
        msg = r.text
    if "already" in msg.lower() or "exists" in msg.lower() or r.status_code == 409:
        print("Task MM-Agent 已存在，繼續上傳")
        return
    r.raise_for_status()


def upload_files(api_base: str, token: str, upload_timeout: int = 300) -> int:
    if not KNOWLEDGE_DIR.is_dir():
        print("知識庫目錄不存在:", KNOWLEDGE_DIR)
        return 1
    files = [f for f in KNOWLEDGE_DIR.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not files:
        print("知識庫目錄為空")
        return 0
    headers = {"Authorization": f"Bearer {token}"}
    ok = 0
    for path in sorted(files):
        with open(path, "rb") as f:
            suffix = path.suffix.lower()
            if suffix == ".md":
                mime = "text/markdown"
            elif suffix == ".pdf":
                mime = "application/pdf"
            else:
                mime = "application/octet-stream"
            r = requests.post(
                f"{api_base}/api/v1/files/v2/upload",
                headers=headers,
                files=[("files", (path.name, f, mime))],
                data={"task_id": TASK_ID},
                timeout=upload_timeout,
            )
        if r.status_code in (200, 201):
            print("上傳成功:", path.name)
            ok += 1
        else:
            print("上傳失敗:", path.name, r.status_code, r.text[:200])
    print("上架完成:", ok, "/", len(files))
    return 0 if ok == len(files) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="上架 MM-Agent 知識庫")
    ap.add_argument("--api-base", default="http://localhost:8000", help="API 基底 URL")
    ap.add_argument(
        "--password",
        default=None,
        help="systemAdmin 密碼；可從 SYSTEADMIN_PASSWORD 或 SYSTEM_ADMIN_PASSWORD 讀取",
    )
    ap.add_argument(
        "--upload-timeout",
        type=int,
        default=300,
        help="單檔上傳 HTTP timeout（秒）；MM 含大檔案，預設 300",
    )
    args = ap.parse_args()
    pw = (
        args.password
        or os.environ.get("SYSTEADMIN_PASSWORD")
        or os.environ.get("SYSTEM_ADMIN_PASSWORD")
    )
    if not pw:
        pw = "systemAdmin@2026"
        print("使用 auth fallback 密碼（未設定 SYSTEADMIN_PASSWORD / SYSTEM_ADMIN_PASSWORD）")
    token = login(args.api_base, pw)
    ensure_task(args.api_base, token)
    return upload_files(args.api_base, token, args.upload_timeout)


if __name__ == "__main__":
    sys.exit(main())
