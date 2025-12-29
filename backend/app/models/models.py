"""
Database models and schemas
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TelegramMessage(Base):
    """Store raw Telegram messages"""
    __tablename__ = "telegram_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, index=True)
    chat_name = Column(String)
    message_id = Column(Integer)
    message_text = Column(Text)
    sender = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_processed = Column(Boolean, default=False)
    parsed_signal = Column(Text, nullable=True)  # JSON string of parsed signal


class Trade(Base):
    """Store trade information"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, index=True)
    symbol = Column(String, index=True)
    action = Column(String)  # BUY or SELL
    quantity = Column(Integer)
    entry_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    order_type = Column(String)  # MARKET, LIMIT, etc.
    exchange = Column(String)  # NSE, BSE, NFO, etc.
    product_type = Column(String)  # DELIVERY, INTRADAY, MARGIN
    broker_type = Column(String, default="angel_one", index=True)  # Broker used for this trade
    
    # Order execution details
    order_id = Column(String, nullable=True)
    status = Column(String, default="PENDING")  # PENDING, APPROVED, EXECUTED, REJECTED, FAILED
    execution_price = Column(Float, nullable=True)
    execution_time = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional info
    notes = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)


class BrokerConfig(Base):
    """Store broker configuration"""
    __tablename__ = "broker_config"
    
    id = Column(Integer, primary_key=True, index=True)
    broker_name = Column(String, default="angel_one", index=True)  # angel_one, zerodha, upstox, fyers
    api_key = Column(String)
    api_secret = Column(String, nullable=True)  # For brokers like Zerodha that need API secret
    client_id = Column(String)
    password_encrypted = Column(String)
    totp_secret = Column(String, nullable=True)  # For Angel One TOTP
    is_active = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    # Session persistence fields
    auth_token = Column(Text, nullable=True)  # Encrypted auth token for session persistence
    refresh_token = Column(Text, nullable=True)  # Encrypted refresh token
    feed_token = Column(Text, nullable=True)  # Encrypted feed token (for websocket)
    session_expiry = Column(DateTime, nullable=True)  # When the session expires
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TelegramConfig(Base):
    """Store Telegram configuration"""
    __tablename__ = "telegram_config"
    
    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(String)
    api_hash = Column(String)
    phone_number = Column(String)
    session_string = Column(Text, nullable=True)
    monitored_chats = Column(Text)  # JSON array of chat IDs/usernames
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AppSettings(Base):
    """Store application settings"""
    __tablename__ = "app_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    auto_trade_enabled = Column(Boolean, default=False)
    require_manual_approval = Column(Boolean, default=True)
    default_quantity = Column(Integer, default=1)
    max_trades_per_day = Column(Integer, default=10)
    risk_percentage = Column(Float, default=1.0)
    paper_trading_enabled = Column(Boolean, default=True)  # Paper trading mode
    paper_trading_balance = Column(Float, default=100000.0)  # Virtual starting balance
    active_broker_type = Column(String, default="angel_one")  # Currently active broker
    price_tolerance_percent = Column(Float, default=2.0)  # Max % deviation from signal price for auto-trade
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaperTrade(Base):
    """Store paper/simulated trades for testing"""
    __tablename__ = "paper_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    action = Column(String)  # BUY or SELL
    quantity = Column(Integer)
    entry_price = Column(Float)
    current_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    exchange = Column(String, default="NSE")
    product_type = Column(String, default="INTRADAY")
    broker_type = Column(String, default="angel_one", index=True)  # Simulated broker type
    
    # P&L tracking
    pnl = Column(Float, default=0.0)
    pnl_percentage = Column(Float, default=0.0)
    
    # Status
    status = Column(String, default="OPEN")  # OPEN, CLOSED, TARGET_HIT, SL_HIT
    exit_price = Column(Float, nullable=True)
    exit_reason = Column(String, nullable=True)
    
    # Timestamps
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime, nullable=True)
    
    # Source
    source_message = Column(Text, nullable=True)  # Original signal message
    notes = Column(Text, nullable=True)
