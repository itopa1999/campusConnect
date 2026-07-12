from django.db.models.signals import post_delete, pre_save, post_save
from django.dispatch import receiver

from apps.campus.models import CampusHotspot, Category, Listing, LostAndFound, Review
from apps.users.models import PointPackage, PointPurchase, PointTransaction
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum
from utils.helpers import convert_to_webp


@receiver(pre_save, sender=LostAndFound)
def store_old_lostfound_image(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_image = old.image
        except sender.DoesNotExist:
            instance._old_image = None
    else:
        instance._old_image = None

@receiver(post_save, sender=LostAndFound)
def convert_lostfound_image(sender, instance, created, **kwargs):
    if getattr(instance, '_converting_images', False):
        return
    updated = False
    if (instance.image and 
        instance.image != instance._old_image and
        not instance.image.name.lower().endswith('.webp')):
        if convert_to_webp(instance, 'image', quality=30):
            updated = True
    if updated:
        instance._converting_images = True
        instance.save(update_fields=['image'])
        instance._converting_images = False

@receiver(pre_save, sender=Listing)
def store_old_listing_image(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_image = old.image
        except sender.DoesNotExist:
            instance._old_image = None
    else:
        instance._old_image = None

@receiver(post_save, sender=Listing)
def convert_listing_image(sender, instance, created, **kwargs):
    if getattr(instance, '_converting_images', False):
        return
    updated = False
    if (instance.image and 
        instance.image != instance._old_image and
        not instance.image.name.lower().endswith('.webp')):
        if convert_to_webp(instance, 'image', quality=30):
            updated = True
    if updated:
        instance._converting_images = True
        instance.save(update_fields=['image'])
        instance._converting_images = False



# for cache invalidation

@receiver(post_save, sender=Listing)
@receiver(post_delete, sender=Listing)
def listing_changed(sender, instance, **kwargs):
    user_id = instance.user_id if instance else None
    if user_id:
        invalidate_dashboard_cache(user_id)
    invalidate_listing_caches(instance)
    GlobalCache.delete(CacheKeysEnum.INDEX_PRODUCTS.value)


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def review_changed(sender, instance, **kwargs):

    user_id = instance.to_user_id if instance else None
    if user_id:
        invalidate_dashboard_cache(user_id)

    cache_key = CacheKeysEnum.format(CacheKeysEnum.LISTING_DETAIL, user_id=user_id, listing_id=instance.listing_id)
    cache_key2 = CacheKeysEnum.format(CacheKeysEnum.PUBLIC_LISTING_DETAILS, user_id=user_id, listing_id=instance.listing_id)
    GlobalCache.delete(cache_key)
    GlobalCache.delete(cache_key2)


@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def category_changed(sender, instance, **kwargs):
    invalidate_lookup_cache()

@receiver(post_save, sender=CampusHotspot)
@receiver(post_delete, sender=CampusHotspot)
def campus_hotspot_changed(sender, instance, **kwargs):
    invalidate_lookup_cache()


@receiver(post_save, sender=LostAndFound)
@receiver(post_delete, sender=LostAndFound)
def lost_item_changed(sender, instance, **kwargs):
    GlobalCache.delete_prefix("lost_items_")


@receiver(post_save, sender=PointPackage)
@receiver(post_delete, sender=PointPackage)
def point_package_changed(sender, instance, **kwargs):
    invalidate_packages_cache()


@receiver(post_save, sender=PointPurchase)
@receiver(post_delete, sender=PointPurchase)
def point_purchase_changed(sender, instance, **kwargs):
    invalidate_user_point_caches(instance.user_id)


@receiver(post_save, sender=PointTransaction)
@receiver(post_delete, sender=PointTransaction)
def point_transaction_changed(sender, instance, **kwargs):
    invalidate_user_point_caches(instance.user_id)



def invalidate_dashboard_cache(user_id):
    if not user_id:
        return
    key = CacheKeysEnum.format(CacheKeysEnum.DASHBOARD, user_id=user_id)
    GlobalCache.delete(key)


def invalidate_lookup_cache():
    GlobalCache.delete(CacheKeysEnum.LOOKUP_DATA.value)


def invalidate_listing_caches(listing):
    if not listing or not listing.user_id:
        return
    detail_key = CacheKeysEnum.format(CacheKeysEnum.LISTING_DETAIL,
                                      user_id=listing.user_id,
                                      listing_id=listing.id)
    
    GlobalCache.delete(detail_key)

    prefix = "categorized_listings_"
    GlobalCache.delete_prefix(prefix)


def invalidate_packages_cache():
    GlobalCache.delete(CacheKeysEnum.POINT_PACKAGES.value)

def invalidate_user_purchases_cache(user_id):
    prefix = f"purchases_{user_id}_"
    GlobalCache.delete_prefix(prefix)

def invalidate_user_transactions_cache(user_id):
    prefix = f"transactions_{user_id}_"
    GlobalCache.delete_prefix(prefix)

def invalidate_user_point_caches(user_id):
    invalidate_user_purchases_cache(user_id)
    invalidate_user_transactions_cache(user_id)

    cache_key = CacheKeysEnum.format(CacheKeysEnum.GET_POINTS_BALANCE, user_id=user_id)
    GlobalCache.delete(cache_key)