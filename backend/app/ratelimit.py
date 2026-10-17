"""Small in-process rate limiter. Good enough for a single instance; swap for Redis when scaling out.

On Vercel each function instance keeps its own counts, so the limits there are per instance.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import get_settings

_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
enabled = True


def rate_limit(bucket: str, limit: int, per_seconds: int):
    async def dependency(request: Request) -> None:
        if not enabled:
            return
        key = (bucket, _client_ip(request))
        now = time.monotonic()
        hits = _hits[key]
        while hits and hits[0] <= now - per_seconds:
            hits.popleft()
        if len(hits) >= limit:
            raise HTTPException(429, "Too many requests, slow down")
        hits.append(now)

    return dependency


def _client_ip(request: Request) -> str:
    # Vercel sets X-Real-IP to the caller's address and overwrites any value the client sent.
    if get_settings().vercel and (ip := request.headers.get("x-real-ip")):
        return ip
    return request.client.host if request.client else "unknown"
