# 代碼功能說明: 文件加密服務
# 創建日期: 2025-12-06 15:20 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:20 (UTC+8)

"""文件加密服務 - 實現 AES-256-GCM 加密/解密"""

import os
import base64
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog

logger = structlog.get_logger(__name__)

# 加密算法配置
ALGORITHM = "AES-256-GCM"
KEY_SIZE = 32  # 256 bits
NONCE_SIZE = 12  # 96 bits for GCM
SALT_SIZE = 16  # 128 bits


class EncryptionService:
    """文件加密服務"""

    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        初始化加密服務

        Args:
            encryption_key: 加密密鑰（可選，如果不提供則從環境變數讀取）
        """
        self.encryption_key = encryption_key or self._get_encryption_key()
        self.logger = logger

    def _get_encryption_key(self) -> bytes:
        """
        從環境變數獲取加密密鑰

        Returns:
            bytes: 加密密鑰

        Raises:
            RuntimeError: 如果密鑰未配置
        """
        # 從環境變數讀取密鑰（敏感信息）
        key_str = os.getenv("FILE_ENCRYPTION_KEY")
        if not key_str:
            # 如果未配置，使用默認密鑰（僅用於開發環境）
            # 生產環境必須設置 FILE_ENCRYPTION_KEY
            if os.getenv("SECURITY_MODE", "development").lower() == "production":
                raise RuntimeError(
                    "FILE_ENCRYPTION_KEY environment variable is required in production mode"
                )
            self.logger.warning(
                "Using default encryption key. This is insecure for production!"
            )
            key_str = "default-file-encryption-key-change-in-production"

        # 將字符串密鑰轉換為固定長度的字節
        # 使用 PBKDF2 派生固定長度的密鑰
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=b"file_encryption_salt",  # 固定salt（生產環境應使用隨機salt）
            iterations=100000,
            backend=default_backend(),
        )
        key = kdf.derive(key_str.encode("utf-8"))
        return key

    def encrypt(self, plaintext: bytes) -> bytes:
        """
        加密文件內容

        Args:
            plaintext: 明文文件內容

        Returns:
            bytes: 加密後的文件內容（格式：nonce + salt + ciphertext + tag）
        """
        # 生成隨機 nonce
        nonce = os.urandom(NONCE_SIZE)

        # 創建 AESGCM 實例
        aesgcm = AESGCM(self.encryption_key)

        # 加密文件內容
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # 組合 nonce + ciphertext（GCM模式會自動附加tag）
        encrypted_data = nonce + ciphertext

        return encrypted_data

    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        解密文件內容

        Args:
            ciphertext: 加密後的文件內容（格式：nonce + ciphertext + tag）

        Returns:
            bytes: 解密後的明文文件內容

        Raises:
            ValueError: 如果解密失敗（密鑰錯誤或數據損壞）
        """
        if len(ciphertext) < NONCE_SIZE:
            raise ValueError("Invalid ciphertext: too short")

        # 提取 nonce 和實際的密文
        nonce = ciphertext[:NONCE_SIZE]
        encrypted_data = ciphertext[NONCE_SIZE:]

        # 創建 AESGCM 實例
        aesgcm = AESGCM(self.encryption_key)

        # 解密文件內容
        try:
            plaintext = aesgcm.decrypt(nonce, encrypted_data, None)
            return plaintext
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    def is_encrypted(self, data: bytes) -> bool:
        """
        檢查數據是否已加密

        簡單檢查：如果數據長度足夠包含 nonce，則認為可能已加密
        實際應用中可能需要更複雜的檢查機制

        Args:
            data: 數據字節

        Returns:
            bool: 是否已加密
        """
        return len(data) >= NONCE_SIZE

    def rotate_key(self, new_key: bytes) -> None:
        """
        輪換加密密鑰

        注意：輪換密鑰後，舊密鑰加密的文件需要重新加密

        Args:
            new_key: 新的加密密鑰
        """
        if len(new_key) != KEY_SIZE:
            raise ValueError(f"Key must be {KEY_SIZE} bytes long")
        self.encryption_key = new_key
        self.logger.info("Encryption key rotated successfully")


# 全局服務實例（懶加載）
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """獲取加密服務實例（單例模式）"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
