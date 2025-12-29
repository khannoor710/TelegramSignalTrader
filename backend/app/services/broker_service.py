"""
Angel One broker service for order execution
"""
try:
    from SmartApi.smartConnect import SmartConnect
except ImportError as e:
    raise ImportError("SmartAPI is not installed or is broken. Please run 'pip install smartapi-python logzero websocket-client' in your backend environment.") from e

from typing import Optional, Dict, Any, List
import pyotp
import requests
import json
from datetime import datetime
from pathlib import Path

from app.core.database import SessionLocal
from app.models.models import BrokerConfig
from app.services.broker_interface import BrokerInterface


class SymbolMaster:
    """Manages Angel One symbol/token mapping"""
    
    INSTRUMENT_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "scripmaster.json"
    
    def __init__(self):
        self._instruments: Dict[str, Dict] = {}
        self._loaded = False
    
    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    def load_instruments(self, force_refresh: bool = False) -> bool:
        """Load instrument master data"""
        if self._loaded and not force_refresh:
            return True
        
        self._ensure_data_dir()
        
        # Try to load from cache first
        if not force_refresh and self.CACHE_FILE.exists():
            try:
                cache_age = datetime.now().timestamp() - self.CACHE_FILE.stat().st_mtime
                # Cache valid for 24 hours
                if cache_age < 86400:
                    with open(self.CACHE_FILE, 'r') as f:
                        instruments_list = json.load(f)
                        self._build_index(instruments_list)
                        self._loaded = True
                        print(f"✅ Loaded {len(self._instruments)} instruments from cache")
                        return True
            except Exception as e:
                print(f"⚠️ Failed to load cache: {e}")
        
        # Download fresh data
        try:
            print("📥 Downloading instrument master...")
            response = requests.get(self.INSTRUMENT_URL, timeout=30)
            response.raise_for_status()
            instruments_list = response.json()
            
            # Save to cache
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(instruments_list, f)
            
            self._build_index(instruments_list)
            self._loaded = True
            print(f"✅ Downloaded and indexed {len(self._instruments)} instruments")
            return True
            
        except Exception as e:
            print(f"❌ Failed to download instrument master: {e}")
            return False
    
    def _build_index(self, instruments_list: list):
        """Build searchable index from instruments list"""
        self._instruments = {}
        for inst in instruments_list:
            # Create key as exchange:symbol for quick lookup
            key = f"{inst.get('exch_seg', '')}:{inst.get('symbol', '')}"
            self._instruments[key] = inst
            
            # Also index by trading symbol
            trading_key = f"{inst.get('exch_seg', '')}:{inst.get('name', '')}"
            if trading_key not in self._instruments:
                self._instruments[trading_key] = inst
    
    def get_token(self, symbol: str, exchange: str = "NSE") -> Optional[str]:
        """Get symbol token for a given symbol and exchange"""
        if not self._loaded:
            self.load_instruments()
        
        # Try exact match first
        key = f"{exchange}:{symbol}"
        if key in self._instruments:
            return self._instruments[key].get('token')
        
        # Try with -EQ suffix for NSE equity
        if exchange == "NSE":
            eq_key = f"{exchange}:{symbol}-EQ"
            if eq_key in self._instruments:
                return self._instruments[eq_key].get('token')
        
        # Search by name
        for inst_key, inst in self._instruments.items():
            if inst.get('name', '').upper() == symbol.upper() and inst.get('exch_seg') == exchange:
                return inst.get('token')
        
        return None
    
    def search_symbol(self, query: str, exchange: str = None, limit: int = 10) -> list:
        """Search for symbols matching query"""
        if not self._loaded:
            self.load_instruments()
        
        results = []
        seen = set()  # Track unique results by token+exchange
        query_upper = query.upper()
        
        for key, inst in self._instruments.items():
            if len(results) >= limit:
                break
            
            name = inst.get('name', '').upper()
            symbol = inst.get('symbol', '').upper()
            token = inst.get('token', '')
            exch = inst.get('exch_seg', '')
            
            # Create unique key to avoid duplicates
            unique_key = f"{token}:{exch}"
            if unique_key in seen:
                continue
            
            if query_upper in name or query_upper in symbol:
                if exchange is None or exch == exchange:
                    seen.add(unique_key)
                    results.append({
                        'symbol': inst.get('symbol'),
                        'name': inst.get('name'),
                        'token': token,
                        'exchange': exch,
                        'instrument_type': inst.get('instrumenttype', '')
                    })
        
        return results


# Global symbol master instance
symbol_master = SymbolMaster()


