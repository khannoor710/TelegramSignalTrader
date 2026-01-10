"""
Shoonya (Finvasia) broker implementation.
Implements BrokerInterface for Shoonya's API.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import hashlib

try:
    from NorenRestApiPy.NorenApi import NorenApi
except ImportError:
    NorenApi = None

from app.services.broker_interface import BrokerInterface

logger = logging.getLogger(__name__)


class ShoonyaBrokerService(BrokerInterface):
    """
    Shoonya (Finvasia) broker implementation.
    Requires NorenRestApiPy library: pip install NorenRestApiPy
    """
    
    def __init__(self):
        self._api: Optional[NorenApi] = None
        self._client_id: Optional[str] = None
        self._is_logged_in: bool = False
        
        if NorenApi is None:
            logger.warning(
                "NorenRestApiPy library not installed. "
                "Shoonya broker will not be functional. "
                "Install with: pip install NorenRestApiPy"
            )
    
    @property
    def is_logged_in(self) -> bool:
        """Check if broker is logged in."""
        return self._is_logged_in and self._api is not None
    
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
        Login to Shoonya account.
        
        Args:
            api_key: Vendor code (VC) from Shoonya
            client_id: User ID
            password: Trading password
            totp_secret: TOTP token (6-digit OTP) or TOTP secret for auto-generation
            
        Returns:
            Dict with login status
        """
        if NorenApi is None:
            return {
                "status": "error",
                "message": "NorenRestApiPy library not installed. Run: pip install NorenRestApiPy"
            }
        
        try:
            self._api = NorenApi(
                host='https://api.shoonya.com/NorenWClientTP/',
                websocket='wss://api.shoonya.com/NorenWSTP/'
            )
            
            self._client_id = client_id
            
            # Generate TOTP if secret provided
            totp_token = totp_secret
            if totp_secret and len(totp_secret) > 10:
                # Assume it's TOTP secret, generate token
                try:
                    import pyotp
                    totp = pyotp.TOTP(totp_secret)
                    totp_token = totp.now()
                except Exception as e:
                    logger.warning(f"TOTP generation failed: {e}")
                    totp_token = totp_secret
            
            # Generate password hash
            pwd_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Login to Shoonya
            result = self._api.login(
                userid=client_id,
                password=pwd_hash,
                twoFA=totp_token if totp_token else '',
                vendor_code=api_key,
                api_secret=client_id,  # Shoonya uses userid as api_secret
                imei='abc1234'
            )
            
            if result and result.get('stat') == 'Ok':
                self._is_logged_in = True
                return {
                    "status": "success",
                    "message": "Successfully logged in to Shoonya",
                    "session_token": result.get('susertoken', '')
                }
            else:
                error_msg = result.get('emsg', 'Login failed') if result else 'Login failed'
                return {
                    "status": "error",
                    "message": f"Login failed: {error_msg}"
                }
        
        except Exception as e:
            logger.error(f"Shoonya login failed: {str(e)}")
            self._is_logged_in = False
            return {
                "status": "error",
                "message": f"Login failed: {str(e)}"
            }
    
    def logout(self) -> None:
        """Logout from Shoonya account."""
        try:
            if self._api:
                self._api.logout()
        except Exception as e:
            logger.warning(f"Logout warning: {str(e)}")
        finally:
            self._api = None
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
        Place an order on Shoonya.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE-EQ")
            action: BUY or SELL
            quantity: Number of shares
            order_type: MARKET, LIMIT, SL-LMT, SL-MKT
            price: Limit price
            exchange: NSE, BSE, NFO, etc.
            product_type: MIS (intraday), CNC (delivery), NRML (F&O)
            
        Returns:
            Dict with order_id and status
        """
        if not self.is_logged_in:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            # Map order types
            shoonya_order_type = {
                "MARKET": "MKT",
                "LIMIT": "LMT",
                "SL": "SL-LMT",
                "SL-M": "SL-MKT"
            }.get(order_type, "MKT")
            
            # Map product types
            shoonya_product = {
                "INTRADAY": "I",
                "MIS": "I",
                "DELIVERY": "C",
                "CNC": "C",
                "MARGIN": "M",
                "NRML": "M"
            }.get(product_type, "I")
            
            # Transaction type
            transaction_type = "B" if action == "BUY" else "S"
            
            # Add exchange suffix if not present
            if "-" not in symbol:
                symbol = f"{symbol}-EQ"
            
            # Place order
            result = self._api.place_order(
                buy_or_sell=transaction_type,
                product_type=shoonya_product,
                exchange=exchange,
                tradingsymbol=symbol,
                quantity=quantity,
                discloseqty=0,
                price_type=shoonya_order_type,
                price=price if price else 0,
                trigger_price=None,
                retention='DAY',
                remarks=f'API Order'
            )
            
            if result and result.get('stat') == 'Ok':
                return {
                    "status": "success",
                    "order_id": result.get('norenordno'),
                    "message": f"Order placed successfully: {result.get('norenordno')}"
                }
            else:
                error_msg = result.get('emsg', 'Order failed') if result else 'Order failed'
                return {
                    "status": "error",
                    "message": error_msg
                }
        
        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def cancel_order(self, order_id: str, variety: str = "NORMAL") -> Dict[str, Any]:
        """Cancel an order."""
        if not self.is_logged_in:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            result = self._api.cancel_order(orderno=order_id)
            
            if result and result.get('stat') == 'Ok':
                return {
                    "status": "success",
                    "message": f"Order {order_id} cancelled"
                }
            else:
                error_msg = result.get('emsg', 'Cancel failed') if result else 'Cancel failed'
                return {"status": "error", "message": error_msg}
        
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
            params = {"orderno": order_id}
            
            if quantity is not None:
                params["quantity"] = quantity
            if price is not None:
                params["price"] = price
            if order_type is not None:
                params["price_type"] = order_type
            
            result = self._api.modify_order(**params)
            
            if result and result.get('stat') == 'Ok':
                return {
                    "status": "success",
                    "message": f"Order {order_id} modified"
                }
            else:
                error_msg = result.get('emsg', 'Modify failed') if result else 'Modify failed'
                return {"status": "error", "message": error_msg}
        
        except Exception as e:
            logger.error(f"Modify order failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_positions(self) -> Dict[str, Any]:
        """Get current positions."""
        if not self.is_logged_in:
            return {"status": "error", "data": []}
        
        try:
            result = self._api.get_positions()
            
            if result and isinstance(result, list):
                return {"status": "success", "data": result}
            else:
                return {"status": "error", "data": [], "message": "No positions data"}
        
        except Exception as e:
            logger.error(f"Get positions failed: {str(e)}")
            return {"status": "error", "data": [], "message": str(e)}
    
    def get_holdings(self) -> Dict[str, Any]:
        """Get holdings (long-term investments)."""
        if not self.is_logged_in:
            return {"status": "error", "data": []}
        
        try:
            result = self._api.get_holdings()
            
            if result and isinstance(result, list):
                return {"status": "success", "data": result}
            else:
                return {"status": "error", "data": [], "message": "No holdings data"}
        
        except Exception as e:
            logger.error(f"Get holdings failed: {str(e)}")
            return {"status": "error", "data": [], "message": str(e)}
    
    def get_orders(self) -> Dict[str, Any]:
        """Get all orders for the day."""
        if not self.is_logged_in:
            return {"status": "error", "data": []}
        
        try:
            result = self._api.get_order_book()
            
            if result and isinstance(result, list):
                return {"status": "success", "data": result}
            else:
                return {"status": "error", "data": [], "message": "No orders data"}
        
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
            result = self._api.single_order_history(orderno=order_id)
            
            if result and isinstance(result, list) and len(result) > 0:
                latest = result[-1]
                return {
                    "status": "success",
                    "order_status": latest.get("status"),
                    "data": latest
                }
            else:
                return {"status": "error", "message": "Order not found"}
        
        except Exception as e:
            logger.error(f"Get order status failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_funds(self) -> Dict[str, Any]:
        """Get account funds/margins."""
        if not self.is_logged_in:
            return {"status": "error", "data": None}
        
        try:
            result = self._api.get_limits()
            
            if result and result.get('stat') == 'Ok':
                return {
                    "status": "success",
                    "data": {
                        "available_cash": float(result.get('cash', 0)),
                        "used_margin": float(result.get('marginused', 0)),
                        "available_margin": float(result.get('marginused', 0))
                    }
                }
            else:
                error_msg = result.get('emsg', 'Failed to get funds') if result else 'Failed'
                return {"status": "error", "data": None, "message": error_msg}
        
        except Exception as e:
            logger.error(f"Get funds failed: {str(e)}")
            return {"status": "error", "data": None, "message": str(e)}
    
    def search_symbols(self, query: str, exchange: str = None) -> List[Dict[str, Any]]:
        """
        Search for trading symbols.
        
        Args:
            query: Search query
            exchange: Exchange filter (NSE, BSE, etc.)
            
        Returns:
            List of matching symbols
        """
        if not self.is_logged_in:
            return []
        
        try:
            # Shoonya requires exchange for search
            if not exchange:
                exchange = "NSE"
            
            result = self._api.searchscrip(exchange=exchange, searchtext=query)
            
            if result and result.get('stat') == 'Ok' and 'values' in result:
                symbols = []
                for item in result['values'][:20]:  # Limit to 20 results
                    symbols.append({
                        "symbol": item.get('tsym'),
                        "name": item.get('cname', ''),
                        "exchange": item.get('exch'),
                        "token": item.get('token'),
                        "instrument_type": item.get('instname', 'EQ')
                    })
                return symbols
            else:
                return []
        
        except Exception as e:
            logger.error(f"Symbol search failed: {str(e)}")
            return []
    
    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """
        Get last traded price for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange (NSE, BSE, etc.)
            
        Returns:
            Dict with LTP data
        """
        if not self.is_logged_in:
            return {"status": "error", "ltp": None}
        
        try:
            # Add exchange suffix if not present
            if "-" not in symbol:
                symbol = f"{symbol}-EQ"
            
            result = self._api.get_quotes(
                exchange=exchange,
                token=symbol
            )
            
            if result and result.get('stat') == 'Ok':
                return {
                    "status": "success",
                    "ltp": float(result.get('lp', 0))
                }
            else:
                return {"status": "error", "ltp": None}
        
        except Exception as e:
            logger.error(f"Get LTP failed: {str(e)}")
            return {"status": "error", "ltp": None}
    
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
            # Add exchange suffix if not present
            if "-" not in symbol:
                symbol = f"{symbol}-EQ"
            
            result = self._api.get_quotes(
                exchange=exchange,
                token=symbol
            )
            
            if result and result.get('stat') == 'Ok':
                return result
            else:
                return {}
        
        except Exception as e:
            logger.error(f"Get quote failed: {str(e)}")
            return {}
    
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
        Place a bracket order on Shoonya.
        
        Shoonya supports bracket orders through place_order with book_profit and book_loss.
        """
        if not self.is_logged_in:
            return {"status": "error", "message": "Not logged in"}
        
        try:
            # Add exchange suffix if not present
            if "-" not in symbol:
                symbol = f"{symbol}-EQ"
            
            transaction_type = "B" if action.upper() == "BUY" else "S"
            
            result = self._api.place_order(
                buy_or_sell=transaction_type,
                product_type="B",  # Bracket order
                exchange=exchange,
                tradingsymbol=symbol,
                quantity=quantity,
                discloseqty=0,
                price_type="LMT",
                price=entry_price,
                trigger_price=None,
                retention='DAY',
                book_loss_price=stop_loss,
                book_profit_price=target_price
            )
            
            if result and result.get('stat') == 'Ok':
                return {
                    "status": "success",
                    "order_id": result.get('norenordno'),
                    "message": "Bracket order placed successfully",
                    "entry_price": entry_price,
                    "target_price": target_price,
                    "stop_loss": stop_loss
                }
            else:
                error_msg = result.get('emsg', 'BO failed') if result else 'BO failed'
                return {"status": "error", "message": error_msg}
        
        except Exception as e:
            logger.error(f"Bracket order failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
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
        Place a GTT (Good Till Triggered) order on Shoonya.
        
        Note: Shoonya's GTT functionality may be limited. Check API documentation.
        """
        if not self.is_logged_in:
            return {"status": "error", "message": "Not logged in"}
        
        # Shoonya may not have native GTT support - return not supported
        return {
            "status": "error",
            "message": "GTT orders are not currently supported on Shoonya. Use bracket orders instead."
        }
    
    def get_all_order_statuses(self) -> Dict[str, Any]:
        """Get all orders with their statuses."""
        if not self.is_logged_in:
            return {"status": "error", "message": "Not logged in", "orders": []}
        
        try:
            result = self._api.get_order_book()
            
            if not result or not isinstance(result, list):
                return {"status": "success", "orders": []}
            
            order_list = []
            for order in result:
                status = order.get("status", "").lower()
                
                # Map Shoonya statuses to internal statuses
                if status in ["complete", "fill"]:
                    internal_status = "EXECUTED"
                elif status == "rejected":
                    internal_status = "REJECTED"
                elif status in ["cancelled", "cancel"]:
                    internal_status = "CANCELLED"
                elif status in ["open", "pending", "trigger_pending"]:
                    internal_status = "OPEN"
                else:
                    internal_status = "PENDING"
                
                order_list.append({
                    "order_id": order.get("norenordno"),
                    "broker_status": status,
                    "internal_status": internal_status,
                    "symbol": order.get("tsym"),
                    "quantity": int(order.get("qty", 0)),
                    "filled_quantity": int(order.get("fillshares", 0)),
                    "average_price": float(order.get("avgprc", 0) or 0),
                    "rejection_reason": order.get("rejreason") if status == "rejected" else None
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
            result = self._api.get_user_details()
            
            if result and result.get('stat') == 'Ok':
                return {
                    "status": "success",
                    "data": result
                }
            else:
                error_msg = result.get('emsg', 'Failed') if result else 'Failed'
                return {"status": "error", "message": error_msg}
        
        except Exception as e:
            logger.error(f"Get profile failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def refresh_instruments(self) -> bool:
        """
        Refresh instrument master data.
        
        Note: Shoonya doesn't require explicit instrument refresh.
        Instruments are fetched on-demand via search.
        """
        return True  # Always return True as no refresh needed


# Only create singleton if library is available
if NorenApi is not None:
    shoonya_broker_service = ShoonyaBrokerService()
else:
    shoonya_broker_service = None
    logger.warning("Shoonya broker service not available (NorenRestApiPy not installed)")
