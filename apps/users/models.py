from django.db import models

from utils.base_model import BaseModel
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, RegexValidator
from datetime import timedelta
import random
from apps.users.manager import UserManager
from utils.enums import NotificationEnum, PointPurchaseStatusEnum, PointTransactionTypeEnum, ReportStatusEnum, TokenTypeEnum, TwoFactorMethodEnum, UserIdVerificationEnum
from utils.enums import IssueTypeEnum
# Create your models here.
import os
import uuid


def profile_picture_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    unique = uuid.uuid4().hex[:10]

    return f"profile_pictures/profile_picture_{instance.id}_{unique}{ext}"


def student_id_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    unique = uuid.uuid4().hex[:10]

    return f"student_ids/student_ids_{instance.id}_{unique}{ext}"



class Badge(BaseModel):
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Name of the badge (e.g., 'Top Seller', 'Verified Student')."
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Optional icon class (e.g., FontAwesome icon name)."
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of what the badge represents."
    )

    class Meta:
        verbose_name = "Badge"
        verbose_name_plural = "Badges"

    def __str__(self):
        return self.name


class User(BaseModel, AbstractUser):
    username = None
    email = models.EmailField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text="User's primary email address (used for login)."
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
        unique=True,
        help_text="Nigerian phone number (e.g., 08012345678 or +2348012345678)."
    )
    profile_picture = models.ImageField(
        upload_to=profile_picture_upload_path,
        blank=True,
        null=True,
        help_text="Upload a profile picture that will appear on all your product listings."
    )
    points = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        null=True,
        default=0,
        help_text="Current point balance (used for promoting listings, etc.)."
    )
    matric_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Student matriculation number (if applicable)."
    )

    student_id_photo = models.ImageField(
        upload_to=student_id_upload_path,
        null=True,
        blank=True,
        help_text="Photo of student ID for verification purposes."
    )
    student_id_verified = models.BooleanField(
        default=False,
        help_text="Whether the student ID has been verified."
    )
    student_id_verified_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=UserIdVerificationEnum.choices(),
        help_text="Verification status of the student ID (pending, approved, rejected)."
    )
    
    department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Academic department of the student."
    )
    faculty = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Faculty to which the department belongs."
    )
    level = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Year of study (e.g., 100, 200, 300, 400)."
    )
    average_rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        default=0.00,
        help_text="Average rating received from other users (0.0 to 5.0)."
    )
    sold_items = models.PositiveIntegerField(
        blank=True,
        null=True,
        default=0,
        help_text="Total number of items sold by this user."
    )
    email_verified = models.BooleanField(
        default=False,
        help_text="Email verification status (True if verified)."
    )

    hall_residence = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name of the student hall of residence."
    )
    hall_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Room/hall number or block."
    )
    hall_verified = models.BooleanField(
        default=False,
        help_text="Whether the student hall/residence has been verified."
    )
    hall_verified_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=UserIdVerificationEnum.choices(),
        help_text="Verification status of hall/residence (pending, approved, rejected)."
    )

    user_badges = models.ManyToManyField(
        Badge,
        blank=True,
        related_name="users_with_badge",
        help_text="Badges earned by the user (e.g., for trust, activity, achievements)."
    )

    notification = models.BooleanField(
        default=True,
        help_text="Whether the user wants to receive notifications."
    )
    visibility = models.BooleanField(
        default=True,
        help_text="Whether the user's profile is visible to others."
    )

    two_factor_enabled = models.BooleanField(
        default=False,
        help_text="Whether two‑factor authentication is enabled for this user."
    )

    def save(self, *args, **kwargs):
        self.first_name = self.first_name.title()
        self.last_name = self.last_name.title()
                    
        super().save(*args, **kwargs)  


    def get_full_name(self):
        return super().get_full_name()  

    objects=UserManager()
    USERNAME_FIELD ='email'
    REQUIRED_FIELDS=['first_name',"last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
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
        constraints = [
            models.CheckConstraint(
                condition=models.Q(average_rating__gte=0) & models.Q(average_rating__lte=5),
                name="user_rating_range",
            ),
            models.CheckConstraint(
                condition=models.Q(points__gte=0),
                name="user_points_non_negative"
            ),
        ]
    
    def __str__(self):
        return f"{self.email}"

def token_expiry():
    return timezone.now() + timedelta(minutes=10)

class VerificationToken(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='verification_tokens',
        help_text="The user for whom this token is generated."
    )
    token = models.PositiveIntegerField(
        unique=True,
        help_text="Six‑digit verification code."
    )
    token_type = models.CharField(
        max_length=50,
        choices=TokenTypeEnum.choices(),
        help_text="Purpose of token (e.g., email_verification, password_reset)."
    )
    is_used = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the token has already been consumed."
    )
    expires_at = models.DateTimeField(
        default=token_expiry,
        help_text="Timestamp when the token expires."
    )
    
    
    class Meta:
        verbose_name = "Verification Token"
        verbose_name_plural = "Verification Tokens"
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



