# 代碼功能說明: Policy Engine 政策文件加載器
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Policy Engine 政策文件加載器

支持動態熱加載政策文件。
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from agents.services.policy_engine.models import Policy
from agents.services.policy_engine.policy_parser import PolicyParser

logger = logging.getLogger(__name__)


class PolicyLoader:
    """政策文件加載器"""

    def __init__(self):
        """初始化政策文件加載器"""
        self._policies: Dict[str, Policy] = {}
        self._file_timestamps: Dict[str, float] = {}

    def load_policy(self, policy_path: str | Path) -> Policy:
        """
        加載政策文件

        Args:
            policy_path: 政策文件路徑（YAML 或 JSON）

        Returns:
            Policy 對象
        """
        policy_path = Path(policy_path)

        if not policy_path.exists():
            raise FileNotFoundError(f"Policy file not found: {policy_path}")

        # 檢查文件擴展名
        if policy_path.suffix.lower() == ".yaml" or policy_path.suffix.lower() == ".yml":
            policy = PolicyParser.parse_yaml(policy_path)
        elif policy_path.suffix.lower() == ".json":
            policy = PolicyParser.parse_json(policy_path)
        else:
            raise ValueError(f"Unsupported policy file format: {policy_path.suffix}")

        # 記錄文件時間戳（用於熱加載檢測）
        self._file_timestamps[str(policy_path)] = policy_path.stat().st_mtime
        self._policies[str(policy_path)] = policy

        logger.info(f"Loaded policy from: {policy_path}")
        return policy

    def reload_policy(self, policy_path: str | Path) -> Policy:
        """
        重新加載政策文件（熱加載）

        Args:
            policy_path: 政策文件路徑

        Returns:
            Policy 對象
        """
        policy_path = Path(policy_path)
        policy_path_str = str(policy_path)

        # 檢查文件是否已修改
        if policy_path_str in self._file_timestamps:
            current_mtime = policy_path.stat().st_mtime
            if current_mtime <= self._file_timestamps[policy_path_str]:
                logger.debug(f"Policy file not modified: {policy_path}")
                return self._policies[policy_path_str]

        # 重新加載
        logger.info(f"Reloading policy from: {policy_path}")
        return self.load_policy(policy_path)

    def get_policy(self, policy_path: str | Path) -> Optional[Policy]:
        """
        獲取已加載的政策

        Args:
            policy_path: 政策文件路徑

        Returns:
            Policy 對象，如果未加載則返回 None
        """
        return self._policies.get(str(policy_path))

    def check_and_reload(self, policy_path: str | Path) -> Optional[Policy]:
        """
        檢查並重新加載政策文件（如果已修改）

        Args:
            policy_path: 政策文件路徑

        Returns:
            Policy 對象，如果文件不存在或未加載則返回 None
        """
        policy_path = Path(policy_path)

        if not policy_path.exists():
            return None

        try:
            return self.reload_policy(policy_path)
        except Exception as e:
            logger.error(f"Failed to reload policy: {e}", exc_info=True)
            return None
