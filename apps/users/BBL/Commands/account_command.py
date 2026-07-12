from apps.users.models import User, VerificationToken
from utils.Tasks.emailService import background_task_send_account_verify_email, background_task_send_verification_email
from utils.base_result import BaseResult, BaseResultWithData
from utils.constant_helper import ConstantHelper
from utils.enums import BadgeChoiceEnum, DefaultPointEnum, FeatureFlagEnum, GroupNames, PointTransactionTypeEnum, TokenType
from utils.emails_helper import EmailHelper
from utils.featureflag import is_feature_active
from utils.helpers import BadgeService, UpdatePointsService, validate_ui_email, normalize_nigerian_phone
from django.db import transaction
from utils.log_helpers import logger, OperationLogger
from celery.exceptions import OperationalError

class AccountCommand:    
    @staticmethod
    def Execute(request, validated_data):
        email = validated_data.get('email')
        raw_phone = validated_data.get('phone')
        op = OperationLogger(f"AccountCommand.Execute account creation for  {email}", email=email, phone=raw_phone)
        op.start()
        try:
            normalized_phone = normalize_nigerian_phone(raw_phone)
            if not normalized_phone:
                op.fail(f"[AccountCommand.Execute] Invalid phone format: {raw_phone}")
                return BaseResult(
                    message="Invalid Nigerian phone number format.",
                    status_code=400
                )
            
            # is_valid, message = validate_ui_email(email)
            # if not is_valid:
            #     op.fail(f"[AccountCommand.Execute] Invalid email: {email}")
            #     return BaseResultWithData(
            #         message=message,
            #         data=None,
            #         status_code=400
            #     )

            if User.objects.filter(email=email, is_deleted=False).exists():
                op.fail(f"[AccountCommand.Execute] Email already registered: {email}")
                return BaseResult(
                    message="Email already registered.",
                    status_code=400
                )

            if User.objects.filter(phone=normalized_phone, is_deleted=False).exists():
                op.fail(f"[AccountCommand.Execute] Phone already registered: {normalized_phone}")
                return BaseResult(
                    message="Phone already registered with.",
                    status_code=400
                )
            
            password = validated_data.get('password')
            if not password or len(password) < 8:
                op.fail(f"[AccountCommand.Execute] Weak password provided for email: {email}")
                return BaseResult(
                    message="Password must be at least 8 characters long.",
                    status_code=400
                )
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    phone=normalized_phone,
                    first_name=validated_data.get('first_name'),
                    last_name=validated_data.get('last_name'),
                    password=password,
                    is_active=True,
                    email_verified=False,
                    group_name=GroupNames.STUDENT.value
                )

                if is_feature_active(FeatureFlagEnum.ACCOUNT_CREATION_BONUS.value):
                    UpdatePointsService.update_points(
                        user=user,
                        points=ConstantHelper.ACCOUNT_CREATION_BONUS_POINTS,
                        action=ConstantHelper.POINT_ADDITION,
                        transaction_type=PointTransactionTypeEnum.ACCOUNT_CREATION_BONUS.value,
                        description=f"Account Creation Bouns",
                        reference=f"user_id: {user.id}"
                    )

                BadgeService.set(user, [BadgeChoiceEnum.UN_VERIFIED.value])

                verification_token = AccountCommand._create_verification_token(user, token_type=TokenType.EMAIL_VERIFICATION.value)
                
                verification_link = f"{request.build_absolute_uri('/user/api/auth/verify-email')}?token={verification_token.token}"

            try:
                background_task_send_verification_email.delay(user.email, user.first_name, verification_link)
            except OperationalError as e:
                op.success("Account created successfully, but failed to queue verification email")
            
            op.success(f"Account created successfully for user: {user.first_name or user.email}")
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
            op.fail(f"Error creating account for email {email}", exc=e)
            return BaseResult(
                message=f"Error creating account: {str(e)}",
                status_code=400
            )
    
    @staticmethod
    def VerifyEmail(request, token):
        """Verify user email using verification token"""
        op = OperationLogger(f"AccountCommand.VerifyEmail {token}", token=token)
        op.start()
        try:
            is_valid, result = AccountCommand._verify_token(token, token_type=TokenType.EMAIL_VERIFICATION.value)
            if not is_valid:
                op.fail(f"[AccountCommand.VerifyEmail] Token: {token} verification failed: {result}")
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
            
            op.success(f"Email: {user.email} verified successfully for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Email verified successfully",
                data={'user_id': user.id, 'email': user.email},
                status_code=200
            )
            
        except Exception as e:
            op.fail(f"Error verifying email for token: {token}", exc=e)
            return BaseResult(
                message=f"Error verifying email: {str(e)}",
                status_code=500
            )
        
    @staticmethod
    def ResendEmail(request, validated_data):
        email = validated_data.get('email', '').strip()
        op = OperationLogger(f"AccountCommand.ResendEmail for {email}", email=email)
        op.start()
        user = User.objects.filter(email=email, email_verified=False, is_active=True).first()
        if not user:
            return BaseResult(
                message="If this email is registered, a verification link has been sent.",
                status_code=200
            )
        verification_token = AccountCommand._create_verification_token(user, token_type=TokenType.EMAIL_VERIFICATION.value)
                
        verification_link = f"{request.build_absolute_uri('/user/api/auth/verify-email')}?token={verification_token.token}"
        try:
            background_task_send_verification_email.delay(user.email, user.first_name, verification_link)
        except OperationalError as e:
            op.success("Verification email successfully, but failed to queue verification email")


        op.success(f"Verification email: {user.email} queued successfully for user: {user.first_name or user.email}")  
        return BaseResultWithData(
            message="Verification email successfully sent. Please check your email to verify your account.",
            data={
                'user_id': user.id,
                'email': user.email,
                'message': 'If this email is registered, a verification link has been sent.'
            },
            status_code=200
        )
        

    
    @staticmethod
    def _create_verification_token(user, token_type=TokenType.EMAIL_VERIFICATION.value):
        """Create a verification token for email verification"""
        op = OperationLogger(f"AccountCommand._create_verification_token for user: {user.first_name or user.email} ", user_id=user.id, token_type=token_type)
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
        op.success(f"Verification token: {token} created for user: {user.first_name or user.email}")
        return verification_token
    
    @staticmethod
    def _verify_token(token, token_type):
        """Verify if a token is valid for a given token type"""
        op = OperationLogger("AccountCommand._verify_token", token=token, token_type=token_type)
        op.start()

        if not token:
            op.fail(f"[AccountCommand._verify_token] Token: {token} is required")
            return False, "Token is required"
        
        verification_token = VerificationToken.objects.filter(
            token=token,
            token_type=token_type,
            is_deleted=False
        ).first()
        
        if not verification_token:
            op.fail(f"[AccountCommand._verify_token] Invalid token: {token}")
            return False, "Invalid token"
        
        if not verification_token.is_valid():
            op.fail(f"[AccountCommand._verify_token] Token invalid or expired: {token}")
            return False, "Token has already been used or has expired"
        
        verification_token.is_used = True
        verification_token.save(update_fields=["is_used"])
        op.success(f"Token verified successfully for user: {verification_token.user.first_name or verification_token.user.email}")
        
        return True, verification_token

