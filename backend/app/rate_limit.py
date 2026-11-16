"""Small process-local sliding-window limiter for image uploads."""

from collections import deque
from threading import Lock
from time import monotonic


class UploadRateLimit:
    def __init__(self, limit: int, window_seconds: int = 60, max_clients: int = 1_024):
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self._clients: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, client: str) -> bool:
        now = monotonic()
        with self._lock:
            requests = self._clients.pop(client, deque())
            while requests and now - requests[0] >= self.window_seconds:
                requests.popleft()
            if len(requests) >= self.limit:
                self._clients[client] = requests
                return False
            requests.append(now)
            self._clients[client] = requests
            while len(self._clients) > self.max_clients:
                self._clients.pop(next(iter(self._clients)))
            return True
