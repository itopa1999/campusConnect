from apps.users.BBL.Commands.account_command import AccountCommand
from apps.users.models import User
from utils.Tasks.emailService import background_task_send_change_password_email, background_task_send_notification_email, background_task_send_password_reset_email
from utils.base_result import BaseResultWithData
from rest_framework_simplejwt.tokens import RefreshToken
from utils.emails_helper import EmailHelper
from celery.exceptions import OperationalError
from utils.log_helpers import logger, OperationLogger
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.conf import settings

from utils.enums import TokenType
from utils.helpers import validate_ui_email, is_email_verified

class AuthCommand:    
    @staticmethod
    def Execute(request, validated_data):
        email = validated_data.get('email')
        password = validated_data.get('password')
        op = OperationLogger("AuthCommand.Execute", email=email)
        op.start()
        try:
            # is_valid, message = validate_ui_email(email)
            # if not is_valid:
            #     op.fail(f"[AuthCommand.Execute] Invalid email: {email}")
            #     return BaseResultWithData(
            #         message=message,
            #         data=None,
            #         status_code=400
            #     )
            
            user = User.objects.filter(email=email, is_deleted=False).first()
            
            if not user:
                op.fail(f"[AuthCommand.Execute] Login failed for email: {email}")
                return BaseResultWithData(
                    message="Invalid email or password",
                    data=None,
                    status_code=400
                )
            
            if not user.check_password(password):
                op.fail(f"[AuthCommand.Execute] Invalid password attempt for email: {email}")
                return BaseResultWithData(
                    message="Invalid email or password",
                    data=None,
                    status_code=400
                )
            
            if not is_email_verified(user):
                op.fail(f"[AuthCommand.Execute] Email not verified for user_id: {user.id}")
                return BaseResultWithData(
                    message="Email not verified. Please check your inbox for the verification email.",
                    data=None,
                    status_code=400
                )

            if not user.is_active:
                op.fail(f"[AuthCommand.Execute] Inactive account login attempt: user_id={user.id}")
                return BaseResultWithData(
                    message="Your account has been deactivated. Please contact support for assistance.",
                    data=None,
                    status_code=400
                )
            
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            op.success("Login successful")
            
            if user.profile_picture and hasattr(user.profile_picture, 'url'):
                profile_pic_url = request.build_absolute_uri(user.profile_picture.url)
            else:
                profile_pic_url = None
            
            return BaseResultWithData(
                message="Login successful",
                data={
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'user_id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'profile_pic': profile_pic_url,
                    'point_bal': user.points if user.points else 0,
                    'trusting_score': user.average_rating,
                    'is_email_verified': user.email_verified,
                    'is_hall_verified' : user.hall_verified
                },
                status_code=200
            )
            
        except Exception as e:
            op.fail("Error during login", exc=e)
            return BaseResultWithData(
                message=f"Error during login: {str(e)}",
                data=None,
                status_code=500
            )


    @staticmethod
    def ForgotPassword(request, validated_data):
        email = validated_data.get('email')
        op = OperationLogger("AuthCommand.ForgotPassword", email=email)
        op.start()
        try:
            # is_valid, message = validate_ui_email(email)
            # if not is_valid:
            #     op.fail(f"[AuthCommand.ForgotPassword] Invalid email: {email}")
            #     return BaseResultWithData(
            #         message=message,
            #         data=None,
            #         status_code=400
            #     )
            
            user = User.objects.filter(email=email, is_deleted=False).first()
            
            if not user:
                op.fail(f"[AuthCommand.ForgotPassword] No account found for email: {email}")
                return BaseResultWithData(
                    message="Account with email doesn't exists",
                    data=None,
                    status_code=400
                )

            if not is_email_verified(user):
                op.fail(f"[AuthCommand.ForgotPassword] Email not verified for user_id: {user.id}")
                return BaseResultWithData(
                    message="Email not verified.",
                    data=None,
                    status_code=400
                )
            
            verification_token = AccountCommand._create_verification_token(user, token_type=TokenType.PASSWORD_RESET.value)
            
            link = f"{request.build_absolute_uri('/user/api/auth/verify-forget-password-email')}?token={verification_token.token}"
            try:
                background_task_send_password_reset_email.delay(user.email, user.first_name, link)
            except OperationalError as e:
                op.success("Password reset successful, but failed to queue reset email")
            else:
                op.success("Password reset email queued")
            return BaseResultWithData(
                message="If an account with that email exists, an email containing a new password has been sent",
                data=None,
                status_code=200
            )
            
        except Exception as e:
            op.fail("Error processing password reset", exc=e)
            return BaseResultWithData(
                message=f"Error processing password reset: {str(e)}",
                data=None,
                status_code=500
            )
        
    @staticmethod
    def VerifyForgetPasswordEmail(request, token):
        op = OperationLogger("AuthCommand.VerifyForgetPasswordEmail", token=token)
        op.start()
        try:
            is_valid, result = AccountCommand._verify_token(token, token_type=TokenType.PASSWORD_RESET.value)
            if not is_valid:
                op.fail(f"[AuthCommand.VerifyForgetPasswordEmail] Token verification failed: {result}")
                return BaseResultWithData(
                    message=result,
                    data=None,
                    status_code=400
                )
            
            verification_token = result
            user = verification_token.user
            op.success("Password reset token verified")
            
            return BaseResultWithData(
                message="Link verified successful.",
                data={
                    'user_id': user.id,
                    'email': user.email
                },
                status_code=200
            )
            
        except Exception as e:
            op.fail("Error verifying password reset token", exc=e)
            return BaseResultWithData(
                message=f"Error verifying password reset token: {str(e)}",
                data=None,
                status_code=500
            )
        
    @staticmethod
    def ConfirmResetPassword(request, validated_data):
        user_id = validated_data.get('user_id', '')
        email = validated_data.get('email', '').strip()
        password = validated_data.get('password', '').strip()
        confirm_password = validated_data.get('confirm_password', '').strip()
        op = OperationLogger("AuthCommand.ConfirmResetPassword", user_id=user_id, email=email)
        op.start()
        try:
            if password != confirm_password:
                op.fail(f"[AuthCommand.ConfirmResetPassword] Password mismatch for user_id: {user_id}")
                return BaseResultWithData(
                    message="Password and confirm password do not match",
                    data=None,
                    status_code=400
                )
            
            user = User.objects.filter(id=user_id, email=email, is_active=True, is_deleted=False).first()
            
            if not user:
                op.fail(f"[AuthCommand.ConfirmResetPassword] Invalid user or inactive account: {user_id}")
                return BaseResultWithData(
                    message="Account has issues. Please contact support for assistance.",
                    data=None,
                    status_code=400
                )
            
            user.set_password(password)
            user.save()

            try:
                background_task_send_notification_email.delay(user.email, user.first_name)
            except OperationalError as e:
                op.success("Password reset successful, but failed to queue reset email")
            else:
                op.success("Password reset successful and notification email queued")
            
            return BaseResultWithData(
                message="Password reset successful. You can now log in with your new password.",
                data=None,
                status_code=200
            )
            
        except Exception as e:
            op.fail("Error resetting password", exc=e)
            return BaseResultWithData(
                message=f"Error resetting password: {str(e)}",
                data=None,
                status_code=500
            )
            
    
    @staticmethod
    def ChangePassword(request, validated_data):
        user = request.user
        op = OperationLogger("AuthCommand.ChangePassword", user_id=getattr(user, 'id', None))
        op.start()
        try:
            current_password = validated_data.get('current_password')
            new_password = validated_data.get('new_password')
            
            if not user.check_password(current_password):
                op.fail(f"[AuthCommand.ChangePassword] Incorrect current password for user_id: {user.id}")
                return BaseResultWithData(
                    message="Current password is incorrect",
                    data=None,
                    status_code=400
                )
            
            if len(new_password) < 8:
                op.fail(f"[AuthCommand.ChangePassword] New password too short for user_id: {user.id}")
                return BaseResultWithData(
                    message="New password must be at least 8 characters long",
                    data=None,
                    status_code=400
                )
            
            user.set_password(new_password)
            user.save()

            try:
                background_task_send_change_password_email.delay(user.email, user.first_name)
            except OperationalError as e:
                op.success("Password changed successfully, but failed to queue change password email")
            else:
                op.success("Password changed successfully and change password email queued")

            return BaseResultWithData(
                message="Password changed successfully",
                data=None,
                status_code=200
            )
            
        except Exception as e:
            op.fail("Error changing password", exc=e)
            return BaseResultWithData(
                message=f"Error changing password: {str(e)}",
                data=None,
                status_code=500
            )

    @staticmethod
    def RefreshToken(request, validated_data):
        """
        Verify refresh token, rotate tokens, and blacklist the old refresh token.
        Returns new access token and new refresh token.
        """
        refresh_token_str = validated_data.get('refresh_token')
        op = OperationLogger("AuthCommand.RefreshToken", refresh_token=refresh_token_str)
        op.start()

        try:
            # 1. Validate the incoming refresh token
            try:
                old_refresh = RefreshToken(refresh_token_str)
            except (TokenError, InvalidToken) as e:
                op.fail(f"Invalid refresh token: {e}")
                return BaseResultWithData(
                    message="Invalid or expired refresh token",
                    data=None,
                    status_code=400
                )

            user_id = old_refresh.payload.get('user_id')
            if not user_id:
                op.fail("Missing user_id in token payload")
                return BaseResultWithData(
                    message="Invalid token payload",
                    data=None,
                    status_code=400
                )

            # 2. Fetch the user (must be verified and active)
            try:
                user = User.objects.get(
                    id=user_id,
                    email_verified=True,
                    is_active=True,
                    is_deleted=False
                )
            except User.DoesNotExist:
                op.fail(f"User {user_id} not found or not eligible")
                return BaseResultWithData(
                    message="User account not found or not verified",
                    data=None,
                    status_code=404
                )

            # 3. Blacklist the old refresh token (if feature enabled)
            if getattr(settings, 'SIMPLE_JWT', {}).get('BLACKLIST_AFTER_ROTATION', False):
                try:
                    old_refresh.blacklist()
                except AttributeError:
                    op.fail("Blacklist method not available – ensure token_blacklist is installed")
                except Exception as e:
                    op.fail(f"Failed to blacklist old token: {e}")

            # 4. Create brand new tokens
            new_refresh = RefreshToken.for_user(user)
            new_access = new_refresh.access_token

            if user.profile_picture and hasattr(user.profile_picture, 'url'):
                profile_pic_url = request.build_absolute_uri(user.profile_picture.url)
            else:
                profile_pic_url = None

            data = {
                'access_token': str(new_access),
                'refresh_token': str(new_refresh),
                'user_id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'profile_pic': profile_pic_url,
                'point_bal': user.points if user.points else 0,
                'trusting_score': user.average_rating,
                'is_email_verified': user.email_verified,
                'is_hall_verified' : user.hall_verified
            }

            op.success("Token refreshed and old token blacklisted")
            return BaseResultWithData(
                message="Token refreshed successfully",
                data=data,
                status_code=200
            )

        except Exception as e:
            op.fail("Unexpected error during token refresh", exc=e)
            logger.exception(f"Refresh token error: {e}")
            return BaseResultWithData(
                message="Unable to refresh token. Please login again.",
                data=None,
                status_code=500
            )