class AngelOneBrokerService(BrokerInterface):
    """Angel One implementation of BrokerInterface."""
    
    def __init__(self):
        self.smart_api = None  # Will be SmartConnect instance
        self._client_id: Optional[str] = None
        self._is_logged_in = False
        self._try_restore_session()  # Try to restore from saved session
    
    def _try_restore_session(self):
        """Try to restore session from saved tokens"""
        try:
            from app.core.encryption import get_encryption_manager
            
            db = SessionLocal()
            try:
                # Get the most recent Angel One config with valid session
                config = db.query(BrokerConfig).filter(
                    BrokerConfig.broker_name == 'angel_one',
                    BrokerConfig.auth_token.isnot(None),
                    BrokerConfig.session_expiry > datetime.utcnow()
                ).order_by(BrokerConfig.last_login.desc()).first()
                
                if not config:
                    print("ℹ️ No saved broker session found")
                    return  # No valid session found
                
                # Get encryption manager
                encryption_manager = get_encryption_manager()
                
                # Decrypt tokens
                jwt_token = encryption_manager.decrypt(config.auth_token)
                
                # Restore SmartAPI session
                self.smart_api = SmartConnect(api_key=config.api_key)
                self.smart_api.setAccessToken(jwt_token)
                
                # Validate the session actually works by making a test call
                try:
                    profile = self.smart_api.getProfile(config.client_id)
                    if profile and profile.get('status', False):
                        self._client_id = config.client_id
                        self._is_logged_in = True
                        print(f"✅ Restored and validated broker session for {config.client_id}")
                    else:
                        print(f"⚠️ Saved session for {config.client_id} is invalid, need re-login")
                        self.smart_api = None
                except Exception as validation_error:
                    print(f"⚠️ Session validation failed: {validation_error}")
                    self.smart_api = None
                
            finally:
                db.close()
        except Exception as e:
            print(f"⚠️ Failed to restore broker session: {e}")
            # Not a critical error - user can re-login
    
    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in
    
    @property
    def client_id(self) -> Optional[str]:
        return self._client_id
    
    def login(self, api_key: str, client_id: str, password: str, totp_secret: Optional[str] = None) -> Dict[str, Any]:
        """Login to Angel One broker"""
        try:
            self.smart_api = SmartConnect(api_key=api_key)
            
            # Generate TOTP if secret is provided
            totp_token = None
            if totp_secret:
                totp = pyotp.TOTP(totp_secret)
                totp_token = totp.now()
            
            # Login
            data = self.smart_api.generateSession(client_id, password, totp_token)
            
            if data['status']:
                self._client_id = client_id
                self._is_logged_in = True
                
                # Update database and save session tokens
                db = SessionLocal()
                try:
                    from app.core.encryption import get_encryption_manager
                    from datetime import timedelta
                    
                    # Get encryption manager
                    encryption_manager = get_encryption_manager()
                    
                    # Find config by broker_name and client_id for accuracy
                    config = db.query(BrokerConfig).filter(
                        BrokerConfig.broker_name == 'angel_one',
                        BrokerConfig.client_id == client_id
                    ).first()
                    
                    # Fallback: try just by client_id if not found
                    if not config:
                        config = db.query(BrokerConfig).filter(
                            BrokerConfig.client_id == client_id
                        ).first()
                    
                    if config:
                        config.is_active = True
                        config.last_login = datetime.utcnow()
                        
                        # Save encrypted session tokens for persistence
                        tokens_saved = []
                        
                        # Debug: Log the full response structure
                        print(f"📊 Login response: {data}")
                        
                        # Extract tokens from various possible locations in the response
                        token_source = None
                        
                        # Check nested 'data' first (most common)
                        if 'data' in data and isinstance(data['data'], dict) and data['data']:
                            token_source = data['data']
                            print(f"📊 Using nested data for tokens: {list(token_source.keys())}")
                        # Check top level
                        elif 'jwtToken' in data:
                            token_source = data
                            print(f"📊 Using top-level data for tokens")
                        
                        # Also try to get tokens directly from SmartAPI object
                        if not token_source or 'jwtToken' not in token_source:
                            if hasattr(self.smart_api, 'access_token') and self.smart_api.access_token:
                                token_source = token_source or {}
                                token_source['jwtToken'] = self.smart_api.access_token
                                print(f"📊 Got jwtToken from SmartAPI object")
                            if hasattr(self.smart_api, 'refresh_token') and self.smart_api.refresh_token:
                                token_source = token_source or {}
                                token_source['refreshToken'] = self.smart_api.refresh_token
                                print(f"📊 Got refreshToken from SmartAPI object")
                            if hasattr(self.smart_api, 'feed_token') and self.smart_api.feed_token:
                                token_source = token_source or {}
                                token_source['feedToken'] = self.smart_api.feed_token
                                print(f"📊 Got feedToken from SmartAPI object")
                            
                        if token_source:
                            if 'jwtToken' in token_source and token_source['jwtToken']:
                                config.auth_token = encryption_manager.encrypt(token_source['jwtToken'])
                                tokens_saved.append('auth')
                            if 'refreshToken' in token_source and token_source['refreshToken']:
                                config.refresh_token = encryption_manager.encrypt(token_source['refreshToken'])
                                tokens_saved.append('refresh')
                            if 'feedToken' in token_source and token_source['feedToken']:
                                config.feed_token = encryption_manager.encrypt(token_source['feedToken'])
                                tokens_saved.append('feed')
                        
                        if not tokens_saved:
                            print("⚠️ No tokens could be extracted from response or SmartAPI object")
                        
                        # Set expiry (Angel One sessions typically last 24 hours)
                        config.session_expiry = datetime.utcnow() + timedelta(hours=24)
                        
                        db.commit()
                        print(f"✅ Session tokens saved for {client_id}: {tokens_saved}")
                    else:
                        print(f"⚠️ No config found for client_id {client_id}, tokens not saved")
                except Exception as e:
                    print(f"❌ Error saving session tokens: {e}")
                    import traceback
                    traceback.print_exc()
                    db.rollback()
                finally:
                    db.close()
                
                return {
                    "status": "success",
                    "message": "Logged in successfully",
                    "data": data.get('data', data)
                }
            else:
                return {
                    "status": "error",
                    "message": data.get('message', 'Login failed')
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def place_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        exchange: str = "NSE",
        order_type: str = "MARKET",
        product_type: str = "INTRADAY",
        price: Optional[float] = None,
        trigger_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Place order on Angel One"""
        if not self._is_logged_in or not self.smart_api:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            # Map our order types to Angel One format
            order_type_map = {
                "MARKET": "MARKET",
                "LIMIT": "LIMIT",
                "SL": "STOPLOSS_LIMIT",
                "SL-M": "STOPLOSS_MARKET"
            }
            
            product_type_map = {
                "INTRADAY": "INTRADAY",
                "DELIVERY": "DELIVERY",
                "MARGIN": "MARGIN"
            }
            
            transaction_type = "BUY" if action.upper() == "BUY" else "SELL"
            
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": self._get_symbol_token(symbol, exchange),
                "transactiontype": transaction_type,
                "exchange": exchange,
                "ordertype": order_type_map.get(order_type, "MARKET"),
                "producttype": product_type_map.get(product_type, "INTRADAY"),
                "duration": "DAY",
                "quantity": quantity
            }
            
            if price and order_type in ["LIMIT", "SL"]:
                order_params["price"] = price
            
            if trigger_price and order_type in ["SL", "SL-M"]:
                order_params["triggerprice"] = trigger_price
            
            response = self.smart_api.placeOrder(order_params)
            
            if response['status']:
                return {
                    "status": "success",
                    "message": "Order placed successfully",
                    "order_id": response['data']['orderid']
                }
            else:
                return {
                    "status": "error",
                    "message": response.get('message', 'Order placement failed')
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        if not self._is_logged_in or not self.smart_api:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            response = self.smart_api.orderBook()
            if response['status']:
                orders = response['data']
                for order in orders:
                    if order['orderid'] == order_id:
                        return {
                            "status": "success",
                            "data": order
                        }
                return {
                    "status": "error",
                    "message": "Order not found"
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to fetch order book"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_positions(self) -> Dict[str, Any]:
        """Get current positions"""
        if not self._is_logged_in or not self.smart_api:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            response = self.smart_api.position()
            return response
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_holdings(self) -> Dict[str, Any]:
        """Get long-term holdings (delivery stocks)"""
        if not self._is_logged_in or not self.smart_api:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            response = self.smart_api.holding()
            return response
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_order_book(self) -> Dict[str, Any]:
        """Get all orders for today"""
        if not self._is_logged_in or not self.smart_api:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            response = self.smart_api.orderBook()
            return response
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_funds(self) -> Dict[str, Any]:
        """Get account funds/margin"""
        if not self._is_logged_in or not self.smart_api:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            response = self.smart_api.rmsLimit()
            return response
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """Get last traded price for a symbol"""
        if not self._is_logged_in or not self.smart_api:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            token = self._get_symbol_token(symbol, exchange)
            response = self.smart_api.ltpData(exchange, symbol, token)
            return response
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def cancel_order(self, order_id: str, variety: str = "NORMAL") -> Dict[str, Any]:
        """Cancel an open order"""
        if not self._is_logged_in or not self.smart_api:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            response = self.smart_api.cancelOrder(order_id, variety)
            if response['status']:
                return {
                    "status": "success",
                    "message": "Order cancelled successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": response.get('message', 'Cancel failed')
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _get_symbol_token(self, symbol: str, exchange: str) -> str:
        """Get symbol token from Angel One using symbol master"""
        token = symbol_master.get_token(symbol, exchange)
        if token:
            return token
        
        # Fallback: try to search
        results = symbol_master.search_symbol(symbol, exchange, limit=1)
        if results:
            return results[0].get('token', '0')
        
        print(f"⚠️ Could not find token for {symbol} on {exchange}")
        return "0"
    
    def search_symbols(self, query: str, exchange: str = None) -> List[Dict[str, Any]]:
        """Search for symbols in the instrument master"""
        return symbol_master.search_symbol(query, exchange)
    
    def refresh_instruments(self) -> bool:
        """Force refresh of instrument master data"""
        return symbol_master.load_instruments(force_refresh=True)
    
    def logout(self) -> None:
        """Logout from broker"""
        if self.smart_api:
            try:
                self.smart_api.terminateSession(self._client_id)
            except Exception:
                pass
        
        self._is_logged_in = False
        self.smart_api = None


# Global instance
broker_service = AngelOneBrokerService()
