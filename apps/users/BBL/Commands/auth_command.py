
from apps.users.models import User
from utils.base_result import BaseResultWithData
from rest_framework_simplejwt.tokens import RefreshToken
from utils.emails_helper import EmailHelper
import secrets
import string


class AuthCommand:    
    @staticmethod
    def Execute(request, validated_data):
        try:
            email = validated_data['email']
            password = validated_data['password']
            
            # Get user by email
            user = User.objects.filter(email=email).first()
            
            if not user:
                return BaseResultWithData(
                    message="Invalid email or password",
                    data=None,
                    status_code=401
                )
            
            # Verify password
            if not user.check_password(password):
                return BaseResultWithData(
                    message="Invalid email or password",
                    data=None,
                    status_code=401
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
                    'user_id': user.id
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
            
            # Get user by email
            user = User.objects.filter(email=email).first()
            
            if not user:
                return BaseResultWithData(
                    message="If an account with that email exists, an email containing a new password has been sent",
                    data=None,
                    status_code=200
                )
            
            # Generate new random password
            new_password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(12))
            
            # Update user password
            user.set_password(new_password)
            user.save()
            
            # Send password reset email
            subject = "Your Campus Connect Password Has Been Reset"
            message = f"""
Hello {user.first_name},

Your password has been reset. Here is your new password:

{new_password}

Please log in with this password and change it to something more secure in your account settings.

If you didn't request this, please contact our support team immediately.

Best regards,
Campus Connect Team
            """
            
            EmailHelper.send_email(
                subject=subject,
                message=message,
                recipient_list=[user.email],
                fail_silently=False
            )
            
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
