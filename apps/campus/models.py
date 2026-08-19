from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
import datetime
from django.utils import timezone
from apps.users.models import User
from utils.enums import ListingConditionEnum, ListingTypeEnum, ListingStatusTypeEnum, LostAndFoundStatusEnum, PreferredGenderEnum, PreferredStudentEnum, PurposeChoicesEnum
from utils.base_model import BaseModel
import os
import uuid
import re

def listing_upload_path(instance, filename):
    item_name = instance.title.strip()
    item_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", item_name)
    item_name = item_name[:80].strip("_")
    unique = uuid.uuid4().hex[:10]
    return f"listing_images/Listing_image_{item_name}_{unique}.webp"

def lost_and_found_upload_path(instance, filename):
    item_name = instance.item_name.strip()
    item_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", item_name)
    item_name = item_name[:80].strip("_")
    unique = uuid.uuid4().hex[:10]
    return f"lost_and_found/lost_and_found_{item_name}_{unique}.webp"


class Category(BaseModel):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name (e.g., 'Electronics', 'Books')."
    )
    listing_type = models.CharField(
        max_length=100,
        null=True,
        choices=ListingTypeEnum.choices(),
        help_text="Category type (e.g., sell, wanted, service, accommodation)."
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL‑friendly version of the name (auto‑generated)."
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Optional icon class (e.g., FontAwesome icon name)."
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Brief description of the category."
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)."
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=['listing_type']),
            models.Index(fields=['name', 'listing_type']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['sort_order']),
            models.Index(fields=['is_deleted', 'sort_order']),
        ]
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class SubCategory(BaseModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        related_name="subcategories",
        help_text="Parent category this subcategory belongs to."
    )
    name = models.CharField(
        max_length=100,
        help_text="Subcategory name (e.g., 'Laptops', 'Fiction')."
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Optional icon class (e.g., FontAwesome icon name)."
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL‑friendly version of the name."
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Brief description of the subcategory."
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the parent category."
    )

    class Meta:
        verbose_name = "Subcategory"
        verbose_name_plural = "Subcategories"
        constraints = [
            models.UniqueConstraint(
                fields=["category", "name"],
                name="unique_subcategory_per_category",
            ),
        ]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["is_deleted"]),
            models.Index(fields=["sort_order"]),
            models.Index(fields=["category", "is_deleted", "sort_order"]),
        ]
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.category.name} → {self.name}"


class CampusHotspot(BaseModel):
    name = models.CharField(
        max_length=150,
        help_text="Name of the hotspot (e.g., 'Student Union', 'Library')."
    )
    slug = models.SlugField(
        max_length=100,
        null=True,
        unique=True,
        help_text="URL‑friendly version of the name."
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Brief description of the hotspot."
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)."
    )

    class Meta:
        verbose_name = "Campus Hotspot"
        verbose_name_plural = "Campus Hotspots"
        indexes = [
            models.Index(fields=['is_deleted']),
            models.Index(fields=['sort_order']),
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_deleted', 'sort_order']),
        ]
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.name}"


