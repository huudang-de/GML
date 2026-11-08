"""In-memory metrics registry for node latencies, SQL validity, requests, and cache.

Specifications:
- Spec §5 T5, §11.7
"""

from collections import defaultdict
import threading
from typing import Any


class MetricsRegistry:
    """Thread-safe metrics accumulator."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._node_latencies: dict[str, list[float]] = defaultdict(list)
        self._sql_validity: dict[str, int] = {"valid": 0, "invalid": 0}
        self._requests: dict[str, int] = defaultdict(int)
        self._cache_stats: dict[str, int] = {"hit": 0, "miss": 0}

    def record_node_latency(self, node: str, latency_ms: float) -> None:
        """Record execution latency in milliseconds for a workflow node."""
        with self._lock:
            self._node_latencies[node].append(float(latency_ms))

    def record_sql_validity(self, is_valid: bool) -> None:
        """Record whether generated SQL passed AST security validation."""
        with self._lock:
            if is_valid:
                self._sql_validity["valid"] += 1
            else:
                self._sql_validity["invalid"] += 1

    def record_request(self, endpoint: str, status_code: int) -> None:
        """Record HTTP request by endpoint and status code."""
        key = f"{endpoint}:{status_code}"
        with self._lock:
            self._requests[key] += 1

    def record_cache(self, hit: bool) -> None:
        """Record cache hit or miss."""
        with self._lock:
            if hit:
                self._cache_stats["hit"] += 1
            else:
                self._cache_stats["miss"] += 1

    def snapshot(self) -> dict[str, Any]:
        """Return point-in-time snapshot with aggregates (count, avg, p95)."""
        with self._lock:
            node_stats = {}
            for node, latencies in self._node_latencies.items():
                if not latencies:
                    continue
                sorted_lat = sorted(latencies)
                n = len(sorted_lat)
                p50 = sorted_lat[int(n * 0.50)]
                p95 = sorted_lat[min(int(n * 0.95), n - 1)]
                avg = sum(sorted_lat) / n
                node_stats[node] = {
                    "count": n,
                    "avg_ms": round(avg, 2),
                    "p50_ms": round(p50, 2),
                    "p95_ms": round(p95, 2),
                }

            cache_total = self._cache_stats["hit"] + self._cache_stats["miss"]
            hit_ratio = round(self._cache_stats["hit"] / cache_total, 4) if cache_total > 0 else 0.0

            sql_total = self._sql_validity["valid"] + self._sql_validity["invalid"]
            sql_pass_rate = round(self._sql_validity["valid"] / sql_total, 4) if sql_total > 0 else 1.0

            return {
                "nodes": node_stats,
                "sql_validity": {
                    "valid": self._sql_validity["valid"],
                    "invalid": self._sql_validity["invalid"],
                    "pass_rate": sql_pass_rate,
                },
                "requests": dict(self._requests),
                "cache": {
                    "hit": self._cache_stats["hit"],
                    "miss": self._cache_stats["miss"],
                    "hit_ratio": hit_ratio,
                },
            }

    def reset(self) -> None:
        """Reset all metric counters."""
        with self._lock:
            self._node_latencies.clear()
            self._sql_validity = {"valid": 0, "invalid": 0}
            self._requests.clear()
            self._cache_stats = {"hit": 0, "miss": 0}


_GLOBAL_METRICS = MetricsRegistry()


def get_metrics_registry() -> MetricsRegistry:
    """Return singleton MetricsRegistry."""
    return _GLOBAL_METRICS
