"""
Main FastAPI application entry point
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env file before other imports

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import asyncio
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime

from app.api import telegram, broker, trades, config, paper_trading
from app.core.database import init_db, SessionLocal
from app.core.logging_config import get_logger
from app.core.settings import get_settings
from app.core.middleware import RequestLoggingMiddleware
from app.services.telegram_service import TelegramService
from app.services.websocket_manager import WebSocketManager
from app.services.broker_registry import broker_registry
from app.services.broker_service import AngelOneBrokerService, broker_service
from app.services.zerodha_broker_service import ZerodhaBrokerService
from app.services.shoonya_broker_service import ShoonyaBrokerService
from app.models.models import Trade

# Setup logger
logger = get_logger("main")

# Initialize managers
ws_manager = WebSocketManager()
telegram_service = None
order_sync_task = None


async def periodic_order_status_sync():
    """Background task to sync order statuses every 15 seconds (increased from 10)"""
    while True:
        try:
            await asyncio.sleep(15)  # Increased from 10 to reduce load
            
            # Only sync if broker is logged in
            if not broker_service.is_logged_in:
                continue
            
            # Get trades that need status sync
            db = SessionLocal()
            try:
                trades_to_sync = db.query(Trade).filter(
                    Trade.order_id.isnot(None),
                    Trade.status.in_(["SUBMITTED", "OPEN", "PENDING"])
                ).limit(50).all()  # Limit batch size
                
                if not trades_to_sync:
                    continue
                
                logger.debug(f"🔄 Syncing {len(trades_to_sync)} open orders...")
                
                # Get all orders from broker
                order_book = broker_service.get_all_order_statuses()
                
                if order_book.get('status') != 'success':
                    logger.warning(f"⚠️ Failed to fetch order book: {order_book.get('message')}")
                    continue
                
                broker_orders = {str(o['order_id']): o for o in order_book.get('orders', [])}
                
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
                        
                        if old_status != trade.status:
                            logger.info(f"📊 Trade {trade.id} status: {old_status} → {trade.status}")
                            updates.append({
                                "trade_id": trade.id,
                                "order_id": trade.order_id,
                                "old_status": old_status,
                                "new_status": trade.status,
                                "broker_status": broker_status,
                                "rejection_reason": trade.broker_rejection_reason
                            })
                
                if updates:
                    db.commit()
                    # Notify via WebSocket
                    await ws_manager.broadcast({
                        "type": "trades_synced",
                        "data": {
                            "updated_count": len(updates),
                            "updates": updates
                        }
                    })
                    
            except Exception as e:
                logger.error(f"❌ Error in order sync: {str(e)}")
            finally:
                db.close()
                
        except asyncio.CancelledError:
            logger.info("🛑 Order sync task cancelled")
            break
        except Exception as e:
            logger.error(f"❌ Error in periodic sync: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global order_sync_task
    
    # Startup
    logger.info("🚀 Starting Telegram Trading Bot...")
    init_db()
    logger.info("✅ Database initialized")
    
    # Register brokers
    broker_registry.register("angel_one", AngelOneBrokerService)
    broker_registry.register("zerodha", ZerodhaBrokerService)
    broker_registry.register("shoonya", ShoonyaBrokerService)
    logger.info("✅ Registered brokers: angel_one, zerodha, shoonya")
    
    global telegram_service
    telegram_service = TelegramService(ws_manager)
    
    # Inject dependencies into API modules
    telegram.telegram_service = telegram_service
    trades.ws_manager = ws_manager
    
    await telegram_service.start()
    logger.info("✅ Telegram service started")
    
    # Start background order sync task
    order_sync_task = asyncio.create_task(periodic_order_status_sync())
    logger.info("✅ Order status sync task started")
    
    logger.info("🎉 Application startup complete!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    if order_sync_task:
        order_sync_task.cancel()
        try:
            await order_sync_task
        except asyncio.CancelledError:
            pass
    if telegram_service:
        await telegram_service.stop()
    broker_registry.clear_instances()
    logger.info("👋 Goodbye!")


app = FastAPI(
    title="Telegram Trading Bot",
    description="Automated trading from Telegram signals to Angel One broker",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(telegram.router, prefix="/api/telegram", tags=["Telegram"])
app.include_router(broker.router, prefix="/api/broker", tags=["Broker"])
app.include_router(trades.router, prefix="/api/trades", tags=["Trades"])
app.include_router(config.router, prefix="/api/config", tags=["Configuration"])
app.include_router(paper_trading.router, prefix="/api/paper", tags=["Paper Trading"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Telegram Trading Bot API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, handle incoming messages if needed
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
