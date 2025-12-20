"""
Broker API endpoints for multi-broker integration

Supports:
- Angel One SmartAPI
- Zerodha Kite Connect
- Additional brokers via BrokerInterface
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from pathlib import Path
import os
from typing import Optional

from app.core.database import get_db
from app.schemas.schemas import (
    BrokerConfigCreate,
    BrokerConfigResponse
)
from app.models.models import BrokerConfig, AppSettings
from app.services.broker_registry import broker_registry
from app.services.broker_service import broker_service

router = APIRouter()

# Encryption key for storing credentials
# In production, set ENCRYPTION_KEY env var to a stable Fernet key
# Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
def get_encryption_key():
    """Get or create a stable encryption key"""
    key_file = Path(__file__).parent.parent.parent / "data" / ".encryption_key"
    env_key = os.getenv("ENCRYPTION_KEY")
    
    if env_key:
        # Use environment variable if set
        if isinstance(env_key, str) and len(env_key) == 44:
            return env_key.encode()
        return env_key if isinstance(env_key, bytes) else Fernet.generate_key()
    
    # Try to load from file for persistence across restarts
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if key_file.exists():
        return key_file.read_bytes()
    
    # Generate new key and save it
    new_key = Fernet.generate_key()
    key_file.write_bytes(new_key)
    return new_key

ENCRYPTION_KEY = get_encryption_key()
cipher = Fernet(ENCRYPTION_KEY)


@router.post("/config", response_model=BrokerConfigResponse)
async def create_broker_config(config: BrokerConfigCreate, db: Session = Depends(get_db)):
    """
    Create or update broker configuration.
    
    Supports multiple brokers:
    - angel_one: Requires api_key, client_id, pin, totp_secret
    - zerodha: Requires api_key, api_secret, client_id
    - upstox: Requires api_key, api_secret, client_id, pin
    """
    # Validate broker type
    if not broker_registry.is_registered(config.broker_name):
        available = broker_registry.list_available_brokers()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid broker type. Available: {available}"
        )
    
    # Encrypt PIN/password
    encrypted_pin = cipher.encrypt(config.pin.encode()).decode()
    
    # Encrypt TOTP secret if provided
    encrypted_totp = None
    if config.totp_secret:
        encrypted_totp = cipher.encrypt(config.totp_secret.encode()).decode()
    
    # Encrypt API secret if provided (for Zerodha, Upstox, etc.)
    encrypted_api_secret = None
    if config.api_secret:
        encrypted_api_secret = cipher.encrypt(config.api_secret.encode()).decode()
    
    # Check if config already exists for this broker
    existing = db.query(BrokerConfig).filter(
        BrokerConfig.broker_name == config.broker_name
    ).first()
    
    if existing:
        # Update existing
        existing.api_key = config.api_key
        existing.api_secret = encrypted_api_secret
        existing.client_id = config.client_id
        existing.password_encrypted = encrypted_pin
        existing.totp_secret = encrypted_totp
        db_config = existing
    else:
        # Create new config
        db_config = BrokerConfig(
            broker_name=config.broker_name,
            api_key=config.api_key,
            api_secret=encrypted_api_secret,
            client_id=config.client_id,
            password_encrypted=encrypted_pin,
            totp_secret=encrypted_totp,
            is_active=False
        )
        db.add(db_config)
    
    db.commit()
    db.refresh(db_config)
    
    return BrokerConfigResponse(
        id=db_config.id,
        broker_name=db_config.broker_name,
        client_id=db_config.client_id,
        is_active=db_config.is_active,
        has_totp_secret=bool(db_config.totp_secret),
        has_api_secret=bool(db_config.api_secret),
        last_login=db_config.last_login
    )


@router.get("/config")
async def get_broker_config(
    broker_type: Optional[str] = Query(None, description="Specific broker type to get config for"),
    db: Session = Depends(get_db)
):
    """Get broker configuration(s)"""
    if broker_type:
        # Get specific broker config
        config = db.query(BrokerConfig).filter(
            BrokerConfig.broker_name == broker_type
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"No configuration found for {broker_type}"
            )
        
        return BrokerConfigResponse(
            id=config.id,
            broker_name=config.broker_name,
            client_id=config.client_id,
            is_active=config.is_active,
            has_totp_secret=bool(config.totp_secret),
            has_api_secret=bool(config.api_secret),
            last_login=config.last_login
        )
    else:
        # Get all broker configs
        configs = db.query(BrokerConfig).all()
        return {
            "brokers": [
                BrokerConfigResponse(
                    id=c.id,
                    broker_name=c.broker_name,
                    client_id=c.client_id,
                    is_active=c.is_active,
                    has_totp_secret=bool(c.totp_secret),
                    has_api_secret=bool(c.api_secret),
                    last_login=c.last_login
                )
                for c in configs
            ]
        }


@router.get("/config/legacy", response_model=BrokerConfigResponse)
async def get_broker_config_legacy(db: Session = Depends(get_db)):
    """Get active broker configuration (legacy endpoint for backward compatibility)"""
    # Always use the most recent Angel One config
    config = db.query(BrokerConfig).filter(BrokerConfig.broker_name == 'angel_one').order_by(BrokerConfig.created_at.desc()).first()
    if not config:
        raise HTTPException(status_code=404, detail="No Angel One configuration found")
    return BrokerConfigResponse(
        id=config.id,
        broker_name=config.broker_name,
        client_id=config.client_id,
        is_active=config.is_active,
        has_totp_secret=bool(config.totp_secret),
        has_api_secret=bool(config.api_secret) if hasattr(config, 'api_secret') and config.api_secret else False,
        last_login=config.last_login
    )


@router.post("/login")
async def broker_login(db: Session = Depends(get_db)):
    """
    Login to broker account using stored credentials.
    
    The TOTP code is auto-generated from the stored TOTP secret.
    No manual OTP entry required!
    """
    # Always use the most recent Angel One config
    config = db.query(BrokerConfig).filter(BrokerConfig.broker_name == 'angel_one').order_by(BrokerConfig.created_at.desc()).first()
    if not config:
        raise HTTPException(status_code=404, detail="No Angel One configuration found. Please configure first.")
    if not config.totp_secret:
        raise HTTPException(
            status_code=400,
            detail="TOTP secret not configured. Please update configuration with TOTP secret for auto-login."
        )
    # Decrypt credentials
    decrypted_pin = cipher.decrypt(config.password_encrypted.encode()).decode()
    decrypted_totp_secret = cipher.decrypt(config.totp_secret.encode()).decode()
    # Login with auto-generated TOTP
    result = broker_service.login(
        api_key=config.api_key,
        client_id=config.client_id,
        password=decrypted_pin,
        totp_secret=decrypted_totp_secret
    )
    if result['status'] == 'success':
        return result
    else:
        raise HTTPException(status_code=401, detail=result['message'])


@router.post("/logout")
async def broker_logout():
    """Logout from broker account"""
    broker_service.logout()
    return {"status": "success", "message": "Logged out successfully"}


@router.get("/status")
async def broker_status():
    """Get broker connection status"""
    return {
        "is_logged_in": broker_service.is_logged_in,
        "client_id": broker_service.client_id
    }


@router.get("/positions")
async def get_positions():
    """Get current positions"""
    result = broker_service.get_positions()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.get("/holdings")
async def get_holdings():
    """Get long-term holdings (delivery stocks)"""
    result = broker_service.get_holdings()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.get("/orders")
async def get_order_book():
    """Get all orders for today"""
    result = broker_service.get_order_book()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.get("/funds")
async def get_funds():
    """Get account funds and margin"""
    result = broker_service.get_funds()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.get("/ltp/{exchange}/{symbol}")
async def get_ltp(exchange: str, symbol: str):
    """Get last traded price for a symbol"""
    result = broker_service.get_ltp(symbol, exchange)
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str, variety: str = "NORMAL"):
    """Cancel an open order"""
    result = broker_service.cancel_order(order_id, variety)
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.get("/symbols/search")
async def search_symbols(query: str, exchange: str = None):
    """Search for trading symbols"""
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    results = broker_service.search_symbols(query, exchange)
    return {"symbols": results}


@router.post("/symbols/refresh")
async def refresh_symbols():
    """Refresh instrument master data"""
    success = broker_service.refresh_instruments()
    if success:
        return {"status": "success", "message": "Instrument master refreshed"}
    else:
        raise HTTPException(status_code=500, detail="Failed to refresh instrument master")


# ============= Multi-Broker Endpoints =============

@router.get("/brokers")
async def list_brokers():
    """Get list of all available brokers"""
    available = broker_registry.list_available_brokers()
    return {
        "brokers": available,
        "default": broker_registry.get_default_broker()
    }


@router.get("/brokers/configured")
async def list_configured_brokers(db: Session = Depends(get_db)):
    """Get list of configured brokers with their status"""
    configs = broker_registry.get_configured_brokers(db)
    return {"brokers": configs}


@router.get("/brokers/active")
async def get_active_broker(db: Session = Depends(get_db)):
    """Get currently active broker"""
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        return {
            "broker_type": None,
            "message": "No active broker set"
        }
    
    # Check if broker is logged in
    broker = broker_registry.create_broker(settings.active_broker_type)
    return {
        "broker_type": settings.active_broker_type,
        "is_logged_in": broker.is_logged_in,
        "client_id": broker.client_id
    }


@router.post("/brokers/active")
async def set_active_broker(
    broker_type: str = Query(..., description="Broker type to activate"),
    db: Session = Depends(get_db)
):
    """Set the active broker for trading"""
    # Validate broker type
    if not broker_registry.is_registered(broker_type):
        available = broker_registry.list_available_brokers()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid broker type. Available: {available}"
        )
    
    # Update settings
    settings = db.query(AppSettings).first()
    if not settings:
        settings = AppSettings(active_broker_type=broker_type)
        db.add(settings)
    else:
        settings.active_broker_type = broker_type
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Active broker set to {broker_type}",
        "broker_type": broker_type
    }


@router.get("/brokers/{broker_type}/status")
async def get_broker_status(broker_type: str):
    """Get status of a specific broker"""
    if not broker_registry.is_registered(broker_type):
        raise HTTPException(status_code=404, detail="Broker not found")
    
    broker = broker_registry.create_broker(broker_type)
    return {
        "broker_type": broker_type,
        "is_logged_in": broker.is_logged_in,
        "client_id": broker.client_id
    }


@router.post("/brokers/{broker_type}/login")
async def login_specific_broker(broker_type: str, db: Session = Depends(get_db)):
    """Login to a specific broker"""
    if not broker_registry.is_registered(broker_type):
        raise HTTPException(status_code=404, detail="Broker not found")
    
    # Get broker config
    config = db.query(BrokerConfig).filter(
        BrokerConfig.broker_name == broker_type
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"No configuration found for {broker_type}"
        )
    
    # Decrypt credentials
    decrypted_pin = cipher.decrypt(config.password_encrypted.encode()).decode()
    decrypted_totp_secret = None
    decrypted_api_secret = None
    
    if config.totp_secret:
        decrypted_totp_secret = cipher.decrypt(config.totp_secret.encode()).decode()
    
    if config.api_secret:
        decrypted_api_secret = cipher.decrypt(config.api_secret.encode()).decode()
    
    # Get broker instance
    broker = broker_registry.create_broker(broker_type)
    
    # Login (API secret reuses totp_secret parameter for Zerodha)
    if broker_type == "zerodha" and decrypted_api_secret:
        # For Zerodha, password should be request_token, totp_secret is api_secret
        result = broker.login(
            api_key=config.api_key,
            client_id=config.client_id,
            password=decrypted_pin,  # This would be request_token for Zerodha
            totp_secret=decrypted_api_secret
        )
    else:
        # Standard login flow (Angel One)
        result = broker.login(
            api_key=config.api_key,
            client_id=config.client_id,
            password=decrypted_pin,
            totp_secret=decrypted_totp_secret
        )
    
    if result['status'] == 'success':
        # Update last login
        from datetime import datetime
        config.last_login = datetime.utcnow()
        db.commit()
        return result
    else:
        raise HTTPException(status_code=401, detail=result.get('message', 'Login failed'))


@router.post("/brokers/{broker_type}/logout")
async def logout_specific_broker(broker_type: str):
    """Logout from a specific broker"""
    if not broker_registry.is_registered(broker_type):
        raise HTTPException(status_code=404, detail="Broker not found")
    
    broker = broker_registry.create_broker(broker_type)
    broker.logout()
    
    return {
        "status": "success",
        "message": f"Logged out from {broker_type}"
    }

