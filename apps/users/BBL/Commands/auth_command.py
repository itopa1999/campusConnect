
from apps.users.BBL.Commands.account_command import AccountCommand
from apps.users.models import User
from utils.Tasks.emailService import background_task_send_password_reset_email
from utils.base_result import BaseResultWithData
from rest_framework_simplejwt.tokens import RefreshToken
from utils.emails_helper import EmailHelper
import secrets
import string
from utils.enums import TokenType
from utils.helpers import validate_ui_email, is_email_verified

class AuthCommand:    
    @staticmethod
    def Execute(request, validated_data):
        try:
            email = validated_data['email']
            password = validated_data['password']

            # is_valid, message = validate_ui_email(email)
            # if not is_valid:
            #     return BaseResultWithData(
            #         message=message,
            #         data=None,
            #         status_code=400
            #     )
            
            # Get user by email
            user = User.objects.filter(email=email, is_deleted = False).first()
            
            if not user:
                return BaseResultWithData(
                    message="Invalid email or password",
                    data=None,
                    status_code=400
                )
            
            # Verify password
            if not user.check_password(password):
                return BaseResultWithData(
                    message="Invalid email or password",
                    data=None,
                    status_code=400
                )
            
            if not is_email_verified(user):
                return BaseResultWithData(
                    message="Email not verified. Please check your inbox for the verification email.",
                    data=None,
                    status_code=400
                )

            if not user.is_active:
                return BaseResultWithData(
                    message="Your account has been deactivated. Please contact support for assistance.",
                    data=None,
                    status_code=400
                )
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            return BaseResultWithData(
                message="Login successful",
                data={
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'user_id': user.id,
                    'is_email_verified': user.email_verified,
                    'is_hall_verified' : user.hall_verified
                },
                status_code=200
            )
            
        except Exception as e:
            return BaseResultWithData(
                message=f"Error during login: {str(e)}",
                data=None,
                status_code=500
            )


    @staticmethod
    def ForgotPassword(request, validated_data):
        try:
            email = validated_data['email']

            # is_valid, message = validate_ui_email(email)
            # if not is_valid:
            #     return BaseResultWithData(
            #         message=message,
            #         data=None,
            #         status_code=400
            #     )
            
            # Get user by email
            user = User.objects.filter(email=email).first()
            
            if not user:
                return BaseResultWithData(
                    message="Account with email doesn't exists",
                    data=None,
                    status_code=400
                )

            if not is_email_verified(user):
                return BaseResultWithData(
                    message="Email not verified.",
                    data=None,
                    status_code=400
                )
            
            verification_token = AccountCommand._create_verification_token(user, token_type=TokenType.PASSWORD_RESET.value)
            
            reset_link = f"{request.build_absolute_uri('/user/api/auth/verify-forget-password-email')}?token={verification_token.token}"
            background_task_send_password_reset_email.delay(user.email, user.first_name, reset_link)
            
            return BaseResultWithData(
                message="If an account with that email exists, an email containing a new password has been sent",
                data=None,
                status_code=200
            )
            
        except Exception as e:
            return BaseResultWithData(
                message=f"Error processing password reset: {str(e)}",
                data=None,
                status_code=500
            )
        
    @staticmethod
    def VerifyForgetPasswordEmail(request, token):
        try:
            is_valid, result = AccountCommand._verify_token(token, token_type=TokenType.PASSWORD_RESET.value)
            if not is_valid:
                return BaseResultWithData(
                    message=result,
                    data=None,
                    status_code=400
                )
            
            verification_token = result
            user = verification_token.user
            
                        
            return BaseResultWithData(
                message="Link verified successful.",
                data={
                    'user_id': user.id,
                    'email': user.email
                },
                status_code=200
            )
            
        except Exception as e:
            return BaseResultWithData(
                message=f"Error verifying password reset token: {str(e)}",
                data=None,
                status_code=500
            )
        
    @staticmethod
    def ConfirmResetPassword(request, validated_data):
        try:
            user_id = validated_data['user_id'].strip()
            email = validated_data['email'].strip()
            password = validated_data['password'].strip()
            confirm_password = validated_data['confirm_password'].strip()

            if password != confirm_password:
                return BaseResultWithData(
                    message="Password and confirm password do not match",
                    data=None,
                    status_code=400
                )
            
            user = User.objects.filter(id=user_id, email=email, is_active=True, is_deleted=False).first()
            
            if not user:
                return BaseResultWithData(
                    message="Account has issues. Please contact support for assistance.",
                    data=None,
                    status_code=400
                )
            
            user.set_password(password)
            user.save()
            
            return BaseResultWithData(
                message="Password reset successful. You can now log in with your new password.",
                data=None,
                status_code=200
            )
            
        except Exception as e:
            return BaseResultWithData(
                message=f"Error resetting password: {str(e)}",
                data=None,
                status_code=500
            )
            
    
    @staticmethod
    def ChangePassword(request, validated_data):
        try:
            user = request.user
            
            current_password = validated_data['current_password']
            new_password = validated_data['new_password']
            
            if not user.check_password(current_password):
                return BaseResultWithData(
                    message="Current password is incorrect",
                    data=None,
                    status_code=400
                )
            
            if len(new_password) < 8:
                return BaseResultWithData(
                    message="New password must be at least 8 characters long",
                    data=None,
                    status_code=400
                )
            
            user.set_password(new_password)
            user.save()
            
            return BaseResultWithData(
                message="Password changed successfully",
                data=None,
                status_code=200
            )
            
        except Exception as e:
            return BaseResultWithData(
                message=f"Error changing password: {str(e)}",
                data=None,
                status_code=500
            )

    @staticmethod
    def RefreshToken(request, validated_data):
        """
        Verify refresh token, check user exists and is not deleted,
        return new access token and rotated refresh token.
        """
        refresh_token_str = validated_data.get('refresh_token')
        
        user_id = None
        is_email_verified = None
        hall_verified = None
        try:
            refresh = RefreshToken(refresh_token_str)
            
            user_id = refresh.payload.get('user_id')
            if not user_id:
                return BaseResultWithData(
                    message="Invalid token payload",
                    data=None,
                    status_code=400
                )
            
            try:
                user = User.objects.get(id=user_id, email_verified=True, is_active = True, is_deleted=False)
                user_id = user.id
                is_email_verified = user.email_verified
                hall_verified = user.hall_verified
            except User.DoesNotExist:
                return BaseResultWithData(
                    message="User account not found or not verified",
                    data=None,
                    status_code=400
                )
            
            new_access_token = str(refresh.access_token)
            new_refresh_token = str(refresh) 
            
            data = {
                'access_token': new_access_token,
                'refresh_token': new_refresh_token,
                'user_id': user_id,
                'is_email_verified': is_email_verified,
                'is_hall_verified' : hall_verified
            }
            
            return BaseResultWithData(
                message="Token refreshed successfully",
                data=data,
                status_code=200
            )
        except Exception as e:
            return BaseResultWithData(
                message="Unable to refresh token",
                data=None,
                status_code=500
            )