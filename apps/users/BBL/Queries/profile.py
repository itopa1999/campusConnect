

from apps.users.models import User
from apps.users.serializers import ProfileSerializer
from utils.base_result import BaseResultWithData


class ProfileQuery:
    @staticmethod
    def get_profile_detail(request, user: User) -> BaseResultWithData:
        """
        Fetch full details of a user profile.
        """
        serializer = ProfileSerializer(user, context={'request': request})
        return BaseResultWithData(
            message="profile details retrieved successfully",
            data=serializer.data,
            status_code=200
        )