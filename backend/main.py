"""
Main FastAPI application entry point
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env file before other imports

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api import telegram, broker, trades, config, paper_trading
from app.core.database import init_db
from app.core.logging_config import get_logger
from app.core.settings import get_settings
from app.core.middleware import RequestLoggingMiddleware
from app.services.telegram_service import TelegramService
from app.services.websocket_manager import WebSocketManager
from app.services.broker_registry import broker_registry
from app.services.broker_service import AngelOneBrokerService
from app.services.zerodha_broker_service import ZerodhaBrokerService
from app.services.shoonya_broker_service import ShoonyaBrokerService

# Setup logger
logger = get_logger("main")

# Initialize managers
ws_manager = WebSocketManager()
telegram_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
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
    logger.info("🎉 Application startup complete!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
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
