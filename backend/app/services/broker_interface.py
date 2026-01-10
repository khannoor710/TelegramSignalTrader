"""
Abstract broker interface for trading operations.
Allows multiple broker implementations (Angel One, Zerodha, etc.) with a common API.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BrokerInterface(ABC):
    """Abstract base class for broker implementations."""
    
    @property
    @abstractmethod
    def is_logged_in(self) -> bool:
        """Check if broker is logged in."""
        pass
    
    @property
    @abstractmethod
    def client_id(self) -> Optional[str]:
        """Get current client ID."""
        pass
    
    @abstractmethod
    def login(
        self, 
        api_key: str, 
        client_id: str, 
        password: str, 
        totp_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Login to broker account.
        
        Returns:
            Dict with 'status' (success/error) and 'message'
        """
        pass
    
    @abstractmethod
    def logout(self) -> None:
        """Logout from broker account."""
        pass
    
    @abstractmethod
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
        """
        Place an order.
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Number of shares/contracts
            exchange: NSE, BSE, NFO, etc.
            order_type: MARKET, LIMIT, SL, SL-M
            product_type: INTRADAY, DELIVERY, MARGIN
            price: Limit price (for LIMIT/SL orders)
            trigger_price: Trigger price (for SL orders)
        
        Returns:
            Dict with 'status', 'message', and 'order_id' if successful
        """
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a specific order."""
        pass
    
    @abstractmethod
    def get_positions(self) -> Dict[str, Any]:
        """Get current open positions."""
        pass
    
    @abstractmethod
    def get_holdings(self) -> Dict[str, Any]:
        """Get long-term holdings (delivery stocks)."""
        pass
    
    @abstractmethod
    def get_order_book(self) -> Dict[str, Any]:
        """Get all orders for today."""
        pass
    
    @abstractmethod
    def get_funds(self) -> Dict[str, Any]:
        """Get account funds and margin information."""
        pass
    
    @abstractmethod
    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """Get last traded price for a symbol."""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, variety: str = "NORMAL") -> Dict[str, Any]:
        """Cancel an open order."""
        pass
    
    @abstractmethod
    def search_symbols(self, query: str, exchange: str = None) -> List[Dict[str, Any]]:
        """Search for trading symbols."""
        pass
    
    @abstractmethod
    def refresh_instruments(self) -> bool:
        """Refresh instrument master data."""
        pass
    
    # ============= Advanced Order Types =============
    
    @abstractmethod
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
        Place a bracket order with entry, target, and stop-loss.
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Number of shares/contracts
            entry_price: Entry limit price
            target_price: Target/profit booking price
            stop_loss: Stop-loss price
            exchange: NSE, BSE, NFO, etc.
            product_type: INTRADAY, DELIVERY
            trailing_sl: Optional trailing stop-loss points
        
        Returns:
            Dict with 'status', 'order_id', 'target_order_id', 'sl_order_id'
        """
        pass
    
    @abstractmethod
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
        Place a GTT (Good Till Triggered) order.
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Number of shares
            trigger_price: Price at which order gets triggered
            price: Order price after trigger
            exchange: Exchange
            order_type: LIMIT or MARKET
        
        Returns:
            Dict with 'status', 'gtt_id', 'message'
        """
        pass
    
    @abstractmethod
    def modify_order(
        self,
        order_id: str,
        quantity: int = None,
        price: float = None,
        trigger_price: float = None,
        order_type: str = None
    ) -> Dict[str, Any]:
        """
        Modify an existing open order.
        
        Args:
            order_id: ID of order to modify
            quantity: New quantity (optional)
            price: New price (optional)
            trigger_price: New trigger price (optional)
            order_type: New order type (optional)
        
        Returns:
            Dict with 'status' and 'message'
        """
        pass
    
    @abstractmethod
    def get_all_order_statuses(self) -> Dict[str, Any]:
        """Get all orders with their statuses."""
        pass

