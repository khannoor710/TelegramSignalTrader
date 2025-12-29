"""
Telegram service for reading messages from groups
"""
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from typing import Optional, List, Dict, Any
import json
import asyncio
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
        self.last_message_time: Optional[datetime] = None
        self.connection_error: Optional[str] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._config_id: Optional[int] = None
        self._message_handler = None  # Store reference to handler for removal
        
    async def initialize(self, api_id: str, api_hash: str, phone: str, session_string: Optional[str] = None):
        """Initialize Telegram client"""
        try:
            self.connection_error = None
            
            if session_string:
                self.client = TelegramClient(StringSession(session_string), api_id, api_hash)
            else:
                self.client = TelegramClient(StringSession(), api_id, api_hash)
            
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                await self.client.send_code_request(phone)
                return {
                    "status": "code_sent", 
                    "message": "Verification code sent to your Telegram app",
                    "phone": phone
                }
            
            self.is_connected = True
            # Broadcast connection status
            await self._broadcast_status_update()
            return {
                "status": "authorized", 
                "message": "Already authorized and connected",
                "is_connected": True
            }
            
        except Exception as e:
            error_msg = str(e)
            self.connection_error = error_msg
            logger.error(f"Error initializing Telegram client: {e}")
            await self._broadcast_status_update()
            return {"status": "error", "message": self._get_user_friendly_error(error_msg)}
    
    async def verify_code(self, phone: str, code: str):
        """Verify the code sent to phone"""
        try:
            await self.client.sign_in(phone, code)
            session_string = self.client.session.save()
            self.is_connected = True
            self.connection_error = None
            await self._broadcast_status_update()
            return {
                "status": "success", 
                "session_string": session_string,
                "message": "Successfully verified! You can now select channels to monitor."
            }
        except Exception as e:
            error_msg = str(e)
            self.connection_error = error_msg
            logger.error(f"Error verifying code: {e}")
            return {"status": "error", "message": self._get_user_friendly_error(error_msg)}
    
    def _get_user_friendly_error(self, error: str) -> str:
        """Convert technical errors to user-friendly messages"""
        error_lower = error.lower()
        
        if "api_id" in error_lower or "api_hash" in error_lower:
            return "Invalid API credentials. Please check your API ID and API Hash from my.telegram.org"
        elif "phone" in error_lower:
            return "Invalid phone number format. Use international format like +911234567890"
        elif "code" in error_lower or "invalid" in error_lower:
            return "Invalid verification code. Please try again with the code from your Telegram app"
        elif "flood" in error_lower:
            return "Too many attempts. Please wait a few minutes before trying again"
        elif "network" in error_lower or "connection" in error_lower:
            return "Network error. Please check your internet connection"
        elif "session" in error_lower:
            return "Session expired. Please re-authenticate with your phone number"
        else:
            return f"Error: {error}"
    
    async def _broadcast_status_update(self):
        """Broadcast connection status to all WebSocket clients"""
        try:
            await self.ws_manager.broadcast({
                "type": "telegram_status",
                "data": self.get_connection_status()
            })
        except Exception as e:
            logger.error(f"Error broadcasting status update: {e}")
    
    async def start(self):
        """Start the Telegram service"""
        db = SessionLocal()
        try:
            config = db.query(TelegramConfig).filter(TelegramConfig.is_active).first()
            if not config:
                logger.warning("No active Telegram configuration found")
                self.connection_error = "No Telegram configuration found. Please set up Telegram credentials."
                await self._broadcast_status_update()
                return
            
            self._config_id = config.id
            
            if not config.session_string:
                logger.warning("No session string found - user needs to authenticate")
                self.connection_error = "Not authenticated. Please verify your phone number."
                await self._broadcast_status_update()
                return
            
            if config.session_string:
                self.client = TelegramClient(
                    StringSession(config.session_string),
                    config.api_id,
                    config.api_hash
                )
                await self.client.connect()
                
                # Check if still authorized
                if not await self.client.is_user_authorized():
                    logger.warning("Session expired - user needs to re-authenticate")
                    self.connection_error = "Session expired. Please re-authenticate."
                    self.is_connected = False
                    await self._broadcast_status_update()
                    return
                
                # Parse monitored chats - keep as strings initially, convert to int for Telethon
                raw_chats = json.loads(config.monitored_chats) if config.monitored_chats else []
                # Store as strings for status reporting
                self.monitored_chats = [str(chat_id) for chat_id in raw_chats]
                # Convert to integers for Telethon's event handler
                chats_to_monitor = [int(chat_id) for chat_id in raw_chats] if raw_chats else None
                
                # Define and register message handler
                async def message_handler(event):
                    await self.handle_new_message(event)
                
                self._message_handler = message_handler
                self.client.add_event_handler(message_handler, events.NewMessage(chats=chats_to_monitor))
                
                await self.client.start()
                self.is_connected = True
                self.connection_error = None
                
                # Log helpful status
                if self.monitored_chats:
                    logger.info(f"✅ Telegram client connected, monitoring {len(self.monitored_chats)} chats: {self.monitored_chats}")
                else:
                    logger.info("⚠️ Telegram client connected, but NO chats are being monitored. Select channels in the UI.")
                
                await self._broadcast_status_update()
                
        except Exception as e:
            self.connection_error = self._get_user_friendly_error(str(e))
            self.is_connected = False
            logger.error(f"Error starting Telegram service: {e}")
            await self._broadcast_status_update()
        finally:
            db.close()
    
    async def reload(self):
        """Reload Telegram service with updated configuration"""
        logger.info("🔄 Reloading Telegram service configuration...")
        db = SessionLocal()
        try:
            if not self.client or not self.is_connected:
                logger.warning("Client not connected, performing full start instead of reload")
                await self.start()
                return self.get_connection_status()
            
            # Get updated config from database
            config = db.query(TelegramConfig).filter(TelegramConfig.is_active).first()
            if not config:
                logger.warning("No active Telegram configuration found")
                return self.get_connection_status()
            
            # Update monitored chats list
            raw_chats = json.loads(config.monitored_chats) if config.monitored_chats else []
            old_count = len(self.monitored_chats)
            self.monitored_chats = [str(chat_id) for chat_id in raw_chats]
            new_count = len(self.monitored_chats)
            
            logger.info(f"📊 Monitored chats updated: {old_count} -> {new_count}")
            logger.info(f"   Chat IDs: {self.monitored_chats}")
            
            # Remove old event handler if it exists
            if self._message_handler:
                try:
                    self.client.remove_event_handler(self._message_handler)
                    logger.info("✅ Removed old message handler")
                except Exception as e:
                    logger.warning(f"Could not remove old handler: {e}")
            
            # Register new message handler with updated chat list
            chats_to_monitor = [int(chat_id) for chat_id in raw_chats] if raw_chats else None
            
            async def message_handler(event):
                await self.handle_new_message(event)
            
            self._message_handler = message_handler
            self.client.add_event_handler(message_handler, events.NewMessage(chats=chats_to_monitor))
            
            logger.info(f"✅ Telegram service reloaded - now monitoring {new_count} chats")
            if new_count == 0:
                logger.warning("⚠️  No chats being monitored! Select channels to receive messages.")
            
            await self._broadcast_status_update()
            return self.get_connection_status()
            
        except Exception as e:
            error_msg = str(e)
            self.connection_error = self._get_user_friendly_error(error_msg)
            logger.error(f"❌ Error reloading Telegram service: {e}", exc_info=True)
            await self._broadcast_status_update()
            return self.get_connection_status()
        finally:
            db.close()
    
    async def stop(self):
        """Stop the Telegram service"""
        if self.client:
            try:
                await self.client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting client: {e}")
            self.is_connected = False
            logger.info("Telegram client disconnected")
            await self._broadcast_status_update()
    
    def get_connection_status(self) -> dict:
        """Get current connection status with detailed info"""
        status = {
            "is_connected": self.is_connected,
            "client_initialized": self.client is not None,
            "monitored_chats_count": len(self.monitored_chats),
            "monitored_chats": self.monitored_chats,
            "last_message_time": self.last_message_time.isoformat() if self.last_message_time else None,
            "error": self.connection_error,
            "needs_setup": not self.client,
            "needs_auth": self.client is not None and not self.is_connected and "authenticate" in (self.connection_error or "").lower(),
            "needs_channels": self.is_connected and len(self.monitored_chats) == 0
        }
        return status
    
    async def handle_new_message(self, event):
        """Handle new message from monitored chats"""
        db = SessionLocal()
        try:
            chat = await event.get_chat()
            sender = await event.get_sender()
            
            chat_name = getattr(chat, 'title', str(event.chat_id))
            sender_name = getattr(sender, 'username', None) or getattr(sender, 'first_name', 'Unknown')
            message_text = event.message.text or ""
            
            # Update last message time
            self.last_message_time = datetime.utcnow()
            
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
            
            # If it's a signal, also broadcast a signal-specific event for notifications
            if parsed_signal:
                await self.ws_manager.broadcast({
                    "type": "new_signal",
                    "data": {
                        "id": message.id,
                        "symbol": parsed_signal.get('symbol'),
                        "action": parsed_signal.get('action'),
                        "chat_name": chat_name,
                        "message": f"New {parsed_signal.get('action')} signal for {parsed_signal.get('symbol')} from {chat_name}"
                    }
                })
                
                # Attempt automatic trade execution
                try:
                    from app.services.auto_trade_service import get_auto_trade_service
                    
                    auto_trade_service = get_auto_trade_service()
                    
                    # Broadcast that auto-trade is being attempted
                    await self.ws_manager.broadcast({
                        "type": "auto_trade_started",
                        "data": {
                            "message_id": message.id,
                            "symbol": parsed_signal.get('symbol'),
                            "action": parsed_signal.get('action'),
                            "chat_name": chat_name
                        }
                    })
                    
                    # Process the signal for auto-trading
                    auto_result = await auto_trade_service.process_signal(
                        parsed_signal=parsed_signal,
                        message_id=message.id,
                        chat_name=chat_name,
                        db=db
                    )
                    
                    # Broadcast auto-trade result
                    await self.ws_manager.broadcast({
                        "type": "auto_trade_result",
                        "data": auto_result
                    })
                    
                    if auto_result.get("status") == "executed":
                        logger.info(f"🎯 Auto-trade executed for {parsed_signal.get('symbol')}: Order ID {auto_result.get('order_id')}")
                    elif auto_result.get("auto_trade_attempted"):
                        logger.info(f"ℹ️ Auto-trade result for {parsed_signal.get('symbol')}: {auto_result.get('status')} - {auto_result.get('reason')}")
                    
                except Exception as auto_trade_error:
                    logger.error(f"Error in auto-trade processing: {auto_trade_error}", exc_info=True)
                    # Broadcast error but don't fail the message handling
                    await self.ws_manager.broadcast({
                        "type": "auto_trade_error",
                        "data": {
                            "message_id": message.id,
                            "error": str(auto_trade_error)
                        }
                    })
            
            logger.info(f"📨 New message from {chat_name}: {message_text[:50]}..." if len(message_text) > 50 else f"📨 New message from {chat_name}: {message_text}")
            
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
