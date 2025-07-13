"""
Caching layer for embedding results to improve performance.

Implements LRU cache with TTL support and safety-aware caching.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import OrderedDict
from threading import Lock

from .models import (
    EmbeddingResult,
    CacheEntry,
    ContentType,
    generate_content_hash
)

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    LRU cache for embedding results with TTL and safety validation.
    
    Features:
    - Thread-safe LRU eviction
    - TTL-based expiration
    - Safety score validation
    - Memory usage monitoring
    - Cache statistics
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl_seconds: int = 3600,  # 1 hour
        min_safety_score: float = 0.8,
        enable_stats: bool = True
    ):
        """
        Initialize embedding cache.
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl_seconds: Default TTL for cache entries
            min_safety_score: Minimum safety score for caching
            enable_stats: Whether to collect cache statistics
        """
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self.min_safety_score = min_safety_score
        self.enable_stats = enable_stats
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        
        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'safety_rejections': 0,
            'total_requests': 0
        }
    
    def generate_cache_key(
        self,
        content: str,
        model_name: str,
        content_type: ContentType = ContentType.TEXT,
        language: Optional[str] = None
    ) -> str:
        """
        Generate a cache key for content.
        
        Args:
            content: Content to cache
            model_name: Model used for embedding
            content_type: Type of content
            language: Optional language specification
            
        Returns:
            Cache key string
        """
        # Include all relevant parameters in key
        key_components = [
            generate_content_hash(content, model_name),
            content_type.value,
            model_name,
            language or "unknown"
        ]
        return ":".join(key_components)
    
    async def get(self, cache_key: str) -> Optional[EmbeddingResult]:
        """
        Retrieve embedding from cache.
        
        Args:
            cache_key: Key to look up
            
        Returns:
            EmbeddingResult if found and valid, None otherwise
        """
        with self._lock:
            if self.enable_stats:
                self._stats['total_requests'] += 1
            
            if cache_key not in self._cache:
                if self.enable_stats:
                    self._stats['misses'] += 1
                return None
            
            entry = self._cache[cache_key]
            
            # Check expiration
            if entry.is_expired():
                del self._cache[cache_key]
                if self.enable_stats:
                    self._stats['expirations'] += 1
                    self._stats['misses'] += 1
                logger.debug(f"Cache entry expired: {cache_key}")
                return None
            
            # Check safety score
            if entry.embedding_result.metadata.safety_score < self.min_safety_score:
                del self._cache[cache_key]
                if self.enable_stats:
                    self._stats['safety_rejections'] += 1
                    self._stats['misses'] += 1
                logger.warning(
                    f"Cached embedding rejected due to low safety score: "
                    f"{entry.embedding_result.metadata.safety_score}"
                )
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(cache_key)
            entry.touch()
            
            if self.enable_stats:
                self._stats['hits'] += 1
            
            # Mark as cache hit
            result = entry.embedding_result.copy(deep=True)
            result.cache_hit = True
            
            logger.debug(f"Cache hit: {cache_key}")
            return result
    
    async def put(
        self,
        cache_key: str,
        embedding_result: EmbeddingResult,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Store embedding in cache.
        
        Args:
            cache_key: Key to store under
            embedding_result: Embedding to cache
            ttl_seconds: Custom TTL, uses default if None
            
        Returns:
            True if stored successfully
        """
        # Validate safety score
        if embedding_result.metadata.safety_score < self.min_safety_score:
            if self.enable_stats:
                self._stats['safety_rejections'] += 1
            logger.warning(
                f"Embedding not cached due to low safety score: "
                f"{embedding_result.metadata.safety_score}"
            )
            return False
        
        with self._lock:
            # Create cache entry
            entry = CacheEntry(
                cache_key=cache_key,
                embedding_result=embedding_result.copy(deep=True),
                ttl_seconds=ttl_seconds or self.default_ttl_seconds
            )
            
            # Add to cache
            self._cache[cache_key] = entry
            self._cache.move_to_end(cache_key)
            
            # Evict if necessary
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                if self.enable_stats:
                    self._stats['evictions'] += 1
                logger.debug(f"Evicted cache entry: {oldest_key}")
            
            logger.debug(f"Cached embedding: {cache_key}")
            return True
    
    async def get_batch(self, cache_keys: List[str]) -> Dict[str, EmbeddingResult]:
        """
        Retrieve multiple embeddings from cache.
        
        Args:
            cache_keys: List of keys to retrieve
            
        Returns:
            Dictionary mapping keys to embedding results
        """
        results = {}
        for key in cache_keys:
            result = await self.get(key)
            if result is not None:
                results[key] = result
        return results
    
    async def put_batch(
        self,
        entries: Dict[str, EmbeddingResult],
        ttl_seconds: Optional[int] = None
    ) -> int:
        """
        Store multiple embeddings in cache.
        
        Args:
            entries: Dictionary mapping keys to embedding results
            ttl_seconds: Custom TTL for all entries
            
        Returns:
            Number of entries successfully cached
        """
        success_count = 0
        for key, result in entries.items():
            if await self.put(key, result, ttl_seconds):
                success_count += 1
        return success_count
    
    async def invalidate(self, cache_key: str) -> bool:
        """
        Remove specific entry from cache.
        
        Args:
            cache_key: Key to remove
            
        Returns:
            True if entry was found and removed
        """
        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug(f"Invalidated cache entry: {cache_key}")
                return True
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Remove entries matching pattern from cache.
        
        Args:
            pattern: Pattern to match (simple string contains)
            
        Returns:
            Number of entries removed
        """
        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if pattern in key
            ]
            
            for key in keys_to_remove:
                del self._cache[key]
            
            logger.debug(f"Invalidated {len(keys_to_remove)} entries matching: {pattern}")
            return len(keys_to_remove)
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            entry_count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {entry_count} cache entries")
    
    async def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            if self.enable_stats:
                self._stats['expirations'] += len(expired_keys)
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary of cache statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats.update({
                'cache_size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': (
                    stats['hits'] / stats['total_requests'] 
                    if stats['total_requests'] > 0 else 0.0
                ),
                'memory_usage_estimate': self._estimate_memory_usage()
            })
            return stats
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information.
        
        Returns:
            Dictionary with cache details
        """
        with self._lock:
            now = datetime.utcnow()
            entries_info = []
            
            for key, entry in self._cache.items():
                age_seconds = (now - entry.created_at).total_seconds()
                entries_info.append({
                    'key': key,
                    'age_seconds': age_seconds,
                    'access_count': entry.access_count,
                    'last_accessed': entry.last_accessed,
                    'safety_score': float(entry.embedding_result.metadata.safety_score),
                    'dimensions': entry.embedding_result.metadata.dimensions,
                    'expired': entry.is_expired()
                })
            
            return {
                'total_entries': len(self._cache),
                'max_size': self.max_size,
                'default_ttl_seconds': self.default_ttl_seconds,
                'min_safety_score': self.min_safety_score,
                'entries': entries_info
            }
    
    def _estimate_memory_usage(self) -> int:
        """
        Estimate memory usage in bytes.
        
        Returns:
            Estimated memory usage in bytes
        """
        if not self._cache:
            return 0
        
        # Rough estimate based on typical embedding size
        # This is approximate - actual usage may vary
        avg_vector_size = 384 * 4  # 384 dimensions * 4 bytes per float
        avg_metadata_size = 200    # Estimated metadata overhead
        avg_entry_size = avg_vector_size + avg_metadata_size
        
        return len(self._cache) * avg_entry_size
    
    async def start_cleanup_task(self, interval_seconds: int = 300) -> None:
        """
        Start background task to clean up expired entries.
        
        Args:
            interval_seconds: Cleanup interval in seconds
        """
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    expired_count = await self.cleanup_expired()
                    if expired_count > 0:
                        logger.info(f"Background cleanup removed {expired_count} expired entries")
                except Exception as e:
                    logger.error(f"Error in cache cleanup task: {e}")
        
        # Start the cleanup task
        asyncio.create_task(cleanup_loop())
        logger.info(f"Started cache cleanup task with {interval_seconds}s interval")