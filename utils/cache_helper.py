from django.core.cache import cache
from django.conf import settings

from utils.log_helpers import OperationLogger

CACHE_TTL = settings.DEFAULT_CACHE_TTL 


class GlobalCache:
    @staticmethod
    def get(key):
        op = OperationLogger("get_cache", data={"cache_key": key})
        op.start()

        try:
            return cache.get(key)
        except Exception as e:
            op.fail(f"Failed to get cache key '{key}': {e}")
            return None

    @staticmethod
    def set(key, value, timeout=CACHE_TTL):
        """Store data globally"""
        op = OperationLogger("set_cache", data={"cache_key": key})
        op.start()

        try:
            cache.set(key, value, timeout)
        except Exception as e:
            op.fail(f"Failed to set cache key '{key}': {e}")

    @staticmethod
    def delete(key):
        """Delete a single cache key"""
        op = OperationLogger("delete_cache", data={"cache_key": key})
        op.start()

        try:
            cache.delete(key)
        except Exception as e:
            op.fail(f"Failed to delete cache key '{key}': {e}")

    @staticmethod
    def clear():
        """Clear all cache data (GLOBAL CLEAR)"""
        op = OperationLogger("clear_cache")
        op.start()
        try:
            cache.clear()
        except Exception as e:
            op.fail(f"Failed to clear cache: {e}")
        return True

    @staticmethod
    def delete_prefix(prefix: str):
        """
        Delete all cache keys starting with a given prefix.
        Works with Redis and LocMemCache (if keys() supported).
        """
        op = OperationLogger("delete_cache_prefix", data={"prefix": prefix})
        op.start()
        
        pattern = f"{prefix}*"
        try:
            # For RedisCache (supports delete_pattern)
            if hasattr(cache, "delete_pattern"):
                cache.delete_pattern(pattern)
            # For caches that expose .keys() (like LocMemCache)
            elif hasattr(cache, "keys"):
                for key in cache.keys(pattern):
                    cache.delete(key)
            else:
                cache.clear()
                op.fail("⚠️ Cache backend doesn't support prefix delete — cleared all cache.")
            return True
        except Exception as e:
            op.fail(f"Failed to delete prefix '{prefix}' from cache: {e}")
            return False