from dataclasses import dataclass


@dataclass(slots=True)
class RateLimitResult:
    """
    Represents the outcome of a rate limit check.
    """

    allowed: bool
    limit: int
    remaining: int
    retry_after: int | None = None