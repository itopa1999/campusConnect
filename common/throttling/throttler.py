from common.throttling.enums import UserTypeEnum
from common.throttling.helpers import check_rate_limit
from rest_framework.throttling import BaseThrottle

def CustomRateThrottle(rate, period, user_type="anon", scope=None):
    class DynamicThrottle(BaseThrottle):
        def __init__(self):
            self.rate = rate
            self.period = period
            self.user_type = (
                UserTypeEnum.AUTH
                if user_type == "auth"
                else UserTypeEnum.ANON
            )
            self._scope = scope
            self._result = None

        def allow_request(self, request, view):
            if self._scope:
                throttle_scope = self._scope
            else:
                throttle_scope = (
                    f"{view.__class__.__name__}:{request.method.lower()}"
                )

            result = check_rate_limit(
                request=request,
                scope=throttle_scope,
                limit=self.rate,
                seconds=self.period,
                user_type=self.user_type,
            )

            self._result = result
            return result.allowed

        def wait(self):
            if self._result and not self._result.allowed:
                return self._result.retry_after
            return None

    return DynamicThrottle