class TwoFactorMethod(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='two_factor_methods',
        help_text="The user who enabled this 2FA method."
    )
    method = models.CharField(
        max_length=20,
        choices=TwoFactorMethodEnum.choices(),
        help_text="2FA method (e.g., authenticator_app, sms, email)."
    )
    is_enabled = models.BooleanField(
        default=False,
        help_text="Whether this method is currently active."
    )
    secret = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text="Secret key or TOTP seed (if applicable)."
    )

    class Meta:
        verbose_name = "Two‑Factor Method"
        verbose_name_plural = "Two‑Factor Methods"
        unique_together = ('user', 'method')

    def __str__(self):
        return f"{self.user.email} - {self.method}"



class BackupCode(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='backup_codes',
        help_text="The user who owns these backup codes."
    )
    code_hash = models.CharField(
        max_length=128,
        help_text="Hashed backup code (for security, never store plaintext)."
    )
    is_used = models.BooleanField(
        default=False,
        help_text="Whether this backup code has been used."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the backup code was generated."
    )

    class Meta:
        verbose_name = "Backup Code"
        verbose_name_plural = "Backup Codes"

    def __str__(self):
        return f"Backup code for {self.user.email}"
        

class ContactReport(BaseModel):

    # Basic info
    reporter_name = models.CharField(
        max_length=255,
        help_text="Full name of the person reporting."
    )
    reporter_email = models.EmailField(
        help_text="Email address of the person reporting."
    )

    # Issue categorization
    issue_type = models.CharField(
        max_length=30,
        choices=IssueTypeEnum.choices(),
        db_index=True,
        help_text="Category of the issue (e.g., report_listing, report_user, general_inquiry)."
    )

    # Fields specific to certain issue types (optional)
    listing_identifier = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Listing URL or title (for report_listing)."
    )
    reported_user_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email of the user being reported (for report_user)."
    )

    # Main message
    message = models.TextField(
        help_text="Detailed description of the issue."
    )

    # Metadata
    is_reviewed = models.BooleanField(
        default=False,
        help_text="Admin has reviewed this report."
    )
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes from admin."
    )

    status = models.CharField(
        max_length=20,
        choices=ReportStatusEnum.choices(),
        default=ReportStatusEnum.PENDING.value,
        help_text="Current status of the report (pending, in_progress, resolved, closed)."
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_reports',
        help_text="Moderator assigned to handle this report."
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports',
        help_text="Moderator who resolved this report."
    )
    resolved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when the report was resolved."
    )
    resolution_notes = models.TextField(
        blank=True,
        help_text="Details of the resolution (e.g., action taken)."
    )
    escalated_to_admin = models.BooleanField(
        default=False,
        help_text="Whether this report was escalated to a higher admin level."
    )
    escalated_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of escalation."
    )
    escalated_note = models.TextField(
        blank=True,
        help_text="Reason for escalation."
    )
    escalated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escalated_reports',
        help_text="Admin who escalated this report."
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Contact / Report"
        verbose_name_plural = "Contact / Reports"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['issue_type']),
            models.Index(fields=['reporter_email']),
        ]

    def __str__(self):
        return f"{self.get_issue_type_display()} - {self.reporter_name} ({self.created_at.date()})"
    

