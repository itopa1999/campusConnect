from apps.users.models import TwoFactorMethod
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
import random
from django.core.cache import cache
from django.conf import settings
from celery.exceptions import OperationalError
from utils.Tasks.backgroundTask import background_task_send_2fa_otp_email
from utils.enums import TwoFactorMethodEnum
from utils.log_helpers import OperationLogger

# ─── Constants ──────────────────────────────────────────────────────
OTP_EXPIRY = 180   # 3 minutes
OTP_LENGTH = 6

# ─── OTP Manager ──────────────────────────────────────────────────
class OTPManager:
    @staticmethod
    def generate_otp() -> str:
        """Generate a 6‑digit OTP."""
        return f"{random.randint(0, 10**OTP_LENGTH - 1):0{OTP_LENGTH}d}"

    @staticmethod
    def _make_key(user_id, method) -> str:
        return f"otp:{user_id}:{method}"

    @staticmethod
    def store_otp(user_id, method, otp):
        """Store OTP in Redis with 3‑minute TTL."""
        key = OTPManager._make_key(user_id, method)
        cache.set(key, otp, timeout=OTP_EXPIRY)

    @staticmethod
    def get_otp(user_id, method):
        """Retrieve OTP from Redis (returns None if expired)."""
        key = OTPManager._make_key(user_id, method)
        return cache.get(key)

    @staticmethod
    def verify_otp(user_id, method, code) -> bool:
        """
        Verify OTP and delete it (one‑time use).
        Returns True only if code matches and exists.
        """
        key = OTPManager._make_key(user_id, method)
        stored = cache.get(key)
        if stored and stored == code:
            cache.delete(key)
            return True
        return False

    @staticmethod
    def send_otp_email(user, otp, op=None) -> bool:
        """Send OTP via email using Celery background task."""
        if op is None:
            op = OperationLogger(f"OTPManager.send_otp_email for {user.email}")
            op.start()
        try:
            background_task_send_2fa_otp_email.delay(user.email, user.first_name, otp)
            op.success("OTP email queued successfully")
            return True
        except OperationalError as e:
            op.fail(f"Failed to queue OTP email: {e}")
            return False

    @staticmethod
    def send_otp_sms(user, otp, op=None) -> bool:
        """Send OTP via SMS (Twilio etc.) – currently logging."""
        if op is None:
            op = OperationLogger(f"OTPManager.send_otp_sms for {user.phone}")
            op.start()
        try:
            # Uncomment and configure Twilio when ready:
            # client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
            # client.messages.create(
            #     body=f'Your CampusHub OTP is: {otp} (valid 3 min)',
            #     from_=settings.TWILIO_PHONE_NUMBER,
            #     to=user.phone,
            # )
            # op.success("SMS OTP sent successfully")
            # return True

            # Dev mode: log the OTP
            op.info(f"OTP for {user.phone}: {otp}")
            return True
        except Exception as e:
            op.fail(f"Failed to send SMS OTP: {e}")
            return False


# ─── Helper Functions ──────────────────────────────────────────────

def revoke_all_user_tokens(user):
    """Revoke all tokens for a specific user."""
    try:
        tokens = OutstandingToken.objects.filter(user=user)
        blacklisted_tokens = [BlacklistedToken(token=t) for t in tokens]
        if blacklisted_tokens:
            BlacklistedToken.objects.bulk_create(blacklisted_tokens, ignore_conflicts=True)
        return True
    except Exception:
        return False


def prepare_2fa_challenge(user):
    """
    Prepares the 2FA challenge for the user.
    For TOTP: just returns the method.
    For SMS/Email: generates and sends OTP.
    Returns dict with 'requires_2fa', 'active_method', and optionally 'otp_sent'.
    Raises ValueError if OTP sending fails.
    """
    op = OperationLogger(f"TwoFactor.prepare_2fa_challenge for user: {user.first_name or user.email}")
    op.start()

    active_method = TwoFactorMethod.objects.filter(user=user, is_enabled=True).first()
    if not active_method:
        return {'requires_2fa': False, 'active_method': None}

    method_type = active_method.method.lower()
    result = {'requires_2fa': True, 'active_method': method_type}

    if method_type == TwoFactorMethodEnum.SMS.value.lower():
        otp = OTPManager.generate_otp()
        OTPManager.store_otp(user.id, TwoFactorMethodEnum.SMS.value, otp)
        sent = OTPManager.send_otp_sms(user, otp, op=op)
        if not sent:
            op.fail("Failed to send SMS OTP")
            raise ValueError("Failed to send SMS OTP")
        op.success("OTP sent to SMS successfully")
        result['otp_sent'] = True

    elif method_type == TwoFactorMethodEnum.EMAIL.value.lower():
        otp = OTPManager.generate_otp()
        OTPManager.store_otp(user.id, TwoFactorMethodEnum.EMAIL.value, otp)
        sent = OTPManager.send_otp_email(user, otp, op=op)
        if not sent:
            op.fail("Failed to send Email OTP")
            raise ValueError("Failed to send Email OTP")
        op.success("OTP sent to Email successfully")
        result['otp_sent'] = True

    return result