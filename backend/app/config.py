"""Application settings — all values come from environment variables / .env file."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "ResumeForge API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host/db

    # ── Auth ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str  # ≥ 32 chars, random
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # ── Encryption (for user API keys stored in DB) ───────────────────────────
    ENCRYPTION_KEY: str  # exactly 32 bytes (URL-safe base64 encoded 32-byte key)

    # ── S3 ────────────────────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: str | None = None  # set for R2 / MinIO

    # ── Platform LLM fallback key ─────────────────────────────────────────────
    PLATFORM_ANTHROPIC_KEY: str = ""
    PLATFORM_OPENAI_KEY: str = ""

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_BUILDS_PER_HOUR: int = 10  # for users without own key

    @property
    def encryption_key_bytes(self) -> bytes:
        """Return the encryption key as raw bytes (decode if base64-encoded, fallback to sha256)."""
        import base64
        import hashlib
        try:
            decoded = base64.urlsafe_b64decode(self.ENCRYPTION_KEY + "==")
            if len(decoded) == 32:
                return decoded
        except Exception:
            pass
        raw = self.ENCRYPTION_KEY.encode()
        if len(raw) == 32:
            return raw
        # Safe fallback: derive deterministic 32-byte key from whatever string was configured
        return hashlib.sha256(raw).digest()


@lru_cache
def get_settings() -> Settings:
    return Settings()
