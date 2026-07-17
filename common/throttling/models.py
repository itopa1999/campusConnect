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

    def __post_init__(self):
        """Validate that remaining is never negative."""
        if self.remaining < 0:
            self.remaining = 0