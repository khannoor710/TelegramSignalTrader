"""
Centralized application settings loaded from environment variables.
Avoids external dependencies and provides typed accessors.
"""
from __future__ import annotations

import os
import json
from typing import List, Optional


class Settings:
    """Application settings with environment-backed defaults."""

    def __init__(self):
        # Database
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./trading_bot.db")

        # CORS
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            try:
                # Supports JSON array or comma-separated string
                if cors_env.strip().startswith("["):
                    self.CORS_ORIGINS: List[str] = json.loads(cors_env)
                else:
                    self.CORS_ORIGINS = [o.strip() for o in cors_env.split(",") if o.strip()]
            except Exception:
                self.CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
        else:
            self.CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

        # Security / Encryption
        self.ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY")

        # AI Signal Parsing (Google Gemini)
        self.GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    def __repr__(self) -> str:
        return (
            f"Settings(DATABASE_URL={self.DATABASE_URL}, CORS_ORIGINS={self.CORS_ORIGINS}, "
            f"GEMINI_MODEL={self.GEMINI_MODEL})"
        )


# Singleton instance accessor
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
