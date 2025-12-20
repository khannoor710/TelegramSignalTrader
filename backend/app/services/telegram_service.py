"""
Telegram service for reading messages from groups
"""
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from typing import Optional, List
import json
from datetime import datetime

from app.core.database import SessionLocal
from app.models.models import TelegramMessage, TelegramConfig
from app.services.signal_parser import SignalParser
from app.services.websocket_manager import WebSocketManager
from app.core.logging_config import get_logger

logger = get_logger("telegram_service")


class TelegramService:
    def __init__(self, ws_manager: WebSocketManager):
        self.client: Optional[TelegramClient] = None
        self.ws_manager = ws_manager
        self.signal_parser = SignalParser()
        self.monitored_chats: List[str] = []
        self.is_connected = False
        
    async def initialize(self, api_id: str, api_hash: str, phone: str, session_string: Optional[str] = None):
        """Initialize Telegram client"""
        try:
            if session_string:
                self.client = TelegramClient(StringSession(session_string), api_id, api_hash)
            else:
                self.client = TelegramClient(StringSession(), api_id, api_hash)
            
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                await self.client.send_code_request(phone)
                return {"status": "code_sent", "message": "Verification code sent to your phone"}
            
            self.is_connected = True
            return {"status": "authorized", "message": "Already authorized"}
            
        except Exception as e:
            logger.error(f"Error initializing Telegram client: {e}")
            return {"status": "error", "message": str(e)}
    
    async def verify_code(self, phone: str, code: str):
        """Verify the code sent to phone"""
        try:
            await self.client.sign_in(phone, code)
            session_string = self.client.session.save()
            self.is_connected = True
            return {"status": "success", "session_string": session_string}
        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            return {"status": "error", "message": str(e)}
    
    async def start(self):
        """Start the Telegram service"""
        db = SessionLocal()
        try:
            config = db.query(TelegramConfig).filter(TelegramConfig.is_active).first()
            if not config:
                logger.warning("No active Telegram configuration found")
                return
            
            if config.session_string:
                self.client = TelegramClient(
                    StringSession(config.session_string),
                    config.api_id,
                    config.api_hash
                )
                await self.client.connect()
                
                # Parse monitored chats - convert to integers for Telethon
                raw_chats = json.loads(config.monitored_chats) if config.monitored_chats else []
                self.monitored_chats = [int(chat_id) for chat_id in raw_chats]
                
                # Set up message handler - use None if no chats to monitor ALL
                chats_to_monitor = self.monitored_chats if self.monitored_chats else None
                
                @self.client.on(events.NewMessage(chats=chats_to_monitor))
                async def message_handler(event):
                    await self.handle_new_message(event)
                
                await self.client.start()
                self.is_connected = True
                logger.info(f"Telegram client connected, monitoring {len(self.monitored_chats)} chats: {self.monitored_chats}")
                
        except Exception as e:
            logger.error(f"Error starting Telegram service: {e}")
        finally:
            db.close()
    
    async def reload(self):
        """Reload Telegram service with updated configuration"""
        logger.info("Reloading Telegram service...")
        await self.stop()
        await self.start()
        return self.get_connection_status()
    
    async def stop(self):
        """Stop the Telegram service"""
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
            logger.info("Telegram client disconnected")
    
    def get_connection_status(self) -> dict:
        """Get current connection status"""
        return {
            "is_connected": self.is_connected,
            "client_initialized": self.client is not None,
            "monitored_chats_count": len(self.monitored_chats)
        }
    
    async def handle_new_message(self, event):
        """Handle new message from monitored chats"""
        db = SessionLocal()
        try:
            chat = await event.get_chat()
            sender = await event.get_sender()
            
            chat_name = getattr(chat, 'title', str(event.chat_id))
            sender_name = getattr(sender, 'username', None) or getattr(sender, 'first_name', 'Unknown')
            message_text = event.message.text or ""
            
            # Store message in database
            message = TelegramMessage(
                chat_id=str(event.chat_id),
                chat_name=chat_name,
                message_id=event.id,
                message_text=message_text,
                sender=sender_name,
                timestamp=datetime.utcnow()
            )
            
            # Try to parse trading signal
            parsed_signal = None
            if message_text:
                parsed_signal = self.signal_parser.parse_message(message_text)
                if parsed_signal:
                    message.parsed_signal = json.dumps(parsed_signal)
                    message.is_processed = False
            
            db.add(message)
            db.commit()
            db.refresh(message)
            
            # Broadcast message via WebSocket (all messages, not just signals)
            await self.ws_manager.broadcast({
                "type": "new_message",
                "data": {
                    "id": message.id,
                    "message_text": message_text,
                    "chat_name": chat_name,
                    "chat_id": str(event.chat_id),
                    "sender": sender_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "parsed_signal": parsed_signal,
                    "is_signal": parsed_signal is not None
                }
            })
            
            logger.info(f"New message from {chat_name}: {message_text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def get_monitored_chats(self) -> List[dict]:
        """Get list of all available chats"""
        if not self.client or not self.client.is_connected():
            return []
        
        try:
            dialogs = await self.client.get_dialogs()
            chats = []
            for dialog in dialogs:
                if dialog.is_group or dialog.is_channel:
                    chats.append({
                        "id": dialog.id,
                        "name": dialog.name,
                        "username": dialog.entity.username if hasattr(dialog.entity, 'username') else None
                    })
            return chats
        except Exception as e:
            logger.error(f"Error getting chats: {e}")
            return []
    
    async def fetch_historic_messages(
        self, 
        chat_id: str, 
        limit: int = 100, 
        offset_date: datetime = None
    ) -> List[dict]:
        """
        Fetch historic messages from a specific chat.
        
        Args:
            chat_id: The chat ID to fetch messages from
            limit: Maximum number of messages to fetch (default 100)
            offset_date: Fetch messages before this date (optional)
        
        Returns:
            List of message dictionaries
        """
        if not self.client or not self.client.is_connected():
            logger.warning("Telegram client not connected")
            return []
        
        try:
            # Convert chat_id to int if needed
            try:
                chat_entity = int(chat_id)
            except ValueError:
                chat_entity = chat_id
            
            messages = []
            async for message in self.client.iter_messages(
                chat_entity, 
                limit=limit,
                offset_date=offset_date
            ):
                if message.text:
                    # Get sender info
                    sender = await message.get_sender()
                    sender_name = None
                    if sender:
                        sender_name = getattr(sender, 'username', None) or getattr(sender, 'first_name', 'Unknown')
                    
                    # Try to parse as trading signal
                    parsed_signal = self.signal_parser.parse_message(message.text)
                    
                    messages.append({
                        "message_id": message.id,
                        "chat_id": str(chat_id),
                        "message_text": message.text,
                        "sender": sender_name,
                        "timestamp": message.date.isoformat() if message.date else None,
                        "parsed_signal": parsed_signal,
                        "is_signal": parsed_signal is not None
                    })
            
            logger.info(f"Fetched {len(messages)} historic messages from chat {chat_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching historic messages: {e}")
            return []
    
    async def save_historic_messages_to_db(
        self, 
        chat_id: str, 
        limit: int = 100, 
        offset_date: datetime = None
    ) -> dict:
        """
        Fetch historic messages and save them to database.
        
        Returns:
            Summary of saved messages
        """
        messages = await self.fetch_historic_messages(chat_id, limit, offset_date)
        
        if not messages:
            return {"saved": 0, "skipped": 0, "signals": 0}
        
        db = SessionLocal()
        saved = 0
        skipped = 0
        signals = 0
        
        try:
            # Get chat name
            try:
                chat_entity = int(chat_id)
                entity = await self.client.get_entity(chat_entity)
                chat_name = getattr(entity, 'title', str(chat_id))
            except Exception:
                chat_name = str(chat_id)
            
            for msg in messages:
                # Check if message already exists
                existing = db.query(TelegramMessage).filter(
                    TelegramMessage.chat_id == str(chat_id),
                    TelegramMessage.message_id == msg["message_id"]
                ).first()
                
                if existing:
                    skipped += 1
                    continue
                
                # Create new message
                db_message = TelegramMessage(
                    chat_id=str(chat_id),
                    chat_name=chat_name,
                    message_id=msg["message_id"],
                    message_text=msg["message_text"],
                    sender=msg["sender"] or "Unknown",
                    timestamp=datetime.fromisoformat(msg["timestamp"].replace('Z', '+00:00')) if msg["timestamp"] else datetime.utcnow()
                )
                
                if msg["parsed_signal"]:
                    db_message.parsed_signal = json.dumps(msg["parsed_signal"])
                    db_message.is_processed = False
                    signals += 1
                
                db.add(db_message)
                saved += 1
            
            db.commit()
            logger.info(f"Saved {saved} messages, skipped {skipped} duplicates, found {signals} signals")
            
            return {
                "saved": saved,
                "skipped": skipped,
                "signals": signals
            }
            
        except Exception as e:
            logger.error(f"Error saving historic messages: {e}")
            db.rollback()
            return {"saved": 0, "skipped": 0, "signals": 0, "error": str(e)}
        finally:
            db.close()
