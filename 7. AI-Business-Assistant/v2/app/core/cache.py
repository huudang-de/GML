"""Scoped TTL Cache for KPI query caching with strict isolation.

Specifications:
- Review Focus #2: ScopedTTLCache key MUST be (data_profile, role, kpi_key, as_of_date).
  Isolates real vs synth and role permissions.
- Spec §5 T5, §11.7
"""

from collections import OrderedDict
from dataclasses import dataclass
import threading
import time
from typing import Any


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class ScopedTTLCache:
    """Thread-safe TTL cache scoped by data profile, role, KPI key, and as-of date."""

    def __init__(self, ttl_seconds: int = 60, max_entries: int = 512) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._store: OrderedDict[tuple[str, str, str, str], _CacheEntry] = OrderedDict()

    @staticmethod
    def make_kpi_key(data_profile: str, role: str, kpi_key: str, as_of_date: str) -> tuple[str, str, str, str]:
        """Generate normalized 4-tuple cache key."""
        return (
            (data_profile or "").strip().lower(),
            (role or "").strip().lower(),
            (kpi_key or "").strip().lower(),
            (as_of_date or "").strip(),
        )

    def get(self, key: tuple[str, str, str, str], now: float | None = None) -> Any | None:
        """Retrieve cached value if not expired; moves key to end (LRU)."""
        current_time = time.time() if now is None else float(now)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if current_time >= entry.expires_at:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return entry.value

    def set(
        self,
        key: tuple[str, str, str, str],
        value: Any,
        now: float | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        """Set cached value with TTL. Evicts expired or oldest entries if over max_entries."""
        current_time = time.time() if now is None else float(now)
        effective_ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        expires_at = current_time + effective_ttl

        with self._lock:
            # Purge expired entries if size threshold approached
            if len(self._store) >= self.max_entries:
                expired_keys = [k for k, v in self._store.items() if current_time >= v.expires_at]
                for k in expired_keys:
                    del self._store[k]

            # Evict oldest if still at max capacity
            while len(self._store) >= self.max_entries:
                self._store.popitem(last=False)

            self._store[key] = _CacheEntry(value=value, expires_at=expires_at)
            self._store.move_to_end(key)

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
