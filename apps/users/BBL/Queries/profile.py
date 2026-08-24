from apps.users.models import User
from apps.users.serializers import ProfileSerializer
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum, FeatureFlagEnum, UserIdVerificationEnum
from utils.featureflag import is_feature_active
from asgiref.sync import sync_to_async
import asyncio

class ProfileQuery:
    @staticmethod
    async def get_profile_detail(request, user: User) -> BaseResultWithData:
        """
        Fetch full details of a user profile.
        """

        cache_key = CacheKeysEnum.format(CacheKeysEnum.PROFILE, user_id=user.id)

        @sync_to_async(thread_sensitive=False)
        def build_profile_data():
            """Heavy computation callback – runs only on cache miss."""
            serializer = ProfileSerializer(user, context={'request': request})
            return serializer.data

        try:
            data = await GlobalCache.aget_or_set(
                key=cache_key,
                callback=build_profile_data,
                timeout=86400,
                lock_timeout=30,
                max_wait=5.0,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return BaseResultWithData(
                message=f"An error occurred: {str(e)}",
                status_code=500
            )

        return BaseResultWithData(
            message="Profile details retrieved successfully",
            data=data,
            status_code=200
        )

    @staticmethod
    def get_student_id_record(request, user: User) -> BaseResultWithData:
        cache_key = CacheKeysEnum.format(CacheKeysEnum.PROFILE_ID, user_id=user.id)

        is_verified = (
            user.student_id_verified is True
            or str(user.student_id_verified_status).lower() == UserIdVerificationEnum.APPROVED.value.lower()
        )
        data = {
            'student_id_verified': user.student_id_verified,
            'student_id_verified_status': user.student_id_verified_status,
            'student_id_photo_url': None,
            'student_id_verified_rejection_reason': None
        }
        if not is_verified and user.student_id_photo:
            data["student_id_photo_url"] = user.student_id_photo.url

        if user.student_id_verified_status == UserIdVerificationEnum.REJECTED.value:
            data["student_id_verified_rejection_reason"] = user.student_id_verified_rejection_reason


        return BaseResultWithData(
            message="Student ID record retrieved",
            data=data,
            status_code=200
        )



    @staticmethod
    def get_student_hall_verification_record(request, user: User) -> BaseResultWithData:
        data = {
            'student_hall_verified': user.hall_verified,
            'student_hall_verified_status': user.hall_verified_status,
            'hall_residence': user.hall_residence,
            'hall_number': user.hall_number,
            'hall_verified_status_rejection_reason': None
        }

        if user.hall_verified_status == UserIdVerificationEnum.REJECTED.value:
            data["hall_verified_status_rejection_reason"] = user.hall_verified_status_rejection_reason

        return BaseResultWithData(
            message="Student ID record retrieved",
            data=data,
            status_code=200
        )


    @staticmethod
    def get_student_visibility(request, user: User) -> BaseResultWithData:
        if is_feature_active(FeatureFlagEnum.HIDE_VISIBILITY.value):
            data = {
                'is_visibility': None, 
            }
        else:
            data = {
                'is_visibility': user.visibility,
            }

        return BaseResultWithData(
            message="Student Visibility record retrieved",
            data=data,
            status_code=200
        )