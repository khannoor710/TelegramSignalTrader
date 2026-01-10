"""
Zerodha Kite broker implementation.
Implements BrokerInterface for Zerodha's Kite Connect API.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

try:
    from kiteconnect import KiteConnect
except ImportError:
    KiteConnect = None

from app.services.broker_interface import BrokerInterface

logger = logging.getLogger(__name__)


class ZerodhaBrokerService(BrokerInterface):
    """
    Zerodha Kite broker implementation.
    Requires pykiteconnect library: pip install kiteconnect
    """
    
    def __init__(self):
        self._kite: Optional[KiteConnect] = None
        self._api_key: Optional[str] = None
        self._access_token: Optional[str] = None
        self._client_id: Optional[str] = None
        self._is_logged_in: bool = False
        
        # Don't raise error on init, only when trying to use
        if KiteConnect is None:
            logger.warning(
                "kiteconnect library not installed. "
                "Zerodha broker will not be functional. "
                "Install with: pip install kiteconnect"
            )
    
    @property
    def is_logged_in(self) -> bool:
        """Check if broker is logged in."""
        return self._is_logged_in and self._kite is not None
    
    @property
    def client_id(self) -> Optional[str]:
        """Get current client ID."""
        return self._client_id
    
    def login(
        self, 
        api_key: str, 
        client_id: str, 
        password: str, 
        totp_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Login to Zerodha account.
        
        Note: Zerodha requires manual login flow:
        1. Get login URL with kite.login_url()
        2. User logs in via browser
        3. User authorizes app
        4. Get request_token from redirect URL
        5. Generate access_token using request_token
        
        For this method, 'password' can be either:
        - request_token from OAuth redirect (for new login)
        - access_token (for session restoration)
        
        Args:
            api_key: Zerodha API key
            client_id: Zerodha client ID (user ID)
            password: Request token from OAuth redirect OR access_token for restoration
            totp_secret: API secret (for OAuth) or None (for token restoration)
            
        Returns:
            Dict with login status
        """
        if KiteConnect is None:
            return {
                "status": "error",
                "message": "kiteconnect library not installed. Run: pip install kiteconnect"
            }
        
        try:
            self._api_key = api_key
            self._client_id = client_id
            
            # Initialize KiteConnect
            self._kite = KiteConnect(api_key=api_key)
            
            # If password is provided
            if password:
                # Check if this is an access token (starts with certain pattern) or request token
                # Access tokens are typically longer and start with specific pattern
                # For simplicity, if totp_secret (api_secret) is provided, it's OAuth flow
                # If not provided, assume password is an access_token for restoration
                
                if totp_secret:
                    # OAuth flow: password is request_token, totp_secret is api_secret
                    api_secret = totp_secret
                    data = self._kite.generate_session(
                        request_token=password,
                        api_secret=api_secret
                    )
                    
                    self._access_token = data["access_token"]
                    self._kite.set_access_token(self._access_token)
                    self._is_logged_in = True
                    
                    return {
                        "status": "success",
                        "message": "Successfully logged in to Zerodha",
                        "access_token": self._access_token
                    }
                else:
                    # Session restoration: password is access_token
                    self._access_token = password
                    self._kite.set_access_token(self._access_token)
                    
                    # Verify token by making a simple API call
                    try:
                        profile = self._kite.profile()
                        self._is_logged_in = True
                        logger.info(f"✅ Zerodha session restored for {profile.get('user_id', client_id)}")
                        return {
                            "status": "success",
                            "message": "Session restored successfully",
                            "access_token": self._access_token
                        }
                    except Exception as e:
                        logger.warning(f"⚠️ Access token validation failed: {str(e)}")
                        self._is_logged_in = False
                        return {
                            "status": "error",
                            "message": f"Saved session invalid: {str(e)}"
                        }
            else:
                # Return login URL for manual login
                login_url = self._kite.login_url()
                return {
                    "status": "pending",
                    "message": "Please complete login via browser",
                    "login_url": login_url
                }
        
        except Exception as e:
            logger.error(f"Zerodha login failed: {str(e)}")
            self._is_logged_in = False
            return {
                "status": "error",
                "message": f"Login failed: {str(e)}"
            }
    
    def logout(self) -> None:
        """Logout from Zerodha account."""
        try:
            if self._kite and self._access_token:
                self._kite.invalidate_access_token(self._access_token)
        except Exception as e:
            logger.warning(f"Logout warning: {str(e)}")
        finally:
            self._kite = None
            self._access_token = None
            self._is_logged_in = False
    
    def place_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        exchange: str = "NSE",
        product_type: str = "MIS"
    ) -> Dict[str, Any]:
        """
        Place an order on Zerodha.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            action: BUY or SELL
            quantity: Number of shares
            order_type: MARKET, LIMIT, SL, SL-M
            price: Limit price (required for LIMIT orders)
            exchange: NSE, BSE, NFO, etc.
            product_type: MIS (intraday), CNC (delivery), NRML (F&O)
            
        Returns:
            Dict with order_id and status
        """
        if not self.is_logged_in:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            # Map order types
            kite_order_type = {
                "MARKET": self._kite.ORDER_TYPE_MARKET,
                "LIMIT": self._kite.ORDER_TYPE_LIMIT,
                "SL": self._kite.ORDER_TYPE_SL,
                "SL-M": self._kite.ORDER_TYPE_SLM
            }.get(order_type, self._kite.ORDER_TYPE_MARKET)
            
            # Map product types
            kite_product = {
                "INTRADAY": self._kite.PRODUCT_MIS,
                "MIS": self._kite.PRODUCT_MIS,
                "DELIVERY": self._kite.PRODUCT_CNC,
                "CNC": self._kite.PRODUCT_CNC,
                "MARGIN": self._kite.PRODUCT_NRML,
                "NRML": self._kite.PRODUCT_NRML
            }.get(product_type, self._kite.PRODUCT_MIS)
            
            # Map transaction type
            transaction_type = self._kite.TRANSACTION_TYPE_BUY if action == "BUY" else self._kite.TRANSACTION_TYPE_SELL
            
            # Place order
            order_id = self._kite.place_order(
                tradingsymbol=symbol,
                exchange=exchange,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=kite_order_type,
                product=kite_product,
                price=price,
                variety=self._kite.VARIETY_REGULAR
            )
            
            return {
                "status": "success",
                "order_id": order_id,
                "message": f"Order placed successfully: {order_id}"
            }
        
        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        if not self.is_logged_in:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            self._kite.cancel_order(
                variety=self._kite.VARIETY_REGULAR,
                order_id=order_id
            )
            return {
                "status": "success",
                "message": f"Order {order_id} cancelled"
            }
        except Exception as e:
            logger.error(f"Cancel order failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Modify an existing order."""
        if not self.is_logged_in:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            params = {"variety": self._kite.VARIETY_REGULAR, "order_id": order_id}
            
            if quantity is not None:
                params["quantity"] = quantity
            if price is not None:
                params["price"] = price
            if order_type is not None:
                params["order_type"] = order_type
            
            self._kite.modify_order(**params)
            return {
                "status": "success",
                "message": f"Order {order_id} modified"
            }
        except Exception as e:
            logger.error(f"Modify order failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_positions(self) -> Dict[str, Any]:
        """Get current positions."""
        if not self.is_logged_in:
            return {"status": "error", "data": []}
        
        try:
            positions = self._kite.positions()
            return {
                "status": "success",
                "data": positions.get("net", [])
            }
        except Exception as e:
            logger.error(f"Get positions failed: {str(e)}")
            return {"status": "error", "data": [], "message": str(e)}
    
    def get_holdings(self) -> Dict[str, Any]:
        """Get holdings (long-term investments)."""
        if not self.is_logged_in:
            return {"status": "error", "data": []}
        
        try:
            holdings = self._kite.holdings()
            return {"status": "success", "data": holdings}
        except Exception as e:
            logger.error(f"Get holdings failed: {str(e)}")
            return {"status": "error", "data": [], "message": str(e)}
    
    def get_orders(self) -> Dict[str, Any]:
        """Get all orders for the day."""
        if not self.is_logged_in:
            return {"status": "error", "data": []}
        
        try:
            orders = self._kite.orders()
            return {"status": "success", "data": orders}
        except Exception as e:
            logger.error(f"Get orders failed: {str(e)}")
            return {"status": "error", "data": [], "message": str(e)}
    
    def get_order_book(self) -> Dict[str, Any]:
        """Get all orders for today (alias for get_orders)."""
        return self.get_orders()
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a specific order."""
        if not self.is_logged_in:
            return {"status": "error"}
        
        try:
            order_history = self._kite.order_history(order_id=order_id)
            if order_history:
                latest = order_history[-1]
                return {
                    "status": "success",
                    "order_status": latest.get("status"),
                    "data": latest
                }
            return {"status": "error", "message": "Order not found"}
        except Exception as e:
            logger.error(f"Get order status failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_funds(self) -> Dict[str, Any]:
        """Get account funds/margins."""
        if not self.is_logged_in:
            return {"status": "error", "data": None}
        
        try:
            margins = self._kite.margins()
            equity = margins.get("equity", {})
            return {
                "status": "success",
                "data": {
                    "available_cash": equity.get("available", {}).get("cash", 0),
                    "used_margin": equity.get("utilised", {}).get("debits", 0),
                    "available_margin": equity.get("available", {}).get("live_balance", 0)
                }
            }
        except Exception as e:
            logger.error(f"Get funds failed: {str(e)}")
            return {"status": "error", "data": None, "message": str(e)}
    
    def search_symbols(self, query: str, exchange: str = None) -> List[Dict[str, Any]]:
        """
        Search for trading symbols.
        
        Args:
            query: Search query
            exchange: Optional exchange filter (NSE, BSE, NFO, etc.)
            
        Returns:
            List of matching symbols
        """
        if not self.is_logged_in:
            return []
        
        try:
            # Get instruments (optionally filter by exchange)
            if exchange:
                instruments = self._kite.instruments(exchange)
            else:
                instruments = self._kite.instruments()
            
            # Filter by query
            query_upper = query.upper()
            results = []
            
            for inst in instruments:
                if query_upper in inst.get("tradingsymbol", "").upper():
                    results.append({
                        "symbol": inst.get("tradingsymbol"),
                        "name": inst.get("name", ""),
                        "exchange": inst.get("exchange"),
                        "instrument_token": inst.get("instrument_token"),
                        "instrument_type": inst.get("instrument_type")
                    })
                    
                    if len(results) >= 20:
                        break
            
            return results
        except Exception as e:
            logger.error(f"Symbol search failed: {str(e)}")
            return []
    
    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Optional[float]:
        """
        Get last traded price for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange (NSE, BSE, etc.)
            
        Returns:
            Last traded price or None
        """
        if not self.is_logged_in:
            return None
        
        try:
            key = f"{exchange}:{symbol}"
            ltp_data = self._kite.ltp([key])
            return ltp_data.get(key, {}).get("last_price")
        except Exception as e:
            logger.error(f"Get LTP failed: {str(e)}")
            return None
    
    def get_quote(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """
        Get detailed quote for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange
            
        Returns:
            Quote data dictionary
        """
        if not self.is_logged_in:
            return {}
        
        try:
            key = f"{exchange}:{symbol}"
            quote = self._kite.quote([key])
            return quote.get(key, {})
        except Exception as e:
            logger.error(f"Get quote failed: {str(e)}")
            return {}
    
    def refresh_instruments(self) -> bool:
        """
        Refresh instrument master data.
        
        Note: Zerodha instruments are fetched on-demand.
        This method returns True for compatibility but doesn't cache data.
        """
        if not self.is_logged_in:
            return False
        
        try:
            # Verify we can fetch instruments
            instruments = self._kite.instruments()
            return len(instruments) > 0
        except Exception as e:
            logger.error(f"Refresh instruments failed: {str(e)}")
            return False
    
    def place_bracket_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        entry_price: float,
        target_price: float,
        stop_loss: float,
        exchange: str = "NSE",
        product_type: str = "INTRADAY",
        trailing_sl: float = None
    ) -> Dict[str, Any]:
        """
        Place a bracket order (BO).
        
        Note: Zerodha has discontinued bracket orders.
        This method is kept for interface compatibility but will return an error.
        Use GTT orders instead for target/stoploss triggers.
        """
        return {
            "status": "error",
            "message": "Bracket orders are no longer supported by Zerodha. Use GTT orders instead."
        }
    
    def place_gtt_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        trigger_price: float,
        price: float,
        exchange: str = "NSE",
        order_type: str = "LIMIT"
    ) -> Dict[str, Any]:
        """
        Place a GTT (Good Till Triggered) order on Zerodha.
        
        Zerodha supports GTT via the gtt_place_order API.
        """
        if not self.is_logged_in:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            transaction_type = self._kite.TRANSACTION_TYPE_BUY if action.upper() == "BUY" else self._kite.TRANSACTION_TYPE_SELL
            
            # For single trigger GTT
            gtt_params = {
                "trigger_type": self._kite.GTT_TYPE_SINGLE,
                "tradingsymbol": symbol,
                "exchange": exchange,
                "trigger_values": [trigger_price],
                "last_price": trigger_price,  # Will be replaced with actual LTP
                "orders": [{
                    "transaction_type": transaction_type,
                    "quantity": quantity,
                    "order_type": self._kite.ORDER_TYPE_LIMIT if order_type == "LIMIT" else self._kite.ORDER_TYPE_MARKET,
                    "product": self._kite.PRODUCT_CNC,
                    "price": price
                }]
            }
            
            # Get current LTP
            try:
                ltp = self.get_ltp(symbol, exchange)
                if ltp:
                    gtt_params["last_price"] = ltp
            except Exception:
                pass
            
            if hasattr(self._kite, 'gtt_place_order'):
                result = self._kite.place_gtt(**gtt_params)
                return {
                    "status": "success",
                    "gtt_id": result.get("trigger_id"),
                    "message": "GTT order created successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": "GTT not supported in current kiteconnect version"
                }
                
        except Exception as e:
            logger.error(f"GTT order failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_all_order_statuses(self) -> Dict[str, Any]:
        """Get all orders with their statuses."""
        if not self.is_logged_in:
            return {"status": "error", "message": "Not logged in", "orders": []}
        
        try:
            orders = self._kite.orders()
            order_list = []
            
            for order in orders:
                status = order.get("status", "").lower()
                
                # Map Zerodha statuses to internal statuses
                if status == "complete":
                    internal_status = "EXECUTED"
                elif status == "rejected":
                    internal_status = "REJECTED"
                elif status == "cancelled":
                    internal_status = "CANCELLED"
                elif status in ["open", "pending", "trigger pending"]:
                    internal_status = "OPEN"
                else:
                    internal_status = "PENDING"
                
                order_list.append({
                    "order_id": order.get("order_id"),
                    "broker_status": status,
                    "internal_status": internal_status,
                    "symbol": order.get("tradingsymbol"),
                    "quantity": order.get("quantity"),
                    "filled_quantity": order.get("filled_quantity", 0),
                    "average_price": order.get("average_price", 0),
                    "rejection_reason": order.get("status_message") if status == "rejected" else None
                })
            
            return {"status": "success", "orders": order_list}
            
        except Exception as e:
            logger.error(f"Get all order statuses failed: {str(e)}")
            return {"status": "error", "message": str(e), "orders": []}
    
    def get_profile(self) -> Dict[str, Any]:
        """Get user profile information."""
        if not self.is_logged_in:
            return {"status": "error"}
        
        try:
            profile = self._kite.profile()
            return {
                "status": "success",
                "data": profile
            }
        except Exception as e:
            logger.error(f"Get profile failed: {str(e)}")
            return {"status": "error", "message": str(e)}


# Only create singleton if library is available
if KiteConnect is not None:
    # Global Zerodha broker instance (singleton)
    zerodha_broker_service = ZerodhaBrokerService()
else:
    zerodha_broker_service = None
    logger.warning("Zerodha broker service not available (kiteconnect not installed)")
