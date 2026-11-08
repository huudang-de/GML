"""Thread-safe Sliding Window Rate Limiter.

Specifications:
- TC-T5-04: SlidingWindowRateLimiter blocks burst requests exceeding limit.
- Spec §5 T5, §11.7
"""

from collections import defaultdict, deque
import threading
import time


class SlidingWindowRateLimiter:
    """Sliding-window in-memory rate limiter per user/key."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def check(self, user_id: str, now: float | None = None) -> tuple[bool, int]:
        """Check whether request is permitted under rate limit.

        Returns:
            tuple[bool, int]: (allowed, remaining_requests_in_window)
        """
        current_time = time.time() if now is None else float(now)
        cutoff = current_time - self.window_seconds

        with self._lock:
            q = self._windows[user_id]
            # Evict timestamps older than sliding window
            while q and q[0] <= cutoff:
                q.popleft()

            if len(q) < self.max_requests:
                q.append(current_time)
                remaining = self.max_requests - len(q)
                return True, remaining
            else:
                return False, 0

    def reset(self, user_id: str | None = None) -> None:
        """Reset rate limiter state for a specific user or all users."""
        with self._lock:
            if user_id:
                self._windows.pop(user_id, None)
            else:
                self._windows.clear()
