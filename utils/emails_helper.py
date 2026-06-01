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
    def send_verification_email(email, first_name, verification_link):
        try:
            subject = "Verify Your Campus Connect Email"
            message = f"""
Hello {first_name},

Welcome to Campus Connect! Please verify your email by clicking the link below:

{verification_link}

This link will expire in 10 minutes.

This link is unique and can only be used once. If you didn't create this account, please ignore this email.

Best regards,
Campus Connect Team
            """
            
            # Send email
            return EmailHelper.send_email(
                subject=subject,
                message=message,
                recipient_list=[email],
                fail_silently=False
            )
        except Exception as e:
            print(f"Error sending verification email: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_email(email, first_name, link):
        try:         
            # Email subject and message
            subject = "Reset Your Campus Connect Password"
            message = f"""
Hello {first_name},

We received a request to reset your password. Click the link below to reset it:

{link}

This link will expire in 10 minutes.

If you didn't request this, please ignore this email.

Best regards,
Campus Connect Team
            """
            
            # Send email
            return EmailHelper.send_email(
                subject=subject,
                message=message,
                recipient_list=[email],
                fail_silently=False
            )
        except Exception as e:
            print(f"Error sending password reset email: {str(e)}")
            return False


    @staticmethod
    def send_password_reset_confirmation_email(email, first_name):
        try:
            subject = "Your Campus Connect Password Has Been Reset"
            message = f"""
Hello {first_name},
Your password has been successfully reset. If you did not perform this action, please contact our support team immediately.
Best regards,
Campus Connect Team
            """
            return EmailHelper.send_email(
                subject=subject,
                message=message,
                recipient_list=[email],
                fail_silently=False
            )
        except Exception as e:
            print(f"Error sending password reset confirmation email: {str(e)}")
            return False
        

    @staticmethod
    def send_account_verification_success_email(email, first_name):
        try:
            subject = "Your Campus Connect Account Has Been Verified"
            message = f"""
Hello {first_name},

Your account has been successfully verified. You can now log in to your Campus Connect account.

Best regards,
Campus Connect Team
            """
            return EmailHelper.send_email(
                subject=subject,
                message=message,
                recipient_list=[email],
                fail_silently=False
            )
        except Exception as e:
            print(f"Error sending account verification success email: {str(e)}")
            return False
        
    @staticmethod
    def send_password_change_confirmation_email(email, first_name):
        try:
            subject = "Your Campus Connect Password Has Been Changed"
            message = f"""
Hello {first_name},
Your password has been successfully changed. If you did not perform this action, please contact our support team immediately.
Best regards,
Campus Connect Team
            """
            return EmailHelper.send_email(
                subject=subject,
                message=message,
                recipient_list=[email],
                fail_silently=False
            )
        except Exception as e:
            print(f"Error sending password change confirmation email: {str(e)}")
            return False
        
