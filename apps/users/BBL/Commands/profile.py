

from apps.users.models import User
from utils.base_result import BaseResultWithData
from utils.constant_helper import ConstantHelper
from utils.enums import NotificationEnum, UserIdVerificationEnum
from utils.helpers import create_notification
from utils.log_helpers import OperationLogger
from django.db import transaction
from django.utils import timezone
import os
from PIL import Image
from django.core.files.storage import default_storage
from datetime import timedelta

class ProfileCommand:
    @staticmethod
    def update_profile(request, user, validated_data) -> BaseResultWithData:
        op = OperationLogger(f"ProfileCommand.update_profile for user: {user.first_name or user.email}", data=validated_data)
        op.start()

        # ─── Edit Restriction Logic ──────────────────────────────
        edit_day = ConstantHelper.USER_EDIT_DAY
        modified_at = user.modified_at

        # If modified_at is None, treat as today's date (new user)
        if modified_at is None:
            modified_at = timezone.now()

        if edit_day > 0:
            days_since = (timezone.now() - modified_at).days
            if days_since < edit_day:
                next_edit_date = modified_at + timedelta(days=edit_day)
                op.fail(f"Edit restriction for user: {user.first_name or user.email}")
                return BaseResultWithData(
                    message=f"You can only edit once every {edit_day} days. Editing will be available on {next_edit_date.strftime('%Y-%m-%d')}.",
                    status_code=400
                )

        try:
            with transaction.atomic():
                # ─── Extract fields ──────────────────────────────
                phone = validated_data.get('phone')
                level = validated_data.get('level')
                department = validated_data.get('department')
                faculty = validated_data.get('faculty')
                matric_number = validated_data.get('matric_number')

                # ─── Validate phone uniqueness ──────────────────
                if phone is not None and phone.strip() != '':
                    phone_exists = User.objects.filter(
                        phone=phone,
                        is_deleted=False
                    ).exclude(id=user.id).exists()
                    if phone_exists:
                        op.fail(f"Phone {phone} already in use by another user.")
                        return BaseResultWithData(
                            message="Phone number already in use by another user.",
                            status_code=400
                        )

                # ─── Validate matric_number uniqueness ──────────
                if matric_number is not None and matric_number.strip() != '':
                    matric_exists = User.objects.filter(
                        matric_number=matric_number,
                        is_deleted=False
                    ).exclude(id=user.id).exists()
                    if matric_exists:
                        op.fail(f"Matric number {matric_number} already in use.")
                        return BaseResultWithData(
                            message="Matric number already in use by another user.",
                            status_code=400
                        )

                # ─── Validate level range ───────────────────────
                if level is not None:
                    if level < 1 or level > 7:
                        op.fail(f"Invalid level: {level}. Must be between 1 and 7.")
                        return BaseResultWithData(
                            message="Invalid level. Please enter a value between 1 and 7.",
                            status_code=400
                        )

                # ─── Conditional Field Updates ──────────────────
                # Always update phone if provided
                if phone is not None:
                    user.phone = phone

                # Always update level if provided
                if level is not None:
                    user.level = level

                # Only update department if currently empty (null or empty string)
                if department is not None:
                    if user.department is None or user.department == '':
                        user.department = department
                    # else: silently ignore – already has a value

                # Only update faculty if currently empty (null or empty string)
                if faculty is not None:
                    if user.faculty is None or user.faculty == '':
                        user.faculty = faculty
                    # else: silently ignore – already has a value

                # Only update matric_number if currently empty (null or empty string)
                if matric_number is not None:
                    if user.matric_number is None or user.matric_number == '':
                        user.matric_number = matric_number
                    # else: silently ignore – already has a value

                user.save()

                # ─── Send notification ──────────────────────────
                create_notification(
                    user=user,
                    notification_type=NotificationEnum.ACCOUNT.value,
                    title="Profile Update",
                    message="Your profile has been updated successfully",
                    action_url="/student/profile.html"
                )

                op.success(f"Profile updated for user {user.email}")
                return BaseResultWithData(
                    message="Profile updated successfully.",
                    data={'notification': True},
                    status_code=200
                )

        except Exception as e:
            op.fail(f"Unexpected error during profile update for user: {user.first_name or user.email}", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )        

    @staticmethod
    def update_profile_picture(request, user, validated_data) -> BaseResultWithData:
        op = OperationLogger(f"ProfileCommand.update_profile_picture for user: {user.first_name or user.email}", data={'user_id': user.id})
        op.start()

        # 1. Extract the uploaded file
        image_file = validated_data.get('profile_picture')
        if not image_file:
            op.fail(f"No image file provided while update_profile_picture for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="No image file provided.",
                status_code=400
            )

        if image_file.size > ConstantHelper.IMAGE_SIZE:
            op.fail(f"Image too large while update_profile_picture for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message=f"Image file size must not exceed {ConstantHelper.IMAGE_SIZE} MB.",
                status_code=400
            )

        # 3. Validate file type (allowed extensions)
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in allowed_extensions:
            op.fail(f"Invalid file type while update_profile_picture for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Only JPG, PNG, and WEBP images are allowed.",
                status_code=400
            )

        try:
            img = Image.open(image_file)
            img.verify()
        except Exception:
            op.fail(f"Invalid image file while update_profile_picture for user: {user.first_name or user.email}")
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
                        op.fail(f"Could not delete old picture while update_profile_picture for user: {user.first_name or user.email}:  {e}")

                user.profile_picture = image_file

                user.save(update_fields=['profile_picture'])

                op.success(f"Profile picture updated for user {user.first_name or user.email}")
                return BaseResultWithData(
                    message="Profile picture updated successfully.",
                    data = {
                        'profile_picture_url': request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None
                    },
                    status_code=200
                )
 
        except Exception as e:
            op.fail(f"Unexpected error during profile picture update_profile_picture for user: {user.first_name or user.email}", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        

    @staticmethod
    def upload_student_id(request, user: User, validated_data) -> BaseResultWithData:
        op = OperationLogger(f"ProfileCommand.upload_student_id for user: {user.first_name or user.email}", data={'user_id': user.id})
        op.start()

        if user.student_id_verified:
            return BaseResultWithData(
                message="Student ID already verified.",
                status_code=400
            )

        # 1. Extract the uploaded file
        image_file = validated_data.get('student_id')
        if not image_file:
            op.fail(f"No image file provided while upload_student_id for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="No image file provided.",
                status_code=400
            )

        if image_file.size > ConstantHelper.IMAGE_SIZE:
            op.fail(f"Image too large while upload_student_id for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message=f"Image file size must not exceed {ConstantHelper.IMAGE_SIZE} MB.",
                status_code=400
            )

        # 3. Validate file type (allowed extensions)
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in allowed_extensions:
            op.fail(f"Invalid file type while upload_student_id for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Only JPG, PNG, and WEBP images are allowed.",
                status_code=400
            )

        try:
            img = Image.open(image_file)
            img.verify()
        except Exception:
            op.fail(f"Invalid image file while upload_student_id for user: {user.first_name or user.email}")
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
                        op.fail(f"Could not delete old picture while upload_student_id for user: {user.first_name or user.email}: {e}")

                user.student_id_photo = image_file
                user.student_id_verified_status = UserIdVerificationEnum.PENDING.value

                user.save(update_fields=['student_id_photo', 'student_id_verified_status'])

                create_notification(
                    user=user,
                    notification_type=NotificationEnum.ACCOUNT.value,
                    title="Student ID Uploaded",
                    message="Your student ID has been uploaded successfully",
                    action_url="/student/profile.html"
                )

                # send email later here please

                op.success(f"Id Uploaded for user {user.first_name or user.email}")
                return BaseResultWithData(
                    message="Id Uploaded successfully. We review and update you on the progress",
                    data = {'notification': True},
                    status_code=200
                )
 
        except Exception as e:
            op.fail(f"Unexpected error during student id picture update for user: {user.first_name or user.email}", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )

    @staticmethod
    def add_student_hall(request, user: User, validated_data) -> BaseResultWithData:
        op = OperationLogger(
            f"ProfileCommand.add_student_hall for user: {user.email}",
            user_id=getattr(user, 'id', None)
        )
        op.start()
        try:
            if user.hall_verified or user.hall_verified_status.lower() == UserIdVerificationEnum.APPROVED.value.lower():
                op.fail(f"User {user.email} hall is already verified; updates not allowed.")
                return BaseResultWithData(
                    message="Your hall is already verified. Updates are not allowed.",
                    data=None,
                    status_code=400
                )

            hall_residence = validated_data.get('hall_residence')
            hall_number = validated_data.get('hall_number')

            user.hall_residence = hall_residence
            user.hall_number = hall_number
            user.hall_verified = False
            user.hall_verified_status = UserIdVerificationEnum.PENDING.value
            user.save(update_fields=['hall_residence', 'hall_number',
                                    'hall_verified', 'hall_verified_status'])

            create_notification(
                user=user,
                notification_type=NotificationEnum.ACCOUNT.value,
                title="Hall Verification Submitted",
                message=(
                    f"Your hall details for '{hall_residence}' (Room {hall_number}) "
                    "have been submitted for verification. We will review and notify you."
                ),
                action_url="/student/hall-verification.html"
            )

            # TODO Optionally send email notification via background task

            op.success(f"Hall details updated for user: {user.email}")
            return BaseResultWithData(
                message="Hall details submitted for verification.",
                data={
                    "hall_residence": hall_residence,
                    "hall_number": hall_number,
                    "student_hall_verified": False,
                    "student_hall_verified_status": UserIdVerificationEnum.PENDING.value,
                    'notification': True
                },
                status_code=200
            )

        except Exception as e:
            op.fail(f"Error updating hall details: {str(e)}", exc=e)
            return BaseResultWithData(
                message=f"Error updating hall details: {str(e)}",
                data=None,
                status_code=500
            )


    @staticmethod
    def toggle_visibilty(request, user: User) -> BaseResultWithData:
        op = OperationLogger(
            f"ProfileCommand.toggle_visibilty for user: {user.email}",
            user_id=getattr(user, 'id', None)
        )
        op.start()

        new_visibilty = not user.visibility
        user.visibility = new_visibilty
        user.save(update_fields=['visibility'])

        message=f"Profile set to {'public' if new_visibilty else 'private'} successfully",

        return BaseResultWithData(
            message=message,
            data={
                'is_visibilty': user.visibility
            },
            status_code=200
        )

