

from django.core.cache import cache
from django.http import HttpRequest

from .enums import UserType
from .models import RateLimitResult
from .utils import build_cache_key, get_client_identifier


def check_rate_limit(
    *,
    request: HttpRequest,
    scope: str,
    limit: int,
    seconds: int,
    user_type: UserType,
) -> RateLimitResult:
    """
    Checks whether a client has exceeded the configured rate limit.
    """

    if limit <= 0:
        raise ValueError("'limit' must be greater than 0.")

    if seconds <= 0:
        raise ValueError("'seconds' must be greater than 0.")

    if not scope.strip():
        raise ValueError("'scope' cannot be empty.")
    
    identifier = get_client_identifier(
        request=request,
        user_type=user_type,
    )


    cache_key = build_cache_key(
        scope=scope,
        identifier=identifier,
        user_type=user_type,
    )