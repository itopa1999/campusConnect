from django.db.models.signals import post_delete, pre_save, post_save
from django.dispatch import receiver

from apps.users.models import PointPurchase, User
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum
from utils.helpers import convert_to_webp

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
@receiver(post_delete, sender=User)
def user_profile_changed(sender, instance, **kwargs):
    invalidate_profile_cache(instance.id)



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