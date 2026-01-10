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
from app.services.broker_service import broker_service, symbol_master
from app.services.symbol_resolver import get_symbol_resolver
from app.services.websocket_manager import WebSocketManager
from app.core.logging_config import get_logger

logger = get_logger("trades_api")

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
    
    # === Symbol Resolution at Creation ===
    # Resolve generic signal symbol to correct broker-compatible format
    original_symbol = trade.symbol.upper()
    resolved_symbol = original_symbol
    notes = None
    
    resolver = get_symbol_resolver(symbol_master)
    resolution_result = resolver.resolve_symbol(
        raw_symbol=original_symbol,
        exchange=trade.exchange
    )
    
    if resolution_result.get("success") and resolution_result.get("resolved_symbol"):
        resolved_symbol = resolution_result["resolved_symbol"]
        resolved_exchange = resolution_result.get("exchange", trade.exchange)  # Use resolved exchange if available
        if resolved_symbol != original_symbol:
            notes = f"Symbol resolved: {original_symbol} → {resolved_symbol}"
            if resolved_exchange != trade.exchange:
                notes += f" (exchange: {resolved_exchange})"
            logger.info(f"🔍 {notes}")
    else:
        resolved_exchange = trade.exchange
    
    db_trade = Trade(
        message_id=trade.message_id,
        symbol=resolved_symbol,  # Use resolved symbol
        action=trade.action.upper(),  # Normalize action
        quantity=quantity,
        entry_price=trade.entry_price,
        target_price=trade.target_price,
        stop_loss=trade.stop_loss,
        order_type=trade.order_type,
        exchange=resolved_exchange,  # Use resolved exchange (BFO for SENSEX, etc.)
        product_type=trade.product_type,
        status="PENDING",
        notes=notes  # Store resolution info
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


# ====== Static routes (must be defined before /{trade_id}) ======

@router.post("/resolve-symbol")
async def resolve_symbol(
    symbol: str,
    exchange: str = "NSE"
):
    """
    Test symbol resolution - convert generic signal name to broker-compatible format
    
    Examples:
    - symbol="RELIANCE" → "RELIANCE-EQ"
    - symbol="NIFTY 25000 CE" → "NIFTY25DEC25000CE"
    - symbol="TCS" → "TCS-EQ"
    """
    resolver = get_symbol_resolver(symbol_master)
    result = resolver.resolve_symbol(raw_symbol=symbol, exchange=exchange)
    
    return {
        "original": symbol,
        "resolved": result.get("resolved_symbol"),
        "token": result.get("token"),
        "exchange": result.get("exchange"),
        "instrument_type": result.get("instrument_type"),
        "success": result.get("success"),
        "message": result.get("message")
    }


@router.get("/search-symbols")
async def search_symbols(
    query: str,
    exchange: str = "NSE",
    limit: int = 10
):
    """
    Search for symbols matching a query
    Returns matching instruments from the symbol master
    """
    if not symbol_master:
        raise HTTPException(status_code=500, detail="Symbol master not initialized")
    
    results = symbol_master.search_symbol(query, exchange, limit=limit)
    return {
        "query": query,
        "exchange": exchange,
        "count": len(results),
        "results": results
    }

# ====== Dynamic routes (/{trade_id} patterns) ======

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
    # Force refresh critical broker data before trade execution
    from app.api.broker import force_refresh_broker_data
    force_refresh_broker_data()
    
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if not broker_service.is_logged_in:
        trade.status = "FAILED"
        trade.error_message = "Broker not logged in"
        db.commit()
        raise HTTPException(status_code=400, detail="Broker not logged in")
    
    # === Symbol Resolution ===
    # Resolve generic signal symbol to correct broker-compatible format
    resolver = get_symbol_resolver(symbol_master)
    original_symbol = trade.symbol
    resolution_result = resolver.resolve_symbol(
        raw_symbol=trade.symbol,
        exchange=trade.exchange
    )
    
    if resolution_result.get("success"):
        resolved_symbol = resolution_result["resolved_symbol"]
        resolved_exchange = resolution_result.get("exchange", trade.exchange)  # Get resolved exchange
        logger.info(f"🔍 Symbol resolved: {original_symbol} → {resolved_symbol} (exchange: {resolved_exchange})")
        
        # Update trade with resolved symbol and exchange if different
        if resolved_symbol != original_symbol:
            trade.notes = f"Symbol resolved: {original_symbol} → {resolved_symbol}"
            trade.symbol = resolved_symbol
        if resolved_exchange != trade.exchange:
            trade.notes = (trade.notes or "") + f" (exchange: {trade.exchange} → {resolved_exchange})"
            trade.exchange = resolved_exchange  # CRITICAL: Update exchange for BFO/BSE options
        db.flush()  # Update in session
    else:
        logger.warning(f"⚠️ Symbol resolution warning: {resolution_result.get('message')}")
        # Continue with original symbol, but log the warning
    
    # Place order with resolved symbol AND exchange
    result = broker_service.place_order(
        symbol=trade.symbol,
        action=trade.action,
        quantity=trade.quantity,
        exchange=trade.exchange,  # Now uses BFO for SENSEX, etc.
        order_type=trade.order_type,
        product_type=trade.product_type,
        price=trade.entry_price
    )
    
    if result['status'] == 'success':
        trade.order_id = result['order_id']
        trade.status = "SUBMITTED"  # Changed from EXECUTED - order is submitted, not executed yet
        trade.execution_time = datetime.utcnow()
        
        # Immediately check actual order status from broker
        import asyncio
        await asyncio.sleep(1)  # Brief delay to let broker process
        order_status = broker_service.get_order_status(result['order_id'])
        
        if order_status.get('status') == 'success':
            trade.broker_status = order_status.get('broker_status')
            trade.filled_quantity = order_status.get('filled_quantity')
            trade.average_price = order_status.get('average_price')
            trade.last_status_check = datetime.utcnow()
            
            # Update internal status based on broker status
            internal_status = order_status.get('internal_status', 'PENDING')
            if internal_status == 'EXECUTED':
                trade.status = "EXECUTED"
                trade.execution_price = order_status.get('average_price') or trade.entry_price
            elif internal_status == 'REJECTED':
                trade.status = "REJECTED"
                trade.broker_rejection_reason = order_status.get('rejection_reason')
                trade.error_message = order_status.get('rejection_reason')
            elif internal_status == 'CANCELLED':
                trade.status = "CANCELLED"
            else:
                trade.status = "OPEN"  # Order is open/pending at broker
        
        # Notify via WebSocket
        if ws_manager:
            await ws_manager.broadcast({
                "type": "trade_status_update",
                "data": {
                    "trade_id": trade.id,
                    "order_id": result['order_id'],
                    "status": trade.status,
                    "broker_status": trade.broker_status,
                    "rejection_reason": trade.broker_rejection_reason
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


@router.post("/{trade_id}/execute-bracket")
async def execute_bracket_order(
    trade_id: int,
    trailing_sl: float = None,
    db: Session = Depends(get_db)
):
    """
    Execute a trade as a bracket order with entry, target, and stop-loss.
    
    Bracket orders:
    - Entry order at the trade's entry_price
    - Target order at target_price (profit booking)
    - Stop-loss order at stop_loss price
    
    Args:
        trade_id: ID of the trade to execute
        trailing_sl: Optional trailing stop-loss in points
    
    Note: Requires entry_price, target_price, and stop_loss to be set on the trade.
    """
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    # Validate required fields for bracket order
    if not trade.entry_price:
        raise HTTPException(status_code=400, detail="Entry price is required for bracket orders")
    if not trade.target_price:
        raise HTTPException(status_code=400, detail="Target price is required for bracket orders")
    if not trade.stop_loss:
        raise HTTPException(status_code=400, detail="Stop loss is required for bracket orders")
    
    if not broker_service.is_logged_in:
        trade.status = "FAILED"
        trade.error_message = "Broker not logged in"
        db.commit()
        raise HTTPException(status_code=400, detail="Broker not logged in")
    
    # Place bracket order
    result = broker_service.place_bracket_order(
        symbol=trade.symbol,
        action=trade.action,
        quantity=trade.quantity,
        entry_price=trade.entry_price,
        target_price=trade.target_price,
        stop_loss=trade.stop_loss,
        exchange=trade.exchange,
        product_type=trade.product_type,
        trailing_sl=trailing_sl
    )
    
    if result.get('status') == 'success':
        trade.order_id = result.get('order_id')
        trade.status = "SUBMITTED"
        trade.order_variety = "BRACKET"  # Track that this is a bracket order
        trade.execution_time = datetime.utcnow()
        trade.notes = f"Bracket order: Entry={trade.entry_price}, Target={trade.target_price}, SL={trade.stop_loss}"
        
        if ws_manager:
            await ws_manager.broadcast({
                "type": "bracket_order_placed",
                "data": {
                    "trade_id": trade.id,
                    "order_id": result.get('order_id'),
                    "entry_price": trade.entry_price,
                    "target_price": trade.target_price,
                    "stop_loss": trade.stop_loss
                }
            })
    else:
        trade.status = "FAILED"
        trade.error_message = result.get('message', 'Bracket order failed')
    
    db.commit()
    db.refresh(trade)
    
    return {
        "trade_id": trade.id,
        "status": trade.status,
        "order_id": trade.order_id,
        "order_variety": "BRACKET",
        "message": result.get('message'),
        "entry_price": trade.entry_price,
        "target_price": trade.target_price,
        "stop_loss": trade.stop_loss
    }


@router.get("/stats/summary")
async def get_trade_stats(db: Session = Depends(get_db)):
    """Get trade statistics - optimized single query"""
    from datetime import date
    from sqlalchemy import func, case
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    
    # Single query with conditional counts (much faster than 7 separate queries)
    stats = db.query(
        func.count(Trade.id).label('total'),
        func.sum(case((Trade.status == "EXECUTED", 1), else_=0)).label('executed'),
        func.sum(case((Trade.status == "PENDING", 1), else_=0)).label('pending'),
        func.sum(case((Trade.status == "FAILED", 1), else_=0)).label('failed'),
        func.sum(case((Trade.status == "REJECTED", 1), else_=0)).label('rejected'),
        func.sum(case((Trade.status == "OPEN", 1), else_=0)).label('open'),
        func.sum(case((Trade.created_at >= today_start, 1), else_=0)).label('today')
    ).first()
    
    # Get settings for limit info
    settings = db.query(AppSettings).first()
    max_trades = settings.max_trades_per_day if settings else 10
    today_count = stats.today or 0
    
    return {
        "total": stats.total or 0,
        "executed": stats.executed or 0,
        "pending": stats.pending or 0,
        "failed": stats.failed or 0,
        "rejected": stats.rejected or 0,
        "open": stats.open or 0,
        "today": today_count,
        "limit": max_trades,
        "remaining": max(0, max_trades - today_count)
    }


@router.post("/sync-status")
async def sync_all_order_statuses(db: Session = Depends(get_db)):
    """Sync status of all open/submitted orders from broker"""
    if not broker_service.is_logged_in:
        raise HTTPException(status_code=400, detail="Broker not logged in")
    
    # Get all trades with order_id that are not in final state
    trades_to_sync = db.query(Trade).filter(
        Trade.order_id.isnot(None),
        Trade.status.in_(["SUBMITTED", "OPEN", "PENDING", "EXECUTED"])  # Include EXECUTED to verify
    ).all()
    
    if not trades_to_sync:
        return {"status": "success", "message": "No trades to sync", "updated": 0}
    
    # Get all orders from broker
    order_book = broker_service.get_all_order_statuses()
    
    if order_book.get('status') != 'success':
        raise HTTPException(status_code=500, detail=order_book.get('message', 'Failed to fetch orders'))
    
    broker_orders = {str(o['order_id']): o for o in order_book.get('orders', [])}
    
    updated_count = 0
    updates = []
    
    for trade in trades_to_sync:
        broker_order = broker_orders.get(str(trade.order_id))
        
        if broker_order:
            old_status = trade.status
            broker_status = broker_order.get('broker_status')
            internal_status = broker_order.get('internal_status')
            
            # Update trade with broker data
            trade.broker_status = broker_status
            trade.filled_quantity = broker_order.get('filled_quantity')
            trade.average_price = broker_order.get('average_price')
            trade.last_status_check = datetime.utcnow()
            
            # Update internal status if changed
            if internal_status == 'EXECUTED' and trade.status != 'EXECUTED':
                trade.status = "EXECUTED"
                trade.execution_price = broker_order.get('average_price') or trade.entry_price
            elif internal_status == 'REJECTED' and trade.status != 'REJECTED':
                trade.status = "REJECTED"
                trade.broker_rejection_reason = broker_order.get('rejection_reason')
                trade.error_message = broker_order.get('rejection_reason')
            elif internal_status == 'CANCELLED' and trade.status != 'CANCELLED':
                trade.status = "CANCELLED"
            elif internal_status == 'OPEN' and trade.status not in ['EXECUTED', 'REJECTED', 'CANCELLED']:
                trade.status = "OPEN"
            
            if old_status != trade.status:
                updated_count += 1
                updates.append({
                    "trade_id": trade.id,
                    "order_id": trade.order_id,
                    "old_status": old_status,
                    "new_status": trade.status,
                    "broker_status": broker_status,
                    "rejection_reason": trade.broker_rejection_reason
                })
    
    db.commit()
    
    # Notify via WebSocket about updates
    if ws_manager and updates:
        await ws_manager.broadcast({
            "type": "trades_synced",
            "data": {
                "updated_count": updated_count,
                "updates": updates
            }
        })
    
    return {
        "status": "success",
        "message": f"Synced {len(trades_to_sync)} trades, {updated_count} updated",
        "updated": updated_count,
        "updates": updates
    }


@router.post("/{trade_id}/refresh-status")
async def refresh_trade_status(trade_id: int, db: Session = Depends(get_db)):
    """Refresh status of a specific trade from broker"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if not trade.order_id:
        raise HTTPException(status_code=400, detail="Trade has no broker order ID")
    
    if not broker_service.is_logged_in:
        raise HTTPException(status_code=400, detail="Broker not logged in")
    
    # Get order status from broker
    order_status = broker_service.get_order_status(trade.order_id)
    
    if order_status.get('status') != 'success':
        raise HTTPException(status_code=500, detail=order_status.get('message', 'Failed to fetch order status'))
    
    old_status = trade.status
    
    # Update trade with broker data
    trade.broker_status = order_status.get('broker_status')
    trade.filled_quantity = order_status.get('filled_quantity')
    trade.average_price = order_status.get('average_price')
    trade.last_status_check = datetime.utcnow()
    
    # Update internal status
    internal_status = order_status.get('internal_status')
    if internal_status == 'EXECUTED':
        trade.status = "EXECUTED"
        trade.execution_price = order_status.get('average_price') or trade.entry_price
    elif internal_status == 'REJECTED':
        trade.status = "REJECTED"
        trade.broker_rejection_reason = order_status.get('rejection_reason')
        trade.error_message = order_status.get('rejection_reason')
    elif internal_status == 'CANCELLED':
        trade.status = "CANCELLED"
    elif internal_status == 'OPEN':
        trade.status = "OPEN"
    
    db.commit()
    db.refresh(trade)
    
    # Notify via WebSocket
    if ws_manager and old_status != trade.status:
        await ws_manager.broadcast({
            "type": "trade_status_update",
            "data": {
                "trade_id": trade.id,
                "order_id": trade.order_id,
                "old_status": old_status,
                "new_status": trade.status,
                "broker_status": trade.broker_status,
                "rejection_reason": trade.broker_rejection_reason
            }
        })
    
    return trade
