
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Import routers and models
from app.api import telegram, trades
from app.core.database import Base, get_db
from app.models.models import Trade, AppSettings, TelegramConfig, TelegramMessage
from app.services.websocket_manager import WebSocketManager
from app.services.telegram_service import TelegramService

# Create in-memory db
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_integration.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Create a local app for testing
app = FastAPI()
app.include_router(telegram.router, prefix="/api/telegram")
app.include_router(trades.router, prefix="/api/trades")

# Mock services
ws_manager = WebSocketManager()
telegram.telegram_service = TelegramService(ws_manager)
trades.ws_manager = ws_manager

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def setup_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create default settings
    db = TestingSessionLocal()
    if not db.query(AppSettings).first():
        settings = AppSettings(
            default_quantity=10,
            auto_trade_enabled=False,
            max_trades_per_day=5
        )
        db.add(settings)
        db.commit()
    db.close()
    
    yield
    
    # Drop tables
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_config_endpoint(setup_db, client):
    """Test Telegram config endpoint"""
    config_data = {
        "api_id": "12345",
        "api_hash": "abcdef123456",
        "phone_number": "+919876543210",
        "monitored_chats": [1001, 1002]
    }
    response = await client.post("/api/telegram/config", json=config_data)
    assert response.status_code == 200
    data = response.json()
    assert data["api_id"] == "12345"
    assert data["phone_number"] == "+919876543210"

@pytest.mark.asyncio
async def test_trades_crud(setup_db, client):
    """Test Trades CRUD"""
    
    # 1. Create Trade
    trade_data = {
        "symbol": "RELIANCE",
        "action": "BUY",
        "quantity": 5,
        "entry_price": 2500.0,
        "target_price": 2600.0,
        "stop_loss": 2450.0,
        "order_type": "MARKET",
        "exchange": "NSE",
        "product_type": "INTRADAY",
        "message_id": 123
    }
    
    response = await client.post("/api/trades/", json=trade_data)
    assert response.status_code == 200, response.text
    created_trade = response.json()
    trade_id = created_trade["id"]
    assert created_trade["symbol"] == "RELIANCE"
    assert created_trade["status"] == "PENDING"
    
    # 2. Get Trade by ID
    response = await client.get(f"/api/trades/{trade_id}")
    assert response.status_code == 200
    assert response.json()["id"] == trade_id
    
    # 3. Get All Trades
    response = await client.get("/api/trades/")
    assert response.status_code == 200
    trades = response.json()
    assert len(trades) >= 1
    
    # 4. Approve Trade (Simulation)
    approval_data = {
        "trade_id": trade_id,
        "approved": True
    }
    response = await client.post("/api/trades/approve", json=approval_data)
    # Expect 400 because broker not logged in
    assert response.status_code == 400
    assert "Broker not logged in" in response.json()["detail"]

@pytest.mark.asyncio
async def test_telegram_messages_crud(setup_db, client):
    """Test Message CRUD"""
    
    # Insert dummy message
    db = TestingSessionLocal()
    msg = TelegramMessage(
        chat_id="123",
        chat_name="Test Chat",
        message_id=999,
        message_text="Test Message",
        sender="TestUser",
        timestamp=datetime.utcnow()
    )
    db.add(msg)
    db.commit()
    db.close()
    
    response = await client.get("/api/telegram/messages")
    assert response.status_code == 200
    messages = response.json()
    # It might return messages from previous runs if DB persists, but we recreate tables in fixture
    # However we inserted one just now
    assert len(messages) >= 1
    # Check if our message is in the list
    found = any(m["message_text"] == "Test Message" for m in messages)
    assert found

