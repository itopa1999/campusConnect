from apps.users.models import Point, User, VerificationToken
from utils.Tasks.emailService import background_task_send_account_verify_email, background_task_send_verification_email
from utils.base_result import BaseResult, BaseResultWithData
from utils.enums import BadgeChoiceEnum, TokenType
from utils.emails_helper import EmailHelper
from utils.helpers import BadgeService, validate_ui_email, normalize_nigerian_phone
from django.db import transaction
from utils.log_helpers import logger, OperationLogger
from celery.exceptions import OperationalError

class AccountCommand:    
    @staticmethod
    def Execute(request, validated_data):
        email = validated_data.get('email')
        raw_phone = validated_data.get('phone')
        op = OperationLogger("AccountCommand.Execute", email=email, phone=raw_phone)
        op.start()
        try:
            normalized_phone = normalize_nigerian_phone(raw_phone)
            if not normalized_phone:
                logger.warning(f"[AccountCommand.Execute] Invalid phone format: {raw_phone}")
                return BaseResult(
                    message="Invalid Nigerian phone number format.",
                    status_code=400
                )
            
            # is_valid, message = validate_ui_email(email)
            # if not is_valid:
            #     logger.warning(f"[AccountCommand.Execute] Invalid email: {email}")
            #     return BaseResultWithData(
            #         message=message,
            #         data=None,
            #         status_code=400
            #     )

            if User.objects.filter(email=email, is_deleted=False).exists():
                logger.warning(f"[AccountCommand.Execute] Email already registered: {email}")
                return BaseResult(
                    message="Email already registered.",
                    status_code=400
                )

            if User.objects.filter(phone=normalized_phone, is_deleted=False).exists():
                logger.warning(f"[AccountCommand.Execute] Phone already registered: {normalized_phone}")
                return BaseResult(
                    message="Phone already registered with.",
                    status_code=400
                )
            
            password = validated_data.get('password')
            if not password or len(password) < 8:
                logger.warning(f"[AccountCommand.Execute] Weak password provided for email: {email}")
                return BaseResult(
                    message="Password must be at least 8 characters long.",
                    status_code=400
                )
            
            user = User.objects.create_user(
                email=email,
                phone=normalized_phone,
                first_name=validated_data.get('first_name'),
                last_name=validated_data.get('last_name'),
                password=password,
                is_active=True,
                email_verified=False
            )

            Point.objects.create(user=user, amount=3)

            BadgeService.set(user, [BadgeChoiceEnum.UN_VERIFIED.value])

            verification_token = AccountCommand._create_verification_token(user, token_type=TokenType.EMAIL_VERIFICATION.value)
            
            verification_link = f"{request.build_absolute_uri('/user/api/auth/verify-email')}?token={verification_token.token}"
            try:
                background_task_send_verification_email.delay(user.email, user.first_name, verification_link)
            except OperationalError as e:
                op.success("Account created successfully, but failed to queue verification email")
            else:
                op.success("Account created successfully, verification email queued")
            
            return BaseResultWithData(
                message="Account created successfully. Please check your email to verify your account.",
                data={
                    'user_id': user.id,
                    'email': user.email,
                    'message': 'Verification link sent to your email'
                },
                status_code=201
            )
            
        except Exception as e:
            op.fail("Error creating account", exc=e)
            return BaseResult(
                message=f"Error creating account: {str(e)}",
                status_code=400
            )
    
    @staticmethod
    def VerifyEmail(request, token):
        """Verify user email using verification token"""
        op = OperationLogger("AccountCommand.VerifyEmail", token=token)
        op.start()
        try:
            is_valid, result = AccountCommand._verify_token(token, token_type=TokenType.EMAIL_VERIFICATION.value)
            if not is_valid:
                logger.warning(f"[AccountCommand.VerifyEmail] Token verification failed: {result}")
                return BaseResult(
                    message=result,
                    status_code=400
                )
            user = result.user
            user.email_verified = True
            user.is_active = True
            user.save(update_fields=["email_verified", "is_active"])
            BadgeService.remove(user, BadgeChoiceEnum.UN_VERIFIED.value)
            BadgeService.set(user, [BadgeChoiceEnum.VERIFIED.value])

            try:
                background_task_send_account_verify_email.delay(user.email, user.first_name)
            except OperationalError as e:
                op.success("Email verified successfully, but failed to queue verification email")
            else:
                op.success("Email verified successfully")
            
            return BaseResultWithData(
                message="Email verified successfully",
                data={'user_id': user.id, 'email': user.email},
                status_code=200
            )
            
        except Exception as e:
            op.fail("Error verifying email", exc=e)
            return BaseResult(
                message=f"Error verifying email: {str(e)}",
                status_code=500
            )
    
    @staticmethod
    def _create_verification_token(user, token_type=TokenType.EMAIL_VERIFICATION.value):
        """Create a verification token for email verification"""
        op = OperationLogger("AccountCommand._create_verification_token", user_id=user.id, token_type=token_type)
        op.start()

        VerificationToken.objects.filter(
            user=user,
            token_type=token_type,
            is_used=False
        ).update(is_used=True)
        
        token = VerificationToken.generate_token()
        
        while VerificationToken.objects.filter(
            token=token,
            is_used=False
        ).exists():
            token = VerificationToken.generate_token()
        
        verification_token = VerificationToken.objects.create(
            user=user,
            token=token,
            token_type=token_type,
        )
        op.success("Verification token created")
        return verification_token
    
    @staticmethod
    def _verify_token(token, token_type):
        """Verify if a token is valid for a given token type"""
        op = OperationLogger("AccountCommand._verify_token", token=token, token_type=token_type)
        op.start()

        if not token:
            logger.warning("[AccountCommand._verify_token] Token is required")
            return False, "Token is required"
        
        verification_token = VerificationToken.objects.filter(
            token=token,
            token_type=token_type,
            is_deleted=False
        ).first()
        
        if not verification_token:
            logger.warning(f"[AccountCommand._verify_token] Invalid token: {token}")
            return False, "Invalid token"
        
        if not verification_token.is_valid():
            logger.warning(f"[AccountCommand._verify_token] Token invalid or expired: {token}")
            return False, "Token has already been used or has expired"
        
        verification_token.is_used = True
        verification_token.save(update_fields=["is_used"])
        op.success("Token verified successfully")
        
        return True, verification_token

