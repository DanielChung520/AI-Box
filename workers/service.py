# 代碼功能說明: RQ Worker Service 管理模組
# 創建日期: 2025-12-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-25 22:30 UTC+8

"""RQ Worker Service 管理模組 - 提供 Worker 的啟動、監控、重啟等功能"""

from __future__ import annotations

import atexit
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

# 加載環境變數（在導入其他模組之前）
# 修改時間：2025-12-31 - 確保 .env 文件在 Worker 啟動時被加載
try:
    from dotenv import load_dotenv

    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        logger = structlog.get_logger(__name__)
        logger.info("已加載 .env 文件", env_file=str(env_file))
except ImportError:
    logger = structlog.get_logger(__name__)
    logger.warning("python-dotenv 未安裝，無法自動加載 .env 文件")

logger = structlog.get_logger(__name__)

# 項目根目錄
PROJECT_ROOT = Path(__file__).parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


class WorkerService:
    """RQ Worker Service 管理類"""

    def __init__(
        self,
        queue_names: List[str],
        worker_name: Optional[str] = None,
        redis_url: Optional[str] = None,
        log_file: Optional[str] = None,
        python_path: Optional[str] = None,
        num_workers: int = 1,
    ):
        """
        初始化 Worker Service

        Args:
            queue_names: 要監聽的隊列名稱列表
            worker_name: Worker 名稱（默認為自動生成 UUID）
            redis_url: Redis URL（默認從環境變數讀取）
            log_file: 日誌文件路徑（默認自動生成）
            python_path: Python 可執行文件路徑（默認自動檢測）
            num_workers: Worker 實例數量（並發處理，默認 1）
        """
        import uuid

        self.queue_names = queue_names
        self.worker_name = worker_name or str(uuid.uuid4())[:8]  # 使用 UUID 前 8 位作為名稱
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.log_file = log_file or str(LOG_DIR / f"rq_worker_{self.worker_name}.log")
        self.python_path = python_path or self._detect_python_path()
        self.rq_command = self._detect_rq_command()
        self.num_workers = num_workers

        self.processes: List[subprocess.Popen] = []  # 支持多個 worker 實例
        self.is_running = False
        self.restart_count = 0
        self.max_restarts = 10  # 最大重啟次數
        self.restart_delay = 5  # 重啟延遲（秒）

        # 註冊退出處理
        atexit.register(self.stop)

    def _detect_python_path(self) -> str:
        """自動檢測 Python 可執行文件路徑"""
        # 優先使用虛擬環境中的 Python
        venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)

        # 使用系統 Python（專案統一使用 venv，不使用 .venv）
        return sys.executable

    def _detect_rq_command(self) -> str:
        """自動檢測 RQ 命令路徑"""
        # 優先使用虛擬環境中的 rq 命令
        venv_rq = PROJECT_ROOT / "venv" / "bin" / "rq"
        if venv_rq.exists():
            return str(venv_rq)

        # 使用系統 rq 命令（如果可用；專案統一使用 venv）
        import shutil

        rq_path = shutil.which("rq")
        if rq_path:
            return rq_path

        # 如果找不到 rq 命令，使用 python -m rq.cli
        return ""  # type: ignore[return-value]  # 返回空字符串而不是 None，因為函數簽名要求返回 str

    def _check_dependencies(self) -> bool:
        """檢查依賴是否滿足"""
        try:
            # 檢查 RQ 是否安裝
            result = subprocess.run(
                [self.python_path, "-c", "import rq"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                logger.error("RQ 未安裝，請執行: pip install rq")
                return False

            # 檢查 Redis 連接
            result = subprocess.run(
                [
                    self.python_path,
                    "-c",
                    "from database.redis import get_redis_client; get_redis_client().ping()",
                ],
                cwd=str(PROJECT_ROOT),
                env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                logger.error("無法連接到 Redis，請確保 Redis 服務正在運行")
                return False

            return True
        except Exception as e:
            logger.error("檢查依賴時發生錯誤", error=str(e))
            return False

    def _cleanup_old_worker_registry(self) -> None:
        """
        清理 Redis 中同名的舊 Worker 註冊信息

        修改時間：2026-01-21 - 修復 Worker 重啟時的註冊衝突問題
        當 Worker 異常退出時，Redis 中的註冊信息可能沒有被正確清理，
        導致新 Worker 無法註冊。在啟動新 Worker 前先清理舊的註冊信息。
        """
        try:
            from database.redis import get_redis_client

            redis_client = get_redis_client()

            # 清理同名的 worker 註冊鍵
            worker_key = f"rq:worker:{self.worker_name}"
            birth_key = f"{worker_key}:birth"

            # 檢查並刪除 worker 註冊信息
            if redis_client.exists(worker_key):
                logger.info(
                    "發現舊的 Worker 註冊信息，正在清理",
                    worker_name=self.worker_name,
                    worker_key=worker_key,
                )
                redis_client.delete(worker_key)

            # 檢查並刪除 birth 鍵
            if redis_client.exists(birth_key):
                redis_client.delete(birth_key)

            logger.debug("Worker 註冊信息清理完成", worker_name=self.worker_name)

        except Exception as e:
            # 清理失敗不應該阻止 Worker 啟動，只記錄警告
            logger.warning(
                "清理舊 Worker 註冊信息時發生錯誤，將繼續啟動",
                worker_name=self.worker_name,
                error=str(e),
            )

    def start(self) -> bool:
        """
        啟動 Worker

        Returns:
            是否成功啟動
        """
        if self.is_running:
            logger.warning("Worker 已經在運行中")
            return True

        if not self._check_dependencies():
            return False

        # 修改時間：2026-01-21 - 在啟動前清理舊的 Worker 註冊信息
        # 避免因舊註冊信息導致新 Worker 無法啟動的問題
        self._cleanup_old_worker_registry()

        try:
            # 構建 RQ Worker 命令
            # 修改時間：2025-12-12 - 修復 RQ Worker 啟動方式
            # 優先使用 rq 命令，如果不可用則使用 python -m rq.cli
            if self.rq_command:
                _cmd = [
                    self.rq_command,
                    "worker",
                    *self.queue_names,
                    "--name",
                    self.worker_name,
                    "--url",
                    self.redis_url,
                    "--with-scheduler",
                ]
            else:
                # 使用 python -m rq.cli 作為備選方案（instance_cmd 在迴圈內依此邏輯構建）
                _cmd = [
                    self.python_path,
                    "-m",
                    "rq.cli",
                    "worker",
                    *self.queue_names,
                    "--name",
                    self.worker_name,
                    "--url",
                    self.redis_url,
                    "--with-scheduler",
                ]

            logger.info(
                "啟動 RQ Worker",
                worker_name=self.worker_name,
                queues=self.queue_names,
                redis_url=self.redis_url,
                log_file=self.log_file,
                num_workers=self.num_workers,
            )

            # 修改時間：2025-12-31 - 確保 Worker 進程能夠訪問環境變數
            # 重新加載 .env 文件以確保環境變數可用（因為 Worker 是子進程）
            worker_env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}

            # 確保 .env 文件中的環境變數被包含在 worker_env 中
            try:
                from dotenv import dotenv_values

                env_file = PROJECT_ROOT / ".env"
                if env_file.exists():
                    env_vars = dotenv_values(env_file)
                    # 將 .env 文件中的變數添加到 worker_env（不覆蓋已存在的環境變數）
                    for key, value in env_vars.items():
                        if value is not None and key not in worker_env:
                            worker_env[key] = value
                    logger.info(
                        "已將 .env 文件中的環境變數添加到 Worker 環境", env_file=str(env_file)
                    )
            except ImportError:
                logger.warning("python-dotenv 未安裝，無法從 .env 文件加載環境變數到 Worker")
            except Exception as e:
                logger.warning("加載 .env 文件到 Worker 環境時發生錯誤", error=str(e))

            # 修改時間：2025-12-12 - 修復 macOS fork 安全問題
            # 設置環境變量以解決 macOS 上 fork() 時 Objective-C 初始化衝突問題
            if sys.platform == "darwin":  # macOS
                worker_env["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
                logger.info("已設置 OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES 以解決 macOS fork 問題")

            # 修改時間：2026-01-25 - 支持啟動多個 worker 實例（並發處理）
            # 啟動多個 worker 進程以實現並發處理
            self.processes = []
            for i in range(self.num_workers):
                # 為每個 worker 實例生成唯一的名稱
                instance_name = (
                    f"{self.worker_name}_{i + 1}" if self.num_workers > 1 else self.worker_name
                )
                instance_log_file = (
                    str(LOG_DIR / f"rq_worker_{instance_name}.log")
                    if self.num_workers > 1
                    else self.log_file
                )

                # 構建該實例的命令（使用實例名稱）
                if self.rq_command:
                    instance_cmd = [
                        self.rq_command,
                        "worker",
                        *self.queue_names,
                        "--name",
                        instance_name,
                        "--url",
                        self.redis_url,
                        "--with-scheduler",
                    ]
                else:
                    instance_cmd = [
                        self.python_path,
                        "-m",
                        "rq.cli",
                        "worker",
                        *self.queue_names,
                        "--name",
                        instance_name,
                        "--url",
                        self.redis_url,
                        "--with-scheduler",
                    ]

                # 打開日誌文件
                log_file_handle = open(instance_log_file, "a")

                # 過濾 None 值，確保 cmd 列表中的元素都是字符串
                cmd_filtered: list[str] = [arg for arg in instance_cmd if arg is not None]
                process = subprocess.Popen(
                    cmd_filtered,  # type: ignore[arg-type]  # 已過濾 None，但 mypy 仍報告類型錯誤
                    cwd=str(PROJECT_ROOT),
                    env=worker_env,
                    stdout=log_file_handle,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid,  # 創建新的進程組
                )

                self.processes.append(process)
                logger.info(
                    "RQ Worker 實例已啟動",
                    instance=i + 1,
                    total=self.num_workers,
                    pid=process.pid,
                    worker_name=instance_name,
                )

            self.is_running = True
            logger.info(
                "所有 RQ Worker 實例已啟動",
                num_workers=self.num_workers,
                pids=[p.pid for p in self.processes],
            )

            return True

        except Exception as e:
            logger.error("啟動 Worker 失敗", error=str(e), exc_info=True)
            self.is_running = False
            return False

    def stop(self) -> bool:
        """
        停止所有 Worker 實例

        Returns:
            是否成功停止
        """
        if not self.is_running or not self.processes:
            return True

        try:
            logger.info(
                "停止 RQ Worker 實例",
                num_workers=len(self.processes),
                pids=[p.pid for p in self.processes],
            )

            # 停止所有 worker 實例
            for i, process in enumerate(self.processes):
                try:
                    # 發送 SIGTERM 信號給整個進程組
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    # 進程已經不存在，跳過
                    logger.warning(f"Worker 實例 {i + 1} (PID {process.pid}) 已不存在")
                    continue

            # 等待所有進程結束（最多等待 10 秒）
            for i, process in enumerate(self.processes):
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # 如果 10 秒內沒有結束，強制終止
                    logger.warning(
                        f"Worker 實例 {i + 1} (PID {process.pid}) 未在 10 秒內結束，強制終止"
                    )
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        process.wait()
                    except ProcessLookupError:
                        pass  # 進程已不存在

            self.is_running = False
            self.processes = []
            logger.info("所有 RQ Worker 實例已停止")
            return True

        except Exception as e:
            logger.error("停止 Worker 失敗", error=str(e), exc_info=True)
            # 即使部分失敗，也標記為已停止
            self.is_running = False
            self.processes = []
            return False

    def restart(self) -> bool:
        """
        重啟 Worker

        Returns:
            是否成功重啟
        """
        logger.info("重啟 RQ Worker", restart_count=self.restart_count)
        self.restart_count += 1

        if self.restart_count > self.max_restarts:
            logger.error(
                "達到最大重啟次數，停止重啟",
                max_restarts=self.max_restarts,
            )
            return False

        self.stop()
        time.sleep(self.restart_delay)
        return self.start()

    def is_alive(self) -> bool:
        """
        檢查所有 Worker 實例是否還在運行

        Returns:
            是否至少有一個 Worker 實例存活
        """
        if not self.is_running or not self.processes:
            return False

        # 檢查所有進程是否還在運行
        alive_count = 0
        for i, process in enumerate(self.processes):
            return_code = process.poll()
            if return_code is not None:
                # 進程已經結束
                logger.warning(
                    f"Worker 實例 {i + 1} 進程已結束",
                    pid=process.pid,
                    return_code=return_code,
                )
            else:
                alive_count += 1

        # 如果所有實例都結束了，標記為未運行
        if alive_count == 0:
            self.is_running = False
            return False

        return True

    def monitor(self, check_interval: int = 30) -> None:
        """
        監控 Worker，如果崩潰則自動重啟

        Args:
            check_interval: 檢查間隔（秒）
        """
        logger.info(
            "開始監控 Worker",
            worker_name=self.worker_name,
            check_interval=check_interval,
        )

        # 註冊信號處理
        def signal_handler(signum, frame):
            logger.info("收到停止信號，正在停止 Worker")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        try:
            while True:
                if not self.is_alive():
                    logger.warning("Worker 已停止，嘗試重啟")
                    if not self.restart():
                        logger.error("無法重啟 Worker，退出監控")
                        break

                time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("收到中斷信號，停止監控")
            self.stop()

    def get_status(self) -> Dict[str, Any]:
        """
        獲取 Worker 狀態

        Returns:
            Worker 狀態字典
        """
        return {
            "worker_name": self.worker_name,
            "is_running": self.is_running,
            "is_alive": self.is_alive(),
            "num_workers": self.num_workers,
            "pids": [p.pid for p in self.processes] if self.processes else [],
            "queue_names": self.queue_names,
            "restart_count": self.restart_count,
            "log_file": self.log_file,
        }


def main():
    """主函數 - 啟動 Worker Service"""
    import argparse

    parser = argparse.ArgumentParser(description="RQ Worker Service")
    parser.add_argument(
        "--queues",
        nargs="+",
        default=["kg_extraction", "vectorization", "file_processing"],
        help="要監聽的隊列名稱（默認: kg_extraction vectorization file_processing）",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Worker 名稱（默認自動生成）",
    )
    parser.add_argument(
        "--redis-url",
        type=str,
        default=None,
        help="Redis URL（默認從環境變數讀取）",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="日誌文件路徑（默認自動生成）",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="啟用監控模式（自動重啟崩潰的 Worker）",
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=30,
        help="監控檢查間隔（秒，默認 30）",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=5,
        help="Worker 實例數量（並發處理，默認 5）",
    )

    args = parser.parse_args()

    # 創建 Worker Service
    service = WorkerService(
        queue_names=args.queues,
        worker_name=args.name,
        redis_url=args.redis_url,
        log_file=args.log_file,
        num_workers=args.num_workers,
    )

    # 啟動 Worker
    if not service.start():
        logger.error("無法啟動 Worker")
        sys.exit(1)

    # 如果啟用監控模式，則持續監控
    if args.monitor:
        service.monitor(check_interval=args.check_interval)
    else:
        # 否則等待所有進程結束
        if not service.processes:
            logger.warning("Worker processes is empty, cannot wait")
            return
        try:
            # 等待所有 worker 實例結束
            for process in service.processes:
                process.wait()  # type: ignore[union-attr]  # 已檢查不為空
        except KeyboardInterrupt:
            logger.info("收到中斷信號，停止 Worker")
            service.stop()


if __name__ == "__main__":
    main()
