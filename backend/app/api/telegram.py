"""
Telegram API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
from datetime import datetime, date

from app.core.database import get_db
from app.schemas.schemas import (
    TelegramConfigCreate,
    TelegramConfigResponse,
    TelegramMessageResponse,
    TradeCreate
)
from app.models.models import TelegramConfig, TelegramMessage, Trade, AppSettings
from app.services.telegram_service import TelegramService
from app.services.broker_service import broker_service, symbol_master
from app.core.logging_config import get_logger

logger = get_logger("telegram_api")

router = APIRouter()

# This will be injected from main.py
telegram_service: TelegramService = None


@router.post("/config", response_model=TelegramConfigResponse)
async def create_telegram_config(config: TelegramConfigCreate, db: Session = Depends(get_db)):
    """Create or update Telegram configuration"""
    import json
    
    # Try to find existing active config first
    existing_config = db.query(TelegramConfig).filter(TelegramConfig.is_active).first()
    
    # If no active config, check for any config (handles edge cases)
    if not existing_config:
        existing_config = db.query(TelegramConfig).order_by(TelegramConfig.id.desc()).first()
    
    if existing_config:
        # Update existing config and PRESERVE session_string
        existing_config.api_id = config.api_id
        existing_config.api_hash = config.api_hash
        existing_config.phone_number = config.phone_number
        existing_config.monitored_chats = json.dumps(config.monitored_chats)
        existing_config.is_active = True
        
        # If this config doesn't have a session, try to recover from another config
        if not existing_config.session_string:
            session_donor = db.query(TelegramConfig).filter(
                TelegramConfig.session_string.isnot(None),
                TelegramConfig.id != existing_config.id
            ).first()
            if session_donor and session_donor.session_string:
                existing_config.session_string = session_donor.session_string
                logger.info(f"🔄 Recovered session_string from config #{session_donor.id}")
        
        # Note: session_string is preserved automatically as we don't modify it
        db.commit()
        db.refresh(existing_config)
        logger.info(f"✅ Updated Telegram config (ID: {existing_config.id}), session_string preserved: {bool(existing_config.session_string)}")
        return existing_config
    else:
        # Create new config only if none exists at all
        db_config = TelegramConfig(
            api_id=config.api_id,
            api_hash=config.api_hash,
            phone_number=config.phone_number,
            monitored_chats=json.dumps(config.monitored_chats),
            is_active=True
        )
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        logger.info(f"✅ Created new Telegram config (ID: {db_config.id})")
        return db_config


@router.get("/config", response_model=TelegramConfigResponse)
async def get_telegram_config(db: Session = Depends(get_db)):
    """Get active Telegram configuration"""
    config = db.query(TelegramConfig).filter(TelegramConfig.is_active).first()
    if not config:
        raise HTTPException(status_code=404, detail="No active configuration found")
    return config


@router.post("/initialize")
async def initialize_telegram(db: Session = Depends(get_db)):
    """Initialize Telegram client"""
    config = db.query(TelegramConfig).filter(TelegramConfig.is_active).first()
    if not config:
        raise HTTPException(status_code=404, detail="No configuration found")
    
    if telegram_service:
        result = await telegram_service.initialize(
            config.api_id,
            config.api_hash,
            config.phone_number,
            config.session_string
        )
        return result
    
    raise HTTPException(status_code=500, detail="Telegram service not available")


@router.post("/verify-code")
async def verify_code(phone: str, code: str, db: Session = Depends(get_db)):
    """Verify Telegram authentication code"""
    if telegram_service and telegram_service.client:
        result = await telegram_service.verify_code(phone, code)
        
        # Save session string if successful
        if result['status'] == 'success':
            try:
                config = db.query(TelegramConfig).filter(
                    TelegramConfig.phone_number == phone
                ).first()
                if config:
                    config.session_string = result['session_string']
                    db.commit()
                    logger.info(f"Session string saved for phone {phone}")
                else:
                    logger.warning(f"No config found for phone {phone}")
            except Exception as e:
                logger.error(f"Error saving session string: {e}")
                db.rollback()
        
        return result
    
    raise HTTPException(status_code=400, detail="Client not initialized")


@router.get("/chats")
async def get_chats():
    """Get list of available Telegram chats"""
    if telegram_service:
        chats = await telegram_service.get_monitored_chats()
        return {"chats": chats}
    
    raise HTTPException(status_code=500, detail="Telegram service not available")


@router.get("/messages", response_model=List[TelegramMessageResponse])
async def get_messages(
    limit: int = 50,
    skip: int = 0,
    unprocessed_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get Telegram messages"""
    query = db.query(TelegramMessage)
    
    if unprocessed_only:
        query = query.filter(TelegramMessage.is_processed.is_(False))
    
    messages = query.order_by(TelegramMessage.timestamp.desc()).offset(skip).limit(limit).all()
    return messages


