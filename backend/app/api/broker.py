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
import time

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

# Differentiated cache TTL based on data criticality
# Real-time trading data: 5 seconds (positions, orders, funds)
# Moderate refresh: 30 seconds (holdings - delivery stocks change less frequently)
# Static data: 300 seconds (broker configs, symbol master)
_broker_cache = {}
CACHE_TTL_CRITICAL = 5      # positions, orders, funds
CACHE_TTL_MODERATE = 30     # holdings
CACHE_TTL_STATIC = 300      # configs, broker list

def get_cached_broker_data(key: str):
    """Get data from cache if not expired. Returns (data, cached_at) or None"""
    if key in _broker_cache:
        data, cached_at, expires = _broker_cache[key]
        if time.time() < expires:
            return (data, cached_at)
    return None

def set_cached_broker_data(key: str, data, ttl: int = CACHE_TTL_CRITICAL):
    """Set data in cache with TTL and timestamp"""
    cached_at = time.time()
    _broker_cache[key] = (data, cached_at, cached_at + ttl)

def clear_broker_cache():
    """Clear all broker cache"""
    global _broker_cache
    _broker_cache = {}

def force_refresh_broker_data():
    """Force refresh of critical trading data before order execution"""
    # Clear only critical data that needs to be fresh for trading decisions
    keys_to_clear = ['positions', 'orders', 'funds']
    for key in keys_to_clear:
        if key in _broker_cache:
            del _broker_cache[key]


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
        existing.imei = config.imei if hasattr(config, 'imei') else None
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
            imei=config.imei if hasattr(config, 'imei') else None,
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
    # Check cache first (5 second TTL)
    cached_data = get_cached_broker_data('positions')
    if cached_data:
        result, cached_at = cached_data
        result['cached_at'] = cached_at
        return result
    
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        # Fallback to legacy Angel One broker
        result = broker_service.get_positions()
        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('message', 'Not logged in'))
        set_cached_broker_data('positions', result, CACHE_TTL_CRITICAL)
        result['cached_at'] = time.time()
        return result
    
    # Use active broker
    broker = broker_registry.create_broker(settings.active_broker_type)
    if not broker.is_logged_in:
        raise HTTPException(status_code=401, detail="Broker not logged in")
    
    result = broker.get_positions()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result.get('message', 'Failed to fetch positions'))
    set_cached_broker_data('positions', result, CACHE_TTL_CRITICAL)
    result['cached_at'] = time.time()
    return result


@router.get("/holdings")
async def get_holdings(db: Session = Depends(get_db)):
    """Get long-term holdings (delivery stocks) from active broker with current prices"""
    # Check cache first (30 second TTL - holdings change less frequently)
    cached_data = get_cached_broker_data('holdings')
    if cached_data:
        result, cached_at = cached_data
        result['cached_at'] = cached_at
        return result
    
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        # Fallback to legacy Angel One broker
        result = broker_service.get_holdings()
        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('message', 'Not logged in'))
        set_cached_broker_data('holdings', result, CACHE_TTL_MODERATE)
        result['cached_at'] = time.time()
        return result
    
    # Use active broker
    broker = broker_registry.create_broker(settings.active_broker_type)
    if not broker.is_logged_in:
        raise HTTPException(status_code=401, detail="Broker not logged in")
    
    result = broker.get_holdings()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result.get('message', 'Failed to fetch holdings'))
    
    # Process holdings - calculate P&L using available data only (no additional API calls)
    holdings = result.get('data', [])
    if holdings and isinstance(holdings, list):
        enriched_holdings = []
        for holding in holdings:
            try:
                # Use price data already included in the holding (most brokers include this)
                current_price = (
                    holding.get('last_price') or 
                    holding.get('ltp') or 
                    holding.get('lastprice') or
                    holding.get('close_price') or
                    holding.get('close') or
                    0
                )
                
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
            except Exception:
                enriched_holdings.append(holding)
        
        result['data'] = enriched_holdings
    
    set_cached_broker_data('holdings', result, CACHE_TTL_MODERATE)
    result['cached_at'] = time.time()
    return result


