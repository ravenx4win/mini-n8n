"""Execution caching system."""

from typing import Dict, Any, Optional
import hashlib
import json
import time
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with TTL."""
    
    key: str
    value: Any
    timestamp: float
    ttl: float
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl <= 0:
            return False
        return time.time() - self.timestamp > self.ttl


class ExecutionCache:
    """In-memory cache for node execution results."""
    
    def __init__(self, default_ttl: float = 3600):
        """Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (0 = no expiry)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
    
    def _generate_key(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        node_inputs: Dict[str, Any]
    ) -> str:
        """Generate cache key for a node execution.
        
        Args:
            node_type: Type of node
            node_config: Node configuration
            node_inputs: Node inputs
            
        Returns:
            Cache key string
        """
        # Create deterministic representation
        data = {
            "type": node_type,
            "config": node_config,
            "inputs": node_inputs
        }
        
        # Serialize to JSON and hash
        json_str = json.dumps(data, sort_keys=True)
        hash_digest = hashlib.sha256(json_str.encode()).hexdigest()
        
        return f"{node_type}:{hash_digest[:16]}"
    
    def get(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        node_inputs: Dict[str, Any]
    ) -> Optional[Any]:
        """Get cached result for a node execution.
        
        Args:
            node_type: Type of node
            node_config: Node configuration
            node_inputs: Node inputs
            
        Returns:
            Cached result or None
        """
        key = self._generate_key(node_type, node_config, node_inputs)
        
        if key in self._cache:
            entry = self._cache[key]
            
            # Check expiry
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return entry.value
        
        self._misses += 1
        return None
    
    def set(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        node_inputs: Dict[str, Any],
        result: Any,
        ttl: Optional[float] = None
    ) -> None:
        """Cache a node execution result.
        
        Args:
            node_type: Type of node
            node_config: Node configuration
            node_inputs: Node inputs
            result: Result to cache
            ttl: Time-to-live in seconds (None = use default)
        """
        key = self._generate_key(node_type, node_config, node_inputs)
        
        if ttl is None:
            ttl = self._default_ttl
        
        entry = CacheEntry(
            key=key,
            value=result,
            timestamp=time.time(),
            ttl=ttl
        )
        
        self._cache[key] = entry
    
    def invalidate(
        self,
        node_type: Optional[str] = None,
        node_config: Optional[Dict[str, Any]] = None,
        node_inputs: Optional[Dict[str, Any]] = None
    ) -> int:
        """Invalidate cache entries.
        
        Args:
            node_type: Optional node type to filter by
            node_config: Optional node config to filter by
            node_inputs: Optional node inputs to filter by
            
        Returns:
            Number of entries invalidated
        """
        if node_type and node_config and node_inputs:
            # Invalidate specific entry
            key = self._generate_key(node_type, node_config, node_inputs)
            if key in self._cache:
                del self._cache[key]
                return 1
            return 0
        elif node_type:
            # Invalidate all entries for node type
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(f"{node_type}:")
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)
        else:
            # Clear entire cache
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def cleanup_expired(self) -> int:
        """Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "total_requests": total
        }


