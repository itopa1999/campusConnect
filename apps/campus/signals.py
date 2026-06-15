from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from apps.campus.models import Listing, LostAndFound
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