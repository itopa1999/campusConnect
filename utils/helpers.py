import re

from apps.users.models import Badge
from utils.enums import BadgeChoiceEnum
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

def validate_ui_email(email: str) -> tuple[bool, str]:
  
    allowed_domains = ('@ui.edu.ng', '@stu.ui.edu.ng')
    
    if not email:
        return False, "Email address is required."
    
    if email.lower().endswith(allowed_domains):
        return True, ""
    else:
        return False, "Please use a valid @ui.edu.ng or @stu.ui.edu.ng email address."


def is_email_verified(user) -> bool:
    return user.email_verified

def is_fully_verified(user) -> bool:
    return (
        user.email_verified and 
        user.student_id_verified and 
        user.hall_verified
    )


def normalize_nigerian_phone(phone: str) -> str | None:
    """
    Convert any valid Nigerian phone number to the local 11-digit format starting with 0.
    Returns normalized string or None if invalid.
    
    Examples:
        +2348064160380 -> 08064160380
        08064160380    -> 08064160380
        2348064160380  -> 08064160380
        8064160380     -> 08064160380
        07012345678    -> 07012345678
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) == 11 and digits.startswith('0'):
        # Already local format
        return digits
    elif len(digits) == 13 and digits.startswith('234'):
        # Convert +234... to 0...
        return '0' + digits[3:]
    elif len(digits) == 10 and digits[0] != '0':
        # Assume missing leading zero, e.g., 8064160380
        return '0' + digits
    else:
        return None
    

class BadgeService:

    @staticmethod
    def _get_badge_instance(badge):
        if isinstance(badge, Badge):
            return badge
        if isinstance(badge, int):
            # Use get instead of filter().first() - more efficient
            try:
                return Badge.objects.get(id=badge)
            except Badge.DoesNotExist:
                return None
        if isinstance(badge, str):
            badge_obj, _ = Badge.objects.get_or_create(
                name=badge,
                defaults={"description": ""}
            )
            return badge_obj
        return None

    @staticmethod
    def _resolve_badges(badges):
        if badges is None:
            return []
        if isinstance(badges, (Badge, int, str)):
            badges = [badges]

        resolved = []
        for badge in badges:
            badge_instance = BadgeService._get_badge_instance(badge)
            if badge_instance is None:
                raise ValueError(f"Badge could not be resolved: {badge}")
            resolved.append(badge_instance)
        return resolved

    @staticmethod
    def add(user, badge):
        resolved = BadgeService._resolve_badges(badge)
        user.user_badges.add(*resolved)

    @staticmethod
    def remove(user, badge):
        resolved = BadgeService._resolve_badges(badge)
        user.user_badges.remove(*resolved)

    @staticmethod
    def clear(user):
        user.user_badges.clear()

    @staticmethod
    def set(user, badges):
        resolved = BadgeService._resolve_badges(badges)
        user.user_badges.set(resolved)


class UpdatePointsService:
    @staticmethod
    def update_points(user, points: int, action: str):
        """Update user points with atomic transaction for data consistency"""
        from django.db import transaction
        
        with transaction.atomic():

            if action == 'add':
                user.points += points

            elif action == 'subtract':
                user.points = max(user.points - points, 0)

            else:
                raise ValueError("Action must be 'add' or 'subtract'")

            user.save(update_fields=['points'])
        return user.points

    @staticmethod
    def check_points(user) -> int:
        """Get user points without modification"""
        return user.points
    

def convert_to_webp(instance, field_name, quality=30):
    """Convert an ImageField to WebP if not already WebP."""
    field = getattr(instance, field_name)
    if not field or not field.name:
        return False
    if field.name.lower().endswith('.webp'):
        return False
    try:
        from PIL import Image
        from io import BytesIO
        from django.core.files.base import ContentFile
        img = Image.open(field.path)
        output = BytesIO()
        img.save(output, format='WEBP', quality=quality, optimize=True)
        output.seek(0)
        base_name = field.name.rsplit('.', 1)[0]
        new_name = f"{base_name}.webp"
        new_file = ContentFile(output.read(), name=new_name)
        # Delete old file
        field.storage.delete(field.name)
        setattr(instance, field_name, new_file)
        return True
    except Exception as e:
        print(f"Error converting {field_name}: {e}")
        return False