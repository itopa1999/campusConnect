from django.conf import settings
from django.core.cache import cache

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
    def get_or_set(
        key: str,
        callback,
        timeout = 30,
        # timeout: int = CACHE_TTL,
        lock_timeout: int = 30,
        max_wait: float = 5.0,
    ):
        """
        Retrieve data from cache or generate and cache it.

        Uses a distributed lock to reduce cache stampedes when
        multiple requests attempt to populate the same cache key.
        """

        build_key = GlobalCache._key(key)
        lock_key = f"{build_key}:lock"

        op = OperationLogger(
            "cache_get_or_set",
            data={"cache_key": build_key}
        )
        op.start()

        try:
            # Fast path
            cached = cache.get(build_key)

            if cached is not None:
                return None if cached == CACHE_NULL else cached

            # Attempt lock acquisition
            acquired = cache.add(
                lock_key,
                "1",
                timeout=lock_timeout
            )

            if acquired:
                try:
                    value = callback()

                    GlobalCache.set(
                        key=key,
                        value=value,
                        timeout=timeout
                    )

                    return value

                finally:
                    cache.delete(lock_key)

            # Wait for lock holder to populate cache
            start = time.monotonic()
            wait_interval = 0.1

            while time.monotonic() - start < max_wait:

                cached = cache.get(build_key)

                if cached is not None:
                    return (
                        None
                        if cached == CACHE_NULL
                        else cached
                    )

                time.sleep(wait_interval)

                wait_interval = min(
                    wait_interval * 1.5,
                    0.5
                )

            # Final cache check
            cached = cache.get(build_key)

            if cached is not None:
                return (
                    None
                    if cached == CACHE_NULL
                    else cached
                )

            # Fallback computation
            value = callback()

            GlobalCache.set(
                key=key,
                value=value,
                timeout=timeout
            )

            return value

        except Exception as e:
            op.fail(
                f"Cache get_or_set failed for key '{build_key}': {e}"
            )
            raise

    @staticmethod
    def delete(key: str) -> bool:
        build_key = GlobalCache._key(key)

        op = OperationLogger(
            "cache_delete",
            data={"cache_key": build_key}
        )
        op.start()

        try:
            cache.delete(build_key)
            return True

        except Exception as e:
            op.fail(
                f"Failed to delete cache key '{build_key}': {e}"
            )
            return False

    @staticmethod
    def delete_prefix(prefix: str) -> bool:
        """
        Delete all cache keys matching a prefix.

        Requires a cache backend that supports pattern deletion.
        """

        build_key = GlobalCache._key(prefix)

        op = OperationLogger(
            "cache_delete_prefix",
            data={"prefix": build_key}
        )
        op.start()

        pattern = f"{build_key}*"

        try:
            if hasattr(cache, "delete_pattern"):
                cache.delete_pattern(pattern)
                return True

            if hasattr(cache, "keys"):
                keys = cache.keys(pattern)

                for key in keys:
                    cache.delete(key)

                return True

            raise NotImplementedError(
                "Current cache backend does not support prefix deletion."
            )

        except Exception as e:
            op.fail(
                f"Failed to delete cache prefix '{build_key}': {e}"
            )
            return False