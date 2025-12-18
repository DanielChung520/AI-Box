# 代碼功能說明: RQ Worker Service 管理模組
# 創建日期: 2025-12-12
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-12

"""RQ Worker Service 管理模組 - 提供 Worker 的啟動、監控、重啟等功能"""

from __future__ import annotations

import os
import sys
import signal
import subprocess
import time
import atexit
from pathlib import Path
from typing import Optional, List, Dict, Any
import structlog

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
    ):
        """
        初始化 Worker Service

        Args:
            queue_names: 要監聽的隊列名稱列表
            worker_name: Worker 名稱（默認為自動生成）
            redis_url: Redis URL（默認從環境變數讀取）
            log_file: 日誌文件路徑（默認自動生成）
            python_path: Python 可執行文件路徑（默認自動檢測）
        """
        self.queue_names = queue_names
        self.worker_name = worker_name or f"rq_worker_{os.getpid()}"
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.log_file = log_file or str(LOG_DIR / f"rq_worker_{self.worker_name}.log")
        self.python_path = python_path or self._detect_python_path()
        self.rq_command = self._detect_rq_command()

        self.process: Optional[subprocess.Popen] = None
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

        venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)

        # 使用系統 Python
        return sys.executable

    def _detect_rq_command(self) -> str:
        """自動檢測 RQ 命令路徑"""
        # 優先使用虛擬環境中的 rq 命令
        venv_rq = PROJECT_ROOT / "venv" / "bin" / "rq"
        if venv_rq.exists():
            return str(venv_rq)

        venv_rq = PROJECT_ROOT / ".venv" / "bin" / "rq"
        if venv_rq.exists():
            return str(venv_rq)

        # 使用系統 rq 命令（如果可用）
        import shutil

        rq_path = shutil.which("rq")
        if rq_path:
            return rq_path

        # 如果找不到 rq 命令，使用 python -m rq.cli
        return None

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

        try:
            # 構建 RQ Worker 命令
            # 修改時間：2025-12-12 - 修復 RQ Worker 啟動方式
            # 優先使用 rq 命令，如果不可用則使用 python -m rq.cli
            if self.rq_command:
                cmd = [
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
                # 使用 python -m rq.cli 作為備選方案
                cmd = [
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
            )

            # 打開日誌文件
            log_file_handle = open(self.log_file, "a")

            # 修改時間：2025-12-12 - 修復 macOS fork 安全問題
            # 設置環境變量以解決 macOS 上 fork() 時 Objective-C 初始化衝突問題
            worker_env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
            if sys.platform == "darwin":  # macOS
                worker_env["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
                logger.info(
                    "已設置 OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES 以解決 macOS fork 問題"
                )

            # 啟動進程
            self.process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                env=worker_env,
                stdout=log_file_handle,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,  # 創建新的進程組
            )

            self.is_running = True
            logger.info(
                "RQ Worker 已啟動",
                pid=self.process.pid,
                worker_name=self.worker_name,
            )

            return True

        except Exception as e:
            logger.error("啟動 Worker 失敗", error=str(e), exc_info=True)
            self.is_running = False
            return False

    def stop(self) -> bool:
        """
        停止 Worker

        Returns:
            是否成功停止
        """
        if not self.is_running or self.process is None:
            return True

        try:
            logger.info("停止 RQ Worker", pid=self.process.pid)

            # 發送 SIGTERM 信號給整個進程組
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

            # 等待進程結束（最多等待 10 秒）
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # 如果 10 秒內沒有結束，強制終止
                logger.warning("Worker 未在 10 秒內結束，強制終止")
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                self.process.wait()

            self.is_running = False
            self.process = None
            logger.info("RQ Worker 已停止")
            return True

        except ProcessLookupError:
            # 進程已經不存在
            self.is_running = False
            self.process = None
            return True
        except Exception as e:
            logger.error("停止 Worker 失敗", error=str(e), exc_info=True)
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
        檢查 Worker 是否還在運行

        Returns:
            Worker 是否存活
        """
        if not self.is_running or self.process is None:
            return False

        # 檢查進程是否還在運行
        return_code = self.process.poll()
        if return_code is not None:
            # 進程已經結束
            logger.warning(
                "Worker 進程已結束",
                pid=self.process.pid,
                return_code=return_code,
            )
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
            "pid": self.process.pid if self.process else None,
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

    args = parser.parse_args()

    # 創建 Worker Service
    service = WorkerService(
        queue_names=args.queues,
        worker_name=args.name,
        redis_url=args.redis_url,
        log_file=args.log_file,
    )

    # 啟動 Worker
    if not service.start():
        logger.error("無法啟動 Worker")
        sys.exit(1)

    # 如果啟用監控模式，則持續監控
    if args.monitor:
        service.monitor(check_interval=args.check_interval)
    else:
        # 否則等待進程結束
        try:
            service.process.wait()
        except KeyboardInterrupt:
            logger.info("收到中斷信號，停止 Worker")
            service.stop()


if __name__ == "__main__":
    main()
