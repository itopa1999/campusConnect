

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
        cached_data = GlobalCache.get(cache_key)
        if cached_data:
            return BaseResultWithData(
                message="Profile details retrieved",
                data=cached_data,
                status_code=200
            )
        
        serializer = ProfileSerializer(user, context={'request': request})

        data = serializer.data

        GlobalCache.set(cache_key, data)
        return BaseResultWithData(
            message="profile details retrieved successfully",
            data=data,
            status_code=200
        )