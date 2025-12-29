"""
Broker API endpoints for multi-broker integration

Supports:
- Angel One SmartAPI
- Zerodha Kite Connect
- Additional brokers via BrokerInterface
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.encryption import get_encryption_manager
from app.schemas.schemas import (
    BrokerConfigCreate,
    BrokerConfigResponse
)
from app.models.models import BrokerConfig, AppSettings
from app.services.broker_registry import broker_registry
from app.services.broker_service import broker_service

router = APIRouter()

# Get encryption manager for credential encryption/decryption
encryption_manager = get_encryption_manager()


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
    encrypted_pin = encryption_manager.encrypt(config.pin)
    
    # Encrypt TOTP secret if provided
    encrypted_totp = None
    if config.totp_secret:
        encrypted_totp = encryption_manager.encrypt(config.totp_secret)
    
    # Encrypt API secret if provided (for Zerodha, Upstox, etc.)
    encrypted_api_secret = None
    if config.api_secret:
        encrypted_api_secret = encryption_manager.encrypt(config.api_secret)
    
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
    try:
        decrypted_pin = encryption_manager.decrypt(config.password_encrypted)
        decrypted_totp_secret = encryption_manager.decrypt(config.totp_secret)
    except Exception as e:
        print(f"❌ Auto-login decryption failed: {e}")
        config.is_active = False
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Configuration invalid (decryption failed). Please re-configure broker."
        )

    # Login with auto-generated TOTP
    try:
        result = broker_service.login(
            api_key=config.api_key,
            client_id=config.client_id,
            password=decrypted_pin,
            totp_secret=decrypted_totp_secret
        )
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Login process failed: {str(e)}")

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
async def broker_status(db: Session = Depends(get_db)):
    """Get broker connection status from active broker"""
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        # Fallback to legacy Angel One broker
        return {
            "is_logged_in": broker_service.is_logged_in,
            "client_id": broker_service.client_id,
            "broker_type": "angel_one"
        }
    
    # Use active broker
    broker = broker_registry.create_broker(settings.active_broker_type)
    
    # For Zerodha, need to restore session
    if settings.active_broker_type == "zerodha":
        config = db.query(BrokerConfig).filter(
            BrokerConfig.broker_name == 'zerodha'
        ).first()
        
        if config and not broker.is_logged_in:
            # Try to restore session
            try:
                decrypted_token = encryption_manager.decrypt(config.password_encrypted)
                broker.login(
                    api_key=config.api_key,
                    client_id=config.client_id,
                    password=decrypted_token,
                    totp_secret=None
                )
            except:
                pass  # Restoration failed, will show as not logged in
    
    return {
        "is_logged_in": broker.is_logged_in,
        "client_id": broker.client_id,
        "broker_type": settings.active_broker_type
    }


@router.get("/positions")
async def get_positions(db: Session = Depends(get_db)):
    """Get current positions from active broker"""
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        # Fallback to legacy Angel One broker
        result = broker_service.get_positions()
        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('message', 'Not logged in'))
        return result
    
    # Use active broker
    broker = broker_registry.create_broker(settings.active_broker_type)
    if not broker.is_logged_in:
        raise HTTPException(status_code=401, detail="Broker not logged in")
    
    result = broker.get_positions()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result.get('message', 'Failed to fetch positions'))
    return result


@router.get("/holdings")
async def get_holdings(db: Session = Depends(get_db)):
    """Get long-term holdings (delivery stocks) from active broker with current prices"""
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        # Fallback to legacy Angel One broker
        result = broker_service.get_holdings()
        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('message', 'Not logged in'))
        return result
    
    # Use active broker
    broker = broker_registry.create_broker(settings.active_broker_type)
    if not broker.is_logged_in:
        raise HTTPException(status_code=401, detail="Broker not logged in")
    
    result = broker.get_holdings()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result.get('message', 'Failed to fetch holdings'))
    
    # Enrich holdings with current prices if data is available
    holdings = result.get('data', [])
    if holdings and isinstance(holdings, list):
        enriched_holdings = []
        for holding in holdings:
            try:
                # Get symbol and exchange from holding
                symbol = holding.get('tradingsymbol') or holding.get('symbol')
                exchange = holding.get('exchange', 'NSE')
                
                # First check if holding already has price data (Zerodha includes it)
                current_price = (
                    holding.get('last_price') or 
                    holding.get('ltp') or 
                    holding.get('lastprice') or
                    holding.get('close_price')
                )
                
                # Only fetch LTP via API if price not already in holding data
                if not current_price and symbol:
                    try:
                        ltp_result = broker.get_ltp(symbol, exchange)
                        if ltp_result is not None:
                            if isinstance(ltp_result, (int, float)):
                                current_price = float(ltp_result)
                            elif isinstance(ltp_result, dict):
                                if ltp_result.get('status') == 'success':
                                    ltp_data = ltp_result.get('data', {})
                                    if isinstance(ltp_data, dict):
                                        current_price = ltp_data.get('ltp') or ltp_data.get('last_price')
                                    elif isinstance(ltp_data, (int, float)):
                                        current_price = float(ltp_data)
                                else:
                                    current_price = ltp_result.get('ltp') or ltp_result.get('last_price')
                    except Exception:
                        pass  # Silently ignore LTP fetch failures
                
                if current_price:
                    current_price = float(current_price)
                    holding['last_price'] = current_price
                    holding['current_price'] = current_price
                    holding['ltp'] = current_price
                    
                    # Calculate P&L if we have average price
                    avg_price = holding.get('average_price') or holding.get('averageprice') or holding.get('avg_price', 0)
                    quantity = holding.get('quantity') or holding.get('t1_quantity', 0) or 0
                    
                    if avg_price and quantity:
                        avg_price = float(avg_price)
                        quantity = int(quantity)
                        pnl = (current_price - avg_price) * quantity
                        pnl_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
                        
                        holding['pnl'] = round(pnl, 2)
                        holding['pnl_percentage'] = round(pnl_percent, 2)
                        holding['current_value'] = round(current_price * quantity, 2)
                        holding['invested_value'] = round(avg_price * quantity, 2)
                
                enriched_holdings.append(holding)
            except Exception as e:
                # If processing fails, just add the holding as-is
                enriched_holdings.append(holding)
        
        result['data'] = enriched_holdings
    
    return result


@router.get("/orders")
async def get_order_book(db: Session = Depends(get_db)):
    """Get all orders for today from active broker"""
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        # Fallback to legacy Angel One broker
        result = broker_service.get_order_book()
        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('message', 'Not logged in'))
        return result
    
    # Use active broker
    broker = broker_registry.create_broker(settings.active_broker_type)
    if not broker.is_logged_in:
        raise HTTPException(status_code=401, detail="Broker not logged in")
    
    result = broker.get_order_book()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result.get('message', 'Failed to fetch orders'))
    return result


@router.get("/funds")
async def get_funds(db: Session = Depends(get_db)):
    """Get account funds and margin from active broker"""
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        # Fallback to legacy Angel One broker
        result = broker_service.get_funds()
        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('message', 'Not logged in'))
        return result
    
    # Use active broker
    broker = broker_registry.create_broker(settings.active_broker_type)
    if not broker.is_logged_in:
        raise HTTPException(status_code=401, detail="Broker not logged in")
    
    result = broker.get_funds()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result.get('message', 'Failed to fetch funds'))
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
    try:
        decrypted_pin = encryption_manager.decrypt(config.password_encrypted)
        decrypted_totp_secret = None
        decrypted_api_secret = None
        
        if config.totp_secret:
            decrypted_totp_secret = encryption_manager.decrypt(config.totp_secret)
        
        if config.api_secret:
            decrypted_api_secret = encryption_manager.decrypt(config.api_secret)
    except Exception as e:
        print(f"❌ Decryption failed for {broker_type}: {e}")
        # If decryption fails, the config is invalid (key changed?)
        # Reset the config or ask user to re-configure
        config.is_active = False
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Configuration invalid (decryption failed). Please update your broker configuration."
        )
    
    # Get broker instance
    try:
        broker = broker_registry.create_broker(broker_type)
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Failed to initialize broker: {str(e)}")
    
    # Login with appropriate credentials based on broker type
    if broker_type == "zerodha":
        # For Zerodha: try session restoration first (password is access_token)
        # If that fails and api_secret is available, user needs to do OAuth flow again
        result = broker.login(
            api_key=config.api_key,
            client_id=config.client_id,
            password=decrypted_pin,  # access_token for restoration
            totp_secret=None  # No api_secret = session restoration mode
        )
        
        # If restoration failed and we have api_secret, it means token expired
        if result['status'] != 'success' and decrypted_api_secret:
            result['message'] = "Session expired. Please login again via browser."
            result['needs_oauth'] = True
    else:
        # Standard login flow (Angel One, Shoonya, etc.)
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


@router.get("/zerodha/login-url")
async def get_zerodha_login_url(db: Session = Depends(get_db)):
    """
    Get Zerodha OAuth login URL.
    User must visit this URL in browser to authorize the app.
    """
    config = db.query(BrokerConfig).filter(
        BrokerConfig.broker_name == 'zerodha'
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=404,
            detail="Zerodha not configured. Please add API key and API secret first."
        )
    
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=config.api_key)
        login_url = kite.login_url()
        
        return {
            "status": "success",
            "login_url": login_url,
            "message": "Visit this URL to authorize the app"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate login URL: {str(e)}")


@router.post("/zerodha/complete-login")
async def complete_zerodha_login(request_token: str, db: Session = Depends(get_db)):
    """
    Complete Zerodha login using request_token from OAuth redirect.
    
    After user authorizes the app, Zerodha redirects to:
    http://127.0.0.1/?request_token=XXXXXX&action=login&status=success
    
    Copy the request_token and provide it here.
    """
    config = db.query(BrokerConfig).filter(
        BrokerConfig.broker_name == 'zerodha'
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Zerodha configuration not found")
    
    try:
        # Decrypt API secret
        decrypted_api_secret = encryption_manager.decrypt(config.api_secret)
        
        # Get broker instance and login
        broker = broker_registry.create_broker('zerodha')
        result = broker.login(
            api_key=config.api_key,
            client_id=config.client_id,
            password=request_token,  # request_token from OAuth
            totp_secret=decrypted_api_secret  # API secret
        )
        
        if result['status'] == 'success':
            # Update last login and mark as active
            from datetime import datetime
            config.last_login = datetime.utcnow()
            config.is_active = True
            
            # Store access token in PIN field for session persistence
            if 'access_token' in result:
                encrypted_token = encryption_manager.encrypt(result['access_token'])
                config.password_encrypted = encrypted_token
            
            db.commit()
            return {
                "status": "success",
                "message": "Successfully logged in to Zerodha!",
                "access_token": result.get('access_token', 'stored')
            }
        else:
            raise HTTPException(status_code=401, detail=result.get('message', 'Login failed'))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

