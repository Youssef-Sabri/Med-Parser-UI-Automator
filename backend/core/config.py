from pathlib import Path
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from cryptography.fernet import Fernet

class Settings(BaseSettings):
    """System configuration."""
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core
    PORT: int = Field(...)
    DEBUG: bool = Field(...)
    MAX_CAPACITY: int = Field(...)
    MAX_DAILY_CAPACITY: int = Field(...)
    MED_PARSER_API_KEY: str = Field(..., min_length=16)
    MED_PARSER_SECRET_KEY: str = Field(...)
    BRIDGE_PORT: int = Field(...)
    BACKEND_URL: str = Field(...)

    @field_validator("MED_PARSER_SECRET_KEY")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        """Verify Fernet key format."""
        try:
            Fernet(v.encode())
            return v
        except Exception:
            raise ValueError("Invalid MED_PARSER_SECRET_KEY. Must be 32-byte Fernet key.")

    # Storage & Bridge
    STAGING_DIR: Path = Field(...)
    MAX_UPLOAD_SIZE_MB: int = Field(...)
    BRIDGE_AGENT_URL: str = Field(...)

    @property
    def staging_path(self) -> Path:
        """Resolved staging directory."""
        path = self.STAGING_DIR.resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    # AI & Concurrency
    GEMINI_API_KEY: str = Field(...)
    GEMINI_MODEL_ID: str = Field(...)
    GEMINI_TIMEOUT: int = Field(...)
    EXTRACTION_CONCURRENCY_LIMIT: int = Field(...)

    # Database
    DATABASE_URL: str = Field(...)
    DB_POOL_SIZE: int = Field(...)
    DB_MAX_OVERFLOW: int = Field(...)

    # Security
    CORS_ORIGINS: str = Field(...)

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # RPA Tuning
    PMS_TARGET_TITLE: str = Field(...)
    AGENT_API_KEY: str = Field(...)
    TYPING_SPEED_MIN: float = Field(...)
    TYPING_SPEED_MAX: float = Field(...)
    ABORT_HOTKEY: str = Field(...)
    RPA_SAVE_HOTKEY: str = Field(...)
    RPA_CLOSE_HOTKEY: str = Field(...)
    RPA_SELECT_ALL_HOTKEY: str = Field(...)
    
settings = Settings()
