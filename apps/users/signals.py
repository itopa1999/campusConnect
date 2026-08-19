from django.db.models.signals import post_delete, pre_save, post_save
from django.dispatch import receiver

from apps.users.models import Notification, PointPurchase, User
from utils.Middlewares.threadlocals import get_current_user
from utils.base_model import BaseModel
from utils.cache_helper import GlobalCache
from utils.constant_helper import ConstantHelper
from utils.enums import BadgeChoiceEnum, CacheKeysEnum
from utils.helpers import BadgeService, cloudinary_conversion_to_webp
from django.utils import timezone

@receiver(pre_save)
def auto_fill_audit_fields(sender, instance, **kwargs):
    # Only for models inheriting from BaseModel
    if not issubclass(sender, BaseModel):
        return

    user = get_current_user()
    action_by = getattr(user, "first_name", None) or getattr(user, "email", None) or "System"

    if instance._state.adding:
        if not instance.created_by:
            instance.created_by = action_by
    else:
        instance.modified_by = action_by

    if instance.is_deleted and not instance.deleted_at:
        instance.deleted_at = timezone.now()
        instance.deleted_by = action_by

        

@receiver(pre_save, sender=User)
def convert_updated_images_to_webp(sender, instance, **kwargs):

    if not instance.pk:
        if instance.profile_picture:
            cloudinary_conversion_to_webp(
                instance=instance,
                image=instance.profile_picture,
                field_name="profile_picture",
            )

        if instance.student_id_photo:
            cloudinary_conversion_to_webp(
                instance=instance,
                image=instance.student_id_photo,
                field_name="student_id_photo",
            )

        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        old_instance = None

    if not old_instance:
        return

    current_profile = instance.profile_picture
    old_profile = old_instance.profile_picture

    profile_changed = (
        bool(current_profile)
        and (
            not old_profile
            or current_profile.name != old_profile.name
        )
    )

    if profile_changed:
        cloudinary_conversion_to_webp(
            instance=instance,
            image=current_profile,
            field_name="profile_picture",
        )


    current_student_id = instance.student_id_photo
    old_student_id = old_instance.student_id_photo

    student_id_changed = (
        bool(current_student_id)
        and (
            not old_student_id
            or current_student_id.name != old_student_id.name
        )
    )

    if student_id_changed:
        cloudinary_conversion_to_webp(
            instance=instance,
            image=current_student_id,
            field_name="student_id_photo",
        )

    

# for cache


    # if instance.hall_verified and instance.hall_verified_status == UserIdVerificationEnum.APPROVED.value:
    #     BadgeService.set(instance, [BadgeChoiceEnum.HALL_VERIFIED.value])

    # if instance.student_id_verified and instance.student_id_verified_status == UserIdVerificationEnum.APPROVED.value:
    #     BadgeService.set(instance, [BadgeChoiceEnum.ID_VERIFIED.value])


@receiver(post_save, sender=User)
@receiver(post_delete, sender=User)
def user_profile_changed(sender, instance, **kwargs):
    invalidate_profile_cache(instance.id)

    prefix = f"public_listing_details_{instance.id}_"
    GlobalCache.delete_prefix(prefix)



def invalidate_profile_cache(user_id):
    if not user_id:
        return
    key = CacheKeysEnum.format(CacheKeysEnum.PROFILE, user_id=user_id)
    GlobalCache.delete(key)



@receiver(post_save, sender=PointPurchase)
@receiver(post_delete, sender=PointPurchase)
def point_purchase_changed(sender, instance, **kwargs):
    cache_key = CacheKeysEnum.POINT_PACKAGES.value
    GlobalCache.delete(cache_key)

    prefix = f"purchases_{instance.user_id}"
    GlobalCache.delete_prefix(prefix)

    prefix1 = f"transactions_{instance.user_id}"
    GlobalCache.delete_prefix(prefix1)



@receiver(post_save, sender=Notification)
@receiver(post_delete, sender=Notification)
def notification_changed(sender, instance, **kwargs):
    prefix = f"notifications_{instance.user_id}"
    GlobalCache.delete_prefix(prefix)

    prefix1 = f"notifications_header_{instance.user_id}"
    GlobalCache.delete_prefix(prefix1)