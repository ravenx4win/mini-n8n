"""
Execution caching system for workflow nodes.

Provides:
 - Deterministic hashing of node config + inputs
 - Optional TTL expiration
 - Async-safe access for concurrent task execution
 - Detailed cache statistics
"""

from __future__ import annotations
from typing import Dict, Any, Optional
import hashlib
import json
import time
import asyncio
from dataclasses import dataclass, field
import logging


logger = logging.getLogger("executor.cache")


# ============================================================
# Cache Entry
# ============================================================

@dataclass
class CacheEntry:
    """Represents a cached node execution result."""

    key: str
    value: Any
    timestamp: float
    ttl: float = 0.0  # 0 = never expire

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl <= 0:
            return False
        return (time.time() - self.timestamp) > self.ttl


# ============================================================
# Execution Cache
# ============================================================

class ExecutionCache:
    """
    In-memory cache for node execution results.
    Async-safe and stable-hashed for deterministic caching.

    Cache key is based on:
      - node_type
      - normalized node_config
      - normalized node_inputs
    """

    def __init__(self, default_ttl: float = 3600):
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._lock = asyncio.Lock()  # async-safe cache access

    # ------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------

    @staticmethod
    def _normalize_json(value: Any) -> Any:
        """
        Convert Python objects into JSON-stable equivalents.
        Ensures deterministic hashing.
        """
        try:
            if isinstance(value, dict):
                return {k: ExecutionCache._normalize_json(value[k]) for k in sorted(value)}
            if isinstance(value, list):
                return [ExecutionCache._normalize_json(v) for v in value]
            if isinstance(value, (str, int, float, bool)) or value is None:
                return value
            # fallback for objects: convert to string
            return str(value)
        except Exception:
            return str(value)

    def _generate_key(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        node_inputs: Dict[str, Any]
    ) -> str:
        """Generate deterministic cache key."""
        normalized = {
            "type": node_type,
            "config": self._normalize_json(node_config),
            "inputs": self._normalize_json(node_inputs)
        }

        json_str = json.dumps(normalized, sort_keys=True)
        digest = hashlib.sha256(json_str.encode()).hexdigest()

        return f"{node_type}:{digest[:20]}"  # shorten for readability

    # ------------------------------------------------------------
    # Cache Get / Set
    # ------------------------------------------------------------

    async def get(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        node_inputs: Dict[str, Any]
    ) -> Optional[Any]:
        """Retrieve cached result, if valid."""
        key = self._generate_key(node_type, node_config, node_inputs)

        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                logger.debug(f"[CACHE] Expired key removed: {key}")
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            logger.debug(f"[CACHE] HIT for {key}")
            return entry.value

    async def set(
        self,
        node_type: str,
        node_config: Dict[str, Any],
        node_inputs: Dict[str, Any],
        result: Any,
        ttl: Optional[float] = None
    ) -> None:
        """Store new cache entry."""
        key = self._generate_key(node_type, node_config, node_inputs)
        ttl = ttl if ttl is not None else self._default_ttl

        entry = CacheEntry(
            key=key,
            value=result,
            timestamp=time.time(),
            ttl=ttl
        )

        async with self._lock:
            self._cache[key] = entry
            logger.debug(f"[CACHE] Stored key: {key}")

    # ------------------------------------------------------------
    # Cache Invalidation
    # ------------------------------------------------------------

    async def clear(self) -> None:
        """Clear entire cache."""
        async with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("[CACHE] Cleared all cache entries")

    async def clear_node_cache(self, node_type: str) -> int:
        """Clear all cache entries for a node type."""
        async with self._lock:
            keys = [key for key in self._cache if key.startswith(f"{node_type}:")]
            for key in keys:
                del self._cache[key]
            logger.info(f"[CACHE] Cleared {len(keys)} entries for node type '{node_type}'")
            return len(keys)

    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        async with self._lock:
            expired = [k for k, e in self._cache.items() if e.is_expired()]
            for key in expired:
                del self._cache[key]
            if expired:
                logger.info(f"[CACHE] Cleaned {len(expired)} expired cache entries")
            return len(expired)

    # ------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total,
        }
