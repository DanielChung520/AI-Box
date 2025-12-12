# 代碼功能說明: 同步 Ollama 模型（baseline 與 fallback），支援重試與清單輸出
# 創建日期: 2025-11-25 23:40 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:40 (UTC+8)
#!/usr/bin/env python3

"""Download baseline/fallback Ollama models with retry, manifest output, and optional dry-run."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "config.json"
EXAMPLE_CONFIG_PATH = ROOT_DIR / "config" / "config.example.json"
DEFAULT_MANIFEST_PATH = ROOT_DIR / "docs" / "deployment" / "ollama-models-manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync Ollama baseline/fallback models."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="自訂 config.json 路徑，預設會嘗試 config/config.json，再回退到 config/config.example.json。",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="手動指定要同步的模型清單（預設使用 config 中的 baseline + fallback）。",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="同步結果輸出路徑（JSON）。",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="若模型已存在則跳過拉取（僅檢查 digest）。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="忽略現有模型狀態，強制重新下載（可配合 nightly job）。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="僅列出將處理的模型，不實際執行 ollama pull。",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="僅收集現有模型資訊與 manifest，不對遠端節點執行任何下載。",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="覆寫 config/環境變數中的 Ollama 主機。",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="覆寫 config/環境變數中的 Ollama 連接埠。",
    )
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_config(custom_path: Optional[Path]) -> Dict[str, Any]:
    candidates = [custom_path, DEFAULT_CONFIG_PATH, EXAMPLE_CONFIG_PATH]
    for candidate in candidates:
        if candidate and candidate.exists():
            return load_json(candidate)
    raise FileNotFoundError(
        "找不到 config.json 或 config.example.json，請先建立設定檔。"
    )


def dedupe(seq: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def extract_ollama_cfg(config: Dict[str, Any]) -> Dict[str, Any]:
    return config.get("services", {}).get("ollama", {})


def determine_models(args: argparse.Namespace, config: Dict[str, Any]) -> List[str]:
    if args.models:
        return dedupe(args.models)
    ollama_cfg = extract_ollama_cfg(config)
    baseline = ollama_cfg.get("baseline_models", [])
    fallback = ollama_cfg.get("fallback_models", [])
    models = dedupe([*baseline, *fallback])
    if not models:
        return ["gpt-oss:20b", "qwen3-coder:30b"]
    return models


def determine_host_port(
    args: argparse.Namespace, config: Dict[str, Any]
) -> tuple[str, int]:
    host = (
        args.host
        or os.getenv("OLLAMA_REMOTE_HOST")
        or extract_ollama_cfg(config).get("host")
        or "localhost"
    )
    port = (
        args.port
        or int(os.getenv("OLLAMA_REMOTE_PORT", "0") or 0)
        or extract_ollama_cfg(config).get("port")
        or 11434
    )
    return host, int(port)


def build_env(host: str, port: int) -> Dict[str, str]:
    env = os.environ.copy()
    env["OLLAMA_HOST"] = f"{host}:{port}"
    return env


def parse_digest_from_modelfile(modelfile_text: str) -> Optional[str]:
    for line in modelfile_text.splitlines():
        line = line.strip()
        if line.startswith("FROM ") and "sha256-" in line:
            return line.split("sha256-")[-1]
    return None


def get_local_digest(model: str, env: Dict[str, str]) -> Optional[str]:
    try:
        result = subprocess.run(
            ["ollama", "show", model, "--modelfile"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("找不到 ollama CLI，請先安裝或更新 PATH") from exc

    if result.returncode != 0:
        return None
    return parse_digest_from_modelfile(result.stdout)


def pull_model(
    model: str,
    env: Dict[str, str],
    retries: int,
    backoff_seconds: int,
    dry_run: bool,
    force: bool,
) -> None:
    if dry_run:
        print(f"[dry-run] 將下載 {model}")
        return

    if force:
        subprocess.run(
            ["ollama", "rm", model],
            env=env,
            text=True,
            capture_output=True,
        )

    max_attempts = max(1, retries)
    for attempt in range(1, max_attempts + 1):
        result = subprocess.run(
            ["ollama", "pull", model], env=env, text=True, capture_output=True
        )
        if result.returncode == 0:
            print(f"[success] {model} 已同步")
            return
        print(
            f"[warning] {model} 第 {attempt}/{max_attempts} 次下載失敗：{result.stderr.strip()}"
        )
        if attempt < max_attempts:
            sleep_time = backoff_seconds * attempt
            time.sleep(sleep_time)
    raise RuntimeError(f"多次重試後仍無法下載 {model}")


def sync_models(
    args: argparse.Namespace, config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    ollama_cfg = extract_ollama_cfg(config)
    retry_cfg = ollama_cfg.get("download", {}).get("retry", {})
    retries = int(retry_cfg.get("max_attempts", 3))
    backoff_seconds = int(retry_cfg.get("backoff_seconds", 15))
    no_download = args.no_download

    models = determine_models(args, config)
    host, port = determine_host_port(args, config)
    env = build_env(host, port)

    results: List[Dict[str, Any]] = []
    print(f"[info] 目標節點：{host}:{port}")
    print(f"[info] 即將同步模型：{', '.join(models)}")

    for model in models:
        existing_digest = get_local_digest(model, env)
        if existing_digest and (args.skip_existing or no_download) and not args.force:
            print(f"[skip] {model} 已存在（digest={existing_digest[:12]}...）")
            status = "manifest-only" if no_download else "skipped"
            results.append(
                {"model": model, "status": status, "digest": existing_digest}
            )
            continue

        if no_download:
            print(
                f"[warn] {model} 無可用 digest，且 --no-download 已啟用，僅記錄缺失狀態"
            )
            results.append({"model": model, "status": "missing", "digest": None})
            continue

        pull_model(
            model=model,
            env=env,
            retries=retries,
            backoff_seconds=backoff_seconds,
            dry_run=args.dry_run,
            force=args.force,
        )
        digest = get_local_digest(model, env)
        results.append(
            {
                "model": model,
                "status": "synced" if not args.dry_run else "dry-run",
                "digest": digest,
            }
        )

    return results


def write_manifest(
    manifest_path: Path, host: str, port: int, results: List[Dict[str, Any]]
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "target": f"{host}:{port}",
        "models": results,
    }
    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"[info] 已寫入 manifest：{manifest_path}")


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    results = sync_models(args, config)
    host, port = determine_host_port(args, config)
    write_manifest(args.manifest, host, port, results)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[error] {exc}", file=sys.stderr)
        sys.exit(1)
