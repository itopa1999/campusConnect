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
# Create your models here.


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
    # meeting_point_description = models.TextField(
    #     blank=True,
    #     null=True,
    #     help_text="Describe your preferred meeting location/area for product handover",
    #     max_length=500
    # )
    email_verified = models.BooleanField(
        default=False,
        help_text="Email verification status"
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
    

