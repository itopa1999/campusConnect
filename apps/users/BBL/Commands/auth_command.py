from apps.campus.models import Favourite
from apps.users.BBL.Commands.account_command import AccountCommand
from apps.users.models import Notification, TwoFactorMethod, User
from apps.users.utils import prepare_2fa_challenge, revoke_all_user_tokens
from utils.Tasks.backgroundTask import background_task_send_change_password_email, background_task_send_notification_email, background_task_send_password_reset_email
from utils.base_result import BaseResultWithData
from rest_framework_simplejwt.tokens import RefreshToken
from celery.exceptions import OperationalError
from utils.log_helpers import logger, OperationLogger
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.conf import settings

from utils.enums import NotificationEnum, PlatformEnum, TokenTypeEnum
from utils.helpers import create_notification, is_email_verified

class AuthCommand:    
    @staticmethod
    def Execute(request, validated_data) -> BaseResultWithData:
        email = validated_data.get('email')
        password = validated_data.get('password')
        platform = validated_data.get('platform')
        op = OperationLogger(f"AuthCommand.Execute login for user: {email}", email=email)
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
            allowed_values = [choice[0] for choice in PlatformEnum.choices()]
            if platform not in allowed_values:
                op.fail(f"[AuthCommand.Execute] invalid platform for email: {email}")
                return BaseResultWithData(
                    message=f"Platform must be one of: {', '.join(allowed_values)}",
                    status_code=400
                )
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
                op.fail(f"[AuthCommand.Execute] Email not verified for user: {user.first_name or user.email}")
                return BaseResultWithData(
                    message="Email not verified. Please check your inbox for the verification email.",
                    data=None,
                    status_code=400
                )

            if not user.is_active:
                op.fail(f"[AuthCommand.Execute] Inactive account login attempt: user={user.first_name or user.email}")
                return BaseResultWithData(
                    message="Your account has been deactivated. Please contact support for assistance.",
                    data=None,
                    status_code=400
                )
            
            try:
                status = prepare_2fa_challenge(user)
            except ValueError as e:
                op.fail(f"2FA challenge preparation failed: {str(e)}")
                return BaseResultWithData(
                    message=str(e),
                    data=None,
                    status_code=500
                )
            if status['requires_2fa']:
                active_method = status['active_method']
                data = {
                    "requires_2fa": True,
                    "user_id": user.id,
                    "active_method": active_method,
                    "platform": platform,
                }
                if status.get('otp_sent'):
                    data['otp_sent'] = True
                return BaseResultWithData(
                    message=f"Enter your {active_method} code",
                    data=data,
                    status_code=200
                )
            
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            op.success(f"Login successful for user: {user.first_name or user.email}")
            
            if user.profile_picture and hasattr(user.profile_picture, 'url'):
                profile_pic_url = request.build_absolute_uri(user.profile_picture.url)
            else:
                profile_pic_url = None


            total_favourites = Favourite.objects.filter(user=user).count()

            has_unread_notifications = Notification.objects.filter(
                user=user,
                is_read=False
            ).exists()
            
            
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
                    "total_favourites": total_favourites,
                    "has_unread_notifications": has_unread_notifications,
                    }
                },
                status_code=200
            )
            
        except Exception as e:
            op.fail(f"Error during login for email: {email}", exc=e)
            return BaseResultWithData(
                message=f"Error during login: {str(e)}",
                data=None,
                status_code=500
            )


    @staticmethod
    def ForgotPassword(request, validated_data)-> BaseResultWithData:
        email = validated_data.get('email')
        op = OperationLogger(f"AuthCommand.ForgotPassword for user: {email}", email=email)
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
                op.fail(f"[AuthCommand.ForgotPassword] Email not verified for user: {user.first_name or user.email}")
                return BaseResultWithData(
                    message="Email not verified.",
                    data=None,
                    status_code=400
                )
            
            verification_token = AccountCommand._create_verification_token(user, token_type=TokenTypeEnum.PASSWORD_RESET.value)
            
            link = f"{request.build_absolute_uri('/user/api/auth/verify-forget-password-email')}?token={verification_token.token}"
            try:
                background_task_send_password_reset_email.delay(user.email, user.first_name, link)
            except OperationalError:
                op.success("Password reset successful, but failed to queue reset email")
            
            op.success(f"Password reset email successfully queued for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="If an account with that email exists, an email containing a new password has been sent",
                data=None,
                status_code=200
            )
            
        except Exception as e:
            op.fail(f"Error processing password reset for email: {email}", exc=e)
            return BaseResultWithData(
                message=f"Error processing password reset: {str(e)}",
                data=None,
                status_code=500
            )
        
    @staticmethod
    def VerifyForgetPasswordEmail(request)-> BaseResultWithData:
        token = request.GET.get('token')
        op = OperationLogger("AuthCommand.VerifyForgetPasswordEmail", token=token)
        op.start()
        try:
            if not token:
                op.fail("[AuthCommand.VerifyForgetPasswordEmail] Token is required")
                return BaseResultWithData(
                    message="Token is required",
                    data=None,
                    status_code=400
                )
            is_valid, result = AccountCommand._verify_token(token, token_type=TokenTypeEnum.PASSWORD_RESET.value)
            if not is_valid:
                op.fail(f"[AuthCommand.VerifyForgetPasswordEmail] Token: {token} verification failed: {result}")
                return BaseResultWithData(
                    message=result,
                    data=None,
                    status_code=400
                )
            
            verification_token = result
            user = verification_token.user
            op.success(f"Password reset token: {token} verified for user: {user.first_name or user.email}")
            
            return BaseResultWithData(
                message="Link verified successful.",
                data={
                    'user_id': user.id,
                    'email': user.email
                },
                status_code=200
            )
            
        except Exception as e:
            op.fail(f"Error verifying password reset token: {token}", exc=e)
            return BaseResultWithData(
                message=f"Error verifying password reset token: {str(e)}",
                data=None,
                status_code=500
            )
        
    @staticmethod
    def ConfirmResetPassword(request, validated_data)-> BaseResultWithData:
        user_id = validated_data.get('user_id', '')
        email = validated_data.get('email', '').strip()
        password = validated_data.get('password', '').strip()
        confirm_password = validated_data.get('confirm_password', '').strip()
        op = OperationLogger(f"AuthCommand.ConfirmResetPassword for user: {user_id}", user_id=user_id, email=email)
        op.start()
        try:
            if password != confirm_password:
                op.fail(f"[AuthCommand.ConfirmResetPassword] Password mismatch for user: {user_id} : {email}")
                return BaseResultWithData(
                    message="Password and confirm password do not match",
                    data=None,
                    status_code=400
                )
            
            user = User.objects.filter(id=user_id, email=email, is_active=True, is_deleted=False).first()
            
            if not user:
                op.fail(f"[AuthCommand.ConfirmResetPassword] Invalid user or inactive account: user = {user_id} : {email}")
                return BaseResultWithData(
                    message="Account has issues. Please contact support for assistance.",
                    data=None,
                    status_code=400
                )
            
            user.set_password(password)
            user.save()

            create_notification(
                user=user,
                notification_type=NotificationEnum.ACCOUNT.value,
                title="Password Reset Confirmation",
                message="Your password has been reset successfully",
            )

            try:
                background_task_send_notification_email.delay(user.email, user.first_name)
            except OperationalError:
                op.success("Password reset successful, but failed to queue reset email")
            
            op.success(f"Password reset successful and notification email queued for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Password reset successful. You can now log in with your new password.",
                data=None,
                status_code=200
            )
            
        except Exception as e:
            op.fail(f"Error resetting password for user: {user_id} : {email}", exc=e)
            return BaseResultWithData(
                message=f"Error resetting password: {str(e)}",
                data=None,
                status_code=500
            )
            
    
    @staticmethod
    def ChangePassword(request, validated_data)-> BaseResultWithData:
        user = request.user
        op = OperationLogger(f"AuthCommand.ChangePassword for user: {user.first_name or user.email}", user_id=getattr(user, 'id', None))
        op.start()
        try:
            current_password = validated_data.get('current_password')
            new_password = validated_data.get('new_password')
            confirm_password = validated_data.get('confirm_password')

            if new_password != confirm_password:
                op.fail(f"[AuthCommand.ChangePassword] Password confirmation mismatch for user: {user.first_name or user.email}")
                return BaseResultWithData(
                    message="New password and confirmation do not match",
                    data=None,
                    status_code=400
                )

            if user.check_password(new_password):
                op.fail(f"[AuthCommand.ChangePassword] New password is same as current for user: {user.first_name or user.email}")
                return BaseResultWithData(
                    message="New password cannot be the same as your current password",
                    data=None,
                    status_code=400
                )
            
            if not user.check_password(current_password):
                op.fail(f"[AuthCommand.ChangePassword] Incorrect current password for user: {user.first_name or user.email}")
                return BaseResultWithData(
                    message="Current password is incorrect",
                    data=None,
                    status_code=400
                )
            
            if len(new_password) < 8:
                op.fail(f"[AuthCommand.ChangePassword] New password too short for user: {user.first_name or user.email}")
                return BaseResultWithData(
                    message="New password must be at least 8 characters long",
                    data=None,
                    status_code=400
                )
            
            user.set_password(new_password)
            user.save()

            revoke_all_user_tokens(user)

            create_notification(
                user=user,
                notification_type=NotificationEnum.ACCOUNT.value,
                title="Password Change Confirmation",
                message="Your password has been changed successfully",
                action_url="/student/profile.html"
            )

            try:
                background_task_send_change_password_email.delay(user.email, user.first_name)
            except OperationalError:
                op.success("Password changed successfully, but failed to queue change password email")
                
            op.success(f"Password changed successfully and change password email queued for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Password changed successfully",
                data=None,
                status_code=200
            )
            
        except Exception as e:
            op.fail(f"Error changing password for user: {user.first_name or user.email}", exc=e)
            return BaseResultWithData(
                message=f"Error changing password: {str(e)}",
                data=None,
                status_code=500
            )

    @staticmethod
    def RefreshToken(request, validated_data)-> BaseResultWithData:
        """
        Verify refresh token, rotate tokens, and blacklist the old refresh token.
        Returns new access token and new refresh token.
        """
        op = OperationLogger("AuthCommand.RefreshToken", data=validated_data)
        op.start()
        platform = validated_data.get('platform')
        refresh_token_str = None
        if platform == PlatformEnum.WEB.value:
            refresh_token_str = request.COOKIES.get('refresh_token')                
        else:
            refresh_token_str = validated_data.get('refresh_token')
        if not refresh_token_str:
            return BaseResultWithData(
                message= "Refresh token is required.",
                status_code=400
            )
        try:
            # 1. Validate the incoming refresh token
            try:
                old_refresh = RefreshToken(refresh_token_str)
            except (TokenError, InvalidToken) as e:
                op.fail(f"Invalid refresh token {refresh_token_str}: {e}")
                return BaseResultWithData(
                    message="Invalid or expired refresh token",
                    data=None,
                    status_code=400
                )

            user_id = old_refresh.payload.get('user_id')
            if not user_id:
                op.fail(f"Missing user_id in token payload: {refresh_token_str}")
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
                    op.fail("Blacklist method not available")
                except Exception as e:
                    op.fail(f"Failed to blacklist old token {refresh_token_str}: {e}")

            # 4. Create brand new tokens
            new_refresh = RefreshToken.for_user(user)
            new_access = new_refresh.access_token

            if user.profile_picture and hasattr(user.profile_picture, 'url'):
                profile_pic_url = request.build_absolute_uri(user.profile_picture.url)
            else:
                profile_pic_url = None

            total_favourites = Favourite.objects.filter(user=user).count()
                    
            has_unread_notifications = Notification.objects.filter(
                user=user,
                is_read=False
            ).exists()

            data = {
                'access_token': str(new_access),
                'refresh_token': str(new_refresh),
                'user': {
                    "user_id": user.id,
                    "email": user.email,
                    "profile_pic": profile_pic_url,
                    "point_bal": user.points or 0,
                    "trusting_score": user.average_rating,
                    "is_student_id_verified": user.student_id_verified,
                    "is_hall_verified": user.hall_verified,
                    "total_favourites": total_favourites,
                    "has_unread_notifications": has_unread_notifications,
                }
            }

            op.success(f"Token refreshed and old token blacklisted for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Token refreshed successfully",
                data=data,
                status_code=200
            )

        except Exception as e:
            op.fail(f"Unexpected error during token refresh {refresh_token_str}", exc=e)
            logger.exception(f"Refresh token error: {e}")
            return BaseResultWithData(
                message="Unable to refresh token. Please login again.",
                data=None,
                status_code=500
            )