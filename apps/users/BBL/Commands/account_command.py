from apps.users.models import User, VerificationToken
from utils.base_result import BaseResult, BaseResultWithData
from utils.enums import TokenType
from utils.emails_helper import EmailHelper
from utils.helpers import validate_ui_email, normalize_nigerian_phone
from django.db import transaction


class AccountCommand:    
    @staticmethod
    def Execute(request, validated_data):
        try:
            email = validated_data['email']
            raw_phone = validated_data['phone']

            normalized_phone = normalize_nigerian_phone(raw_phone)
            if not normalized_phone:
                return BaseResult(
                    message="Invalid Nigerian phone number format.",
                    status_code=400
                )
            
            # is_valid, message = validate_ui_email(email)
            # if not is_valid:
            #     return BaseResultWithData(
            #         message=message,
            #         data=None,
            #         status_code=400
            #     )

            if User.objects.filter(email=email).exists():
                return BaseResult(
                    message="Email already registered.",
                    status_code=400
                )

            if User.objects.filter(phone=normalized_phone).exists():
                return BaseResult(
                    message="Phone already registered with.",
                    status_code=400
                )
            
            password = validated_data['password']
            if len(password) < 8:
                return BaseResult(
                    message="Password must be at least 8 characters long.",
                    status_code=400
                )
            
            user = User.objects.create_user(
                email=email,
                phone=normalized_phone,
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                password=password,
                is_active = True,
                email_verified=False
            )
            verification_token = AccountCommand._create_verification_token(user, token_type=TokenType.EMAIL_VERIFICATION.value)
            
            verification_link = f"{request.build_absolute_uri('/user/api/auth/verify-email')}?token={verification_token.token}"
            EmailHelper.send_verification_email(user.email, user.first_name, verification_link)
            
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
            return BaseResult(
                message=f"Error creating account: {str(e)}",
                status_code=400
            )
    
    @staticmethod
    def VerifyEmail(request, token):
        """Verify user email using verification token"""
        try:
            
            is_valid, result = AccountCommand._verify_token(token, token_type=TokenType.EMAIL_VERIFICATION.value)
            if not is_valid:
                return BaseResult(
                    message=result,
                    status_code=400
                )
            user = result.user
            user.email_verified = True
            user.is_active = True
            user.save(update_fields=["email_verified", "is_active"])
            
            return BaseResultWithData(
                message="Email verified successfully",
                data={'user_id': user.id, 'email': user.email},
                status_code=200
            )
            
        except Exception as e:
            return BaseResult(
                message=f"Error verifying email: {str(e)}",
                status_code=500
            )
    
    @staticmethod
    def _create_verification_token(user, token_type=TokenType.EMAIL_VERIFICATION.value):
        """Create a verification token for email verification"""

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
        return verification_token
    
    @staticmethod
    def _verify_token(token, token_type):
        """Verify if a token is valid for a given token type"""
        if not token:
            return False, "Token is required"
        
        verification_token = VerificationToken.objects.filter(
            token=token,
            token_type=token_type,
            is_deleted=False
        ).first()
        
        if not verification_token:
            return False, "Invalid token"
        
        if not verification_token.is_valid():
            return False, "Token has already been used or has expired"
        
        verification_token.is_used = True
        verification_token.save(update_fields=["is_used"])
        
        return True, verification_token

