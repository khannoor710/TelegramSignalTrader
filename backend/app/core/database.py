"""
Database initialization and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.models.models import Base
from app.core.settings import get_settings
from functools import lru_cache
from typing import Optional
import time

settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

# Optimize SQLite connection with connection pooling
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30  # Increase timeout for busy database
        },
        poolclass=StaticPool,  # Use static pool for SQLite
        echo=False  # Disable SQL logging for performance
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,  # Connection pool size
        max_overflow=20,  # Allow 20 extra connections during spikes
        pool_pre_ping=True,  # Verify connections before use
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cache for settings to avoid repeated DB lookups
_settings_cache: dict = {"data": None, "expires": 0}
SETTINGS_CACHE_TTL = 30  # Cache settings for 30 seconds


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_cached_settings(db: Session) -> Optional["AppSettings"]:
    """Get settings with caching to reduce DB queries"""
    from app.models.models import AppSettings
    
    current_time = time.time()
    
    # Return cached if valid
    if _settings_cache["data"] is not None and current_time < _settings_cache["expires"]:
        return _settings_cache["data"]
    
    # Fetch from DB and cache
    settings = db.query(AppSettings).first()
    _settings_cache["data"] = settings
    _settings_cache["expires"] = current_time + SETTINGS_CACHE_TTL
    
    return settings


def invalidate_settings_cache():
    """Invalidate settings cache when settings are updated"""
    _settings_cache["data"] = None
    _settings_cache["expires"] = 0