@router.get("/orders")
async def get_order_book(db: Session = Depends(get_db)):
    """Get all orders for today from active broker"""
    # Check cache first (5 second TTL)
    cached_data = get_cached_broker_data('orders')
    if cached_data:
        result, cached_at = cached_data
        result['cached_at'] = cached_at
        return result
    
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        # Fallback to legacy Angel One broker
        result = broker_service.get_order_book()
        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('message', 'Not logged in'))
        set_cached_broker_data('orders', result, CACHE_TTL_CRITICAL)
        result['cached_at'] = time.time()
        return result
    
    # Use active broker
    broker = broker_registry.create_broker(settings.active_broker_type)
    if not broker.is_logged_in:
        raise HTTPException(status_code=401, detail="Broker not logged in")
    
    result = broker.get_order_book()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result.get('message', 'Failed to fetch orders'))
    set_cached_broker_data('orders', result, CACHE_TTL_CRITICAL)
    result['cached_at'] = time.time()
    return result


@router.get("/funds")
async def get_funds(db: Session = Depends(get_db)):
    """Get account funds and margin from active broker"""
    # Check cache first (5 second TTL)
    cached_data = get_cached_broker_data('funds')
    if cached_data:
        result, cached_at = cached_data
        result['cached_at'] = cached_at
        return result
    
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        # Fallback to legacy Angel One broker
        result = broker_service.get_funds()
        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('message', 'Not logged in'))
        set_cached_broker_data('funds', result, CACHE_TTL_CRITICAL)
        result['cached_at'] = time.time()
        return result
    
    # Use active broker
    broker = broker_registry.create_broker(settings.active_broker_type)
    if not broker.is_logged_in:
        raise HTTPException(status_code=401, detail="Broker not logged in")
    
    result = broker.get_funds()
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result.get('message', 'Failed to fetch funds'))
    set_cached_broker_data('funds', result, CACHE_TTL_CRITICAL)
    result['cached_at'] = time.time()
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
    try:
        # Validate broker type
        if not broker_registry.is_registered(broker_type):
            available = broker_registry.list_available_brokers()
            print(f"❌ Invalid broker type: {broker_type}. Available: {available}")
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
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error setting active broker: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


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
        # For SHOONYA, also pass api_secret and imei
        login_params = {
            'api_key': config.api_key,
            'client_id': config.client_id,
            'password': decrypted_pin,
            'totp_secret': decrypted_totp_secret
        }
        
        # Add SHOONYA-specific parameters if broker is shoonya
        if broker_type == "shoonya":
            if decrypted_api_secret:
                login_params['api_secret'] = decrypted_api_secret
            if config.imei:
                login_params['imei'] = config.imei
        
        result = broker.login(**login_params)
    
    if result['status'] == 'success':
        # Clear broker cache on successful login
        clear_broker_cache()
        
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
    
    # Clear broker cache on logout
    clear_broker_cache()
    
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


# ============= Position Management Endpoints =============

@router.post("/positions/square-off-all")
async def square_off_all_positions(db: Session = Depends(get_db)):
    """
    Close all open positions.
    
    This will place market orders to close all intraday and delivery positions.
    Use with caution!
    """
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        broker = broker_service
        broker_type = "angel_one"
    else:
        broker = broker_registry.create_broker(settings.active_broker_type)
        broker_type = settings.active_broker_type
    
    if not broker.is_logged_in:
        raise HTTPException(status_code=401, detail="Broker not logged in")
    
    # Get all positions
    positions_result = broker.get_positions()
    if positions_result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=positions_result.get('message', 'Failed to fetch positions'))
    
    positions = positions_result.get('data', [])
    if not positions:
        return {"status": "success", "message": "No open positions to close", "closed": 0}
    
    closed_count = 0
    errors = []
    
    for position in positions:
        try:
            # Get position details
            symbol = position.get('tradingsymbol') or position.get('symbol') or position.get('tsym')
            quantity = int(position.get('netqty') or position.get('quantity') or position.get('net_quantity', 0))
            exchange = position.get('exchange') or position.get('exch') or 'NSE'
            product_type = position.get('producttype') or position.get('product') or 'INTRADAY'
            
            # Skip if no net position
            if quantity == 0:
                continue
            
            # Determine action (opposite of current position)
            action = "SELL" if quantity > 0 else "BUY"
            close_quantity = abs(quantity)
            
            # Place market order to close
            result = broker.place_order(
                symbol=symbol,
                action=action,
                quantity=close_quantity,
                exchange=exchange,
                order_type="MARKET",
                product_type=product_type
            )
            
            if result.get('status') == 'success':
                closed_count += 1
            else:
                errors.append({
                    "symbol": symbol,
                    "error": result.get('message', 'Unknown error')
                })
        except Exception as e:
            errors.append({
                "symbol": position.get('tradingsymbol', 'Unknown'),
                "error": str(e)
            })
    
    # Clear cache after closing positions
    clear_broker_cache()
    
    return {
        "status": "success",
        "message": f"Closed {closed_count} positions",
        "closed": closed_count,
        "errors": errors if errors else None
    }


