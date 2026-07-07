from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


class EmailHelper:    
    @staticmethod
    def send_email(subject, message, recipient_list, html_message=None, fail_silently=False):
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,           
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_list,
            )
            if html_message:
                email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=fail_silently)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_verification_email(email, first_name, verification_link):
        print("link is here" ,verification_link)

        try:
            context = {
                'first_name': first_name,
                'verification_link': verification_link,
            }

            html_content = render_to_string('verification_email.html', context)

            plain_text  = f"""
Hello {first_name},

Welcome to Campus Connect! Please verify your email by clicking the link below:

{verification_link}

This link will expire in 10 minutes.

This link is unique and can only be used once. If you didn't create this account, please ignore this email.

Best regards,
Campus Connect Team
            """
            
            # Send email
            subject = "Verify Your Campus Connect Email"
            return EmailHelper.send_email(
                subject=subject,
                message=plain_text,
                recipient_list=[email],
                html_message = html_content,
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
        
    @staticmethod
    def send_report_received_email(email, first_name, issue_type):
        try:
            subject = "We Have Received Your Report"
            message = f"""
Hello {first_name},
Thank you for submitting your report regarding "{issue_type}". We have received your report and our team will review it within 48 hours. We appreciate your help in keeping our community safe and welcoming.
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
            print(f"Error sending report received email: {str(e)}")
            return False
        

    @staticmethod
    def send_lost_item_claim_email(item_name, founder_email, founder_full_name,
                                   approval_link, claimer_full_name, answer1, answer2):

        subject = f"Someone wants to claim your lost item: {item_name}"

        message = f"""
Hello {founder_full_name},

A student named {claimer_full_name} has submitted a claim for the item "{item_name}" that you reported lost.

Their answers to your verification questions:
Q1: {answer1}
Q2: {answer2}

If you believe this is the rightful owner, please approve the claim by visiting the link below:
{approval_link}

If you do not recognise this claim, you can safely ignore this email.

Best regards,
CampusConnect Team
        """.strip()

        try:
            return EmailHelper.send_email(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[founder_email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending report received email: {str(e)}")
            return False
        

    @staticmethod
    def send_founder_details_to_claimer_email(
        item_name,
        founder_email,
        founder_full_name,
        founder_phone,
        claimer_full_name,
        claimer_email
    ):
 
        subject = f"✅ Founder of '{item_name}' approved your claim – here's how to reach them"

        message = f"""
Hello {claimer_full_name},

Good news! The founder of the item "{item_name}" has approved your claim and agreed to share their contact details with you.

You can now reach out to them directly:

📌 Founder's Name: {founder_full_name}
📧 Email: {founder_email}
📞 Phone: {founder_phone or 'Not provided'}

Please contact them as soon as possible to arrange the reunion of the item.

If you have any questions, feel free to contact us.

Best regards,
CampusConnect Team
        """

        try:
            return EmailHelper.send_email(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[claimer_email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending report received email: {str(e)}")
            return False