"""
Paper Trading API endpoints with AI-powered signal parsing
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.services.paper_trading_service import paper_trading_service
from app.services.signal_parser import SignalParser
from app.services.broker_service import symbol_master

router = APIRouter()
signal_parser = SignalParser(prefer_ai=True)


class PaperTradeRequest(BaseModel):
    symbol: str
    action: str  # BUY or SELL
    quantity: int = 1
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    exchange: str = "NSE"
    product_type: str = "INTRADAY"


class SignalTestRequest(BaseModel):
    message: str


@router.get("/ai-status")
async def get_ai_status():
    """Check if AI signal parsing is enabled"""
    return {
        "ai_enabled": signal_parser.is_ai_enabled,
        "mode": "Gemini AI" if signal_parser.is_ai_enabled else "Regex",
        "info": "Set GEMINI_API_KEY environment variable to enable AI parsing" if not signal_parser.is_ai_enabled else "Google Gemini AI parsing active"
    }


@router.get("/balance")
async def get_paper_balance(db: Session = Depends(get_db)):
    """Get current paper trading balance and P&L summary"""
    return paper_trading_service.get_balance(db)


@router.post("/order")
async def place_paper_order(order: PaperTradeRequest, db: Session = Depends(get_db)):
    """Place a paper trade order"""
    result = paper_trading_service.place_order(
        symbol=order.symbol,
        action=order.action,
        quantity=order.quantity,
        entry_price=order.entry_price,
        target_price=order.target_price,
        stop_loss=order.stop_loss,
        exchange=order.exchange,
        product_type=order.product_type,
        db=db
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.get("/positions")
async def get_paper_positions(db: Session = Depends(get_db)):
    """Get all paper trading positions"""
    return paper_trading_service.get_all_positions(db)


@router.get("/positions/open")
async def get_open_positions(db: Session = Depends(get_db)):
    """Get open paper trading positions"""
    return {"positions": paper_trading_service.get_open_positions(db)}


@router.get("/positions/closed")
async def get_closed_positions(limit: int = 50, db: Session = Depends(get_db)):
    """Get closed paper trading positions"""
    return {"positions": paper_trading_service.get_closed_positions(db, limit)}


@router.post("/positions/{trade_id}/close")
async def close_paper_position(
    trade_id: int,
    exit_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Close a paper trade position"""
    result = paper_trading_service.close_position(trade_id, exit_price, db)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/update-prices")
async def update_paper_prices(db: Session = Depends(get_db)):
    """Update current prices for all open positions (requires broker login)"""
    result = paper_trading_service.update_prices(db)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/reset")
async def reset_paper_trading(db: Session = Depends(get_db)):
    """Reset all paper trades (delete all and restore balance)"""
    return paper_trading_service.reset_paper_trading(db)


# Signal Testing Endpoints

@router.post("/test-signal")
async def test_signal_parsing(request: SignalTestRequest):
    """
    Test signal parsing using AI (if available) or regex fallback.
    Returns detailed parsing results including AI confidence and reasoning.
    """
    # Use async AI parsing
    parsed = await signal_parser.parse_message_async(request.message)
    
    if not parsed:
        return {
            "status": "no_signal",
            "message": request.message,
            "parsed": None,
            "ai_used": signal_parser.is_ai_enabled,
            "info": "No trading signal detected in this message"
        }
    
    # Validate symbol in instrument master
    token_info = None
    exchange = parsed.get('exchange', 'NSE')
    if parsed.get('symbol'):
        token = symbol_master.get_token(parsed['symbol'], exchange)
        if token:
            token_info = {"token": token, "exchange": exchange, "found": True}
        else:
            # Try other exchanges
            for exch in ['NSE', 'BSE', 'NFO']:
                if exch != exchange:
                    token = symbol_master.get_token(parsed['symbol'], exch)
                    if token:
                        token_info = {"token": token, "exchange": exch, "found": True}
                        break
            if not token_info:
                token_info = {"found": False, "warning": f"Symbol {parsed['symbol']} not found in any exchange"}
    
    return {
        "status": "signal_detected",
        "message": request.message,
        "parsed": parsed,
        "token_info": token_info,
        "ai_used": parsed.get('ai_parsed', False),
        "confidence": parsed.get('confidence'),
        "reasoning": parsed.get('reasoning')
    }


