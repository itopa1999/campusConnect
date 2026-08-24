import re
from django.db import transaction
from utils.cache_helper import GlobalCache
from utils.constant_helper import ConstantHelper
from utils.enums import CacheKeysEnum, PointTransactionTypeEnum
from django.utils import timezone
import asyncio

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
        from apps.users.models import Badge

        if isinstance(badge, Badge):
            return badge
        if isinstance(badge, int):
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
        from apps.users.models import Badge
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
    def update_points(user, points: int, action: str,
                      transaction_type: str = 'other',
                      description: str = '', reference: str = '', purchase=None):
        """
        Update user points and create a transaction record.

        Args:
            user: User instance.
            points: Number of points to add or subtract.
            action: 'add' or 'subtract'.
            transaction_type: String from PointTransactionTypeEnum (e.g., 'purchase').
            description: Optional description.
            reference: Optional reference ID.
            purchase: Optional PointPurchase instance.

        Returns:
            int: New points balance.
        """
        from apps.users.models import PointTransaction
        if action not in [ConstantHelper.POINT_ADDITION, ConstantHelper.POINT_SUBTRACTION]:
            raise ValueError(f"Action must be {ConstantHelper.POINT_SUBTRACTION} or {ConstantHelper.POINT_ADDITION}")

        # Validate transaction_type
        valid_types = PointTransactionTypeEnum.values()
        if transaction_type not in valid_types:
            raise ValueError(f"Invalid transaction_type. Must be one of: {valid_types}")

        with transaction.atomic():
            if action == ConstantHelper.POINT_ADDITION:
                new_balance = user.points + points
                amount = points
            else:  # subtract
                new_balance = max(user.points - points, 0)
                amount = -points

            # Update user balance
            user.points = new_balance
            user.save(update_fields=['points'])

            # Create transaction record
            PointTransaction.objects.create(
                user=user,
                amount=amount,
                balance_after=new_balance,
                transaction_type=transaction_type,
                description=description,
                reference=reference,
                purchase=purchase,
            )

        return user.points

    @staticmethod
    def check_points(user):
        cache_key = CacheKeysEnum.format(CacheKeysEnum.GET_POINTS_BALANCE, user_id=user.id)

        def build_check_point_data():
            points_balance = user.points or 0
            return points_balance
        data = GlobalCache.aget_or_set(
            key=cache_key,
            callback=build_check_point_data,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

        return data

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
    

def cloudinary_conversion_to_webp(instance, image, field_name):
    """
    Convert an uploaded image to a real WebP image.

    The image content is decoded and re-encoded using Pillow.
    The resulting WebP file is assigned back to the specified
    ImageField.

    Args:
        instance: Django model instance.
        image: The uploaded ImageField file.
        field_name: Name of the ImageField on the model.

    Returns:
        True  -> image was converted successfully
        False -> image was already WebP or conversion failed
    """

    try:
        from PIL import Image, ImageOps
        from io import BytesIO
        from django.core.files.base import ContentFile

        image.open("rb")

        with Image.open(image) as original:

            if original.format == "WEBP":
                return False

            img = ImageOps.exif_transpose(original)

            img.load()

            if "A" in img.getbands():
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            output = BytesIO()

            img.save(
                output,
                format="WEBP",
                quality=60,
                method=6,
                lossless=False,
            )

            webp_data = output.getvalue()

        if not webp_data:
            raise ValueError("WebP conversion produced an empty file.")

        converted_file = ContentFile(
            webp_data,
            name="converted.webp",
        )

        converted_file.seek(0)

        setattr(
            instance,
            field_name,
            converted_file,
        )

        return True

    except Exception as e:
        print(
            f"Error converting {field_name} to WebP: {e}"
        )
        return False



    
def parse_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() == 'true'
    return False


def calculate_profile_completion(user):
    """
    Calculate the profile completion percentage for a given user.

    Returns:
        dict: {
            'percentage': int,          # completion percentage (0-100)
            'missing_fields': list      # field names that are empty/False
        }
    """
    profile_fields = {
        'phone': user.phone,
        'profile_picture': user.profile_picture,
        'matric_number': user.matric_number,
        'department': user.department,
        'faculty': user.faculty,
        'level': user.level,
        'student_id_verified': user.student_id_verified,
        'hall_verified': user.hall_verified,
        'email_verified': user.email_verified,
    }

    missing_fields = [field for field, value in profile_fields.items() if not value]
    total_fields = len(profile_fields)
    filled_fields = total_fields - len(missing_fields)
    percentage = int((filled_fields / total_fields) * 100) if total_fields else 0

    return {
        'percentage': percentage,
        'missing_fields': missing_fields
    }

def create_notification(user, notification_type, title, message, action_url=''):
    """
    Create a single notification for a user.

    Args:
        user (User): The recipient user.
        notification_type (str): One of NotificationEnum values.
        title (str): Notification title.
        message (str): Notification message.
        action_url (str, optional): URL for action. Defaults to ''.
        save (bool): If False, return unsaved instance. Default True.

    Returns:
        Notification: The created (and saved) notification instance.
    """
    from apps.users.models import Notification

    notification = Notification(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
    )

    notification.save()

    return notification



def humanize_date(date):
    """Return a human-friendly relative time string."""
    now = timezone.now()
    diff = now - date
    if diff.days == 0:
        if diff.seconds < 60:
            return "just now"
        elif diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.days == 1:
        return "yesterday"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    elif diff.days < 30:
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    else:
        return date.strftime("%b %d, %Y")



def format_naira(amount):
    """
    Convert a number to Naira format with ₦ symbol and comma separators.
    Example: 300000 -> '₦300,000'
    """
    if amount is None:
        return '₦0'
    return f"₦{int(amount):,}"


def run_async(coro, timeout=30):
    """Run an async coroutine with a timeout and return the result."""
    try:
        loop = asyncio.get_running_loop()
        return loop.run_until_complete(
            asyncio.wait_for(coro, timeout=timeout)
        )
    except RuntimeError:
        return asyncio.run(
            asyncio.wait_for(coro, timeout=timeout)
        )