@router.post("/messages/{message_id}/process")
async def mark_message_processed(message_id: int, db: Session = Depends(get_db)):
    """Mark message as processed"""
    message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.is_processed = True
    db.commit()
    
    return {"status": "success", "message": "Message marked as processed"}


@router.get("/status")
async def get_telegram_status():
    """Get Telegram connection status"""
    if telegram_service:
        return telegram_service.get_connection_status()
    return {
        "is_connected": False,
        "client_initialized": False,
        "monitored_chats_count": 0
    }


@router.post("/reload")
async def reload_telegram_service():
    """Reload Telegram service with updated configuration (e.g., after changing monitored chats)"""
    if telegram_service:
        result = await telegram_service.reload()
        return {
            "status": "success",
            "message": "Telegram service reloaded",
            **result
        }
    raise HTTPException(status_code=500, detail="Telegram service not available")


@router.get("/history/{chat_id}")
async def fetch_historic_messages(
    chat_id: str,
    limit: int = 100,
    save_to_db: bool = False
):
    """
    Fetch historic messages from a specific chat.
    
    Args:
        chat_id: The chat ID to fetch messages from
        limit: Maximum number of messages to fetch (default 100, max 500)
        save_to_db: Whether to save fetched messages to database
    
    Returns:
        List of messages or summary if saved to database
    """
    if not telegram_service:
        raise HTTPException(status_code=500, detail="Telegram service not available")
    
    # Limit max messages
    limit = min(limit, 500)
    
    if save_to_db:
        result = await telegram_service.save_historic_messages_to_db(chat_id, limit)
        return {
            "status": "success",
            "chat_id": chat_id,
            **result
        }
    else:
        messages = await telegram_service.fetch_historic_messages(chat_id, limit)
        return {
            "status": "success",
            "chat_id": chat_id,
            "count": len(messages),
            "messages": messages
        }


