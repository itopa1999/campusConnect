from django.db import models

from utils.base_model import BaseModel
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, RegexValidator
from datetime import timedelta
import random
from apps.users.manager import UserManager, SoftDeleteManager
from utils.base_model import BaseModel
from utils.enums import PointPurchaseStatusEnum, PointTransactionTypeEnum, TokenType
import secrets
from utils.enums import IssueTypeEnum
# Create your models here.

class Badge(models.Model):
    name = models.CharField(max_length=50)
    icon = models.ImageField(upload_to='badges/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class User(BaseModel, AbstractUser):
    username = None
    email = models.EmailField(max_length=40, unique=True, db_index=True)
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
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        help_text="Upload a profile picture that will appear on all your product listings"
    )
    points = models.PositiveIntegerField(validators=[MinValueValidator(0)],null=True, default=0)
    matric_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    student_id_photo = models.ImageField(upload_to='student_ids/', null =True, blank=True)
    student_id_verified = models.BooleanField(default=False)
    department = models.CharField(max_length=100, blank=True, null=True)
    faculty = models.CharField(max_length=100, blank=True, null=True)
    level = models.PositiveIntegerField(blank=True, null=True)
    average_rating = models.DecimalField(max_digits=2, decimal_places=1, default=0.00)
    email_verified = models.BooleanField(
        default=False,
        help_text="Email verification status"
    )
    hall_verified = models.BooleanField(default=False, help_text="Student hall/residence verified")
    user_badges = models.ManyToManyField(
        Badge,
        blank=True,
        related_name="users_with_badge"
    )
    def save(self, *args, **kwargs):
        self.first_name = self.first_name.capitalize()
        self.last_name = self.last_name.capitalize()
                    
        super().save(*args, **kwargs)  


    def get_full_name(self):
        return super().get_full_name()  

    objects=UserManager( )
    USERNAME_FIELD ='email'
    REQUIRED_FIELDS=['first_name',"last_name"]

    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['-id']),
            models.Index(fields=['email']),
            models.Index(fields=['email', 'is_deleted']),
            models.Index(fields=['phone']),
            models.Index(fields=['phone', 'is_deleted']),
            models.Index(fields=['matric_number']),
            models.Index(fields=['student_id_verified']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['level']),
            models.Index(fields=['department']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['is_active', 'is_deleted']),
            models.Index(fields=['email_verified', 'is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.email}"

def token_expiry():
    return timezone.now() + timedelta(minutes=10)

class VerificationToken(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.PositiveIntegerField(unique=True)
    token_type = models.CharField(max_length=50, choices=TokenType.choices())
    is_used = models.BooleanField(default=False, db_index=True)
    expires_at = models.DateTimeField(default=token_expiry)
    
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'token_type']),
            models.Index(fields=['token', 'is_deleted']),
            models.Index(fields=['token_type', 'is_used', 'is_deleted']),
            models.Index(fields=['expires_at']),
        ] 
    
    def __str__(self):
        return f"{self.user.email} - {self.token_type}"
    
    def is_valid(self):
        return (
            not self.is_used and
            self.expires_at > timezone.now()
        )

    @staticmethod
    def generate_token():
        return random.randint(100000, 999999)
    

class ContactReport(BaseModel):

    # Basic info
    reporter_name = models.CharField(max_length=255, help_text="Full name of the person reporting")
    reporter_email = models.EmailField(help_text="UI email address")

    # Issue categorization
    issue_type = models.CharField(max_length=30, choices=IssueTypeEnum.choices(), db_index=True)

    # Fields specific to certain issue types (optional)
    listing_identifier = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Listing URL or title (for report_listing)"
    )
    reported_user_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email of the user being reported (for report_user)"
    )

    # Main message
    message = models.TextField(help_text="Detailed description of the issue")

    # Metadata
    is_reviewed = models.BooleanField(default=False, help_text="Admin has reviewed this report")
    admin_notes = models.TextField(blank=True, help_text="Internal notes from admin")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Contact / Report"
        verbose_name_plural = "Contact / Reports"

    def __str__(self):
        return f"{self.get_issue_type_display()} - {self.reporter_name} ({self.created_at.date()})"
    

class PointPackage(BaseModel):
    """
    Predefined point bundles that users can purchase.
    Examples: 5 points for ₦2,500, 12 points for ₦5,000, etc.
    """
    points = models.PositiveIntegerField(
        help_text="Number of points included in this package"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price in Nigerian Naira (₦)"
    )
    description = models.CharField(
        max_length=100,
        blank=True,
        help_text="Short description (e.g., 'Best value', 'Power seller')"
    )
    is_popular = models.BooleanField(
        default=False,
        help_text="Highlight this package as '🔥 Popular'"
    )
    is_best_value = models.BooleanField(
        default=False,
        help_text="Mark as best value for money"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which packages are displayed (lower first)"
    )

    class Meta:
        ordering = ['sort_order', 'points']
        verbose_name = "Point Package"
        verbose_name_plural = "Point Packages"

    def __str__(self):
        return f"{self.points} points – ₦{self.price}"

    @property
    def price_per_point(self):
        """Calculate price per point (for display)."""
        if self.points:
            return self.price / self.points
        return 0

    @property
    def savings_percentage(self):
        """
        Calculate savings compared to the base package (smallest points).
        Assumes base is the lowest points package.
        """
        base_package = PointPackage.objects.order_by('points').first()
        if base_package and base_package.points > 0:
            base_per_point = base_package.price / base_package.points
            current_per_point = self.price / self.points
            if base_per_point > 0:
                return round((1 - (current_per_point / base_per_point)) * 100)
        return 0


class PointPurchase(BaseModel):
    """
    Tracks a user's purchase of a point package.
    When a purchase is successful, the user's Point balance is increased.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='point_purchases'
    )
    package = models.ForeignKey(
        PointPackage,
        on_delete=models.PROTECT,
        related_name='purchases'
    )
    points_awarded = models.PositiveIntegerField(
        help_text="Number of points added to the user's balance"
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount paid in Naira"
    )
    payment_reference = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="Reference from payment gateway"
    )
    status = models.CharField(
        max_length=20,
        choices= PointPurchaseStatusEnum.choices(),
        default='pending',
        db_index=True
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the purchase was successfully completed"
    )

    gateway = models.CharField(
        blank=True,
        max_length=200,
        null=True,
        help_text="payment_gateway"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Point Purchase"
        verbose_name_plural = "Point Purchases"

    def __str__(self):
        return f"{self.user.email} bought {self.points_awarded} points (₦{self.amount_paid})"
    

class PointTransaction(BaseModel):
    """
    Tracks every point addition or subtraction for a user.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='point_transactions'
    )
    amount = models.IntegerField(
        help_text="Positive for addition, negative for subtraction."
    )
    balance_after = models.PositiveIntegerField(
        help_text="The user's point balance after this transaction."
    )
    transaction_type = models.CharField(
        max_length=30,
        choices=PointTransactionTypeEnum.choices(),
        default='other',
        db_index=True
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional description of the transaction."
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional reference ID (e.g., listing_id, purchase_id)."
    )
    purchase = models.ForeignKey(
        'PointPurchase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        help_text="Link to the purchase if this transaction was from a purchase."
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Point Transaction"
        verbose_name_plural = "Point Transactions"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['user', 'transaction_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f"{self.user.email}: {sign}{self.amount} points ({self.transaction_type})"
    

class FeatureFlag(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    users = models.ManyToManyField(User,
        blank=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name', 'is_active', 'is_deleted']),
        ]

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"
