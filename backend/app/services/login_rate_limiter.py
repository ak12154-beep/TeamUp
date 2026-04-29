from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

from fastapi import HTTPException, status


@dataclass
class AttemptWindow:
    attempts: deque[datetime]


class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window = timedelta(seconds=window_seconds)
        self._email_attempts: dict[str, AttemptWindow] = {}
        self._ip_attempts: dict[str, AttemptWindow] = {}
        self._lock = Lock()

    def check(self, email: str, ip_address: str) -> None:
        with self._lock:
            now = datetime.now(UTC)
            email_window = self._get_window(self._email_attempts, email, now)
            ip_window = self._get_window(self._ip_attempts, ip_address, now)
            oldest_retry_at = self._retry_after(email_window, ip_window, now)
            if oldest_retry_at is not None:
                retry_after = max(1, int((oldest_retry_at - now).total_seconds()))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many login attempts. Try again in {retry_after}s.",
                    headers={"Retry-After": str(retry_after)},
                )

    def record_failure(self, email: str, ip_address: str) -> None:
        with self._lock:
            now = datetime.now(UTC)
            self._get_window(self._email_attempts, email, now).append(now)
            self._get_window(self._ip_attempts, ip_address, now).append(now)

    def reset(self, email: str, ip_address: str) -> None:
        with self._lock:
            self._email_attempts.pop(email, None)
            self._ip_attempts.pop(ip_address, None)

    def _get_window(
        self,
        store: dict[str, AttemptWindow],
        key: str,
        now: datetime,
    ) -> deque[datetime]:
        entry = store.get(key)
        if entry is None:
            entry = AttemptWindow(attempts=deque())
            store[key] = entry
        self._prune(entry.attempts, now)
        return entry.attempts

    def _prune(self, attempts: deque[datetime], now: datetime) -> None:
        while attempts and attempts[0] <= now - self.window:
            attempts.popleft()

    def _retry_after(
        self,
        email_attempts: deque[datetime],
        ip_attempts: deque[datetime],
        now: datetime,
    ) -> datetime | None:
        if len(email_attempts) < self.max_attempts and len(ip_attempts) < self.max_attempts:
            return None
        retry_points = []
        if len(email_attempts) >= self.max_attempts:
            retry_points.append(email_attempts[0] + self.window)
        if len(ip_attempts) >= self.max_attempts:
            retry_points.append(ip_attempts[0] + self.window)
        return min(retry_points) if retry_points else None


class SlidingWindowRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int, error_message: str):
        self.max_attempts = max_attempts
        self.window = timedelta(seconds=window_seconds)
        self.error_message = error_message
        self._attempts: dict[str, AttemptWindow] = {}
        self._lock = Lock()

    def hit(self, key: str) -> None:
        with self._lock:
            now = datetime.now(UTC)
            attempts = self._get_window(key, now)
            if len(attempts) >= self.max_attempts:
                retry_after = max(1, int((attempts[0] + self.window - now).total_seconds()))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=self.error_message,
                    headers={"Retry-After": str(retry_after)},
                )
            attempts.append(now)

    def _get_window(self, key: str, now: datetime) -> deque[datetime]:
        entry = self._attempts.get(key)
        if entry is None:
            entry = AttemptWindow(attempts=deque())
            self._attempts[key] = entry
        while entry.attempts and entry.attempts[0] <= now - self.window:
            entry.attempts.popleft()
        return entry.attempts


login_rate_limiter = LoginRateLimiter()
verification_code_rate_limiter = SlidingWindowRateLimiter(
    max_attempts=5,
    window_seconds=600,
    error_message="Too many verification code requests. Please try again later.",
)