@router.get("/messages/by-chat/{chat_id}", response_model=List[TelegramMessageResponse])
async def get_messages_by_chat(
    chat_id: str,
    limit: int = 50,
    skip: int = 0,
    signals_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get messages from a specific chat"""
    query = db.query(TelegramMessage).filter(TelegramMessage.chat_id == chat_id)
    
    if signals_only:
        query = query.filter(TelegramMessage.parsed_signal.isnot(None))
    
    messages = query.order_by(TelegramMessage.timestamp.desc()).offset(skip).limit(limit).all()
    return messages


@router.get("/messages/stats")
async def get_message_stats(db: Session = Depends(get_db)):
    """Get message statistics"""
    from sqlalchemy import func, case
    
    total = db.query(TelegramMessage).count()
    with_signals = db.query(TelegramMessage).filter(TelegramMessage.parsed_signal.isnot(None)).count()
    unprocessed = db.query(TelegramMessage).filter(
        TelegramMessage.parsed_signal.isnot(None),
        TelegramMessage.is_processed.is_(False)
    ).count()
    
    # Get counts by chat
    chat_stats = db.query(
        TelegramMessage.chat_name,
        TelegramMessage.chat_id,
        func.count(TelegramMessage.id).label('message_count'),
        func.sum(
            case(
                (TelegramMessage.parsed_signal.isnot(None), 1),
                else_=0
            )
        ).label('signal_count')
    ).group_by(TelegramMessage.chat_id, TelegramMessage.chat_name).all()
    
    return {
        "total_messages": total,
        "total_signals": with_signals,
        "unprocessed_signals": unprocessed,
        "chats": [
            {
                "chat_id": stat.chat_id,
                "chat_name": stat.chat_name,
                "message_count": stat.message_count,
                "signal_count": stat.signal_count or 0
            }
            for stat in chat_stats
        ]
    }


@router.delete("/messages")
async def delete_all_messages(db: Session = Depends(get_db)):
    """Delete all stored messages (use with caution)"""
    count = db.query(TelegramMessage).count()
    db.query(TelegramMessage).delete()
    db.commit()
    return {"status": "success", "deleted": count}


@router.post("/messages/{message_id}/execute")
async def execute_trade_from_message(
    message_id: int,
    trade_params: TradeCreate,
    db: Session = Depends(get_db)
):
    """
    Execute a trade based on a Telegram message signal.
    
    This endpoint:
    1. Validates the message exists and has a parsed signal
    2. Creates a trade record
    3. Optionally executes immediately based on settings
    4. Marks the message as processed
    """
    # Get the message
    message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if not message.parsed_signal:
        raise HTTPException(status_code=400, detail="Message does not contain a valid trading signal")
    
    # Parse the signal to log AI interpretation
    parsed_signal = json.loads(message.parsed_signal)
    logger.info("="*60)
    logger.info("📊 TRADE EXECUTION REQUEST")
    logger.info("="*60)
    logger.info(f"Message ID: {message_id}")
    logger.info(f"Original Message: {message.message_text[:200]}..." if len(message.message_text) > 200 else f"Original Message: {message.message_text}")
    logger.info("\n🤖 AI INTERPRETATION:")
    logger.info(f"  Symbol: {parsed_signal.get('symbol')}")
    logger.info(f"  Action: {parsed_signal.get('action')}")
    logger.info(f"  Entry Price: ₹{parsed_signal.get('entry_price')}")
    logger.info(f"  Target Price: ₹{parsed_signal.get('target_price')}")
    logger.info(f"  Stop Loss: ₹{parsed_signal.get('stop_loss')}")
    if parsed_signal.get('confidence'):
        logger.info(f"  AI Confidence: {parsed_signal.get('confidence')*100:.1f}%")
    if parsed_signal.get('reasoning'):
        logger.info(f"  AI Reasoning: {parsed_signal.get('reasoning')}")
    logger.info(f"{'='*60}\n")
    
    # Check trade limits
    settings = db.query(AppSettings).first()
    if settings:
        today = date.today()
        today_trades = db.query(Trade).filter(
            Trade.created_at >= datetime(today.year, today.month, today.day)
        ).count()
        
        if today_trades >= settings.max_trades_per_day:
            raise HTTPException(
                status_code=429, 
                detail=f"Daily trade limit ({settings.max_trades_per_day}) reached"
            )
    
    # Get default quantity from settings if not provided or zero
    quantity = trade_params.quantity
    if quantity <= 0 and settings:
        quantity = settings.default_quantity
    if quantity <= 0:
        quantity = 1
    
    # Create trade record
    db_trade = Trade(
        message_id=message_id,
        symbol=trade_params.symbol.upper(),
        action=trade_params.action.upper(),
        quantity=quantity,
        entry_price=trade_params.entry_price,
        target_price=trade_params.target_price,
        stop_loss=trade_params.stop_loss,
        order_type=trade_params.order_type,
        exchange=trade_params.exchange,
        product_type=trade_params.product_type,
        status="PENDING"
    )
    
    logger.info("\n📝 TRADE RECORD CREATED:")
    logger.info(f"  Symbol: {db_trade.symbol}")
    logger.info(f"  Action: {db_trade.action}")
    logger.info(f"  Quantity: {db_trade.quantity}")
    logger.info(f"  Order Type: {db_trade.order_type}")
    logger.info(f"  Exchange: {db_trade.exchange}")
    logger.info(f"  Product Type: {db_trade.product_type}")
    
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    
    logger.info(f"  Trade ID: {db_trade.id}")
    logger.info(f"  Status: {db_trade.status}")
    
    # Mark message as processed
    message.is_processed = True
    db.commit()
    
    # Check broker status
    if not broker_service.is_logged_in:
        logger.warning(f"⚠️  Broker not logged in. Trade {db_trade.id} created but not executed.")
        logger.info(f"{'='*60}\n")
        return {
            "status": "pending",
            "message": "Trade created but broker not logged in. Please login to broker and approve trade.",
            "trade_id": db_trade.id,
            "parsed_signal": parsed_signal,
            "trade": {
                "id": db_trade.id,
                "symbol": db_trade.symbol,
                "action": db_trade.action,
                "quantity": db_trade.quantity,
                "status": db_trade.status
            }
        }
    
    # Execute if auto-trade enabled and no manual approval required
    if settings and settings.auto_trade_enabled and not settings.require_manual_approval:
        logger.info("\n🚀 EXECUTING TRADE ON BROKER...")
        logger.info("  Auto-trade: Enabled")
        logger.info("  Manual approval: Not required")
        
        result = broker_service.place_order(
            symbol=db_trade.symbol,
            action=db_trade.action,
            quantity=db_trade.quantity,
            exchange=db_trade.exchange,
            order_type=db_trade.order_type,
            product_type=db_trade.product_type,
            price=db_trade.entry_price
        )
        
        if result['status'] == 'success':
            db_trade.status = "EXECUTED"
            db_trade.order_id = result['order_id']
            db_trade.execution_time = datetime.utcnow()
            db.commit()
            
            logger.info("\n✅ TRADE EXECUTED SUCCESSFULLY!")
            logger.info(f"  Order ID: {result['order_id']}")
            logger.info("  Status: EXECUTED")
            logger.info(f"{'='*60}\n")
            
            return {
                "status": "executed",
                "message": "Trade executed successfully",
                "trade_id": db_trade.id,
                "order_id": result['order_id'],
                "parsed_signal": parsed_signal,
                "trade": {
                    "id": db_trade.id,
                    "symbol": db_trade.symbol,
                    "action": db_trade.action,
                    "quantity": db_trade.quantity,
                    "status": db_trade.status,
                    "order_id": db_trade.order_id
                }
            }
        else:
            db_trade.status = "FAILED"
            db_trade.error_message = result['message']
            db.commit()
            
            logger.error("\n❌ TRADE EXECUTION FAILED!")
            logger.error(f"  Error: {result['message']}")
            logger.error(f"{'='*60}\n")
            
            return {
                "status": "failed",
                "message": result['message'],
                "trade_id": db_trade.id,
                "parsed_signal": parsed_signal,
                "trade": {
                    "id": db_trade.id,
                    "symbol": db_trade.symbol,
                    "action": db_trade.action,
                    "quantity": db_trade.quantity,
                    "status": db_trade.status,
                    "error": db_trade.error_message
                }
            }
    
    logger.info("\n⏳ TRADE PENDING MANUAL APPROVAL")
    logger.info(f"  Auto-trade: {'Disabled' if not settings or not settings.auto_trade_enabled else 'Enabled'}")
    logger.info(f"  Manual approval: {'Required' if settings and settings.require_manual_approval else 'Not required'}")
    logger.info(f"{'='*60}\n")
    
    return {
        "status": "pending",
        "message": "Trade created and awaiting approval",
        "trade_id": db_trade.id,
        "parsed_signal": parsed_signal,
        "trade": {
            "id": db_trade.id,
            "symbol": db_trade.symbol,
            "action": db_trade.action,
            "quantity": db_trade.quantity,
            "status": db_trade.status
        }
    }


@router.post("/test-signal")
async def test_signal_parsing(message_text: str, db: Session = Depends(get_db)):
    """
    Test endpoint to simulate receiving a Telegram message and parsing it.
    Use this to verify the signal parser works before connecting to Telegram.
    
    Example usage:
    curl -X POST "http://localhost:8000/api/telegram/test-signal?message_text=BUY%20RELIANCE%20@%202450%20Target%202500%20SL%202420"
    """
    from app.services.signal_parser import SignalParser
    
    parser = SignalParser()
    parsed = parser.parse_message(message_text)
    
    if not parsed:
        return {
            "status": "no_signal",
            "message_text": message_text,
            "parsed_signal": None,
            "info": "No trading signal detected in this message"
        }
    
    # Get symbol token for validation
    token_info = None
    if parsed.get('symbol'):
        token = symbol_master.get_token(parsed['symbol'], 'NSE')
        if token:
            token_info = {"token": token, "exchange": "NSE", "found": True}
        else:
            token = symbol_master.get_token(parsed['symbol'], 'BSE')
            if token:
                token_info = {"token": token, "exchange": "BSE", "found": True}
            else:
                token_info = {"found": False, "warning": f"Symbol {parsed['symbol']} not found in master"}
    
    return {
        "status": "signal_detected",
        "message_text": message_text,
        "parsed_signal": parsed,
        "token_info": token_info,
        "broker_status": {
            "is_logged_in": broker_service.is_logged_in,
            "can_execute": broker_service.is_logged_in
        },
        "next_steps": [
            "1. If broker logged in, you can execute this trade",
            "2. Use POST /api/trades/ to create the trade",
            "3. Use POST /api/trades/{id}/execute to execute it"
        ]
    }


@router.post("/simulate-trade")
async def simulate_telegram_trade(
    message_text: str,
    execute: bool = False,
    db: Session = Depends(get_db)
):
    """
    Full simulation: Parse message → Create trade → Optionally execute.
    
    This is the same flow that happens when a real Telegram message arrives.
    
    Args:
        message_text: The message to parse (e.g., "BUY RELIANCE @ 2450 TGT 2500 SL 2420")
        execute: If True and broker is logged in, will actually execute the trade!
    
    WARNING: If execute=True, this will place a REAL order!
    """
    from app.services.signal_parser import SignalParser
    
    parser = SignalParser()
    parsed = parser.parse_message(message_text)
    
    if not parsed:
        return {
            "step": "parse",
            "status": "failed",
            "message": "No trading signal detected",
            "message_text": message_text
        }
    
    # Validate symbol
    token = symbol_master.get_token(parsed['symbol'], 'NSE')
    exchange = 'NSE'
    if not token:
        token = symbol_master.get_token(parsed['symbol'], 'BSE')
        exchange = 'BSE' if token else 'NSE'
    
    if not token:
        return {
            "step": "validate",
            "status": "warning",
            "message": f"Symbol {parsed['symbol']} not found in instrument master",
            "parsed_signal": parsed,
            "suggestion": "Check symbol name or refresh instrument master"
        }
    
    # Get settings
    settings = db.query(AppSettings).first()
    quantity = parsed.get('quantity') or (settings.default_quantity if settings else 1)
    
    # Create trade record
    db_trade = Trade(
        symbol=parsed['symbol'].upper(),
        action=parsed['action'].upper(),
        quantity=quantity,
        entry_price=parsed.get('entry_price'),
        target_price=parsed.get('target_price'),
        stop_loss=parsed.get('stop_loss'),
        order_type='LIMIT' if parsed.get('entry_price') else 'MARKET',
        exchange=exchange,
        product_type='INTRADAY',
        status='PENDING',
        notes=f"Simulated from: {message_text[:100]}"
    )
    
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    
    result = {
        "step": "create",
        "status": "success",
        "message": "Trade created",
        "trade_id": db_trade.id,
        "trade": {
            "id": db_trade.id,
            "symbol": db_trade.symbol,
            "action": db_trade.action,
            "quantity": db_trade.quantity,
            "entry_price": db_trade.entry_price,
            "target_price": db_trade.target_price,
            "stop_loss": db_trade.stop_loss,
            "order_type": db_trade.order_type,
            "exchange": db_trade.exchange,
            "status": db_trade.status
        },
        "parsed_signal": parsed,
        "token": token
    }
    
    # Execute if requested
    if execute:
        if not broker_service.is_logged_in:
            result["execute_status"] = "skipped"
            result["execute_message"] = "Broker not logged in"
            return result
        
        order_result = broker_service.place_order(
            symbol=db_trade.symbol,
            action=db_trade.action,
            quantity=db_trade.quantity,
            exchange=db_trade.exchange,
            order_type=db_trade.order_type,
            product_type=db_trade.product_type,
            price=db_trade.entry_price
        )
        
        if order_result['status'] == 'success':
            db_trade.status = 'EXECUTED'
            db_trade.order_id = order_result['order_id']
            db_trade.execution_time = datetime.utcnow()
            db.commit()
            
            result["step"] = "execute"
            result["execute_status"] = "success"
            result["order_id"] = order_result['order_id']
            result["trade"]["status"] = "EXECUTED"
            result["trade"]["order_id"] = order_result['order_id']
        else:
            db_trade.status = 'FAILED'
            db_trade.error_message = order_result['message']
            db.commit()
            
            result["step"] = "execute"
            result["execute_status"] = "failed"
            result["error"] = order_result['message']
            result["trade"]["status"] = "FAILED"
    
    return result


@router.get("/messages/{message_id}/signal")
async def get_message_signal(message_id: int, db: Session = Depends(get_db)):
    """Get parsed signal details from a message for trade execution"""
    message = db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if not message.parsed_signal:
        raise HTTPException(status_code=400, detail="Message does not contain a valid trading signal")
    
    signal = json.loads(message.parsed_signal)
    
    # Get symbol token for validation
    token_info = None
    if signal.get('symbol'):
        token = symbol_master.get_token(signal['symbol'], 'NSE')
        if token:
            token_info = {"token": token, "exchange": "NSE"}
        else:
            # Try BSE
            token = symbol_master.get_token(signal['symbol'], 'BSE')
            if token:
                token_info = {"token": token, "exchange": "BSE"}
    
    # Get broker status
    broker_status = {
        "is_logged_in": broker_service.is_logged_in,
        "client_id": broker_service.client_id if broker_service.is_logged_in else None
    }
    
    # Get settings
    settings = db.query(AppSettings).first()
    default_quantity = settings.default_quantity if settings else 1
    auto_trade = settings.auto_trade_enabled if settings else False
    
    return {
        "message_id": message_id,
        "message_text": message.message_text,
        "chat_name": message.chat_name,
        "timestamp": message.timestamp.isoformat() if message.timestamp else None,
        "is_processed": message.is_processed,
        "signal": signal,
        "token_info": token_info,
        "broker_status": broker_status,
        "settings": {
            "default_quantity": default_quantity,
            "auto_trade_enabled": auto_trade
        }
    }
