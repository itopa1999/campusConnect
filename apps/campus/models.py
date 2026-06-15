from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
import datetime

from apps.users.models import User
from apps.users.manager import SoftDeleteManager
from utils.enums import BadgeListingType, ListingType, ListingStatusType, LostAndFoundStatusEnum
from utils.base_model import BaseModel


class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['sort_order']),
            models.Index(fields=['is_deleted', 'sort_order']),
        ]
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class CampusHotspot(BaseModel):
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    

    class Meta:
        indexes = [
            models.Index(fields=['is_deleted']),
            models.Index(fields=['sort_order']),
            models.Index(fields=['name']),
            models.Index(fields=['is_deleted', 'sort_order']),
        ]
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.name}"


class Listing(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    category = models.ForeignKey(Category, on_delete=models.RESTRICT, related_name='listings')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ImageField(upload_to='Lisiting_images/',
        blank=True,
        null=True)
    badge = models.CharField(
        max_length=50, 
        choices=BadgeListingType.choices(), 
        blank=True, 
        null=True
    )
    listing_type = models.CharField(
        max_length=10, 
        choices=ListingType.choices(), 
        default=ListingType.SELL.value
    )
    status = models.CharField(
        max_length=10, 
        choices=ListingStatusType.choices(), 
        default=ListingStatusType.ACTIVE.value
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    hotspots = models.ManyToManyField(CampusHotspot, through='ListingHotspot', related_name='listings')
    

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['user', 'is_deleted']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['status', 'is_deleted']),
            models.Index(fields=['listing_type']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['price']),
            models.Index(fields=['status', 'expires_at', 'is_deleted']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-set expires_at to 30 days from creation if not set
        if not self.pk and not self.expires_at:
            self.expires_at = datetime.datetime.now() + datetime.timedelta(days=30)
        super().save(*args, **kwargs)


class ListingHotspot(BaseModel):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    hotspot = models.ForeignKey(CampusHotspot, on_delete=models.CASCADE)

    class Meta:
        unique_together = [['listing', 'hotspot']]
        indexes = [
            models.Index(fields=['listing']),
            models.Index(fields=['hotspot']),
        ]

    def __str__(self):
        return f"{self.listing.title} @ {self.hotspot.name}"


class Review(BaseModel):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    listing = models.ForeignKey(Listing, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = [['from_user', 'to_user', 'listing']]
        indexes = [
            models.Index(fields=['from_user']),
            models.Index(fields=['to_user']),
            models.Index(fields=['listing']),
            models.Index(fields=['rating']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        from_user_name = self.from_user.get_full_name() or self.from_user.email
        to_user_name = self.to_user.get_full_name() or self.to_user.email
        return f"Review by {from_user_name} → {to_user_name}: {self.rating}★"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update average rating of the reviewee (to_user)
        self.to_user.average_rating = self.to_user.reviews_received.aggregate(
            avg=models.Avg('rating')
        )['avg'] or 0.00
        self.to_user.save(update_fields=['average_rating'])


class LostAndFound(BaseModel):
    item_name = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=500)
    date_found = models.DateField()
    status = models.CharField(max_length=20, choices=LostAndFoundStatusEnum.choices(), default='open', db_index=True)
    verification1 = models.CharField(max_length=500)
    answer1 = models.CharField(max_length=500)
    verification2 = models.CharField(max_length=500)
    answer2 = models.CharField(max_length=500)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(max_length=200)
    department = models.CharField(max_length=200)
    image = models.ImageField(upload_to='lost_and_found/',
        blank=True,
        null=True)
    
    

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=['date_found', 'status']),
            models.Index(fields=['email', 'status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item_name} ({self.location})"
    

class Claim(BaseModel):
    lost_item = models.ForeignKey(LostAndFound, on_delete=models.CASCADE, related_name="item_lost")
    answer1 = models.CharField(max_length=500)
    answer2 = models.CharField(max_length=500)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(max_length=200)
    phone_regex = RegexValidator(
        regex=r'^(?:\+234|0)[789][01]\d{8}$',
        message="Phone number must be a valid Nigerian number (e.g., 08012345678 or +2348012345678)."
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=15,
        blank=True,
        null=True
    )


    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=['lost_item']),
            models.Index(fields=['email']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Claim on {self.lost_item.item_name} by {self.full_name}"

    

