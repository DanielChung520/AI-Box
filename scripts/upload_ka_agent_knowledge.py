#!/usr/bin/env python3
# 代碼功能說明: 以 systemAdmin 上架 KA-Agent 知識庫至 task KA-Agent
# 創建日期: 2026-01-25 20:40 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-27 19:50 UTC+8

"""上架 KA-Agent 知識庫（Ontology 須已導入）

使用方式:
    SYSTEADMIN_PASSWORD=xxx python scripts/upload_ka_agent_knowledge.py
    或
    python scripts/upload_ka_agent_knowledge.py --password xxx

須先執行: scripts/import_ka_agent_ontology.py
API 服務須運行於 --api-base（預設 http://localhost:8000）
"""

from __future__ import annotations

import argparse
import fcntl
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

KNOWLEDGE_DIR = _project_root / "docs/系统设计文档/核心组件/Agent平台/KA-Agent/知識庫"
TASK_ID = "KA-Agent"
USER_ID = "systemAdmin"

# 防重複執行鎖機制
LOCK_FILE = _project_root / ".ka_agent_upload.lock"


def acquire_lock():
    """獲取鎖"""
    try:
        fd = os.open(str(LOCK_FILE), os.O_WRONLY | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except (IOError, BlockingIOError):
        return None


def release_lock(fd):
    """釋放鎖"""
    if fd is not None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            fd.close()
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except Exception:
            pass


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
        print("Task KA-Agent 已就緒")
        return
    try:
        err = r.json()
        msg = err.get("message", err.get("detail", r.text))
    except Exception:
        msg = r.text
    if "already" in msg.lower() or "exists" in msg.lower() or r.status_code == 409:
        print("Task KA-Agent 已存在，繼續上傳")
        return
    r.raise_for_status()


def upload_files(api_base: str, token: str) -> int:
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
            mime = "text/markdown" if path.suffix.lower() == ".md" else "application/octet-stream"
            r = requests.post(
                f"{api_base}/api/v1/files/v2/upload",
                headers=headers,
                files=[("files", (path.name, f, mime))],
                data={"task_id": TASK_ID},
                timeout=120,
            )
        if r.status_code in (200, 201):
            print("上傳成功:", path.name)
            ok += 1
        else:
            print("上傳失敗:", path.name, r.status_code, r.text[:200])
    print("上架完成:", ok, "/", len(files))
    return 0 if ok == len(files) else 1


def main() -> int:
    """主函數"""
    # 防止重複執行
    print("檢查鎖檔案...")
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("❌ 另一個實例正在執行，請稍後再試")
        return 1
    print("✅ 獲取鎖成功")

    try:
        ap = argparse.ArgumentParser(description="上架 KA-Agent 知識庫")
        ap.add_argument("--api-base", default="http://localhost:8000", help="API 基底 URL")
        ap.add_argument(
            "--password",
            default=None,
            help="systemAdmin 密碼；可從 SYSTEADMIN_PASSWORD 或 SYSTEM_ADMIN_PASSWORD 讀取",
        )
        args = ap.parse_args()
        pw = (
            args.password
            or os.environ.get("SYSTEADMIN_PASSWORD")
            or os.environ.get("SYSTEM_ADMIN_PASSWORD")
        )
        if not pw:
            pw = "systemAdmin@2026"  # 依 api/routers/auth 的 fallback 一致
            print("使用 auth fallback 密碼（未設定 SYSTEADMIN_PASSWORD / SYSTEM_ADMIN_PASSWORD）")
        token = login(args.api_base, pw)
        ensure_task(args.api_base, token)
        result = upload_files(args.api_base, token)
        return result
    finally:
        # 釋放鎖
        if lock_fd is not None:
            print("釋放鎖...")
            release_lock(lock_fd)


if __name__ == "__main__":
    sys.exit(main())
