import json
import logging
from typing import Any, Optional, Dict
from cryptography.fernet import Fernet, InvalidToken
from core.config import settings

logger = logging.getLogger("Security")

class EncryptionService:
    """
    Handles encryption for sensitive fields.
    Decouples security logic from the database.
    """
    
    _cipher: Optional[Fernet] = None

    @classmethod
    def _get_cipher(cls) -> Fernet:
        if cls._cipher is None:
            # We trust Settings has already validated the key format at boot
            cls._cipher = Fernet(settings.MED_PARSER_SECRET_KEY.encode())
        return cls._cipher

    @classmethod
    def encrypt(cls, text: str) -> str:
        """Encrypt plain text into a secure token."""
        if not text:
            return ""
        return cls._get_cipher().encrypt(text.encode()).decode()

    @classmethod
    def decrypt(cls, token: str) -> str:
        """Decrypt a secure token back to plain text."""
        if not token:
            return ""
        try:
            return cls._get_cipher().decrypt(token.encode()).decode()
        except InvalidToken:
            logger.error("Decryption failed: Key mismatch or corrupted data.")
            # We re-raise to emphasize data integrity failure
            raise
        except Exception as e:
            logger.error(f"Unexpected decryption error: {e}")
            raise

    @classmethod
    def encrypt_json(cls, data: Any) -> str:
        """Serialize and encrypt complex data structures."""
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data)
        else:
            data_str = str(data) if data is not None else "{}"
        return cls.encrypt(data_str)

    @classmethod
    def decrypt_json(cls, token: str) -> Any:
        """Decrypt and deserialize complex data structures."""
        raw = cls.decrypt(token)
        if not raw or raw == "{}":
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

# Exported helper functions for clean usage
encrypt_phi = EncryptionService.encrypt
decrypt_phi = EncryptionService.decrypt
encrypt_json = EncryptionService.encrypt_json
decrypt_json = EncryptionService.decrypt_json