class Listing(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="listings",
        help_text="The user who created this listing."
    )
    listing_type = models.CharField(
        max_length=30,
        choices=ListingTypeEnum.choices(),
        help_text="Type of listing (sell, wanted, service, accommodation)."
    )
    title = models.CharField(
        max_length=200,
        help_text="Short, descriptive title of the listing."
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the item, service, or accommodation."
    )
    image = models.ImageField(
        upload_to=listing_upload_path,
        blank=True,
        null=True,
        help_text="Primary image for the listing."
    )
    status = models.CharField(
        max_length=10,
        choices=ListingStatusTypeEnum.choices(),
        default=ListingStatusTypeEnum.PENDING.value,
        help_text="Current status (pending, active, sold, expired, etc.)."
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this listing will automatically expire."
    )
    hotspots = models.ManyToManyField(
        CampusHotspot,
        through="ListingHotspot",
        related_name="listings",
        help_text="Campus hotspots where this listing is relevant."
    )
    is_hot_sales = models.BooleanField(
        default=False,
        help_text="Whether this listing is promoted as 'Hot Sales'."
    )
    is_hot_sales_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiry date for hot sales promotion."
    )
    is_ads_banner = models.BooleanField(
        default=False,
        help_text="Whether this listing appears as a banner ad."
    )
    is_ads_banner_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiry date for banner ad promotion."
    )
    auto_reactivate = models.BooleanField(
        default=False,
        help_text="Whether to automatically reactivate the listing after expiry."
    )

    class Meta:
        verbose_name = "Listing"
        verbose_name_plural = "Listings"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['user', 'is_deleted']),
            models.Index(fields=['status']),
            models.Index(fields=['status', 'is_deleted']),
            models.Index(fields=['listing_type']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
            models.Index(
                fields=['status', 'is_deleted', 'expires_at'],
                name='listing_expire_idx'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()

    def save(self, *args, **kwargs):
        if self.expires_at is None:
            self.expires_at = datetime.datetime.now() + datetime.timedelta(days=30)

        if self.is_hot_sales and self.is_hot_sales_expires_at is None:
            self.is_hot_sales_expires_at = datetime.datetime.now() + datetime.timedelta(days=30)
        elif not self.is_hot_sales:
            self.is_hot_sales_expires_at = None

        if self.is_ads_banner and self.is_ads_banner_expires_at is None:
            self.is_ads_banner_expires_at = datetime.datetime.now() + datetime.timedelta(days=30)
        elif not self.is_ads_banner:
            self.is_ads_banner_expires_at = None
        super().save(*args, **kwargs)


class SellListing(BaseModel):
    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="sell_details",
        help_text="The base listing this sell detail belongs to."
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        related_name="sell_listings",
        help_text="Category of the product for sale."
    )
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.RESTRICT,
        related_name="sell_listings",
        null=True,
        blank=True,
        help_text="Optional subcategory for finer classification."
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Selling price in Nigerian Naira (₦)."
    )
    negotiation = models.BooleanField(
        default=False,
        help_text="Whether the price is negotiable."
    )
    condition = models.CharField(
        max_length=50,
        choices=ListingConditionEnum.choices(),
        blank=True,
        null=True,
        help_text="Physical condition (e.g., 'New', 'Used - Like New', 'Fair')."
    )
    brand = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Brand of the product (e.g., Apple, Samsung)."
    )
    model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Model name/number (e.g., iPhone 13, Galaxy S21)."
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Number of items available for sale."
    )
    warranty = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Warranty information (e.g., '6 months', '1 year')."
    )

    class Meta:
        verbose_name = "Sell Listing Detail"
        verbose_name_plural = "Sell Listing Details"
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['price']),
            models.Index(fields=['negotiation']),
            models.Index(fields=['condition']),
            models.Index(fields=['brand']),
            models.Index(fields=['model']),
            models.Index(fields=['category', 'price']),
            models.Index(fields=['brand', 'model']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gt=0),
                name="sell_price_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="sell_quantity_positive"
            ),
        ]

    def __str__(self):
        return f"Sell details for listing: {self.listing.title}"


class ServiceListing(BaseModel):
    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="service_details",
        help_text="The base listing this service detail belongs to."
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        related_name="service_listings",
        help_text="Category of the service."
    )
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.RESTRICT,
        related_name="service_listings",
        null=True,
        blank=True,
        help_text="Optional subcategory for the service."
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Service price (optional – can be 'negotiable' or 'free')."
    )
    negotiation = models.BooleanField(
        default=False,
        help_text="Whether the price is negotiable."
    )
    delivery_time = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Estimated delivery or completion time (e.g., '2 days', '1 week')."
    )
    service_duration = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="How long the service lasts (e.g., '1 hour', '3 months')."
    )
    experience = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Years of experience of the service provider."
    )
    portfolio = models.URLField(
        blank=True,
        null=True,
        help_text="Link to a portfolio or previous work examples."
    )
    online_available = models.BooleanField(
        default=False,
        help_text="Whether the service can be delivered online."
    )

    class Meta:
        verbose_name = "Service Listing Detail"
        verbose_name_plural = "Service Listing Details"
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['subcategory']),
            models.Index(fields=['price']),
            models.Index(fields=['negotiation']),
            models.Index(fields=['delivery_time']),
            models.Index(fields=['online_available']),
            models.Index(fields=['category', 'price']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0) | models.Q(price__isnull=True),
                name="service_price_non_negative_or_null"
            ),
        ]

    def __str__(self):
        return f"Service details for listing: {self.listing.title}"


