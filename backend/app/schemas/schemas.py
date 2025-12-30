"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
import json


# Telegram schemas
class TelegramConfigBase(BaseModel):
    api_id: str
    api_hash: str
    phone_number: str
    monitored_chats: List[str] = []


class TelegramConfigCreate(TelegramConfigBase):
    pass


class TelegramConfigResponse(BaseModel):
    id: int
    api_id: str
    api_hash: str
    phone_number: str
    monitored_chats: List[str] = []
    is_active: bool
    created_at: datetime
    
    @field_validator('monitored_chats', mode='before')
    @classmethod
    def parse_monitored_chats(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if v else []
    
    class Config:
        from_attributes = True


class TelegramMessageResponse(BaseModel):
    id: int
    chat_name: str
    message_text: str
    sender: str
    timestamp: datetime
    is_processed: bool
    parsed_signal: Optional[str] = None
    
    class Config:
        from_attributes = True


# Broker schemas
class BrokerConfigBase(BaseModel):
    broker_name: str = "angel_one"  # angel_one, zerodha, upstox, fyers
    api_key: str
    api_secret: Optional[str] = None  # For Zerodha, Upstox
    client_id: str
    pin: str  # Trading PIN or password
    totp_secret: Optional[str] = None  # For Angel One TOTP or Zerodha API secret


class BrokerConfigCreate(BrokerConfigBase):
    pass


class BrokerConfigResponse(BaseModel):
    id: int
    broker_name: str
    client_id: str
    is_active: bool
    has_totp_secret: bool = False  # Indicates if TOTP secret is configured
    has_api_secret: bool = False  # Indicates if API secret is configured
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BrokerInfo(BaseModel):
    broker_type: str
    name: str
    is_registered: bool
    is_configured: bool = False
    is_logged_in: bool = False


class BrokerLoginRequest(BaseModel):
    broker_type: str = "angel_one"
    client_id: str
    password: str
    totp_token: Optional[str] = None


# Trade schemas
class TradeSignal(BaseModel):
    symbol: str
    action: str  # BUY or SELL
    quantity: int = 1
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    order_type: str = "MARKET"
    exchange: str = "NSE"
    product_type: str = "INTRADAY"


class TradeCreate(TradeSignal):
    message_id: Optional[int] = None


class TradeResponse(BaseModel):
    id: int
    symbol: str
    action: str
    quantity: int
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    order_type: str
    exchange: str
    product_type: str
    order_id: Optional[str] = None
    status: str
    broker_status: Optional[str] = None  # Real status from broker
    broker_rejection_reason: Optional[str] = None  # Rejection reason from broker
    average_price: Optional[float] = None  # Actual fill price
    filled_quantity: Optional[int] = None  # Quantity filled
    execution_price: Optional[float] = None
    execution_time: Optional[datetime] = None
    last_status_check: Optional[datetime] = None  # When status was last synced
    created_at: datetime
    notes: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class TradeApproval(BaseModel):
    trade_id: int
    approved: bool
    notes: Optional[str] = None


# Settings schemas
class AppSettingsBase(BaseModel):
    auto_trade_enabled: bool = False
    require_manual_approval: bool = True
    default_quantity: int = 1
    max_trades_per_day: int = 10
    risk_percentage: float = Field(default=1.0, ge=0.1, le=100.0)
    paper_trading_enabled: bool = True
    paper_trading_balance: float = Field(default=100000.0, ge=1000.0)


class AppSettingsCreate(AppSettingsBase):
    pass


class AppSettingsResponse(AppSettingsBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# WebSocket message schemas
class WebSocketMessage(BaseModel):
    type: str
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
