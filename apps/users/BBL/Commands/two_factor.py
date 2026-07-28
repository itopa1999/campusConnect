from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from apps.users.models import BackupCode, TwoFactorMethod
from apps.users.utils import OTPManager
from utils.base_result import BaseResultWithData
from utils.enums import TwoFactorMethodEnum
from utils.log_helpers import OperationLogger
import pyotp
import qrcode
from io import BytesIO
import base64
from django.conf import settings
import secrets
from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class TwoFactorCommand:

    @staticmethod
    def _disable_other_methods(user, exclude_method):
        """Disable all 2FA methods for the user except the one specified."""
        TwoFactorMethod.objects.filter(user=user).exclude(method=exclude_method).update(is_enabled=False)

    @staticmethod
    def toggle_setup(request, validated_data) -> BaseResultWithData:
        user = request.user
        op = OperationLogger(f"TwoFactorCommand.toggle_setup for user: {user.first_name or user.email}", data=validated_data)
        op.start()

        factor_type = validated_data.get('two_factor_Type')
        allowed_type = [choice[0] for choice in TwoFactorMethodEnum.choices()]
        if factor_type not in allowed_type:
            op.fail(f"[TwoFactorCommand.toggle_setup] invalid factor type for email: {user.email}")
            return BaseResultWithData(
                message=f"Method must be one of: {', '.join(allowed_type)}",
                status_code=400
            )

        method, created = TwoFactorMethod.objects.get_or_create(
            user=user,
            method=factor_type
        )

        # ─── TOTP ──────────────────────────────────────────────────────
        if factor_type.lower() == TwoFactorMethodEnum.TOTP.value.lower():
            # ─── 1. Already enabled → toggle OFF ───
            if method.is_enabled:
                method.is_enabled = False
                method.save(update_fields=['is_enabled'])
                op.fail(f"TOTP disabled for {user.email}")
                return BaseResultWithData(
                    message="TOTP disabled.",
                    data={"is_enabled": False},
                    status_code=200
                )

            # ─── 2. Disabled → try to enable ───
            # 2a. No secret → first-time setup → generate QR, keep disabled
            if not method.secret:
                method.secret = pyotp.random_base32()
                method.save(update_fields=['secret'])

            # 2b. Secret exists → check if user ever verified
            has_verified = BackupCode.objects.filter(user=user).exists()
            if has_verified:
                # User already verified once → enable immediately (no re-scan)
                TwoFactorCommand._disable_other_methods(user, factor_type)
                method.is_enabled = True
                method.save(update_fields=['is_enabled'])
                op.success(f"TOTP re-enabled for {user.email}")
                return BaseResultWithData(
                    message="TOTP enabled.",
                    data={"is_enabled": True},
                    status_code=200
                )
            else:
                # User never verified → show QR again (keep disabled)
                totp = pyotp.TOTP(method.secret)
                provisioning_uri = totp.provisioning_uri(
                    name=user.email,
                    issuer_name=settings.PROJECT_NAME
                )
                qr = qrcode.make(provisioning_uri)
                buffered = BytesIO()
                qr.save(buffered, format="PNG")
                qr_base64 = base64.b64encode(buffered.getvalue()).decode()

                # Ensure it stays disabled
                method.is_enabled = False
                method.save(update_fields=['is_enabled'])

                op.success(f"TOTP QR re‑shown for {user.email}")
                return BaseResultWithData(
                    message="Scan this QR code with your authenticator app.",
                    data={
                        "secret": method.secret,
                        "qr_code": f"data:image/png;base64,{qr_base64}",
                        "provisioning_uri": provisioning_uri
                    },
                    status_code=200
                )

        # ─── SMS ──────────────────────────────────────────────────────
        elif factor_type.lower() == TwoFactorMethodEnum.SMS.value.lower():
            if not user.phone:
                op.fail(f"[TwoFactorCommand.toggle_setup] Phone number not available for email: {user.email}")
                return BaseResultWithData(
                    message="Please update your phone number to enable SMS 2FA.",
                    status_code=400
                )

            if method.is_enabled:
                method.is_enabled = False
                method.save(update_fields=['is_enabled'])
                op.success(f"SMS 2FA disabled for {user.email}")
                return BaseResultWithData(message="SMS 2FA disabled.", data={"is_enabled": False}, status_code=200)
            else:
                TwoFactorCommand._disable_other_methods(user, factor_type)
                method.is_enabled = True
                method.save(update_fields=['is_enabled'])
                op.success(f"SMS 2FA enabled for {user.email}")
                return BaseResultWithData(message="SMS 2FA enabled.", data={"is_enabled": True}, status_code=200)

        # ─── EMAIL ────────────────────────────────────────────────────
        elif factor_type.lower() == TwoFactorMethodEnum.EMAIL.value.lower():
            if not user.email:
                op.fail(f"[TwoFactorCommand.toggle_setup] Email address not available for user: {user.email}")
                return BaseResultWithData(
                    message="Please update your email address to enable Email 2FA.",
                    status_code=400
                )
            if method.is_enabled:
                method.is_enabled = False
                method.save(update_fields=['is_enabled'])
                op.success(f"Email 2FA disabled for {user.email}")
                return BaseResultWithData(message="Email 2FA disabled.", data={"is_enabled": False}, status_code=200)
            else:
                TwoFactorCommand._disable_other_methods(user, factor_type)
                method.is_enabled = True
                method.save(update_fields=['is_enabled'])
                op.success(f"Email 2FA enabled for {user.email}")
                return BaseResultWithData(
                    message="Email 2FA enabled successfully.",
                    data=None,
                    status_code=200
                )

        # ─── HARDWARE ─────────────────────────────────────────────────
        elif factor_type.lower() == TwoFactorMethodEnum.HARDWARE.value.lower():
            if method.is_enabled:
                method.is_enabled = False
                method.save(update_fields=['is_enabled'])
                op.success(f"HARDWARE 2FA disabled for {user.email}")
                return BaseResultWithData(message="HARDWARE 2FA disabled.", data={"is_enabled": False}, status_code=200)
            else:
                TwoFactorCommand._disable_other_methods(user, factor_type)
                method.is_enabled = True
                method.save(update_fields=['is_enabled'])
                op.success(f"Hardware 2FA enabled for {user.email}")
                return BaseResultWithData(
                    message="Hardware token 2FA enabled successfully.",
                    data=None,
                    status_code=200
                )

        else:
            op.fail(f"[TwoFactorCommand.toggle_setup] invalid factor type for email: {user.email}")
            return BaseResultWithData(
                message="Invalid factor type.",
                status_code=400
            )

    @staticmethod
    def verify_totp(request, validated_data) -> BaseResultWithData:
        user = request.user
        op = OperationLogger(f"TwoFactorCommand.verify_totp for user: {user.first_name or user.email}", data=validated_data)
        op.start()

        code = validated_data.get('code')
        if not code:
            return BaseResultWithData(message="Code required", status_code=400)

        try:
            method = TwoFactorMethod.objects.get(user=user, method=TwoFactorMethodEnum.TOTP.value)
        except TwoFactorMethod.DoesNotExist:
            return BaseResultWithData(message="TOTP not set up", status_code=404)

        totp = pyotp.TOTP(method.secret)
        if totp.verify(code):
            TwoFactorCommand._disable_other_methods(user, TwoFactorMethodEnum.TOTP.value)
            method.is_enabled = True
            method.save(update_fields=['is_enabled'])

            BackupCode.objects.filter(user=user, is_used=False).delete()
            plain_codes = []
            for _ in range(10):
                plain = secrets.token_hex(4)
                plain_codes.append(plain)
                hashed = make_password(plain)
                BackupCode.objects.create(user=user, code_hash=hashed)

            op.success(f"TOTP enabled and backup codes generated for {user.email}")
            return BaseResultWithData(
                message="TOTP enabled successfully.",
                data={"backup_codes": plain_codes},
                status_code=200
            )
        else:
            op.fail(f"Invalid TOTP code for {user.email}")
            return BaseResultWithData(message="Invalid code", status_code=400)

    @staticmethod
    def _2fa_verify_login(request, validated_data) -> BaseResultWithData:
        user_id = validated_data.get('user_id')
        code = validated_data.get('code')
        platform = validated_data.get('platform')
        valid_method = validated_data.get('method')
        user = get_object_or_404(User, id=user_id)

        op = OperationLogger(f"TwoFactorCommand._2fa_verify_login for user: {user.first_name or user.email}", data=validated_data)
        op.start()

        allowed_type = [choice[0] for choice in TwoFactorMethodEnum.choices()]
        if valid_method not in allowed_type:
            op.fail(f"[TwoFactorCommand._2fa_verify_login] invalid method type for email: {user.email}")
            return BaseResultWithData(
                message=f"Method must be one of: {', '.join(allowed_type)}",
                status_code=400
            )

        valid = False

        # ─── TOTP ──────────────────────────────────────────────────────
        if valid_method.lower() == TwoFactorMethodEnum.TOTP.value.lower():
            try:
                method = TwoFactorMethod.objects.get(user=user, method=TwoFactorMethodEnum.TOTP.value, is_enabled=True)
            except TwoFactorMethod.DoesNotExist:
                op.fail(f"TOTP not enabled for user {user.email}")
                return BaseResultWithData(message="TOTP not enabled", status_code=403)

            totp = pyotp.TOTP(method.secret)
            if not totp.verify(code):
                op.fail("Invalid TOTP code")
                return BaseResultWithData(message="Invalid code", data=None, status_code=400)

            valid = True 

        # ─── SMS and EMAIL ────────────────────────────────────────────
        elif valid_method.lower() in [TwoFactorMethodEnum.SMS.value.lower(), TwoFactorMethodEnum.EMAIL.value.lower()]:
            try:
                method = TwoFactorMethod.objects.get(user=user, method=valid_method.lower(), is_enabled=True)
            except TwoFactorMethod.DoesNotExist:
                op.fail(f"{valid_method.upper()} not enabled for user {user.email}")
                return BaseResultWithData(message=f"{valid_method.upper()} not enabled", status_code=403)

            if not OTPManager.verify_otp(user.id, valid_method.lower(), code):
                op.fail("Invalid or expired OTP")
                return BaseResultWithData(message="Invalid or expired OTP.", status_code=400)

            valid = True

        # ─── BACKUP CODES ─────────────────────────────────────────────
        elif valid_method.lower() == TwoFactorMethodEnum.BACKUP.value.lower():
            backups = BackupCode.objects.filter(user=user, is_used=False)
            for backup in backups:
                if check_password(code, backup.code_hash):
                    backup.is_used = True
                    backup.save(update_fields=['is_used'])
                    op.success(f"Backup code used for {user.email}")
                    valid = True
                    break

            if not valid:
                op.fail(f"Invalid backup code for {user.email}")
                return BaseResultWithData(message="Invalid backup code", data=None, status_code=400)

        # ─── HARDWARE ──────────────────────────────────────────────────
        elif valid_method.lower() == TwoFactorMethodEnum.HARDWARE.value.lower():
            return BaseResultWithData(message="Not yet implemented", data=None, status_code=400)

        else:
            op.fail(f"Unsupported method: {valid_method}")
            return BaseResultWithData(message="Unsupported method", status_code=400)

        if not valid:
            return BaseResultWithData(message="Verification failed", status_code=400)

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        op.success(f"Login successful for user: {user.first_name or user.email}")

        profile_pic_url = request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None

        return BaseResultWithData(
            message="Login successful",
            data={
                'access_token': access_token,
                'refresh_token': refresh_token,
                'platform': platform,
                'user': {
                    "user_id": user.id,
                    "email": user.email,
                    "profile_pic": profile_pic_url,
                    "point_bal": user.points or 0,
                    "trusting_score": user.average_rating,
                    "is_student_id_verified": user.student_id_verified,
                    "is_hall_verified": user.hall_verified,
                }
            },
            status_code=200
        )
    
    @staticmethod
    def disable_2fa(request, validated_data) -> BaseResultWithData:
        user = request.user
        op = OperationLogger(f"TwoFactorCommand.disable_2fa for user: {user.first_name or user.email}", data=validated_data)
        op.start()

        TwoFactorMethod.objects.filter(user=user).update(is_enabled=False)
        op.success(f"All 2FA methods disabled for {user.email}")
        return BaseResultWithData(
            message="All 2FA methods disabled.",
            data=None,
            status_code=200
        )