class AccommodationListing(BaseModel):
    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="accommodation_details",
        help_text="The base listing this accommodation detail belongs to."
    )

    purpose = models.CharField(
        max_length=20,
        choices=PurposeChoicesEnum.choices(),
        default=PurposeChoicesEnum.RENT_ENTIRE.value,
        help_text="Type of accommodation listing (entire unit, room, or roommate wanted)."
    )
    property_type = models.CharField(
        max_length=50,
        help_text="Type of property (e.g., Apartment, Hostel, House)."
    )
    bedrooms = models.PositiveIntegerField(
        default=1,
        help_text="Number of bedrooms."
    )
    bathrooms = models.PositiveIntegerField(
        default=1,
        help_text="Number of bathrooms."
    )
    furnished = models.BooleanField(
        default=False,
        help_text="Whether the property is furnished."
    )
    rent_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monthly rent in Nigerian Naira (₦)."
    )
    available_from = models.DateField(
        null=True,
        blank=True,
        help_text="Date from which the property is available."
    )
    lease_duration = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Lease duration (e.g., '6 months', '1 year')."
    )
    electricity = models.BooleanField(
        default=False,
        help_text="Whether electricity is included/available."
    )
    water = models.BooleanField(
        default=False,
        help_text="Whether water supply is available."
    )
    security = models.BooleanField(
        default=False,
        help_text="Whether security is provided."
    )
    parking = models.BooleanField(
        default=False,
        help_text="Whether parking space is available."
    )
    distance_to_campus = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Distance to campus (e.g., '2km', '5 minutes walk')."
    )
    preferred_gender = models.CharField(
        max_length=10,
        choices=PreferredGenderEnum.choices(),
        blank=True,
        null=True,
        help_text="Preferred gender of the roommate(s)."
    )
    preferred_student_type = models.CharField(
        max_length=10,
        choices=PreferredStudentEnum.choices(),
        blank=True,
        null=True,
        help_text="Preferred type of student (undergrad, graduate, or any)."
    )
    max_occupants = models.PositiveIntegerField(
        default=1,
        help_text="Total number of people the room/unit can accommodate."
    )
    roommate_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes for potential roommates (e.g., habits, preferences)."
    )

    class Meta:
        verbose_name = "Accommodation Listing Detail"
        verbose_name_plural = "Accommodation Listing Details"
        indexes = [
            models.Index(fields=['purpose']),
            models.Index(fields=['property_type']),
            models.Index(fields=['rent_price']),
            models.Index(fields=['bedrooms']),
            models.Index(fields=['furnished']),
            models.Index(fields=['available_from']),
            models.Index(fields=['distance_to_campus']),
            models.Index(fields=['preferred_gender']),
            models.Index(fields=['preferred_student_type']),
            models.Index(fields=['purpose', 'rent_price']),
            models.Index(fields=['property_type', 'furnished']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rent_price__gt=0),
                name="accommodation_rent_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(bedrooms__gte=1),
                name="accommodation_bedrooms_min"
            ),
            models.CheckConstraint(
                condition=models.Q(bathrooms__gte=1),
                name="accommodation_bathrooms_min"
            ),
            models.CheckConstraint(
                condition=models.Q(max_occupants__gte=1),
                name="accommodation_max_occupants_min"
            ),
        ]

    def __str__(self):
        return f"Accommodation details for listing: {self.listing.title}"