@router.post("/positions/{position_key}/square-off")
async def square_off_position(
    position_key: str,
    quantity: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Close a specific position.
    
    Args:
        position_key: Format is "EXCHANGE:SYMBOL" (e.g., "NSE:RELIANCE-EQ")
        quantity: Optional partial quantity to close. If not provided, closes entire position.
    """
    # Parse position key
    try:
        exchange, symbol = position_key.split(":", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid position key. Use format 'EXCHANGE:SYMBOL'")
    
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        broker = broker_service
    else:
        broker = broker_registry.create_broker(settings.active_broker_type)
    
    if not broker.is_logged_in:
        raise HTTPException(status_code=401, detail="Broker not logged in")
    
    # Get positions to find the specific one
    positions_result = broker.get_positions()
    if positions_result.get('status') == 'error':
        raise HTTPException(status_code=400, detail="Failed to fetch positions")
    
    positions = positions_result.get('data', [])
    target_position = None
    
    for pos in positions:
        pos_symbol = pos.get('tradingsymbol') or pos.get('symbol') or pos.get('tsym')
        pos_exchange = pos.get('exchange') or pos.get('exch') or 'NSE'
        
        if pos_symbol == symbol and pos_exchange == exchange:
            target_position = pos
            break
    
    if not target_position:
        raise HTTPException(status_code=404, detail=f"Position not found for {position_key}")
    
    # Get position quantity
    net_qty = int(target_position.get('netqty') or target_position.get('quantity') or target_position.get('net_quantity', 0))
    
    if net_qty == 0:
        return {"status": "success", "message": "Position already closed"}
    
    # Determine close quantity
    close_qty = quantity if quantity else abs(net_qty)
    if close_qty > abs(net_qty):
        raise HTTPException(status_code=400, detail=f"Cannot close more than open quantity ({abs(net_qty)})")
    
    # Determine action
    action = "SELL" if net_qty > 0 else "BUY"
    product_type = target_position.get('producttype') or target_position.get('product') or 'INTRADAY'
    
    # Place order
    result = broker.place_order(
        symbol=symbol,
        action=action,
        quantity=close_qty,
        exchange=exchange,
        order_type="MARKET",
        product_type=product_type
    )
    
    if result.get('status') == 'success':
        clear_broker_cache()
        return {
            "status": "success",
            "message": f"Closed {close_qty} of {symbol}",
            "order_id": result.get('order_id'),
            "quantity_closed": close_qty,
            "remaining": abs(net_qty) - close_qty
        }
    else:
        raise HTTPException(status_code=400, detail=result.get('message', 'Square-off failed'))


@router.put("/orders/{order_id}")
async def modify_existing_order(
    order_id: str,
    quantity: Optional[int] = None,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Modify an existing open order.
    
    Args:
        order_id: ID of order to modify
        quantity: New quantity (optional)
        price: New price (optional)
        trigger_price: New trigger price for SL orders (optional)
    """
    # Get active broker
    settings = db.query(AppSettings).first()
    if not settings or not settings.active_broker_type:
        broker = broker_service
    else:
        broker = broker_registry.create_broker(settings.active_broker_type)
    
    if not broker.is_logged_in:
        raise HTTPException(status_code=401, detail="Broker not logged in")
    
    if not any([quantity, price, trigger_price]):
        raise HTTPException(status_code=400, detail="At least one modification parameter is required")
    
    result = broker.modify_order(
        order_id=order_id,
        quantity=quantity,
        price=price,
        trigger_price=trigger_price
    )
    
    if result.get('status') == 'success':
        clear_broker_cache()
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get('message', 'Modification failed'))


