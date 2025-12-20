"""
Message repository for Telegram message database operations.
Encapsulates query logic for messages and signals.
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.models.models import TelegramMessage


class MessageRepository:
    """Repository for Telegram message CRUD operations."""
    
    @staticmethod
    def create(db: Session, message_data: dict) -> TelegramMessage:
        """Create a new message record."""
        message = TelegramMessage(**message_data)
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    
    @staticmethod
    def get_by_id(db: Session, message_id: int) -> Optional[TelegramMessage]:
        """Get message by ID."""
        return db.query(TelegramMessage).filter(TelegramMessage.id == message_id).first()
    
    @staticmethod
    def get_all(
        db: Session,
        limit: int = 50,
        skip: int = 0,
        unprocessed_only: bool = False
    ) -> List[TelegramMessage]:
        """Get all messages with optional filtering."""
        query = db.query(TelegramMessage)
        
        if unprocessed_only:
            query = query.filter(TelegramMessage.is_processed.is_(False))
        
        return query.order_by(TelegramMessage.timestamp.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_chat(
        db: Session,
        chat_id: str,
        limit: int = 50,
        skip: int = 0,
        signals_only: bool = False
    ) -> List[TelegramMessage]:
        """Get messages from a specific chat."""
        query = db.query(TelegramMessage).filter(TelegramMessage.chat_id == chat_id)
        
        if signals_only:
            query = query.filter(TelegramMessage.parsed_signal.isnot(None))
        
        return query.order_by(TelegramMessage.timestamp.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_unprocessed_signals(db: Session) -> List[TelegramMessage]:
        """Get all unprocessed messages with parsed signals."""
        return db.query(TelegramMessage).filter(
            TelegramMessage.parsed_signal.isnot(None),
            TelegramMessage.is_processed.is_(False)
        ).order_by(TelegramMessage.timestamp).all()
    
    @staticmethod
    def mark_processed(db: Session, message_id: int) -> Optional[TelegramMessage]:
        """Mark a message as processed."""
        message = MessageRepository.get_by_id(db, message_id)
        if not message:
            return None
        
        message.is_processed = True
        db.commit()
        db.refresh(message)
        return message
    
    @staticmethod
    def check_duplicate(db: Session, chat_id: str, message_id: int) -> bool:
        """Check if message already exists."""
        return db.query(TelegramMessage).filter(
            TelegramMessage.chat_id == chat_id,
            TelegramMessage.message_id == message_id
        ).first() is not None
    
    @staticmethod
    def get_stats(db: Session) -> dict:
        """Get message statistics."""
        total = db.query(TelegramMessage).count()
        with_signals = db.query(TelegramMessage).filter(
            TelegramMessage.parsed_signal.isnot(None)
        ).count()
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
    
    @staticmethod
    def delete_all(db: Session) -> int:
        """Delete all messages (use with caution)."""
        count = db.query(TelegramMessage).count()
        db.query(TelegramMessage).delete()
        db.commit()
        return count
    
    @staticmethod
    def bulk_create(db: Session, messages: List[dict]) -> int:
        """Bulk insert messages (skips duplicates)."""
        created = 0
        for msg_data in messages:
            # Check for duplicate
            if not MessageRepository.check_duplicate(
                db, 
                msg_data.get('chat_id'), 
                msg_data.get('message_id')
            ):
                MessageRepository.create(db, msg_data)
                created += 1
        
        return created
