from django.db import models

from utils.base_model import BaseModel
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import RegexValidator
from datetime import timedelta
import random
from apps.users.manager import UserManager
from utils.base_model import BaseModel
from utils.enums import TokenType
import secrets
from utils.enums import IssueTypeEnum
# Create your models here.

# BADGE_CHOICES = (
#     ('none', 'None'),
#     ('trusted', 'Trusted User'),
#     ('verified', 'Verified User'),
#     ('top_seller', 'Top Seller'),
# )

class Badge(models.Model):
    name = models.CharField(max_length=50)
    icon = models.ImageField(upload_to='badges/')
    description = models.TextField()



class User(BaseModel, AbstractUser):
    username = None
    email = models.EmailField(max_length=40, unique=True)
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
    matric_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    student_id_photo = models.ImageField(upload_to='student_ids/', null =True, blank=True)
    student_id_verified = models.BooleanField(default=False)
    department = models.CharField(max_length=100, blank=True, null=True)
    faculty = models.CharField(max_length=100, blank=True, null=True)
    level = models.PositiveIntegerField(blank=True, null=True)
    average_rating = models.DecimalField(max_digits=2, decimal_places=1, default=0.00)
    transaction_count = models.PositiveIntegerField(default=0)
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

    objects=UserManager( )
    USERNAME_FIELD ='email'
    REQUIRED_FIELDS=['first_name',"last_name"]

    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['-id']),
            models.Index(fields=['email']),
            models.Index(fields=['matric_number']),
            models.Index(fields=['student_id_verified']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['level']),
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return f"{self.email}"


class VerificationToken(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.PositiveIntegerField(unique=True)
    token_type = models.CharField(max_length=50, choices=TokenType.choices())
    is_used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'token_type']),
        ] 
    
    def __str__(self):
        return f"{self.user.email} - {self.token_type}"
    
    def is_valid(self):
        return not self.is_used
    
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