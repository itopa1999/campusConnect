from apps.users.models import User
from apps.users.serializers import ProfileSerializer
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum


class ProfileQuery:
    @staticmethod
    def get_profile_detail(request, user: User) -> BaseResultWithData:
        """
        Fetch full details of a user profile.
        """

        cache_key = CacheKeysEnum.format(CacheKeysEnum.PROFILE, user_id=user.id)

        def build_profile_data():
            """Heavy computation callback – runs only on cache miss."""
            serializer = ProfileSerializer(user, context={'request': request})
            return serializer.data

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_profile_data,
            timeout=86400,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Profile details retrieved successfully",
            data=data,
            status_code=200
        )