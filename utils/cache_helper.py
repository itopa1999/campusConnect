from django.conf import settings
from django.core.cache import cache
import asyncio
import random
import time

from utils.log_helpers import OperationLogger

CACHE_TTL = getattr(settings, "DEFAULT_CACHE_TTL", 3600)
CACHE_PREFIX = "campusconnect"
CACHE_NULL = "__NULL__"


class GlobalCache:
    @staticmethod
    def _key(key: str) -> str:
        return f"{CACHE_PREFIX}:{key}"

    @staticmethod
    def get(key: str, default=None):
        build_key = GlobalCache._key(key)

        op = OperationLogger(
            "cache_get",
            data={"cache_key": build_key}
        )
        op.start()

        try:
            value = cache.get(build_key)

            if value == CACHE_NULL:
                return None

            return value if value is not None else default

        except Exception as e:
            op.fail(
                f"Failed to retrieve cache key '{build_key}': {e}"
            )
            return default

    @staticmethod
    def set(
        key: str,
        value,
        timeout: int = CACHE_TTL
    ) -> bool:
        build_key = GlobalCache._key(key)

        if value is None:
            value = CACHE_NULL
            timeout = min(timeout, 300)

        jitter = random.randint(
            0,
            min(300, max(1, timeout // 10))
        )

        final_timeout = timeout + jitter

        op = OperationLogger(
            "cache_set",
            data={
                "cache_key": build_key,
                "timeout": final_timeout,
            },
        )
        op.start()

        try:
            cache.set(
                build_key,
                value,
                final_timeout
            )
            return True

        except Exception as e:
            op.fail(
                f"Failed to store cache key '{build_key}': {e}"
            )
            return False
    
    @staticmethod
    async def aget_or_set(
        key: str,
        callback,
        timeout: int = CACHE_TTL,
        lock_timeout: int = 30,
        max_wait: float = 5.0,
    ):

        return await callback()
        # build_key = GlobalCache._key(key)
        # lock_key = f"{build_key}:lock"
        
        # # Check cache - fast path
        # cached = await cache.aget(build_key)
        # if cached is not None:
        #     print(f"[CACHE HIT] Key: {build_key}")
        #     return None if cached == CACHE_NULL else cached
        
        # print(f"[CACHE MISS] Key: {build_key}")
        
        # # Try to acquire distributed lock
        # existing_lock = await cache.aget(lock_key)
        # if existing_lock is None:
        #     await cache.aset(lock_key, "1", lock_timeout)
        #     print(f"[LOCK ACQUIRED] Key: {build_key}")
        #     try:
        #         value = await callback()
        #         cache_value = CACHE_NULL if value is None else value
        #         await cache.aset(build_key, cache_value, timeout)
        #         print(f"[CACHE SET] Key: {build_key}")
        #         return value
        #     except asyncio.CancelledError:
        #         await cache.adelete(lock_key)
        #         print(f"[LOCK RELEASED - CANCELLED] Key: {build_key}")
        #         raise
        #     finally:
        #         await cache.adelete(lock_key)
        #         print(f"[LOCK RELEASED] Key: {build_key}")
        
        # # Lock holder is generating data, wait for it
        # print(f"[WAITING FOR LOCK] Key: {build_key}")
        # start = time.monotonic()
        # wait_interval = 0.1
        
        # while time.monotonic() - start < max_wait:
        #     cached = await cache.aget(build_key)
        #     if cached is not None:
        #         print(f"[CACHE FOUND AFTER WAIT] Key: {build_key}")
        #         return None if cached == CACHE_NULL else cached
        #     await asyncio.sleep(wait_interval)
        #     wait_interval = min(wait_interval * 1.5, 0.5)
        
        # print(f"[FALLBACK - GENERATING DATA] Key: {build_key}")
        # cached = await cache.aget(build_key)
        # if cached is not None:
        #     print(f"[CACHE FOUND IN FINAL CHECK] Key: {build_key}")
        #     return None if cached == CACHE_NULL else cached
        
        # value = await callback()
        # cache_value = CACHE_NULL if value is None else value
        # await cache.aset(build_key, cache_value, timeout)
        # print(f"[CACHE SET - FALLBACK] Key: {build_key}")
        # return value

    @staticmethod
    async def adelete(key: str) -> bool:
        build_key = GlobalCache._key(key)
        try:
            await cache.adelete(build_key)
            return True
        except Exception:
            return False

    @staticmethod
    async def adelete_prefix(prefix: str) -> bool:
        build_key = GlobalCache._key(prefix)
        pattern = f"{build_key}*"
        
        try:
            if hasattr(cache, "adelete_pattern"):
                await cache.adelete_pattern(pattern)
                return True
            
            if hasattr(cache, "akeys"):
                keys = await cache.akeys(pattern)
                for key in keys:
                    await cache.adelete(key)
                return True
            
            raise NotImplementedError(
                "Current cache backend does not support prefix deletion."
            )
        except Exception:
            return False