TODO: 

------TEST---------
1. write test for get_dashboard_listing and upcoming_expiring_listing, and dashboard_review
2. write test for lost_and_found for moderator buh commands and queries
3. transaction and purchases for user
4. get student_id record user test
5. additional endpoint created profile
----------------------------------

add campus delivery, accommodation listings, student jobs, tutor matching,
add refeerall add help center



Seconds	Time
60	1 minute
300	5 minutes
600	10 minutes
1800	30 minutes
3600	1 hour
7200	2 hours
21600	6 hours
43200	12 hours
86400	24 hours



<!-- Todo -->

Strong additions
Type	Purpose	Example
RENT	Temporarily rent something	"Rent my projector for ₦3,000/day"
EXCHANGE	Swap items instead of selling	"Swap my iPhone 11 for iPhone 12"
ROOMMATE	Looking for / offering a roommate	"Looking for a roommate at Bodija"
ACCOMMODATION	Hostel/room/apartment availability	"Self-contained room available"
JOB	Part-time/student employment	"Part-time graphic designer needed"
EVENT	Promote a campus event	"Tech Meetup — Saturday"
LOST_FOUND	Report a lost or found item	"Found a student ID card"
DONATION	Give something away specifically as a donation	"Donating old clothes"



class Listing(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="listings",
    )

    listing_type = models.CharField(
        max_length=30,
        choices=ListingTypeEnum.choices(),
    )

    title = models.CharField(max_length=200)

    description = models.TextField(
        blank=True,
        null=True,
    )

    image = models.ImageField(
        upload_to=listing_upload_path,
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=10,
        choices=ListingStatusTypeEnum.choices(),
        default=ListingStatusTypeEnum.PENDING.value,
    )

    badge = models.CharField(
        max_length=50,
        choices=BadgeListingTypeEnum.choices(),
        blank=True,
        null=True,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    hotspots = models.ManyToManyField(
        CampusHotspot,
        through="ListingHotspot",
        related_name="listings",
    )

    is_hot_sales = models.BooleanField(default=False)
    is_hot_sales_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_ads_banner = models.BooleanField(default=False)
    is_ads_banner_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    auto_reactivate = models.BooleanField(default=False)

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
    )

    category = models.ForeignKey(
            Category,
            on_delete=models.RESTRICT,
            related_name="sell_listings",
        )
    
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.RESTRICT,
        related_name="sell_listings",
        null=True,
        blank=True,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    negotiation = models.BooleanField(
        default=False,
    )

    condition = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

# brand
# model
# quantity
# condition
# warranty
# purchase_date


class WantedListing(BaseModel):
    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="wanted_details",
    )

    max_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    condition_preference = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

# preferred_brand
# preferred_model
# needed_by
# requirements


class ServiceListing(BaseModel):
    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="service_details",
    )

    category = models.ForeignKey(
            Category,
            on_delete=models.RESTRICT,
            related_name="service_listings",
        )
    
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.RESTRICT,
        related_name="service_listings",
        null=True,
        blank=True,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    negotiation = models.BooleanField(
        default=False,
    )

    delivery_time = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )


# service_duration
# experience
# portfolio
# online_available


class AccommodationListing(BaseModel):
    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="accommodation_details",
    )

    rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    property_type = models.CharField(
        max_length=50,
    )

    bedrooms = models.PositiveIntegerField(
        default=1,
    )

    available_from = models.DateField(
        null=True,
        blank=True,
    )

    furnished = models.BooleanField(
        default=False,
    )


# bathrooms
# electricity
# water
# security
# parking
# distance_to_campus
# lease_duration


class JobListing(BaseModel):
    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="job_details",
    )

    employment_type = models.CharField(
        max_length=50,
    )

    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    application_deadline = models.DateField(
        null=True,
        blank=True,
    )

    requirements = models.TextField(
        blank=True,
        null=True,
    )

# working_hours
# experience_required
# remote
# company
# application_url




check if timezone timeldetal which one is good pass to use for nigeria
check the email template to have standard for all others