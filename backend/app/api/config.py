"""
Configuration API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import (
    AppSettingsCreate,
    AppSettingsResponse
)
from app.models.models import AppSettings

router = APIRouter()


@router.post("/settings", response_model=AppSettingsResponse)
async def create_or_update_settings(settings: AppSettingsCreate, db: Session = Depends(get_db)):
    """Create or update app settings"""
    db_settings = db.query(AppSettings).first()
    
    if db_settings:
        # Update existing
        db_settings.auto_trade_enabled = settings.auto_trade_enabled
        db_settings.require_manual_approval = settings.require_manual_approval
        db_settings.default_quantity = settings.default_quantity
        db_settings.max_trades_per_day = settings.max_trades_per_day
        db_settings.risk_percentage = settings.risk_percentage
        db_settings.paper_trading_enabled = settings.paper_trading_enabled
        db_settings.paper_trading_balance = settings.paper_trading_balance
    else:
        # Create new
        db_settings = AppSettings(**settings.model_dump())
        db.add(db_settings)
    
    db.commit()
    db.refresh(db_settings)
    
    return db_settings


@router.get("/settings", response_model=AppSettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    """Get app settings"""
    settings = db.query(AppSettings).first()
    
    if not settings:
        # Create default settings
        settings = AppSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings
