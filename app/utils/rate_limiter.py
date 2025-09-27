import time
from typing import Optional

from fastapi import HTTPException, Request

from app.deps import get_redis


class RateLimiter:
    """Simple rate limiter using Redis"""

    def __init__(
        self, redis_client, max_requests: int = 100, window_seconds: int = 3600
    ):
        self.redis = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed based on rate limit"""
        current_time = int(time.time())
        window_start = current_time - self.window_seconds

        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current requests
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(current_time): current_time})

        # Set expiration
        pipe.expire(key, self.window_seconds)

        results = await pipe.execute()
        current_count = results[1]

        return current_count < self.max_requests


async def get_rate_limiter():
    """Get rate limiter instance"""
    redis_client = await get_redis()
    return RateLimiter(redis_client)


async def check_rate_limit(request: Request, user_id: Optional[int] = None):
    """Check rate limit for request"""
    rate_limiter = await get_rate_limiter()

    # Use user ID if available, otherwise use IP
    if user_id:
        key = f"rate_limit:user:{user_id}"
    else:
        client_ip = request.client.host
        key = f"rate_limit:ip:{client_ip}"

    if not await rate_limiter.is_allowed(key):
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded. Please try again later."
        )
