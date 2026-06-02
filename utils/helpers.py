import re

from apps.users.models import Badge, Point
from utils.enums import BadgeChoiceEnum

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
            return Badge.objects.filter(id=badge).first()
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
        point_obj, _ = Point.objects.get_or_create(user=user)

        if action == 'add':
            point_obj.amount += points

        elif action == 'subtract':
            point_obj.amount = max(point_obj.amount - points, 0)

        else:
            raise ValueError("Action must be 'add' or 'subtract'")

        point_obj.save(update_fields=['amount'])
        return point_obj.amount

    @staticmethod
    def check_points(user) -> int:
        point_obj, _ = Point.objects.get_or_create(user=user)
        return point_obj.amount