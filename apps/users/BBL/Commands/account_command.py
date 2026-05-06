from apps.users.models import User, VerificationToken
from utils.base_result import BaseResult, BaseResultWithData
from utils.enums import TokenType
from utils.emails_helper import EmailHelper


class AccountCommand:    
    @staticmethod
    def Execute(request, validated_data):
        try:
            email = validated_data['email']
            phone = validated_data['phone']

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

            if User.objects.filter(phone=phone).exists():
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
                email=validated_data['email'],
                phone=validated_data['phone'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                password=validated_data['password'],
                is_active = False,
                email_verified=False
            )
            verification_token = AccountCommand._create_verification_token(user)
            
            # todo: add to background task.
            EmailHelper.send_verification_email(user, verification_token, request)
            
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
            if not token:
                return BaseResult(
                    message="Token is required",
                    status_code=400
                )
            
            # Get verification token
            verification_token = VerificationToken.objects.filter(token=token).first()
            
            if not verification_token:
                return BaseResult(
                    message="Invalid token",
                    status_code=400
                )
            
            if not verification_token.is_valid():
                return BaseResult(
                    message="Token has already been used",
                    status_code=400
                )
            
            # Mark token as used and verify user email
            verification_token.is_used = True
            verification_token.save()
            
            user = verification_token.user
            user.email_verified = True
            user.is_active = True
            user.save()
            
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
    def _create_verification_token(user):
        """Create a verification token for email verification"""
        token = VerificationToken.generate_token()
        
        while VerificationToken.objects.filter(token=token).exists():
            token = VerificationToken.generate_token()
        
        verification_token = VerificationToken.objects.create(
            user=user,
            token=token,
            token_type=TokenType.EMAIL_VERIFICATION.value
        )
        return verification_token

