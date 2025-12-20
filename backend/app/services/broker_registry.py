"""
Broker Registry for managing multiple broker implementations.
Provides factory pattern for creating broker instances and managing active brokers.
"""
from typing import Dict, Type, Optional, List
from enum import Enum
from sqlalchemy.orm import Session

from app.services.broker_interface import BrokerInterface
from app.models.models import BrokerConfig, AppSettings


class BrokerType(str, Enum):
    """Supported broker types"""
    ANGEL_ONE = "angel_one"
    ZERODHA = "zerodha"
    SHOONYA = "shoonya"
    UPSTOX = "upstox"
    FYERS = "fyers"


class BrokerRegistry:
    """
    Registry for managing broker implementations.
    Supports dynamic registration, instance caching, and broker enumeration.
    """
    
    def __init__(self):
        self._brokers: Dict[str, Type[BrokerInterface]] = {}
        self._instances: Dict[str, BrokerInterface] = {}
        self._default_broker: Optional[str] = None
    
    def register(self, broker_type: str, broker_class: Type[BrokerInterface]) -> None:
        """
        Register a broker implementation.
        
        Args:
            broker_type: Unique identifier for the broker (e.g., "angel_one")
            broker_class: Class implementing BrokerInterface
        """
        if not issubclass(broker_class, BrokerInterface):
            raise ValueError(f"{broker_class.__name__} must implement BrokerInterface")
        
        self._brokers[broker_type] = broker_class
        
        # Set first registered broker as default
        if self._default_broker is None:
            self._default_broker = broker_type
    
    def unregister(self, broker_type: str) -> None:
        """
        Unregister a broker implementation.
        
        Args:
            broker_type: Broker type to unregister
        """
        if broker_type in self._brokers:
            del self._brokers[broker_type]
        
        if broker_type in self._instances:
            del self._instances[broker_type]
        
        if self._default_broker == broker_type:
            self._default_broker = next(iter(self._brokers.keys()), None)
    
    def get_broker_class(self, broker_type: str) -> Type[BrokerInterface]:
        """
        Get broker class by type.
        
        Args:
            broker_type: Broker type identifier
            
        Returns:
            Broker class implementing BrokerInterface
            
        Raises:
            ValueError: If broker type is not registered
        """
        if broker_type not in self._brokers:
            raise ValueError(
                f"Broker type '{broker_type}' not registered. "
                f"Available: {list(self._brokers.keys())}"
            )
        
        return self._brokers[broker_type]
    
    def create_broker(
        self, 
        broker_type: str, 
        cache: bool = True
    ) -> BrokerInterface:
        """
        Create or retrieve a broker instance.
        
        Args:
            broker_type: Broker type identifier
            cache: If True, cache and reuse instance (singleton pattern)
            
        Returns:
            Broker instance implementing BrokerInterface
        """
        # Return cached instance if available
        if cache and broker_type in self._instances:
            return self._instances[broker_type]
        
        # Create new instance
        broker_class = self.get_broker_class(broker_type)
        instance = broker_class()
        
        # Cache if requested
        if cache:
            self._instances[broker_type] = instance
        
        return instance
    
    def get_active_broker(self, db: Session) -> Optional[BrokerInterface]:
        """
        Get the currently active broker instance based on database settings.
        
        Args:
            db: Database session
            
        Returns:
            Active broker instance or None if no active broker configured
        """
        # Get active broker from app settings
        settings = db.query(AppSettings).first()
        if not settings or not hasattr(settings, 'active_broker_type'):
            # Fallback to default broker
            if self._default_broker:
                return self.create_broker(self._default_broker)
            return None
        
        active_broker_type = settings.active_broker_type
        if not active_broker_type:
            return None
        
        try:
            return self.create_broker(active_broker_type)
        except ValueError:
            # Broker type not registered
            return None
    
    def get_configured_brokers(self, db: Session) -> List[Dict[str, any]]:
        """
        Get list of all configured brokers with their status.
        Returns only the most recent config for each unique broker_name.
        
        Args:
            db: Database session
            
        Returns:
            List of broker info dictionaries
        """
        # Get all configs and group by broker_name, keeping only the most recent
        configs = db.query(BrokerConfig).order_by(BrokerConfig.created_at.desc()).all()
        
        # Use dict to keep only first (most recent) entry per broker_name
        unique_configs = {}
        for config in configs:
            if config.broker_name not in unique_configs:
                unique_configs[config.broker_name] = config
        
        result = []
        for config in unique_configs.values():
            broker_info = {
                "id": config.id,
                "broker_type": config.broker_name,
                "client_id": config.client_id,
                "is_active": config.is_active,
                "last_login": config.last_login.isoformat() if config.last_login else None,
                "is_registered": config.broker_name in self._brokers
            }
            
            # Add login status if broker is instantiated
            if config.broker_name in self._instances:
                broker = self._instances[config.broker_name]
                broker_info["is_logged_in"] = broker.is_logged_in
            else:
                broker_info["is_logged_in"] = False
            
            result.append(broker_info)
        
        return result
    
    def list_available_brokers(self) -> List[str]:
        """
        Get list of all registered broker types.
        
        Returns:
            List of broker type identifiers
        """
        return list(self._brokers.keys())
    
    def is_registered(self, broker_type: str) -> bool:
        """
        Check if a broker type is registered.
        
        Args:
            broker_type: Broker type identifier
            
        Returns:
            True if registered, False otherwise
        """
        return broker_type in self._brokers
    
    def set_default_broker(self, broker_type: str) -> None:
        """
        Set the default broker type.
        
        Args:
            broker_type: Broker type to set as default
            
        Raises:
            ValueError: If broker type is not registered
        """
        if broker_type not in self._brokers:
            raise ValueError(f"Broker type '{broker_type}' not registered")
        
        self._default_broker = broker_type
    
    def get_default_broker(self) -> Optional[str]:
        """
        Get the default broker type.
        
        Returns:
            Default broker type or None if no brokers registered
        """
        return self._default_broker
    
    def clear_instances(self) -> None:
        """
        Clear all cached broker instances.
        Useful for testing or forcing re-initialization.
        """
        self._instances.clear()


# Global broker registry instance
broker_registry = BrokerRegistry()


def get_broker_registry() -> BrokerRegistry:
    """
    Get the global broker registry instance.
    
    Returns:
        Global BrokerRegistry singleton
    """
    return broker_registry
