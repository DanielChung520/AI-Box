# 代碼功能說明: GenAI Secret 加密服務（用於 API Key 等敏感資訊）
# 創建日期: 2025-12-13 23:34:17 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 23:34:17 (UTC+8)

"""GenAI Secret 加密服務 - 實現 AES-256-GCM 加密/解密。

注意：
- 敏感金鑰以環境變數 `GENAI_SECRET_ENCRYPTION_KEY` 提供（不得寫入 config.json）
- 用於儲存使用者/租戶的 LLM API key 等敏感資訊
"""

from __future__ import annotations

import base64
import os
from typing import Optional

import structlog
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = structlog.get_logger(__name__)

KEY_SIZE = 32
NONCE_SIZE = 12


class GenAISecretEncryptionService:
    """GenAI Secret 加密服務"""

    def __init__(self, encryption_key: Optional[bytes] = None):
        self._key = encryption_key or self._get_encryption_key()
        self._logger = logger

    def _get_encryption_key(self) -> bytes:
        key_str = os.getenv("GENAI_SECRET_ENCRYPTION_KEY")
        if not key_str:
            if os.getenv("SECURITY_MODE", "development").lower() == "production":
                raise RuntimeError(
                    "GENAI_SECRET_ENCRYPTION_KEY environment variable is required in production mode"
                )
            logger.warning(
                "Using default GenAI secret encryption key. This is insecure for production!"
            )
            key_str = "default-genai-secret-encryption-key-change-in-production"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=b"genai_secret_encryption_salt",
            iterations=100000,
            backend=default_backend(),
        )
        return kdf.derive(key_str.encode("utf-8"))

    def encrypt_to_b64(self, plaintext: str) -> str:
        nonce = os.urandom(NONCE_SIZE)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        payload = nonce + ciphertext
        return base64.b64encode(payload).decode("utf-8")

    def decrypt_from_b64(self, payload_b64: str) -> str:
        payload = base64.b64decode(payload_b64.encode("utf-8"))
        if len(payload) < NONCE_SIZE:
            raise ValueError("Invalid ciphertext: too short")
        nonce = payload[:NONCE_SIZE]
        encrypted = payload[NONCE_SIZE:]
        aesgcm = AESGCM(self._key)
        plaintext = aesgcm.decrypt(nonce, encrypted, None)
        return plaintext.decode("utf-8")


_encryption_service: Optional[GenAISecretEncryptionService] = None


def get_genai_secret_encryption_service() -> GenAISecretEncryptionService:
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = GenAISecretEncryptionService()
    return _encryption_service
