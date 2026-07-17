from django.core.cache import cache
from django.http import HttpRequest

from utils.log_helpers import OperationLogger

from .enums import UserTypeEnum
from .models import RateLimitResult
from .utils import build_cache_key, get_client_identifier


def check_rate_limit(
    *,
    request: HttpRequest,
    scope: str,
    limit: int,
    seconds: int,
    user_type: UserTypeEnum,
) -> RateLimitResult:
    """
    Checks whether a client has exceeded the configured rate limit.

    Returns a RateLimitResult indicating:
    - allowed: whether the request is allowed
    - limit: the maximum allowed requests
    - remaining: the number of requests remaining in the window
    - retry_after: seconds to wait if rate-limited (None if allowed)

    Usage:
        result = check_rate_limit(
            request=request,
            scope="api:login",
            limit=5,
            seconds=60,
            user_type=UserTypeEnum.AUTH,
        )

        if not result.allowed:
            return Response(
                {"error": f"Rate limit exceeded. Try again in {result.retry_after} seconds."},
                status=429,
            )
    """

    if limit <= 0:
        raise ValueError("'limit' must be greater than 0.")

    if seconds <= 0:
        raise ValueError("'seconds' must be greater than 0.")

    if not scope.strip():
        raise ValueError("'scope' cannot be empty.")

    # Get client identifier (user ID or IP address)
    identifier = get_client_identifier(
        request=request,
        user_type=user_type,
    )

    # Build cache key for this rate limit window
    cache_key = build_cache_key(
        scope=scope,
        identifier=identifier,
        user_type=user_type,
    )


    # Get current count from cache
    try:
        current_count = cache.get(cache_key, 0)

        # Check if rate limit is exceeded
        if current_count >= limit:
            # Get TTL from cache to calculate retry_after
            ttl = cache.ttl(cache_key)
            if ttl is None or ttl < 0:
                ttl = seconds

            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                retry_after=ttl,
            )

        # Increment the counter atomically
        if current_count == 0:
            cache.set(cache_key, 1, timeout=seconds)
            remaining = limit - 1
        else:
            # Increment and get new value in one atomic operation
            new_count = cache.incr(cache_key)
            # incr doesn't reset TTL, so ensure TTL is set
            cache.expire(cache_key, seconds)
            remaining = limit - new_count

        # Ensure remaining is never negative
        remaining = max(0, remaining)

        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=remaining,
            retry_after=None,
        )

    except Exception as e:
        op = OperationLogger(
            "rate_limit_check",
            data={
                "scope": scope,
                "cache_key": cache_key,
                "user_type": user_type.value,
                "identifier": identifier,
            }
        )
        op.start()
        op.fail(
            f"Rate limit check failed for scope '{scope}': {e}",
            exc=True,
        )

        # Fail open: allow the request
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit - 1,
            retry_after=None,
        )