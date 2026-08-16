from django.db.models.signals import post_delete, pre_save, post_save
from django.dispatch import receiver

from apps.users.models import Notification, PointPurchase, User
from utils.Middlewares.threadlocals import get_current_user
from utils.base_model import BaseModel
from utils.cache_helper import GlobalCache
from utils.constant_helper import ConstantHelper
from utils.enums import BadgeChoiceEnum, CacheKeysEnum
from utils.helpers import BadgeService, convert_to_webp
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
def store_old_images(sender, instance, **kwargs):
    """Store the old image fields before the instance is saved."""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_profile_picture = old.profile_picture
            instance._old_student_id = old.student_id_photo
        except sender.DoesNotExist:
            instance._old_profile_picture = None
            instance._old_student_id = None
    else:
        instance._old_profile_picture = None
        instance._old_student_id = None

@receiver(post_save, sender=User)
def convert_updated_images_to_webp(sender, instance, created, **kwargs):
    """Convert only the image field(s) that were updated."""
    # Avoid infinite recursion
    if getattr(instance, '_converting_images', False):
        return

    updated_fields = []

    # Check if profile_picture changed and needs conversion
    if (instance.profile_picture and 
        instance.profile_picture != instance._old_profile_picture and
        not instance.profile_picture.name.lower().endswith('.webp')):
        if convert_to_webp(instance, 'profile_picture', quality=30):
            updated_fields.append('profile_picture')

    # Check if student_id_photo changed and needs conversion
    if (instance.student_id_photo and 
        instance.student_id_photo != instance._old_student_id and
        not instance.student_id_photo.name.lower().endswith('.webp')):
        if convert_to_webp(instance, 'student_id_photo', quality=30):
            updated_fields.append('student_id_photo')

    # If any conversion happened, save only those fields
    if updated_fields:
        instance._converting_images = True
        instance.save(update_fields=updated_fields)
        instance._converting_images = False



# for cache

@receiver(post_save, sender=User)
def add_badges(sender, instance, **kwargs):
    if instance.sold_items >= ConstantHelper.SOLD_ITEMS_COUNT_FOR_TOP_SELLER_BADGE:
        print(instance.sold_items)
        BadgeService.set(instance, [BadgeChoiceEnum.TOP_SELLER.value])

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