from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import datetime

from apps.users.models import User
from utils.enums import ListingType, ListingStatusType
from utils.base_model import BaseModel


class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)  # emoji or CSS class
    description = models.CharField(max_length=255, blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['sort_order']),
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
    expires_at = models.DateTimeField()

    hotspots = models.ManyToManyField(CampusHotspot, through='ListingHotspot', related_name='listings')

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['listing_type']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['price']),
            models.Index(fields=['status', 'expires_at']),
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
        return f"Review by {self.from_user.full_name} → {self.to_user.full_name}: {self.rating}★"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update average rating of the reviewee (to_user)
        self.to_user.average_rating = self.to_user.reviews_received.aggregate(
            avg=models.Avg('rating')
        )['avg'] or 0.00
        self.to_user.save(update_fields=['average_rating'])