class Favourite(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favourites',
        help_text="The user who favourited the listing."
    )
    listing = models.ForeignKey(
        'Listing',
        on_delete=models.CASCADE,
        related_name='favourited_by',
        help_text="The listing that was favourited."
    )

    class Meta:
        verbose_name = "Favourite"
        verbose_name_plural = "Favourites"
        unique_together = ('user', 'listing')
        indexes = [
            models.Index(fields=['user', 'listing']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} ❤️ {self.listing}"


class ListingHotspot(BaseModel):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        help_text="The listing associated with this hotspot."
    )
    hotspot = models.ForeignKey(
        CampusHotspot,
        on_delete=models.CASCADE,
        help_text="The hotspot associated with this listing."
    )

    class Meta:
        verbose_name = "Listing Hotspot"
        verbose_name_plural = "Listing Hotspots"
        unique_together = [['listing', 'hotspot']]
        indexes = [
            models.Index(fields=['listing']),
            models.Index(fields=['hotspot']),
        ]

    def __str__(self):
        return f"{self.listing.title} @ {self.hotspot.name}"


class Review(BaseModel):
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_given',
        help_text="The user who wrote the review."
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_received',
        help_text="The user who received the review."
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        help_text="The listing being reviewed (optional)."
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars."
    )
    comment = models.TextField(
        blank=True,
        null=True,
        help_text="Optional textual feedback."
    )

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
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
    item_name = models.CharField(
        max_length=200,
        help_text="Name of the lost/found item."
    )
    description = models.TextField(
        help_text="Detailed description of the item."
    )
    location = models.CharField(
        max_length=500,
        help_text="Where the item was lost or found."
    )
    date_found = models.DateField(
        help_text="Date the item was found."
    )
    status = models.CharField(
        max_length=20,
        choices=LostAndFoundStatusEnum.choices(),
        default=LostAndFoundStatusEnum.PENDING.value,
        db_index=True,
        help_text="Current status (pending, claimed, resolved)."
    )
    verification1 = models.CharField(
        max_length=500,
        help_text="First verification question (to prove ownership)."
    )
    answer1 = models.CharField(
        null=True,
        blank=True,
        max_length=500,
        help_text="Correct answer to the first verification question."
    )
    verification2 = models.CharField(
        max_length=500,
        help_text="Second verification question."
    )
    answer2 = models.CharField(
        null=True,
        blank=True,
        max_length=500,
        help_text="Correct answer to the second verification question."
    )
    full_name = models.CharField(
        max_length=200,
        help_text="Full name of the person who found the item."
    )
    email = models.EmailField(
        max_length=200,
        help_text="Email address of the finder."
    )
    claimed_by = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Name of the person who claimed the item."
    )
    phone_regex = RegexValidator(
        regex=r'^(?:\+234|0)[789][01]\d{8}$',
        message="Phone number must be a valid Nigerian number (e.g., 08012345678 or +2348012345678)."
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=15,
        blank=True,
        null=True,
        help_text="Contact phone number of the finder."
    )
    department = models.CharField(
        max_length=200,
        help_text="Academic department of the finder."
    )
    image = models.ImageField(
        upload_to=lost_and_found_upload_path,
        blank=True,
        null=True,
        help_text="Optional image of the item."
    )

    class Meta:
        verbose_name = "Lost & Found Item"
        verbose_name_plural = "Lost & Found Items"
        indexes = [
            models.Index(fields=['date_found', 'status']),
            models.Index(fields=['email', 'status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item_name} ({self.location})"


class Claim(BaseModel):
    lost_item = models.ForeignKey(
        LostAndFound,
        on_delete=models.CASCADE,
        related_name="item_lost",
        help_text="The lost item being claimed."
    )
    answer1 = models.CharField(
        max_length=500,
        help_text="Answer to the first verification question."
    )
    answer2 = models.CharField(
        max_length=500,
        help_text="Answer to the second verification question."
    )
    full_name = models.CharField(
        max_length=200,
        help_text="Full name of the person claiming the item."
    )
    email = models.EmailField(
        max_length=200,
        help_text="Email address of the claimant."
    )
    phone_regex = RegexValidator(
        regex=r'^(?:\+234|0)[789][01]\d{8}$',
        message="Phone number must be a valid Nigerian number (e.g., 08012345678 or +2348012345678)."
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=15,
        blank=True,
        null=True,
        help_text="Contact phone number of the claimant."
    )

    class Meta:
        verbose_name = "Claim"
        verbose_name_plural = "Claims"
        indexes = [
            models.Index(fields=['lost_item']),
            models.Index(fields=['email']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Claim on {self.lost_item.item_name} by {self.full_name}"