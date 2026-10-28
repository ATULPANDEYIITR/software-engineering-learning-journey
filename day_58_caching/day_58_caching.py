from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from time import monotonic, sleep
from typing import Any, Callable, Dict, Optional


class CacheError(Exception):
    """Base exception for cache-related failures."""


class InvalidCacheConfiguration(CacheError):
    """Raised when cache configuration is invalid."""


class CacheMiss(CacheError):
    """Raised internally when an item is not available in cache."""


class CacheSourceError(CacheError):
    """Raised when the backing data source cannot provide a value."""


class CacheState(str, Enum):
    HIT = "hit"
    MISS = "miss"
    STALE = "stale"
    LOADED = "loaded"
    INVALIDATED = "invalidated"


@dataclass
class CacheEntry:
    value: Any
    created_at: float
    expires_at: float
    version: int = 1
    tags: set[str] = field(default_factory=set)

    @property
    def expired(self) -> bool:
        return monotonic() >= self.expires_at

    @property
    def remaining_ttl(self) -> float:
        return max(0.0, self.expires_at - monotonic())


@dataclass(frozen=True)
class CacheEvent:
    key: str
    state: CacheState
    version: Optional[int]
    ttl_remaining: float


class TTLCache:
    """
    Thread-safe in-memory cache implementing:
    - cache-aside reads
    - TTL expiration
    - explicit invalidation
    - tag-based invalidation
    - version-aware writes
    - hit/miss/stale metrics
    """

    def __init__(self, default_ttl: float = 10.0, max_entries: int = 1000) -> None:
        if default_ttl <= 0:
            raise InvalidCacheConfiguration("default_ttl must be positive")
        if max_entries <= 0:
            raise InvalidCacheConfiguration("max_entries must be positive")

        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._entries: Dict[str, CacheEntry] = {}
        self._lock = RLock()

        self.hits = 0
        self.misses = 0
        self.stale = 0
        self.invalidations = 0

    def _evict_if_needed(self) -> None:
        if len(self._entries) < self.max_entries:
            return

        # Remove expired entries first.
        expired_keys = [key for key, entry in self._entries.items() if entry.expired]
        for key in expired_keys:
            del self._entries[key]

        # If still full, remove the entry with the earliest expiration.
        while len(self._entries) >= self.max_entries:
            oldest_key = min(
                self._entries,
                key=lambda key: self._entries[key].expires_at,
            )
            del self._entries[oldest_key]

    def get(self, key: str) -> CacheEntry:
        if not key:
            raise ValueError("Cache key must not be empty")

        with self._lock:
            entry = self._entries.get(key)

            if entry is None:
                self.misses += 1
                raise CacheMiss(key)

            if entry.expired:
                self.stale += 1
                self.misses += 1
                del self._entries[key]
                raise CacheMiss(key)

            self.hits += 1
            return entry

    def put(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        tags: Optional[set[str]] = None,
    ) -> CacheEntry:
        if not key:
            raise ValueError("Cache key must not be empty")

        effective_ttl = self.default_ttl if ttl is None else ttl
        if effective_ttl <= 0:
            raise InvalidCacheConfiguration("TTL must be positive")

        with self._lock:
            self._evict_if_needed()

            old_entry = self._entries.get(key)
            version = 1 if old_entry is None else old_entry.version + 1
            now = monotonic()

            entry = CacheEntry(
                value=value,
                created_at=now,
                expires_at=now + effective_ttl,
                version=version,
                tags=set(tags or set()),
            )
            self._entries[key] = entry
            return entry

    def invalidate(self, key: str) -> bool:
        with self._lock:
            removed = self._entries.pop(key, None)
            if removed is not None:
                self.invalidations += 1
                return True
            return False

    def invalidate_tag(self, tag: str) -> int:
        with self._lock:
            keys = [
                key
                for key, entry in self._entries.items()
                if tag in entry.tags
            ]

            for key in keys:
                del self._entries[key]

            self.invalidations += len(keys)
            return len(keys)

    def clear(self) -> None:
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self.invalidations += count

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "entries": len(self._entries),
                "hits": self.hits,
                "misses": self.misses,
                "stale": self.stale,
                "invalidations": self.invalidations,
            }


