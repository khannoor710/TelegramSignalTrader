"""
Automatic Trade Execution Service

Handles the complete flow of automatic trade execution when signals
are detected from Telegram channels:
1. Check if auto-trade is enabled
2. Verify broker is logged in
3. Validate instrument exists
4. Check current price availability and deviation
5. Execute trade with proper error handling
"""
import json
from datetime import datetime, date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import Trade, AppSettings, TelegramMessage
from app.services.broker_registry import get_broker_registry
from app.core.logging_config import get_logger

logger = get_logger("auto_trade_service")


class AutoTradeService:
    """
    Service for automatic trade execution from parsed Telegram signals.
    
    This service handles:
    - Settings validation (auto-trade enabled, manual approval, etc.)
    - Broker availability and login status checks
    - Instrument/symbol verification
    - Price availability and deviation checks
    - Trade execution with comprehensive logging
    """
    
    def __init__(self):
        self._broker_registry = None
    
    @property
    def broker_registry(self):
        """Lazy load broker registry to avoid circular imports"""
        if self._broker_registry is None:
            self._broker_registry = get_broker_registry()
        return self._broker_registry
    
    async def process_signal(
        self,
        parsed_signal: Dict[str, Any],
        message_id: int,
        chat_name: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Process a parsed trading signal and attempt automatic execution.
        
        Args:
            parsed_signal: Dictionary containing symbol, action, entry_price, etc.
            message_id: Database ID of the TelegramMessage
            chat_name: Name of the Telegram chat/channel
            db: Database session
            
        Returns:
            Dictionary with execution result and status
        """
        logger.info("=" * 60)
        logger.info("🤖 AUTO-TRADE PROCESSING STARTED")
        logger.info("=" * 60)
        logger.info(f"Message ID: {message_id}")
        logger.info(f"Chat: {chat_name}")
        logger.info(f"Signal: {parsed_signal}")
        
        result = {
            "message_id": message_id,
            "chat_name": chat_name,
            "signal": parsed_signal,
            "auto_trade_attempted": False,
            "status": "skipped",
            "reason": None,
            "trade_id": None,
            "order_id": None
        }
        
        try:
            # Step 1: Check settings
            settings = db.query(AppSettings).first()
            if not settings:
                result["reason"] = "No app settings configured"
                logger.warning("⚠️ No app settings found - skipping auto-trade")
                return result
            
            if not settings.auto_trade_enabled:
                result["reason"] = "Auto-trade is disabled"
                logger.info("ℹ️ Auto-trade is disabled in settings")
                return result
            
            if settings.require_manual_approval:
                result["reason"] = "Manual approval required"
                logger.info("ℹ️ Manual approval required - trade will need user approval")
                return result
            
            # Check daily trade limit
            today = date.today()
            today_trades = db.query(Trade).filter(
                Trade.created_at >= datetime(today.year, today.month, today.day)
            ).count()
            
            if today_trades >= settings.max_trades_per_day:
                result["reason"] = f"Daily trade limit ({settings.max_trades_per_day}) reached"
                logger.warning(f"⚠️ Daily trade limit reached: {today_trades}/{settings.max_trades_per_day}")
                return result
            
            result["auto_trade_attempted"] = True
            
            # Step 2: Check broker availability
            # Get settings to log which broker is active
            settings = db.query(AppSettings).first()
            active_broker_type = settings.active_broker_type if settings else None
            logger.info(f"🔍 Active broker type from settings: {active_broker_type}")
            
            active_broker = self.broker_registry.get_active_broker(db)
            if not active_broker:
                result["status"] = "failed"
                result["reason"] = "No active broker configured"
                logger.warning("⚠️ No active broker found")
                return result
            
            # Log broker instance details for debugging
            logger.info(f"🔍 Broker instance: {type(active_broker).__name__}")
            logger.info(f"🔍 Broker client_id: {active_broker.client_id}")
            logger.info(f"🔍 Broker is_logged_in: {active_broker.is_logged_in}")
            
            if not active_broker.is_logged_in:
                # Check if paper trading is enabled - we can still paper trade without broker login
                if settings.paper_trading_enabled:
                    logger.info("ℹ️ Broker not logged in, but paper trading is enabled")
                else:
                    result["status"] = "failed"
                    result["reason"] = "Broker not logged in"
                    logger.warning("⚠️ Broker is not logged in")
                    return result
            
            logger.info(f"✅ Broker available: {active_broker.client_id}")
            
            # Step 3: Validate signal has required fields
            symbol = parsed_signal.get("symbol")
            action = parsed_signal.get("action")
            
            if not symbol or not action:
                result["status"] = "failed"
                result["reason"] = "Invalid signal - missing symbol or action"
                logger.warning("⚠️ Invalid signal - missing required fields")
                return result
            
            # Step 4: Verify instrument and get token
            symbol = symbol.upper()
            action = action.upper()
            
            # Try to determine exchange - default to NSE
            exchange = parsed_signal.get("exchange", "NSE").upper()
            
            # Check if instrument exists
            instrument_check = await self.verify_instrument(active_broker, symbol, exchange)
            if not instrument_check["found"]:
                # Try BSE as fallback
                if exchange == "NSE":
                    instrument_check = await self.verify_instrument(active_broker, symbol, "BSE")
                    if instrument_check["found"]:
                        exchange = "BSE"
            
            if not instrument_check["found"]:
                result["status"] = "failed"
                result["reason"] = f"Instrument {symbol} not found on {exchange}"
                logger.warning(f"⚠️ Instrument {symbol} not found")
                return result
            
            logger.info(f"✅ Instrument verified: {symbol} on {exchange}")
            
            # Step 5: Check price availability and deviation
            signal_price = parsed_signal.get("entry_price")
            price_tolerance = getattr(settings, 'price_tolerance_percent', 2.0)
            
            price_check = await self.check_price_availability(
                broker=active_broker,
                symbol=symbol,
                exchange=exchange,
                signal_price=signal_price,
                tolerance_percent=price_tolerance
            )
            
            if not price_check["available"]:
                result["status"] = "failed"
                result["reason"] = price_check.get("reason", "Price not available")
                logger.warning(f"⚠️ Price check failed: {price_check.get('reason')}")
                return result
            
            current_price = price_check.get("current_price")
            logger.info(f"✅ Price check passed - Current: ₹{current_price}, Signal: ₹{signal_price}")
            
            # Step 6: Determine order parameters
            quantity = parsed_signal.get("quantity") or settings.default_quantity or 1
            target_price = parsed_signal.get("target_price")
            stop_loss = parsed_signal.get("stop_loss")
            
            # Determine order type based on signal
            order_type = "MARKET"
            price = None
            
            if signal_price and current_price:
                # If signal price is significantly different from current, use LIMIT
                price_diff_percent = abs(signal_price - current_price) / current_price * 100
                if price_diff_percent > 0.5:  # More than 0.5% difference
                    order_type = "LIMIT"
                    price = signal_price
            
            # Step 7: Create trade record
            db_trade = Trade(
                message_id=message_id,
                symbol=symbol,
                action=action,
                quantity=quantity,
                entry_price=signal_price or current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                order_type=order_type,
                exchange=exchange,
                product_type="INTRADAY",
                status="PENDING",
                notes=f"Auto-trade from {chat_name}"
            )
            
            db.add(db_trade)
            db.commit()
            db.refresh(db_trade)
            
            result["trade_id"] = db_trade.id
            logger.info(f"📝 Trade record created: ID {db_trade.id}")
            
            # Step 8: Execute the trade (paper or real)
            if settings.paper_trading_enabled:
                # Use paper trading service
                logger.info("📝 Executing PAPER trade...")
                
                from app.services.paper_trading_service import paper_trading_service
                
                paper_result = paper_trading_service.place_order(
                    symbol=symbol,
                    action=action,
                    quantity=quantity,
                    entry_price=current_price,
                    target_price=target_price,
                    stop_loss=stop_loss,
                    exchange=exchange,
                    product_type="INTRADAY",
                    source_message=f"Auto-trade from {chat_name}",
                    db=db
                )
                
                if paper_result.get("status") == "success":
                    db_trade.status = "EXECUTED"
                    db_trade.order_id = f"PAPER-{paper_result.get('trade_id')}"
                    db_trade.execution_time = datetime.utcnow()
                    db_trade.execution_price = current_price
                    db_trade.notes = f"Paper trade - {db_trade.notes or ''}"
                    db.commit()
                    
                    result["status"] = "executed"
                    result["order_id"] = db_trade.order_id
                    result["execution_price"] = current_price
                    result["is_paper_trade"] = True
                    
                    logger.info("=" * 60)
                    logger.info("✅ PAPER TRADE EXECUTED SUCCESSFULLY!")
                    logger.info(f"   Paper Trade ID: {paper_result.get('trade_id')}")
                    logger.info(f"   Symbol: {symbol} {action}")
                    logger.info(f"   Quantity: {quantity}")
                    logger.info(f"   Price: ₹{current_price}")
                    logger.info("=" * 60)
                    
                    # Mark message as processed
                    message = db.query(TelegramMessage).filter(
                        TelegramMessage.id == message_id
                    ).first()
                    if message:
                        message.is_processed = True
                        db.commit()
                else:
                    db_trade.status = "FAILED"
                    db_trade.error_message = paper_result.get("message", "Paper trade failed")
                    db.commit()
                    
                    result["status"] = "failed"
                    result["reason"] = paper_result.get("message", "Paper trade failed")
                    result["is_paper_trade"] = True
                    
                    logger.error("=" * 60)
                    logger.error("❌ PAPER TRADE EXECUTION FAILED!")
                    logger.error(f"   Error: {result['reason']}")
                    logger.error("=" * 60)
            else:
                # Use real broker
                logger.info("🚀 Executing REAL trade on broker...")
                
                order_result = active_broker.place_order(
                    symbol=symbol,
                    action=action,
                    quantity=quantity,
                    exchange=exchange,
                    order_type=order_type,
                    product_type="INTRADAY",
                    price=price
                )
                
                if order_result.get("status") == "success":
                    db_trade.status = "EXECUTED"
                    db_trade.order_id = order_result.get("order_id")
                    db_trade.execution_time = datetime.utcnow()
                    db_trade.execution_price = current_price
                    db.commit()
                    
                    result["status"] = "executed"
                    result["order_id"] = order_result.get("order_id")
                    result["execution_price"] = current_price
                    result["is_paper_trade"] = False
                    
                    logger.info("=" * 60)
                    logger.info("✅ AUTO-TRADE EXECUTED SUCCESSFULLY!")
                    logger.info(f"   Order ID: {result['order_id']}")
                    logger.info(f"   Symbol: {symbol} {action}")
                    logger.info(f"   Quantity: {quantity}")
                    logger.info(f"   Price: ₹{current_price}")
                    logger.info("=" * 60)
                    
                    # Mark message as processed
                    message = db.query(TelegramMessage).filter(
                        TelegramMessage.id == message_id
                    ).first()
                    if message:
                        message.is_processed = True
                        db.commit()
                else:
                    db_trade.status = "FAILED"
                    db_trade.error_message = order_result.get("message", "Unknown error")
                    db.commit()
                    
                    result["status"] = "failed"
                    result["reason"] = order_result.get("message", "Order placement failed")
                    result["is_paper_trade"] = False
                    
                    logger.error("=" * 60)
                    logger.error("❌ AUTO-TRADE EXECUTION FAILED!")
                    logger.error(f"   Error: {result['reason']}")
                    logger.error("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Auto-trade error: {e}", exc_info=True)
            result["status"] = "error"
            result["reason"] = str(e)
            return result
    
    async def verify_instrument(
        self,
        broker,
        symbol: str,
        exchange: str
    ) -> Dict[str, Any]:
        """
        Verify that an instrument exists and is tradeable.
        
        Args:
            broker: Active broker instance
            symbol: Trading symbol
            exchange: Exchange (NSE, BSE, NFO, etc.)
            
        Returns:
            Dictionary with 'found' boolean and 'token' if available
        """
        try:
            # Use broker's search_symbols method
            results = broker.search_symbols(symbol, exchange)
            
            if results:
                # Check for exact match
                for r in results:
                    if r.get("name", "").upper() == symbol or r.get("symbol", "").upper() == symbol:
                        return {
                            "found": True,
                            "token": r.get("token"),
                            "symbol": r.get("symbol"),
                            "name": r.get("name"),
                            "exchange": exchange
                        }
                
                # If no exact match, return first result
                return {
                    "found": True,
                    "token": results[0].get("token"),
                    "symbol": results[0].get("symbol"),
                    "name": results[0].get("name"),
                    "exchange": exchange
                }
            
            return {"found": False, "reason": f"Symbol {symbol} not found on {exchange}"}
            
        except Exception as e:
            logger.error(f"Error verifying instrument: {e}")
            return {"found": False, "reason": str(e)}
    
    async def check_price_availability(
        self,
        broker,
        symbol: str,
        exchange: str,
        signal_price: Optional[float],
        tolerance_percent: float = 2.0
    ) -> Dict[str, Any]:
        """
        Check if current market price is available and within acceptable range.
        
        Args:
            broker: Active broker instance
            symbol: Trading symbol
            exchange: Exchange
            signal_price: Expected price from signal
            tolerance_percent: Maximum acceptable deviation percentage
            
        Returns:
            Dictionary with 'available' boolean and price details
        """
        try:
            # Get last traded price
            ltp_result = broker.get_ltp(symbol, exchange)
            
            if ltp_result.get("status") != "success" and not ltp_result.get("data"):
                return {
                    "available": False,
                    "reason": "Could not fetch current price"
                }
            
            # Extract LTP from response
            ltp_data = ltp_result.get("data", {})
            current_price = None
            
            # Handle different response formats
            if isinstance(ltp_data, dict):
                current_price = ltp_data.get("ltp") or ltp_data.get("last_price") or ltp_data.get("close")
            elif isinstance(ltp_data, (int, float)):
                current_price = float(ltp_data)
            
            if not current_price:
                return {
                    "available": False,
                    "reason": "LTP not available in response"
                }
            
            current_price = float(current_price)
            
            # If no signal price, just verify price is available
            if not signal_price:
                return {
                    "available": True,
                    "current_price": current_price,
                    "deviation_percent": None
                }
            
            # Calculate price deviation
            deviation_percent = abs(signal_price - current_price) / current_price * 100
            
            if deviation_percent > tolerance_percent:
                return {
                    "available": False,
                    "current_price": current_price,
                    "signal_price": signal_price,
                    "deviation_percent": round(deviation_percent, 2),
                    "tolerance_percent": tolerance_percent,
                    "reason": f"Price deviation ({deviation_percent:.1f}%) exceeds tolerance ({tolerance_percent}%)"
                }
            
            return {
                "available": True,
                "current_price": current_price,
                "signal_price": signal_price,
                "deviation_percent": round(deviation_percent, 2)
            }
            
        except Exception as e:
            logger.error(f"Error checking price: {e}")
            return {
                "available": False,
                "reason": f"Price check error: {str(e)}"
            }


# Global singleton instance
auto_trade_service = AutoTradeService()


def get_auto_trade_service() -> AutoTradeService:
    """Get the global AutoTradeService instance."""
    return auto_trade_service
