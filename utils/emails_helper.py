from django.core.mail import send_mail
from django.conf import settings


class EmailHelper:    
    @staticmethod
    def send_email(subject, message, recipient_list, fail_silently=False):
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=fail_silently,
            )
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_verification_email(user, verification_token, request):
        try:
            verification_link = f"{request.build_absolute_uri('/user/api/auth/verify-email/')}?token={verification_token.token}"
            subject = "Verify Your Campus Connect Email"
            message = f"""
Hello {user.first_name},

Welcome to Campus Connect! Please verify your email by clicking the link below:

{verification_link}

This link is unique and can only be used once. If you didn't create this account, please ignore this email.

Best regards,
Campus Connect Team
            """
            
            # Send email
            return EmailHelper.send_email(
                subject=subject,
                message=message,
                recipient_list=[user.email],
                fail_silently=False
            )
        except Exception as e:
            print(f"Error sending verification email: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_email(user, reset_token, request):
        try:
            # Build password reset URL
            reset_url = f"{request.build_absolute_uri('/api/users/reset-password/')}?token={reset_token}"
            
            # Email subject and message
            subject = "Reset Your Campus Connect Password"
            message = f"""
Hello {user.first_name},

We received a request to reset your password. Click the link below to reset it:

{reset_url}

This link will expire in 24 hours.

If you didn't request this, please ignore this email.

Best regards,
Campus Connect Team
            """
            
            # Send email
            return EmailHelper.send_email(
                subject=subject,
                message=message,
                recipient_list=[user.email],
                fail_silently=False
            )
        except Exception as e:
            print(f"Error sending password reset email: {str(e)}")
            return False
