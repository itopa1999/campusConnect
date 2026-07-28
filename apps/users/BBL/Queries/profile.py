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

    @staticmethod
    def get_student_id_record(request, user: User) -> BaseResultWithData:
        cache_key = CacheKeysEnum.format(CacheKeysEnum.PROFILE_ID, user_id=user.id)

        def build_profile_data():
            data = {
                'student_id_verified': user.student_id_verified,
                'student_id_verified_status': user.student_id_verified_status,
                'student_id_photo_url': None,
            }
            if user.student_id_photo:
                data['student_id_photo_url'] = request.build_absolute_uri(user.student_id_photo.url)

            return data

        cached_data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_profile_data,
            timeout=86400,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Student ID record retrieved",
            data=cached_data,
            status_code=200
        )



    @staticmethod
    def get_student_hall_verification_record(request, user: User) -> BaseResultWithData:
        cache_key = CacheKeysEnum.format(CacheKeysEnum.PROFILE_HALL, user_id=user.id)

        def build_profile_data():
            data = {
                'student_hall_verified': user.hall_verified,
                'student_hall_verified_status': user.hall_verified_status,
                'hall_residence': user.hall_residence,
                'hall_number': user.hall_number,
            }

            return data

        cached_data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_profile_data,
            timeout=86400,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Student ID record retrieved",
            data=cached_data,
            status_code=200
        )


    @staticmethod
    def get_student_visibility(request, user: User) -> BaseResultWithData:
        cache_key = CacheKeysEnum.format(CacheKeysEnum.PROFILE_VISIBILITY, user_id=user.id)

        def build_profile_data():
            data = {
                'is_visibility': user.visibility,
            }
            return data

        cached_data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_profile_data,
            timeout=86400,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Student Visibility record retrieved",
            data=cached_data,
            status_code=200
        )