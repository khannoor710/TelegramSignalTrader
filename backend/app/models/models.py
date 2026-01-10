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
    order_id = Column(String, nullable=True, index=True)  # Added index for faster lookup
    status = Column(String, default="PENDING", index=True)  # Added index for status filtering
    broker_status = Column(String, nullable=True)  # Real broker status: open, complete, rejected, cancelled, etc.
    broker_rejection_reason = Column(Text, nullable=True)  # Reason if broker rejected the order
    average_price = Column(Float, nullable=True)  # Actual fill price from broker
    filled_quantity = Column(Integer, nullable=True)  # Quantity actually filled
    execution_price = Column(Float, nullable=True)
    execution_time = Column(DateTime, nullable=True)
    last_status_check = Column(DateTime, nullable=True)  # When we last checked broker status
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)  # Added index for date filtering
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional info
    notes = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Advanced order tracking
    order_variety = Column(String, default="NORMAL")  # NORMAL, BRACKET, GTT
    parent_order_id = Column(String, nullable=True)  # For linked orders (bracket legs)
    target_order_id = Column(String, nullable=True)  # Target/profit booking order ID
    sl_order_id = Column(String, nullable=True)  # Stop-loss order ID


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
    
    # Risk Management Settings
    daily_loss_limit_enabled = Column(Boolean, default=False)  # Enable daily loss limit
    daily_loss_limit_percent = Column(Float, default=5.0)  # Stop trading at X% loss
    daily_loss_limit_amount = Column(Float, nullable=True)  # Or stop at fixed amount loss
    position_sizing_mode = Column(String, default="fixed")  # fixed, percent, risk_based
    max_position_value = Column(Float, nullable=True)  # Maximum value per position
    max_open_positions = Column(Integer, default=10)  # Maximum concurrent positions
    trading_start_time = Column(String, default="09:15")  # Market open time
    trading_end_time = Column(String, default="15:15")  # Stop new trades 15 min before close
    weekend_trading_disabled = Column(Boolean, default=True)  # No trading on weekends
    
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
