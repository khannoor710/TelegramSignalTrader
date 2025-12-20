"""
Trades API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.schemas.schemas import (
    TradeCreate,
    TradeResponse,
    TradeApproval
)
from app.models.models import Trade, AppSettings
from app.services.broker_service import broker_service
from app.services.websocket_manager import WebSocketManager

router = APIRouter()

# This will be injected from main.py
ws_manager: WebSocketManager = None


def check_trade_limits(db: Session) -> dict:
    """Check if trade limits are exceeded"""
    settings = db.query(AppSettings).first()
    if not settings:
        return {"allowed": True}
    
    # Count trades created today
    from datetime import date
    today = date.today()
    today_trades = db.query(Trade).filter(
        Trade.created_at >= datetime(today.year, today.month, today.day)
    ).count()
    
    if today_trades >= settings.max_trades_per_day:
        return {
            "allowed": False, 
            "reason": f"Daily trade limit ({settings.max_trades_per_day}) reached. Today's trades: {today_trades}"
        }
    
    return {"allowed": True, "remaining": settings.max_trades_per_day - today_trades}


@router.post("/", response_model=TradeResponse)
async def create_trade(trade: TradeCreate, db: Session = Depends(get_db)):
    """Create a new trade"""
    # Check trade limits
    limit_check = check_trade_limits(db)
    if not limit_check.get("allowed"):
        raise HTTPException(status_code=429, detail=limit_check.get("reason"))
    
    # Get default quantity from settings if not provided
    settings = db.query(AppSettings).first()
    quantity = trade.quantity
    if quantity <= 0 and settings:
        quantity = settings.default_quantity
    
    db_trade = Trade(
        message_id=trade.message_id,
        symbol=trade.symbol.upper(),  # Normalize symbol to uppercase
        action=trade.action.upper(),  # Normalize action
        quantity=quantity,
        entry_price=trade.entry_price,
        target_price=trade.target_price,
        stop_loss=trade.stop_loss,
        order_type=trade.order_type,
        exchange=trade.exchange,
        product_type=trade.product_type,
        status="PENDING"
    )
    
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    
    # Check if auto-trade is enabled and manual approval is not required
    if settings and settings.auto_trade_enabled and not settings.require_manual_approval:
        # Execute trade automatically
        result = await execute_trade_internal(db_trade.id, db)
        return result
    
    # Notify via WebSocket
    if ws_manager:
        await ws_manager.broadcast({
            "type": "new_trade",
            "data": {
                "trade_id": db_trade.id,
                "symbol": db_trade.symbol,
                "action": db_trade.action,
                "status": db_trade.status
            }
        })
    
    return db_trade


@router.get("/", response_model=List[TradeResponse])
async def get_trades(
    limit: int = 100,
    skip: int = 0,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Get trades"""
    query = db.query(Trade)
    
    if status:
        query = query.filter(Trade.status == status)
    
    trades = query.order_by(Trade.created_at.desc()).offset(skip).limit(limit).all()
    return trades


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """Get specific trade"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.post("/approve")
async def approve_trade(approval: TradeApproval, db: Session = Depends(get_db)):
    """Approve or reject a trade"""
    trade = db.query(Trade).filter(Trade.id == approval.trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if trade.status != "PENDING":
        raise HTTPException(status_code=400, detail="Trade is not pending approval")
    
    if approval.approved:
        # Execute the trade
        result = await execute_trade_internal(approval.trade_id, db)
        if approval.notes:
            trade.notes = approval.notes
            db.commit()
        return result
    else:
        # Reject the trade
        trade.status = "REJECTED"
        trade.notes = approval.notes
        db.commit()
        
        if ws_manager:
            await ws_manager.broadcast({
                "type": "trade_rejected",
                "data": {"trade_id": trade.id}
            })
        
        return {"status": "success", "message": "Trade rejected"}


async def execute_trade_internal(trade_id: int, db: Session):
    """Internal function to execute trade"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if not broker_service.is_logged_in:
        trade.status = "FAILED"
        trade.error_message = "Broker not logged in"
        db.commit()
        raise HTTPException(status_code=400, detail="Broker not logged in")
    
    # Place order
    result = broker_service.place_order(
        symbol=trade.symbol,
        action=trade.action,
        quantity=trade.quantity,
        exchange=trade.exchange,
        order_type=trade.order_type,
        product_type=trade.product_type,
        price=trade.entry_price
    )
    
    if result['status'] == 'success':
        trade.status = "EXECUTED"
        trade.order_id = result['order_id']
        trade.execution_time = datetime.utcnow()
        trade.execution_price = trade.entry_price  # Will be updated when order fills
        
        # Notify via WebSocket
        if ws_manager:
            await ws_manager.broadcast({
                "type": "trade_executed",
                "data": {
                    "trade_id": trade.id,
                    "order_id": result['order_id']
                }
            })
    else:
        trade.status = "FAILED"
        trade.error_message = result['message']
    
    db.commit()
    db.refresh(trade)
    
    return trade


@router.post("/{trade_id}/execute", response_model=TradeResponse)
async def execute_trade(trade_id: int, db: Session = Depends(get_db)):
    """Manually execute a trade"""
    return await execute_trade_internal(trade_id, db)


@router.get("/stats/summary")
async def get_trade_stats(db: Session = Depends(get_db)):
    """Get trade statistics"""
    from datetime import date
    today = date.today()
    
    total_trades = db.query(Trade).count()
    executed_trades = db.query(Trade).filter(Trade.status == "EXECUTED").count()
    pending_trades = db.query(Trade).filter(Trade.status == "PENDING").count()
    failed_trades = db.query(Trade).filter(Trade.status == "FAILED").count()
    
    # Today's trades
    today_trades = db.query(Trade).filter(
        Trade.created_at >= datetime(today.year, today.month, today.day)
    ).count()
    
    # Get settings for limit info
    settings = db.query(AppSettings).first()
    max_trades = settings.max_trades_per_day if settings else 10
    
    return {
        "total": total_trades,
        "executed": executed_trades,
        "pending": pending_trades,
        "failed": failed_trades,
        "today": today_trades,
        "limit": max_trades,
        "remaining": max(0, max_trades - today_trades)
    }
