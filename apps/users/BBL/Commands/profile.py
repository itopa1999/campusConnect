

from apps.users.models import User
from utils.base_result import BaseResultWithData
from utils.constant_helper import ConstantHelper
from utils.log_helpers import OperationLogger
from django.db import transaction
from django.utils import timezone
import os
from PIL import Image
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


class ProfileCommand:
    @staticmethod
    def update_profile(request, user, validated_data) -> BaseResultWithData:
        op = OperationLogger("ProfileCommand.update_profile", data=validated_data)
        op.start()

        if ConstantHelper.USER_EDIT_DAY > 0 and user.modified_at:
            days_since = (timezone.now() - user.modified_at).days
            if days_since < ConstantHelper.USER_EDIT_DAY:
                op.fail("Edit restriction")
                return BaseResultWithData(
                    message=f"You can only edit once every {ConstantHelper.EDIT_DATE} days. Last edit was {user.modified_at.strftime('%Y-%m-%d')}.",
                    status_code=400
                )

        try:
            with transaction.atomic():
                phone = validated_data.get('phone')
                if phone is not None and phone.strip() != '':
                    phone_exists = User.objects.filter(
                        phone=phone,
                        is_deleted=False
                    ).exclude(id=user.id).exists()
                    if phone_exists:
                        op.fail("Phone number already in use by another user.")
                        return BaseResultWithData(
                            message="Phone number already in use by another user.",
                            status_code=400
                        )

                # ─── Validate matric_number uniqueness ─────────
                matric_number = validated_data.get('matric_number')
                if matric_number is not None and matric_number.strip() != '':
                    matric_exists = User.objects.filter(
                        matric_number=matric_number,
                        is_deleted=False
                    ).exclude(id=user.id).exists()
                    if matric_exists:
                        op.fail("Matric number already in use by another user.")
                        return BaseResultWithData(
                            message="Matric number already in use by another user.",
                            status_code=400
                        )

                # ─── Handle full_name ──────────────────────────
                full_name = validated_data.pop('full_name', None)
                if full_name:
                    parts = full_name.split(' ', 1)
                    user.first_name = parts[0]
                    user.last_name = parts[1] if len(parts) > 1 else ''

                # ─── Handle booleans ────────────────────────────
                notification = validated_data.pop('notification', None)
                if notification is not None:
                    user.notification = notification

                visibility = validated_data.pop('visibility', None)
                if visibility is not None:
                    user.visibility = visibility

                # ─── Update remaining fields ────────────────────
                for field in ['phone', 'department', 'faculty', 'level', 'matric_number']:
                    if field in validated_data:
                        setattr(user, field, validated_data[field])

                user.save()

                op.success(f"Profile updated for user {user.email}")
                return BaseResultWithData(
                    message="Profile updated successfully.",
                    status_code=200
                )

        except Exception as e:
            op.fail("Unexpected error during profile update", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        

    @staticmethod
    def update_profile_picture(request, user, validated_data) -> BaseResultWithData:
        op = OperationLogger("ProfileCommand.update_profile_picture", data={'user_id': user.id})
        op.start()

        # 1. Extract the uploaded file
        image_file = validated_data.get('profile_picture')
        if not image_file:
            op.fail("No image file provided")
            return BaseResultWithData(
                message="No image file provided.",
                status_code=400
            )

        if image_file.size > ConstantHelper.IMAGE_SIZE:
            op.fail("Image too large")
            return BaseResultWithData(
                message=f"Image file size must not exceed {ConstantHelper.IMAGE_SIZE} MB.",
                status_code=400
            )

        # 3. Validate file type (allowed extensions)
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in allowed_extensions:
            op.fail("Invalid file type")
            return BaseResultWithData(
                message="Only JPG, PNG, and WEBP images are allowed.",
                status_code=400
            )

        try:
            img = Image.open(image_file)
            img.verify()
        except Exception:
            op.fail("Invalid image file")
            return BaseResultWithData(
                message="The uploaded file is not a valid image.",
                status_code=400
            )

        try:
            with transaction.atomic():
                if user.profile_picture and user.profile_picture.name:
                    try:
                        default_storage.delete(user.profile_picture.path)
                    except Exception as e:
                        op.warning(f"Could not delete old picture: {e}")

                user.profile_picture = image_file

                user.save(update_fields=['profile_picture'])

                op.success(f"Profile picture updated for user {user.id}")
                return BaseResultWithData(
                    message="Profile picture updated successfully.",
                    status_code=200
                )
 
        except Exception as e:
            op.fail("Unexpected error during profile picture update", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        

    @staticmethod
    def upload_student_id(request, user, validated_data) -> BaseResultWithData:
        op = OperationLogger("ProfileCommand.upload_student_id", data={'user_id': user.id})
        op.start()

        if user.student_id_verified:
            return BaseResultWithData(
                message="Student ID already verified.",
                status_code=400
            )

        # 1. Extract the uploaded file
        image_file = validated_data.get('student_id')
        if not image_file:
            op.fail("No image file provided")
            return BaseResultWithData(
                message="No image file provided.",
                status_code=400
            )

        if image_file.size > ConstantHelper.IMAGE_SIZE:
            op.fail("Image too large")
            return BaseResultWithData(
                message=f"Image file size must not exceed {ConstantHelper.IMAGE_SIZE} MB.",
                status_code=400
            )

        # 3. Validate file type (allowed extensions)
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in allowed_extensions:
            op.fail("Invalid file type")
            return BaseResultWithData(
                message="Only JPG, PNG, and WEBP images are allowed.",
                status_code=400
            )

        try:
            img = Image.open(image_file)
            img.verify()
        except Exception:
            op.fail("Invalid image file")
            return BaseResultWithData(
                message="The uploaded file is not a valid image.",
                status_code=400
            )

        try:
            with transaction.atomic():
                if user.student_id_photo and user.student_id_photo.name:
                    try:
                        default_storage.delete(user.student_id_photo.path)
                    except Exception as e:
                        op.warning(f"Could not delete old picture: {e}")

                user.student_id_photo = image_file

                user.save(update_fields=['student_id_photo'])

                # send email later here please

                op.success(f"Id Uploaded for user {user.id}")
                return BaseResultWithData(
                    message="Id Uploaded successfully. We review and updata you the progress",
                    status_code=200
                )
 
        except Exception as e:
            op.fail("Unexpected error during profile picture update", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )



