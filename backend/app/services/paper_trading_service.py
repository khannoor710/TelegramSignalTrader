"""
Paper Trading Service for simulated trading without real money
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import PaperTrade, AppSettings
from app.services.broker_service import broker_service, symbol_master
from app.core.logging_config import get_logger

logger = get_logger("paper_trading")


class PaperTradingService:
    """Manages paper/simulated trading"""
    
    def __init__(self):
        self.virtual_balance = 100000.0  # Default starting balance
    
    def get_balance(self, db: Session) -> Dict[str, Any]:
        """Get current virtual balance and P&L summary"""
        settings = db.query(AppSettings).first()
        initial_balance = settings.paper_trading_balance if settings and settings.paper_trading_balance else 100000.0
        
        # Calculate open positions value
        open_trades = db.query(PaperTrade).filter(PaperTrade.status == "OPEN").all()
        
        total_invested = 0.0
        total_current_value = 0.0
        unrealized_pnl = 0.0
        
        for trade in open_trades:
            invested = trade.entry_price * trade.quantity
            current = (trade.current_price or trade.entry_price) * trade.quantity
            total_invested += invested
            total_current_value += current
            unrealized_pnl += trade.pnl or 0
        
        # Calculate realized P&L from closed trades
        closed_trades = db.query(PaperTrade).filter(PaperTrade.status != "OPEN").all()
        realized_pnl = sum(t.pnl or 0 for t in closed_trades)
        
        available_balance = initial_balance - total_invested + realized_pnl
        
        return {
            "initial_balance": initial_balance,
            "available_balance": round(available_balance, 2),
            "invested_amount": round(total_invested, 2),
            "current_value": round(total_current_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "realized_pnl": round(realized_pnl, 2),
            "total_pnl": round(unrealized_pnl + realized_pnl, 2),
            "total_pnl_percentage": round(((unrealized_pnl + realized_pnl) / initial_balance) * 100, 2) if initial_balance else 0,
            "open_positions": len(open_trades),
            "closed_positions": len(closed_trades)
        }
    
    def place_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        entry_price: Optional[float] = None,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        exchange: str = "NSE",
        product_type: str = "INTRADAY",
        source_message: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Place a paper trade order"""
        
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True
        
        try:
            # Validate symbol exists
            token = symbol_master.get_token(symbol, exchange)
            if not token:
                results = symbol_master.search_symbol(symbol, exchange, limit=1)
                if results:
                    token = results[0].get('token')
                    symbol = results[0].get('name') or symbol
            
            # Get current price if not provided
            if entry_price is None:
                if broker_service.is_logged_in:
                    ltp_result = broker_service.get_ltp(symbol, exchange)
                    if ltp_result.get('status') and ltp_result.get('data'):
                        entry_price = float(ltp_result['data'].get('ltp', 0))
                
                if not entry_price:
                    return {
                        "status": "error",
                        "message": "Could not determine entry price. Please provide one or login to broker for live prices."
                    }
            
            # Check balance
            balance = self.get_balance(db)
            required_amount = entry_price * quantity
            
            if action.upper() == "BUY" and required_amount > balance['available_balance']:
                return {
                    "status": "error",
                    "message": f"Insufficient balance. Required: Rs {required_amount:.2f}, Available: Rs {balance['available_balance']:.2f}"
                }
            
            # Create paper trade
            paper_trade = PaperTrade(
                symbol=symbol.upper(),
                action=action.upper(),
                quantity=quantity,
                entry_price=entry_price,
                current_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                exchange=exchange,
                product_type=product_type,
                status="OPEN",
                pnl=0.0,
                pnl_percentage=0.0,
                source_message=source_message,
                entry_time=datetime.utcnow()
            )
            
            db.add(paper_trade)
            db.commit()
            db.refresh(paper_trade)
            
            logger.info(f"Paper trade placed: {action} {quantity} {symbol} @ {entry_price}")
            
            return {
                "status": "success",
                "message": f"Paper trade placed: {action} {quantity} {symbol} @ Rs {entry_price}",
                "trade_id": paper_trade.id,
                "trade": {
                    "id": paper_trade.id,
                    "symbol": paper_trade.symbol,
                    "action": paper_trade.action,
                    "quantity": paper_trade.quantity,
                    "entry_price": paper_trade.entry_price,
                    "target_price": paper_trade.target_price,
                    "stop_loss": paper_trade.stop_loss,
                    "status": paper_trade.status
                }
            }
            
        except Exception as e:
            logger.error(f"Error placing paper trade: {e}")
            db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
        finally:
            if should_close_db:
                db.close()
    
    def update_prices(self, db: Session) -> Dict[str, Any]:
        """Update current prices for all open positions"""
        if not broker_service.is_logged_in:
            return {
                "status": "error",
                "message": "Broker not logged in. Cannot fetch live prices."
            }
        
        open_trades = db.query(PaperTrade).filter(PaperTrade.status == "OPEN").all()
        updated = 0
        errors = 0
        
        for trade in open_trades:
            try:
                ltp_result = broker_service.get_ltp(trade.symbol, trade.exchange)
                if ltp_result.get('status') and ltp_result.get('data'):
                    current_price = float(ltp_result['data'].get('ltp', trade.current_price))
                    trade.current_price = current_price
                    
                    # Calculate P&L
                    if trade.action == "BUY":
                        trade.pnl = (current_price - trade.entry_price) * trade.quantity
                    else:  # SELL
                        trade.pnl = (trade.entry_price - current_price) * trade.quantity
                    
                    trade.pnl_percentage = (trade.pnl / (trade.entry_price * trade.quantity)) * 100
                    
                    # Check if target or SL hit
                    if trade.target_price and trade.action == "BUY" and current_price >= trade.target_price:
                        self._close_trade(trade, current_price, "TARGET_HIT", db)
                    elif trade.target_price and trade.action == "SELL" and current_price <= trade.target_price:
                        self._close_trade(trade, current_price, "TARGET_HIT", db)
                    elif trade.stop_loss and trade.action == "BUY" and current_price <= trade.stop_loss:
                        self._close_trade(trade, current_price, "SL_HIT", db)
                    elif trade.stop_loss and trade.action == "SELL" and current_price >= trade.stop_loss:
                        self._close_trade(trade, current_price, "SL_HIT", db)
                    
                    updated += 1
            except Exception as e:
                logger.error(f"Error updating price for {trade.symbol}: {e}")
                errors += 1
        
        db.commit()
        
        return {
            "status": "success",
            "updated": updated,
            "errors": errors,
            "total": len(open_trades)
        }
    
    def _close_trade(self, trade: PaperTrade, exit_price: float, reason: str, db: Session):
        """Close a paper trade"""
        trade.status = reason
        trade.exit_price = exit_price
        trade.exit_reason = reason
        trade.exit_time = datetime.utcnow()
        trade.current_price = exit_price
        
        # Final P&L calculation
        if trade.action == "BUY":
            trade.pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            trade.pnl = (trade.entry_price - exit_price) * trade.quantity
        
        trade.pnl_percentage = (trade.pnl / (trade.entry_price * trade.quantity)) * 100
        
        logger.info(f"Paper trade closed: {trade.symbol} - {reason} - P&L: Rs {trade.pnl:.2f}")
    
    def close_position(self, trade_id: int, exit_price: Optional[float] = None, db: Session = None) -> Dict[str, Any]:
        """Manually close a paper trade position"""
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True
        
        try:
            trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id).first()
            if not trade:
                return {"status": "error", "message": "Trade not found"}
            
            if trade.status != "OPEN":
                return {"status": "error", "message": "Trade is already closed"}
            
            # Get current price if not provided
            if exit_price is None:
                if broker_service.is_logged_in:
                    ltp_result = broker_service.get_ltp(trade.symbol, trade.exchange)
                    if ltp_result.get('status') and ltp_result.get('data'):
                        exit_price = float(ltp_result['data'].get('ltp', 0))
                
                if not exit_price:
                    exit_price = trade.current_price or trade.entry_price
            
            self._close_trade(trade, exit_price, "CLOSED", db)
            db.commit()
            
            return {
                "status": "success",
                "message": f"Position closed at Rs {exit_price}",
                "trade": {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "action": trade.action,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "pnl": round(trade.pnl, 2),
                    "pnl_percentage": round(trade.pnl_percentage, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            if should_close_db:
                db.close()
    
    def get_open_positions(self, db: Session) -> List[Dict[str, Any]]:
        """Get all open paper trade positions"""
        trades = db.query(PaperTrade).filter(PaperTrade.status == "OPEN").order_by(PaperTrade.entry_time.desc()).all()
        return [self._trade_to_dict(t) for t in trades]
    
    def get_closed_positions(self, db: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """Get closed paper trade positions"""
        trades = db.query(PaperTrade).filter(PaperTrade.status != "OPEN").order_by(PaperTrade.exit_time.desc()).limit(limit).all()
        return [self._trade_to_dict(t) for t in trades]
    
    def get_all_positions(self, db: Session) -> Dict[str, Any]:
        """Get all positions with summary"""
        open_positions = self.get_open_positions(db)
        closed_positions = self.get_closed_positions(db)
        balance = self.get_balance(db)
        
        return {
            "balance": balance,
            "open_positions": open_positions,
            "closed_positions": closed_positions
        }
    
    def _trade_to_dict(self, trade: PaperTrade) -> Dict[str, Any]:
        """Convert trade model to dictionary"""
        return {
            "id": trade.id,
            "symbol": trade.symbol,
            "action": trade.action,
            "quantity": trade.quantity,
            "entry_price": trade.entry_price,
            "current_price": trade.current_price,
            "target_price": trade.target_price,
            "stop_loss": trade.stop_loss,
            "exchange": trade.exchange,
            "product_type": trade.product_type,
            "pnl": round(trade.pnl, 2) if trade.pnl else 0,
            "pnl_percentage": round(trade.pnl_percentage, 2) if trade.pnl_percentage else 0,
            "status": trade.status,
            "exit_price": trade.exit_price,
            "exit_reason": trade.exit_reason,
            "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            "source_message": trade.source_message
        }
    
    def reset_paper_trading(self, db: Session) -> Dict[str, Any]:
        """Reset all paper trades and restore initial balance"""
        try:
            count = db.query(PaperTrade).count()
            db.query(PaperTrade).delete()
            db.commit()
            
            return {
                "status": "success",
                "message": f"Paper trading reset. Deleted {count} trades.",
                "deleted": count
            }
        except Exception as e:
            db.rollback()
            return {"status": "error", "message": str(e)}


# Global instance
paper_trading_service = PaperTradingService()
