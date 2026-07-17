from django.http import HttpRequest
from .enums import UserTypeEnum


def get_client_identifier(
    request: HttpRequest,
    user_type: UserTypeEnum,
) -> str:
    """
    Returns a unique identifier for the client.

    - AUTH users -> User ID
    - ANON users -> Client IP Address
    """

    if user_type == UserTypeEnum.AUTH:
        return str(request.user.pk)

    if user_type == UserTypeEnum.AUTO:
        if request.user.is_authenticated:
            return str(request.user.pk)

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    ip = request.META.get("REMOTE_ADDR")

    if ip is None:
        raise ValueError("Unable to determine the client's IP address.")

    return ip



def build_cache_key(
    scope: str,
    identifier: str,
    user_type: UserTypeEnum,
) -> str:
    """
    Builds a unique cache key for rate limiting.
    """

    return f"rate_limit:{scope}:{user_type.value}:{identifier}"


def format_duration(seconds: int) -> str:
    """
    Converts seconds into a human-readable duration.

    Examples:
        45 -> "45 seconds"
        90 -> "1 minute 30 seconds"
        3665 -> "1 hour 1 minute 5 seconds"
    """

    if seconds <= 0:
        return "0 seconds"

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []

    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")

    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    if seconds:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    return " ".join(parts)


