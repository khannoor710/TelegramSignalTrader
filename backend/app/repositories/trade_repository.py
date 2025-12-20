"""
Trade repository for encapsulating trade-related database operations.
Separates data access logic from API route handlers.
"""
from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import Trade


class TradeRepository:
    """Repository for trade CRUD operations."""
    
    @staticmethod
    def create(db: Session, trade_data: dict) -> Trade:
        """Create a new trade record."""
        trade = Trade(**trade_data)
        db.add(trade)
        db.commit()
        db.refresh(trade)
        return trade
    
    @staticmethod
    def get_by_id(db: Session, trade_id: int) -> Optional[Trade]:
        """Get trade by ID."""
        return db.query(Trade).filter(Trade.id == trade_id).first()
    
    @staticmethod
    def get_all(
        db: Session, 
        limit: int = 100, 
        skip: int = 0, 
        status: Optional[str] = None
    ) -> List[Trade]:
        """Get all trades with optional filtering."""
        query = db.query(Trade)
        
        if status:
            query = query.filter(Trade.status == status)
        
        return query.order_by(Trade.created_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_pending_trades(db: Session) -> List[Trade]:
        """Get all pending trades awaiting approval."""
        return db.query(Trade).filter(Trade.status == "PENDING").order_by(Trade.created_at).all()
    
    @staticmethod
    def get_todays_trades(db: Session) -> List[Trade]:
        """Get all trades created today."""
        today = date.today()
        return db.query(Trade).filter(
            Trade.created_at >= datetime(today.year, today.month, today.day)
        ).all()
    
    @staticmethod
    def count_todays_trades(db: Session) -> int:
        """Count trades created today."""
        today = date.today()
        return db.query(Trade).filter(
            Trade.created_at >= datetime(today.year, today.month, today.day)
        ).count()
    
    @staticmethod
    def get_stats(db: Session) -> dict:
        """Get trade statistics."""
        today = date.today()
        
        total_trades = db.query(Trade).count()
        executed_trades = db.query(Trade).filter(Trade.status == "EXECUTED").count()
        pending_trades = db.query(Trade).filter(Trade.status == "PENDING").count()
        failed_trades = db.query(Trade).filter(Trade.status == "FAILED").count()
        
        today_trades = db.query(Trade).filter(
            Trade.created_at >= datetime(today.year, today.month, today.day)
        ).count()
        
        return {
            "total": total_trades,
            "executed": executed_trades,
            "pending": pending_trades,
            "failed": failed_trades,
            "today": today_trades,
        }
    
    @staticmethod
    def update_status(
        db: Session, 
        trade_id: int, 
        status: str, 
        order_id: Optional[str] = None,
        execution_price: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> Optional[Trade]:
        """Update trade status and execution details."""
        trade = TradeRepository.get_by_id(db, trade_id)
        if not trade:
            return None
        
        trade.status = status
        if order_id:
            trade.order_id = order_id
        if execution_price:
            trade.execution_price = execution_price
        if status == "EXECUTED":
            trade.execution_time = datetime.utcnow()
        if error_message:
            trade.error_message = error_message
        
        db.commit()
        db.refresh(trade)
        return trade
    
    @staticmethod
    def delete_all(db: Session) -> int:
        """Delete all trades (use with caution)."""
        count = db.query(Trade).count()
        db.query(Trade).delete()
        db.commit()
        return count
