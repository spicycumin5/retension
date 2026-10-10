"""Small in-process rate limiter. Good enough for a single instance; swap for Redis when scaling out."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
enabled = True


def rate_limit(bucket: str, limit: int, per_seconds: int):
    async def dependency(request: Request) -> None:
        if not enabled:
            return
        key = (bucket, request.client.host if request.client else "unknown")
        now = time.monotonic()
        hits = _hits[key]
        while hits and hits[0] <= now - per_seconds:
            hits.popleft()
        if len(hits) >= limit:
            raise HTTPException(429, "Too many requests, slow down")
        hits.append(now)

    return dependency
