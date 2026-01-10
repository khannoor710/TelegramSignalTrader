"""
Configuration API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.schemas import (
    AppSettingsCreate,
    AppSettingsResponse
)
from app.models.models import AppSettings

router = APIRouter()


class RiskSettingsUpdate(BaseModel):
    """Risk management settings update schema"""
    daily_loss_limit_enabled: Optional[bool] = None
    daily_loss_limit_percent: Optional[float] = None
    daily_loss_limit_amount: Optional[float] = None
    position_sizing_mode: Optional[str] = None
    max_position_value: Optional[float] = None
    max_open_positions: Optional[int] = None
    trading_start_time: Optional[str] = None
    trading_end_time: Optional[str] = None
    weekend_trading_disabled: Optional[bool] = None


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


@router.get("/settings/risk")
async def get_risk_settings(db: Session = Depends(get_db)):
    """Get risk management settings"""
    settings = db.query(AppSettings).first()
    
    if not settings:
        settings = AppSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return {
        "daily_loss_limit_enabled": getattr(settings, 'daily_loss_limit_enabled', False),
        "daily_loss_limit_percent": getattr(settings, 'daily_loss_limit_percent', 5.0),
        "daily_loss_limit_amount": getattr(settings, 'daily_loss_limit_amount', None),
        "position_sizing_mode": getattr(settings, 'position_sizing_mode', 'fixed'),
        "max_position_value": getattr(settings, 'max_position_value', None),
        "max_open_positions": getattr(settings, 'max_open_positions', 10),
        "trading_start_time": getattr(settings, 'trading_start_time', '09:15'),
        "trading_end_time": getattr(settings, 'trading_end_time', '15:15'),
        "weekend_trading_disabled": getattr(settings, 'weekend_trading_disabled', True)
    }


@router.put("/settings/risk")
async def update_risk_settings(risk_settings: RiskSettingsUpdate, db: Session = Depends(get_db)):
    """Update risk management settings"""
    settings = db.query(AppSettings).first()
    
    if not settings:
        settings = AppSettings()
        db.add(settings)
    
    # Update only provided fields
    if risk_settings.daily_loss_limit_enabled is not None:
        settings.daily_loss_limit_enabled = risk_settings.daily_loss_limit_enabled
    if risk_settings.daily_loss_limit_percent is not None:
        settings.daily_loss_limit_percent = risk_settings.daily_loss_limit_percent
    if risk_settings.daily_loss_limit_amount is not None:
        settings.daily_loss_limit_amount = risk_settings.daily_loss_limit_amount
    if risk_settings.position_sizing_mode is not None:
        settings.position_sizing_mode = risk_settings.position_sizing_mode
    if risk_settings.max_position_value is not None:
        settings.max_position_value = risk_settings.max_position_value
    if risk_settings.max_open_positions is not None:
        settings.max_open_positions = risk_settings.max_open_positions
    if risk_settings.trading_start_time is not None:
        settings.trading_start_time = risk_settings.trading_start_time
    if risk_settings.trading_end_time is not None:
        settings.trading_end_time = risk_settings.trading_end_time
    if risk_settings.weekend_trading_disabled is not None:
        settings.weekend_trading_disabled = risk_settings.weekend_trading_disabled
    
    db.commit()
    db.refresh(settings)
    
    return {
        "status": "success",
        "message": "Risk settings updated",
        "settings": {
            "daily_loss_limit_enabled": settings.daily_loss_limit_enabled,
            "daily_loss_limit_percent": settings.daily_loss_limit_percent,
            "daily_loss_limit_amount": settings.daily_loss_limit_amount,
            "position_sizing_mode": settings.position_sizing_mode,
            "max_position_value": settings.max_position_value,
            "max_open_positions": settings.max_open_positions,
            "trading_start_time": settings.trading_start_time,
            "trading_end_time": settings.trading_end_time,
            "weekend_trading_disabled": settings.weekend_trading_disabled
        }
    }