class Repository:
    """
    Simulates a backing data store.

    A real service would replace this class with PostgreSQL, another database,
    or a remote API. The cache never becomes the source of truth.
    """

    def __init__(self) -> None:
        self._data: Dict[str, dict[str, Any]] = {
            "user:101": {
                "id": 101,
                "name": "Atul",
                "role": "developer",
                "version": 1,
            },
            "user:102": {
                "id": 102,
                "name": "Priya",
                "role": "reviewer",
                "version": 1,
            },
        }
        self._lock = RLock()

    def get(self, key: str) -> dict[str, Any]:
        with self._lock:
            if key not in self._data:
                raise CacheSourceError(f"Source record does not exist: {key}")
            return dict(self._data[key])

    def update(self, key: str, **changes: Any) -> dict[str, Any]:
        with self._lock:
            if key not in self._data:
                raise CacheSourceError(f"Cannot update missing record: {key}")

            current = self._data[key]
            current.update(changes)
            current["version"] += 1
            return dict(current)


class CacheAsideService:
    """
    Implements the cache-aside pattern:

    1. Try cache.
    2. On miss/stale entry, read source.
    3. Store source result in cache.
    4. Return the result.

    Writes update the source first and invalidate the cache afterward.
    """

    def __init__(
        self,
        repository: Repository,
        cache: TTLCache,
        ttl: float = 5.0,
    ) -> None:
        if ttl <= 0:
            raise InvalidCacheConfiguration("Service TTL must be positive")

        self.repository = repository
        self.cache = cache
        self.ttl = ttl

    def get_user(self, user_id: int) -> dict[str, Any]:
        key = f"user:{user_id}"

        try:
            entry = self.cache.get(key)
            return dict(entry.value)
        except CacheMiss:
            value = self.repository.get(key)
            self.cache.put(
                key,
                value,
                ttl=self.ttl,
                tags={f"user:{user_id}", "users"},
            )
            return value

    def update_user(self, user_id: int, **changes: Any) -> dict[str, Any]:
        key = f"user:{user_id}"

        # Source-of-truth update occurs before cache invalidation.
        updated = self.repository.update(key, **changes)

        # This prevents subsequent readers from receiving the old value.
        self.cache.invalidate(key)

        return updated


def demonstrate_cache_aside() -> None:
    repository = Repository()
    cache = TTLCache(default_ttl=2.0, max_entries=100)
    service = CacheAsideService(repository, cache, ttl=2.0)

    print("Initial cache:", cache.snapshot())

    first = service.get_user(101)
    print("First read (source):", first)
    print("After first read:", cache.snapshot())

    second = service.get_user(101)
    print("Second read (cache):", second)
    print("After second read:", cache.snapshot())

    updated = service.update_user(101, role="senior-developer")
    print("Updated source:", updated)
    print("After invalidation:", cache.snapshot())

    fresh = service.get_user(101)
    print("Read after invalidation:", fresh)
    print("After reload:", cache.snapshot())

    print("\nTesting TTL expiration...")
    service.get_user(102)
    sleep(2.1)

    expired_reload = service.get_user(102)
    print("Read after TTL expiration:", expired_reload)
    print("After TTL reload:", cache.snapshot())

    print("\nTesting tag invalidation...")
    service.get_user(101)
    service.get_user(102)
    removed = cache.invalidate_tag("users")
    print(f"Entries invalidated by tag: {removed}")
    print("Final cache:", cache.snapshot())

    print("\nTesting failure handling...")
    try:
        service.get_user(999)
    except CacheSourceError as exc:
        print("Expected source failure:", exc)


def run_self_tests() -> None:
    cache = TTLCache(default_ttl=1.0, max_entries=2)

    cache.put("a", 10)
    assert cache.get("a").value == 10

    assert cache.invalidate("a") is True

    try:
        cache.get("a")
        raise AssertionError("Expected a cache miss")
    except CacheMiss:
        pass

    cache.put("x", 1, tags={"group"})
    cache.put("y", 2, tags={"group"})
    assert cache.invalidate_tag("group") == 2

    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert len(cache.snapshot()["entries"]).__class__ is int

    try:
        TTLCache(default_ttl=0)
        raise AssertionError("Invalid TTL was accepted")
    except InvalidCacheConfiguration:
        pass

    repository = Repository()
    service = CacheAsideService(repository, cache, ttl=1.0)

    user = service.get_user(101)
    assert user["version"] == 1

    service.update_user(101, role="architect")
    updated = service.get_user(101)
    assert updated["role"] == "architect"
    assert updated["version"] == 2


if __name__ == "__main__":
    run_self_tests()
    demonstrate_cache_aside()
