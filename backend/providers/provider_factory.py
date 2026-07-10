"""
Provider Factory for TradeX Data Engine.
"""

from typing import Dict, Type, Optional, List
import logging
from backend.providers.base_provider import BaseProvider
from backend.providers.openbb_provider import OpenBBProvider

logger = logging.getLogger(__name__)

class ProviderFactory:
    """Factory class for managing data providers."""
    
    def __init__(self):
        self._providers: Dict[str, Type[BaseProvider]] = {}
        self._instances: Dict[str, BaseProvider] = {}
        self._register_default_providers()
    
    def _register_default_providers(self):
        try:
            self.register_provider('openbb', OpenBBProvider)
        except Exception as e:
            logger.warning(f"OpenBB not available: {e}")
        
        logger.info(f"Registered providers: {list(self._providers.keys())}")
    
    def register_provider(self, name: str, provider_class: Type[BaseProvider]):
        self._providers[name.lower()] = provider_class
    
    def get_provider(self, name: Optional[str] = None) -> Optional[BaseProvider]:
        if name:
            name = name.lower()
            if name in self._providers:
                return self._get_or_create_instance(name)
            return None
        
        # Try openbb first, then yahoo
        for provider_name in ['openbb', 'yahoo']:
            if provider_name in self._providers:
                return self._get_or_create_instance(provider_name)
        
        return None
    
    def _get_or_create_instance(self, name: str) -> Optional[BaseProvider]:
        if name not in self._instances:
            try:
                self._instances[name] = self._providers[name]()
            except Exception as e:
                logger.error(f"Error creating {name} provider: {e}")
                return None
        return self._instances[name]
    
    def get_available_providers(self) -> List[str]:
        return list(self._providers.keys())