class PointPackage(BaseModel):
    """
    Predefined point bundles that users can purchase.
    Examples: 5 points for ₦2,500, 12 points for ₦5,000, etc.
    """
    points = models.PositiveIntegerField(
        help_text="Number of points included in this package."
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price in Nigerian Naira (₦)."
    )
    description = models.CharField(
        max_length=100,
        blank=True,
        help_text="Short description (e.g., 'Best value', 'Power seller')."
    )
    is_popular = models.BooleanField(
        default=False,
        help_text="Highlight this package as '🔥 Popular'."
    )
    is_best_value = models.BooleanField(
        default=False,
        help_text="Mark as best value for money."
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which packages are displayed (lower first)."
    )

    class Meta:
        ordering = ['sort_order', 'points']
        verbose_name = "Point Package"
        verbose_name_plural = "Point Packages"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(points__gt=0),
                name="point_package_points_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(price__gt=0),
                name="point_package_price_positive"
            ),
        ]

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
        related_name='point_purchases',
        help_text="The user who made the purchase."
    )
    package = models.ForeignKey(
        PointPackage,
        on_delete=models.PROTECT,
        related_name='purchases',
        help_text="The point package that was bought."
    )
    points_awarded = models.PositiveIntegerField(
        help_text="Number of points added to the user's balance."
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount paid in Naira."
    )
    payment_reference = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="Reference from payment gateway (e.g., Paystack, Flutterwave)."
    )
    status = models.CharField(
        max_length=20,
        choices= PointPurchaseStatusEnum.choices(),
        default=PointPurchaseStatusEnum.PENDING.value,
        db_index=True,
        help_text="Purchase status (pending, completed, failed, refunded)."
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the purchase was successfully completed."
    )

    gateway = models.CharField(
        blank=True,
        max_length=200,
        null=True,
        help_text="Payment gateway used (e.g., paystack, flutterwave)."
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Point Purchase"
        verbose_name_plural = "Point Purchases"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['user', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(points_awarded__gt=0),
                name="point_purchase_awarded_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(amount_paid__gt=0),
                name="point_purchase_amount_positive"
            ),
        ]

    def __str__(self):
        return f"{self.user.email} bought {self.points_awarded} points (₦{self.amount_paid})"
    

class PointTransaction(BaseModel):
    """
    Tracks every point addition or subtraction for a user.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='point_transactions',
        help_text="The user whose balance is affected."
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
        default=PointTransactionTypeEnum.OTHER.value,
        db_index=True,
        help_text="Type of transaction (purchase, listing_promotion, refund, etc.)."
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
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(amount=0),
                name="point_transaction_nonzero_amount"
            ),
        ]

    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f"{self.user.email}: {sign}{self.amount} points ({self.transaction_type})"
    

class FeatureFlag(BaseModel):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Feature name (e.g., 'dark_mode', 'listing_promotion')."
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the feature."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the feature is globally active."
    )
    users = models.ManyToManyField(
        User,
        blank=True,
        help_text="Optional per‑user override (if empty, feature applies globally)."
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Feature Flag"
        verbose_name_plural = "Feature Flags"
        indexes = [
            models.Index(fields=['name', 'is_active', 'is_deleted']),
        ]

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"



class Notification(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notification_user",
        help_text="The user who receives this notification."
    )
    notification_type = models.CharField(
        max_length=255,
        choices=NotificationEnum.choices(),
        default=NotificationEnum.OTHERS.value,
        db_index=True,
        help_text="Category of notification (order, listing, promotion, etc.)."
    )
    title = models.CharField(
        max_length=255,
        help_text="Notification title/short summary."
    )
    message = models.TextField(
        help_text="Full notification message."
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Whether the notification has been read by the user."
    )
    action_url = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional URL to navigate to when the notification is clicked."
    )


    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['user', 'notification_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_read']),
        ]

    def __str__(self):
        return f"{self.user.first_name or self.user.email} title: {self.title}"