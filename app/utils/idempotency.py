import hashlib
import json
from typing import Any, Optional

from fastapi import HTTPException, Request

from app.deps import get_redis


class IdempotencyManager:
    """Manage idempotency keys for API requests"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.key_prefix = "idempotency:"
        self.ttl = 3600  # 1 hour

    async def get_or_create(
        self, idempotency_key: str, request_data: Any, ttl: Optional[int] = None
    ) -> tuple[bool, Any]:
        """
        Get existing result or create new one
        Returns: (is_existing, result)
        """
        key = f"{self.key_prefix}{idempotency_key}"

        # Try to get existing result
        existing = await self.redis.get(key)
        if existing:
            return True, json.loads(existing)

        # Create new entry with request data hash for validation
        request_hash = hashlib.sha256(
            json.dumps(request_data, sort_keys=True).encode()
        ).hexdigest()

        # Store request hash (will be replaced with result)
        await self.redis.setex(
            key,
            ttl or self.ttl,
            json.dumps({"request_hash": request_hash, "status": "processing"}),
        )

        return False, None

    async def store_result(
        self, idempotency_key: str, result: Any, ttl: Optional[int] = None
    ):
        """Store the result of an idempotent operation"""
        key = f"{self.key_prefix}{idempotency_key}"
        await self.redis.setex(key, ttl or self.ttl, json.dumps(result))

    async def validate_request(self, idempotency_key: str, request_data: Any) -> bool:
        """Validate that the request data matches the original"""
        key = f"{self.key_prefix}{idempotency_key}"
        existing = await self.redis.get(key)

        if not existing:
            return True

        try:
            data = json.loads(existing)
            if data.get("status") == "processing":
                return True

            stored_hash = data.get("request_hash")
            current_hash = hashlib.sha256(
                json.dumps(request_data, sort_keys=True).encode()
            ).hexdigest()

            return stored_hash == current_hash
        except (json.JSONDecodeError, KeyError):
            return False


async def get_idempotency_manager():
    """Get idempotency manager instance"""
    redis_client = await get_redis()
    return IdempotencyManager(redis_client)


async def check_idempotency(
    request: Request, idempotency_key: Optional[str] = None, request_data: Any = None
):
    """Check idempotency for request"""
    if not idempotency_key:
        return

    manager = await get_idempotency_manager()

    if not await manager.validate_request(idempotency_key, request_data):
        raise HTTPException(
            status_code=409,
            detail="Idempotency key conflict. Request data does not match original request.",
        )
