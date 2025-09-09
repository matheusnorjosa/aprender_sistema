"""
Advanced Cache Service - Sistema Aprender
High-performance caching with Redis and fallback mechanisms
"""

import json
import hashlib
import logging
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
from functools import wraps

from django.core.cache import cache
from django.conf import settings
from django.db.models import QuerySet
from django.core.serializers import serialize
from django.utils.encoding import force_str

logger = logging.getLogger(__name__)


class CacheService:
    """
    Advanced cache service with intelligent key management and fallbacks
    """
    
    # Cache timeout constants (in seconds)
    CACHE_TIMEOUTS = {
        'short': 300,      # 5 minutes
        'medium': 1800,    # 30 minutes  
        'long': 3600,      # 1 hour
        'very_long': 86400, # 24 hours
    }
    
    # Cache key prefixes
    KEY_PREFIXES = {
        'formador': 'formador',
        'solicitacao': 'solicitacao',
        'availability': 'availability',
        'dashboard': 'dashboard',
        'query': 'query',
        'api': 'api',
    }
    
    def __init__(self):
        self.enabled = hasattr(settings, 'CACHES') and cache is not None
        
    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate a unique cache key based on prefix and parameters
        """
        key_parts = [str(prefix)]
        key_parts.extend(str(arg) for arg in args)
        
        if kwargs:
            # Sort kwargs for consistent key generation
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = json.dumps(sorted_kwargs, sort_keys=True)
            key_parts.append(hashlib.md5(kwargs_str.encode()).hexdigest()[:8])
        
        # Create final key
        key = ':'.join(key_parts)
        
        # Ensure key length doesn't exceed limits (Redis has 512MB limit, but keep reasonable)
        if len(key) > 200:
            key_hash = hashlib.md5(key.encode()).hexdigest()
            key = f"{prefix}:hashed:{key_hash}"
        
        return key
    
    def get(self, key: str, default=None) -> Any:
        """
        Get value from cache with error handling
        """
        if not self.enabled:
            return default
            
        try:
            value = cache.get(key, default)
            if value is not None and value != default:
                logger.debug(f"Cache HIT: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")
            return value
        except Exception as e:
            logger.error(f"Cache GET error for key {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, timeout: Union[int, str] = 'medium') -> bool:
        """
        Set value in cache with error handling and timeout support
        """
        if not self.enabled:
            return False
            
        try:
            # Convert string timeout to seconds
            if isinstance(timeout, str):
                timeout = self.CACHE_TIMEOUTS.get(timeout, self.CACHE_TIMEOUTS['medium'])
            
            cache.set(key, value, timeout)
            logger.debug(f"Cache SET: {key} (timeout: {timeout}s)")
            return True
        except Exception as e:
            logger.error(f"Cache SET error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache
        """
        if not self.enabled:
            return False
            
        try:
            cache.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error for key {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear cache keys matching pattern (Redis specific)
        """
        if not self.enabled:
            return 0
            
        try:
            # This works with Redis backend
            if hasattr(cache, 'delete_pattern'):
                deleted_count = cache.delete_pattern(pattern)
                logger.info(f"Cache CLEAR pattern '{pattern}': {deleted_count} keys deleted")
                return deleted_count
            else:
                # Fallback for other cache backends
                logger.warning("Cache backend doesn't support pattern deletion")
                return 0
        except Exception as e:
            logger.error(f"Cache CLEAR pattern error for '{pattern}': {e}")
            return 0
    
    def cache_queryset(self, queryset: QuerySet, key: str, timeout: Union[int, str] = 'medium', 
                      serialize_format: str = 'json') -> List[Dict]:
        """
        Cache Django QuerySet with serialization
        """
        cached_data = self.get(key)
        if cached_data is not None:
            return cached_data
        
        try:
            # Serialize queryset
            serialized_data = json.loads(serialize(serialize_format, queryset))
            
            # Extract just the fields for cleaner cache data
            clean_data = [item['fields'] for item in serialized_data]
            
            # Add primary keys
            for i, item in enumerate(serialized_data):
                clean_data[i]['id'] = item['pk']
            
            self.set(key, clean_data, timeout)
            return clean_data
            
        except Exception as e:
            logger.error(f"Error caching queryset for key {key}: {e}")
            # Return original queryset as list of dicts
            return list(queryset.values())
    
    def invalidate_related(self, model_name: str, obj_id: Optional[int] = None):
        """
        Invalidate cache keys related to a specific model/object
        """
        patterns_to_clear = []
        
        if obj_id:
            patterns_to_clear.extend([
                f"{model_name}:{obj_id}:*",
                f"{model_name}_detail:{obj_id}",
                f"query:{model_name}:{obj_id}:*"
            ])
        
        # Clear broader patterns for model changes
        patterns_to_clear.extend([
            f"{model_name}_list:*",
            f"dashboard:*",  # Dashboard caches often depend on multiple models
            f"availability:*",  # Availability depends on multiple models
        ])
        
        for pattern in patterns_to_clear:
            self.clear_pattern(pattern)
    
    def get_or_set_json(self, key: str, callable_func, timeout: Union[int, str] = 'medium', 
                       force_refresh: bool = False) -> Any:
        """
        Get from cache or execute function and cache result (JSON serializable data)
        """
        if not force_refresh:
            cached_result = self.get(key)
            if cached_result is not None:
                return cached_result
        
        try:
            result = callable_func()
            
            # Ensure result is JSON serializable
            json.dumps(result)  # Test serialization
            
            self.set(key, result, timeout)
            return result
            
        except Exception as e:
            logger.error(f"Error in get_or_set_json for key {key}: {e}")
            # Return empty result based on common patterns
            if isinstance(callable_func, (list, tuple)):
                return []
            elif isinstance(callable_func, dict):
                return {}
            return None


# Global cache service instance
cache_service = CacheService()


def cached_view(timeout: Union[int, str] = 'medium', key_prefix: str = 'view'):
    """
    Decorator to cache view responses
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Create cache key based on view name and parameters
            view_name = view_func.__name__
            cache_key = cache_service.generate_key(
                key_prefix, 
                view_name,
                request.path,
                request.GET.urlencode(),
                getattr(request.user, 'id', 'anonymous')
            )
            
            # Try to get from cache
            cached_response = cache_service.get(cache_key)
            if cached_response is not None:
                return cached_response
            
            # Execute view and cache result
            response = view_func(request, *args, **kwargs)
            
            # Only cache successful responses
            if hasattr(response, 'status_code') and response.status_code == 200:
                cache_service.set(cache_key, response, timeout)
            
            return response
        
        return wrapper
    return decorator


def cached_property_method(timeout: Union[int, str] = 'short', key_prefix: str = 'property'):
    """
    Decorator to cache expensive property calculations
    """
    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            # Create cache key based on object and method
            cache_key = cache_service.generate_key(
                key_prefix,
                self.__class__.__name__,
                getattr(self, 'pk', 'no_pk'),
                method.__name__,
                *args
            )
            
            return cache_service.get_or_set_json(
                cache_key,
                lambda: method(self, *args, **kwargs),
                timeout
            )
        
        return wrapper
    return decorator


# Convenience functions for common caching patterns
def cache_formador_availability(formador_id: int, start_date: str, end_date: str, data: Dict):
    """Cache formador availability data"""
    key = cache_service.generate_key('availability', 'formador', formador_id, start_date, end_date)
    cache_service.set(key, data, 'medium')


def get_cached_formador_availability(formador_id: int, start_date: str, end_date: str) -> Optional[Dict]:
    """Get cached formador availability data"""
    key = cache_service.generate_key('availability', 'formador', formador_id, start_date, end_date)
    return cache_service.get(key)


def invalidate_formador_cache(formador_id: int):
    """Invalidate all cache entries for a formador"""
    cache_service.invalidate_related('formador', formador_id)


def cache_dashboard_data(dashboard_type: str, user_id: int, data: Dict):
    """Cache dashboard data"""
    key = cache_service.generate_key('dashboard', dashboard_type, user_id)
    cache_service.set(key, data, 'long')


def get_cached_dashboard_data(dashboard_type: str, user_id: int) -> Optional[Dict]:
    """Get cached dashboard data"""
    key = cache_service.generate_key('dashboard', dashboard_type, user_id)
    return cache_service.get(key)


# Cache invalidation signals
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver([post_save, post_delete])
def invalidate_model_cache(sender, instance, **kwargs):
    """
    Auto-invalidate cache when models change
    """
    model_name = sender.__name__.lower()
    obj_id = getattr(instance, 'pk', None)
    
    # Only handle our core models
    cache_models = ['formador', 'solicitacao', 'municipio', 'projeto', 'tipovento']
    
    if model_name in cache_models:
        cache_service.invalidate_related(model_name, obj_id)
        logger.info(f"Cache invalidated for {model_name} {obj_id}")


# Health check for cache
def check_cache_health() -> Dict[str, Any]:
    """
    Check cache system health
    """
    try:
        test_key = 'health_check_test'
        test_value = {'timestamp': datetime.now().isoformat(), 'test': True}
        
        # Test set
        cache_service.set(test_key, test_value, 60)
        
        # Test get
        cached_value = cache_service.get(test_key)
        
        # Test delete
        cache_service.delete(test_key)
        
        return {
            'status': 'healthy',
            'backend': settings.CACHES['default']['BACKEND'],
            'operations': {
                'set': True,
                'get': cached_value == test_value,
                'delete': True
            }
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown')
        }