@router.post("/simulate")
async def simulate_signal_trade(
    request: SignalTestRequest,
    execute_paper: bool = Query(default=False, description="Execute as paper trade"),
    db: Session = Depends(get_db)
):
    """
    Parse a message using AI and optionally execute as paper trade.
    
    Args:
        message: The signal message to parse
        execute_paper: If True, creates a paper trade from the signal
    """
    # Use async AI parsing
    parsed = await signal_parser.parse_message_async(request.message)
    
    if not parsed:
        return {
            "step": "parse",
            "status": "failed",
            "message": "No trading signal detected",
            "original_message": request.message,
            "ai_used": signal_parser.is_ai_enabled
        }
    
    # Use exchange from AI parsing or validate
    exchange = parsed.get('exchange', 'NSE')
    token = symbol_master.get_token(parsed['symbol'], exchange)
    if not token:
        for exch in ['NSE', 'BSE', 'NFO']:
            token = symbol_master.get_token(parsed['symbol'], exch)
            if token:
                exchange = exch
                break
    
    result = {
        "step": "validate",
        "status": "success",
        "original_message": request.message,
        "parsed": parsed,
        "token": token,
        "exchange": exchange,
        "ai_used": parsed.get('ai_parsed', False),
        "confidence": parsed.get('confidence'),
        "reasoning": parsed.get('reasoning')
    }
    
    if not token:
        result["warning"] = f"Symbol {parsed['symbol']} not found in instrument master"
    
    if execute_paper:
        paper_result = paper_trading_service.place_order(
            symbol=parsed['symbol'],
            action=parsed['action'],
            quantity=parsed.get('quantity') or 1,
            entry_price=parsed.get('entry_price'),
            target_price=parsed.get('target_price'),
            stop_loss=parsed.get('stop_loss'),
            exchange=exchange,
            product_type=parsed.get('product_type', 'INTRADAY'),
            source_message=request.message,
            db=db
        )
        
        result["step"] = "execute"
        result["paper_trade"] = paper_result
    
    return result


@router.get("/stats")
async def get_paper_trading_stats(db: Session = Depends(get_db)):
    """Get paper trading statistics"""
    from app.models.models import PaperTrade
    
    balance = paper_trading_service.get_balance(db)
    
    closed_trades = db.query(PaperTrade).filter(PaperTrade.status != "OPEN").all()
    
    winning_trades = sum(1 for t in closed_trades if t.pnl and t.pnl > 0)
    losing_trades = sum(1 for t in closed_trades if t.pnl and t.pnl < 0)
    total_closed = len(closed_trades)
    
    win_rate = (winning_trades / total_closed * 100) if total_closed > 0 else 0
    
    best_trade = max(closed_trades, key=lambda t: t.pnl or 0) if closed_trades else None
    worst_trade = min(closed_trades, key=lambda t: t.pnl or 0) if closed_trades else None
    
    target_hits = sum(1 for t in closed_trades if t.status == "TARGET_HIT")
    sl_hits = sum(1 for t in closed_trades if t.status == "SL_HIT")
    
    return {
        "balance": balance,
        "ai_enabled": signal_parser.is_ai_enabled,
        "performance": {
            "total_trades": total_closed,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "target_hits": target_hits,
            "sl_hits": sl_hits
        },
        "best_trade": {
            "symbol": best_trade.symbol,
            "pnl": round(best_trade.pnl, 2),
            "pnl_percentage": round(best_trade.pnl_percentage, 2)
        } if best_trade and best_trade.pnl else None,
        "worst_trade": {
            "symbol": worst_trade.symbol,
            "pnl": round(worst_trade.pnl, 2),
            "pnl_percentage": round(worst_trade.pnl_percentage, 2)
        } if worst_trade and worst_trade.pnl else None
    }
