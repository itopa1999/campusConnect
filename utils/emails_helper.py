from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from apps.campus.models import Listing
from utils.log_helpers import OperationLogger
from django.utils import timezone
User = get_user_model()


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
        op = OperationLogger("EmailHelper.send_verification_email", email=email)
        op.start()
        try:
            base_url = settings.BASE_FRONTEND_URL
            context = {
                'first_name': first_name,
                'verification_link': verification_link,
                'base_url': base_url,
            }
            html_content = render_to_string('emails/verification_email.html', context)
            plain_text = f"""
Hello {first_name},

Welcome to Campus Connect! Please verify your email by clicking the link below:

{verification_link}

This link will expire in 10 minutes.

This link is unique and can only be used once. If you didn't create this account, please ignore this email.

Best regards,
Campus Connect Team
            """
            subject = "Verify Your Campus Connect Email"
            success = EmailHelper.send_email(
                subject=subject,
                message=plain_text,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False
            )
            if success:
                op.success(f"Verification email sent to {email}")
            else:
                op.fail(f"Failed to send verification email to {email}")
            return success
        except Exception as e:
            op.fail(f"Error sending verification email: {str(e)}")
            return False

    @staticmethod
    def send_password_reset_email(email, first_name, reset_link):
        op = OperationLogger("EmailHelper.send_password_reset_email", email=email)
        op.start()
        try:
            base_url = settings.BASE_FRONTEND_URL
            context = {
                'first_name': first_name,
                'reset_link': reset_link,
                'base_url': base_url,
            }
            html_content = render_to_string('emails/password_reset_email.html', context)
            plain_text = f"""
Hello {first_name},

We received a request to reset your password. Click the link below to reset it:

{reset_link}

This link will expire in 10 minutes.

If you didn't request this, please ignore this email.

Best regards,
Campus Connect Team
            """
            subject = "Reset Your Campus Connect Password"
            success = EmailHelper.send_email(
                subject=subject,
                message=plain_text,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False
            )
            if success:
                op.success(f"Password reset email sent to {email}")
            else:
                op.fail(f"Failed to send password reset email to {email}")
            return success
        except Exception as e:
            op.fail(f"Error sending password reset email: {str(e)}")
            return False

    @staticmethod
    def send_password_reset_confirmation_email(email, first_name):
        op = OperationLogger("EmailHelper.send_password_reset_confirmation_email", email=email)
        op.start()
        try:
            base_url = settings.BASE_FRONTEND_URL
            context = {
                'first_name': first_name,
                'base_url': base_url,
            }
            html_content = render_to_string('emails/password_reset_confirmation_email.html', context)
            plain_text = f"""
Hello {first_name},
Your password has been successfully reset. If you did not perform this action, please contact our support team immediately.
Best regards,
Campus Connect Team
            """
            subject = "Your Campus Connect Password Has Been Reset"
            success = EmailHelper.send_email(
                subject=subject,
                message=plain_text,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False
            )
            if success:
                op.success(f"Password reset confirmation email sent to {email}")
            else:
                op.fail(f"Failed to send password reset confirmation email to {email}")
            return success
        except Exception as e:
            op.fail(f"Error sending password reset confirmation email: {str(e)}")
            return False

    @staticmethod
    def send_account_verification_success_email(email, first_name):
        op = OperationLogger("EmailHelper.send_account_verification_success_email", email=email)
        op.start()
        try:
            base_url = settings.BASE_FRONTEND_URL
            login_url = f"{base_url}/login"  # adjust to your login URL
            context = {
                'first_name': first_name,
                'login_url': login_url,
                'base_url': base_url,
            }
            html_content = render_to_string('emails/account_verification_success_email.html', context)
            plain_text = f"""
Hello {first_name},

Your account has been successfully verified. You can now log in to your Campus Connect account.

Login here: {login_url}

Best regards,
Campus Connect Team
            """
            subject = "Your Campus Connect Account Has Been Verified"
            success = EmailHelper.send_email(
                subject=subject,
                message=plain_text,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False
            )
            if success:
                op.success(f"Account verification success email sent to {email}")
            else:
                op.fail(f"Failed to send account verification success email to {email}")
            return success
        except Exception as e:
            op.fail(f"Error sending account verification success email: {str(e)}")
            return False

    @staticmethod
    def send_password_change_confirmation_email(email, first_name):
        op = OperationLogger("EmailHelper.send_password_change_confirmation_email", email=email)
        op.start()
        try:
            base_url = settings.BASE_FRONTEND_URL
            context = {
                'first_name': first_name,
                'base_url': base_url,
            }
            html_content = render_to_string('emails/password_change_confirmation_email.html', context)
            plain_text = f"""
Hello {first_name},
Your password has been successfully changed. If you did not perform this action, please contact our support team immediately.
Best regards,
Campus Connect Team
            """
            subject = "Your Campus Connect Password Has Been Changed"
            success = EmailHelper.send_email(
                subject=subject,
                message=plain_text,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False
            )
            if success:
                op.success(f"Password change confirmation email sent to {email}")
            else:
                op.fail(f"Failed to send password change confirmation email to {email}")
            return success
        except Exception as e:
            op.fail(f"Error sending password change confirmation email: {str(e)}")
            return False

    @staticmethod
    def send_report_received_email(email, first_name, issue_type):
        op = OperationLogger("EmailHelper.send_report_received_email", email=email)
        op.start()
        try:
            base_url = settings.BASE_FRONTEND_URL
            context = {
                'first_name': first_name,
                'issue_type': issue_type,
                'base_url': base_url,
            }
            html_content = render_to_string('emails/report_received_email.html', context)
            plain_text = f"""
Hello {first_name},
Thank you for submitting your report regarding "{issue_type}". We have received your report and our team will review it within 48 hours. We appreciate your help in keeping our community safe and welcoming.
Best regards,
Campus Connect Team
            """
            subject = "We Have Received Your Report"
            success = EmailHelper.send_email(
                subject=subject,
                message=plain_text,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False
            )
            if success:
                op.success(f"Report received email sent to {email}")
            else:
                op.fail(f"Failed to send report received email to {email}")
            return success
        except Exception as e:
            op.fail(f"Error sending report received email: {str(e)}")
            return False

    @staticmethod
    def send_lost_item_claim_email(item_name, founder_email, founder_full_name, verification1, verification2,
                                approval_link, claimer_full_name, answer1, answer2):
        op = OperationLogger("EmailHelper.send_lost_item_claim_email", founder_email=founder_email)
        op.start()
        try:
            base_url = settings.BASE_FRONTEND_URL
            context = {
                'item_name': item_name,
                'founder_full_name': founder_full_name,
                'claimer_full_name': claimer_full_name,
                'verification1': verification1,
                'verification2': verification2,
                'answer1': answer1,
                'answer2': answer2,
                'approval_link': approval_link,
                'base_url': base_url,
            }
            html_content = render_to_string('emails/lost_item_claim_email.html', context)
            plain_text = f"""
    Hello {founder_full_name},

    A student named {claimer_full_name} has submitted a claim for the item "{item_name}" that you reported lost.

    Their answers to your verification questions:
    Verification Question 1: {verification1}
    Answer: {answer1}
    Verification Question 2: {verification2}
    Answer: {answer2}

    If you believe this is the rightful owner, please approve the claim by visiting the link below:
    {approval_link}

    If you do not recognise this claim, you can safely ignore this email.

    Best regards,
    CampusConnect Team
            """
            subject = f"Someone wants to claim your lost item: {item_name}"
            success = EmailHelper.send_email(
                subject=subject,
                message=plain_text,
                recipient_list=[founder_email],
                html_message=html_content,
                fail_silently=False
            )
            if success:
                op.success(f"Lost item claim email sent to {founder_email}")
            else:
                op.fail(f"Failed to send lost item claim email to {founder_email}")
            return success
        except Exception as e:
            op.fail(f"Error sending lost item claim email: {str(e)}")
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
        op = OperationLogger("EmailHelper.send_founder_details_to_claimer_email", claimer_email=claimer_email)
        op.start()
        try:
            base_url = settings.BASE_FRONTEND_URL
            context = {
                'item_name': item_name,
                'founder_full_name': founder_full_name,
                'founder_email': founder_email,
                'founder_phone': founder_phone,
                'claimer_full_name': claimer_full_name,
                'base_url': base_url,
            }
            html_content = render_to_string('emails/founder_details_to_claimer_email.html', context)
            plain_text = f"""
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
            subject = f"✅ Founder of '{item_name}' approved your claim – here's how to reach them"
            success = EmailHelper.send_email(
                subject=subject,
                message=plain_text,
                recipient_list=[claimer_email],
                html_message=html_content,
                fail_silently=False
            )
            if success:
                op.success(f"Founder details email sent to {claimer_email}")
            else:
                op.fail(f"Failed to send founder details email to {claimer_email}")
            return success
        except Exception as e:
            op.fail(f"Error sending founder details email: {str(e)}")
            return False

    @staticmethod
    def send_expired_lisiting_emails(ids):
        op = OperationLogger("EmailHelper.send_expired_lisiting_emails", ids=ids)
        op.start()
        try:
            listings = Listing.objects.filter(id__in=ids, is_deleted=False).select_related('user')
            if not listings:
                op.fail("No listings found for the provided IDs")
                return

            user_listings = {}
            for listing in listings:
                user_listings.setdefault(listing.user, []).append(listing)

            base_url = settings.BASE_FRONTEND_URL
            dashboard_url = f"{base_url}/student/main.html#listings"

            sent_count = 0
            for user, user_listings_list in user_listings.items():
                titles = [l.title for l in user_listings_list]
                context = {
                    'first_name': user.first_name or user.email,
                    'titles': titles,
                    'base_url': base_url,
                    'dashboard_url': dashboard_url,
                }
                html_content = render_to_string('emails/expired_listings.html', context)
                plain_text = f"""
Hello {user.first_name or user.email},

The following listing(s) on CampusConnect have expired and are no longer visible:

{', '.join(titles)}

You can reactivate each listing for 1 point. Log in to your account to manage your listings.

Visit: {dashboard_url}

Best regards,
CampusConnect Team
                """
                success = EmailHelper.send_email(
                    subject="Your listings have expired on CampusConnect",
                    message=plain_text,
                    recipient_list=[user.email],
                    html_message=html_content,
                    fail_silently=False
                )
                if success:
                    sent_count += 1
                    op.success(f"Expired email sent to {user.email} for {len(titles)} listing(s)")
                else:
                    op.fail(f"Failed to send expired email to {user.email}")

            op.success(f"Sent {sent_count} expired email(s) for {len(listings)} listing(s)")
            return True
        except Exception as e:
            op.fail(f"Error in send_expired_lisiting_emails: {str(e)}")
            return False

    @staticmethod
    def send_auto_reactivate_listing_emails(ids):
        op = OperationLogger("EmailHelper.send_auto_reactivate_listing_emails", ids=ids)
        op.start()
        try:
            listings = Listing.objects.filter(id__in=ids, is_deleted=False).select_related('user')
            if not listings:
                op.fail("No listings found for the provided IDs")
                return

            user_listings = {}
            for listing in listings:
                user_listings.setdefault(listing.user, []).append(listing)

            base_url = settings.BASE_FRONTEND_URL
            dashboard_url = f"{base_url}/student/main.html#listings"

            sent_count = 0
            for user, user_listings_list in user_listings.items():
                titles = [l.title for l in user_listings_list]
                context = {
                    'first_name': user.first_name or user.email,
                    'titles': titles,
                    'base_url': base_url,
                    'dashboard_url': dashboard_url,
                }
                html_content = render_to_string('emails/auto_reactivated_listings.html', context)
                plain_text = f"""
Hello {user.first_name or user.email},

The following listing(s) on CampusConnect have been automatically reactivated because they expired and you had auto-reactivation enabled:

{', '.join(titles)}

1 point was deducted from your balance for each listing.

They are now active for another 30 days.

Manage your listings: {dashboard_url}

Best regards,
CampusConnect Team
                """
                success = EmailHelper.send_email(
                    subject="Your listings have been auto-reactivated on CampusConnect",
                    message=plain_text,
                    recipient_list=[user.email],
                    html_message=html_content,
                    fail_silently=False
                )
                if success:
                    sent_count += 1
                    op.success(f"Auto-reactivation email sent to {user.email} for {len(titles)} listing(s)")
                else:
                    op.fail(f"Failed to send auto-reactivation email to {user.email}")

            op.success(f"Sent {sent_count} auto-reactivation email(s) for {len(listings)} listing(s)")
            return True
        except Exception as e:
            op.fail(f"Error in send_auto_reactivate_listing_emails: {str(e)}")
            return False
        

    @staticmethod
    def send_banner_expired_emails(ids):
        """
        Send email notifications to users whose banner promotions have expired.
        """
        op = OperationLogger("EmailHelper.send_banner_expired_emails", ids=ids)
        op.start()
        try:
            listings = Listing.objects.filter(id__in=ids, is_deleted=False).select_related('user')
            if not listings:
                op.fail("No listings found for the provided IDs")
                return

            user_listings = {}
            for listing in listings:
                user_listings.setdefault(listing.user, []).append(listing)

            base_url = settings.BASE_FRONTEND_URL
            dashboard_url = f"{base_url}/student/main.html#listings"

            sent_count = 0
            for user, user_listings_list in user_listings.items():
                titles = [l.title for l in user_listings_list]
                context = {
                    'first_name': user.first_name or user.email,
                    'titles': titles,
                    'base_url': base_url,
                    'dashboard_url': dashboard_url,
                }
                html_content = render_to_string('emails/banner_expired_email.html', context)
                plain_text = f"""
    Hello {user.first_name or user.email},

    The banner promotion for the following listing(s) on CampusConnect has expired:

    {', '.join(titles)}

    You can renew the banner promotion from your listing management page.

    Manage your listings: {dashboard_url}

    Best regards,
    CampusConnect Team
                """
                success = EmailHelper.send_email(
                    subject="Your banner promotions have expired on CampusConnect",
                    message=plain_text,
                    recipient_list=[user.email],
                    html_message=html_content,
                    fail_silently=False
                )
                if success:
                    sent_count += 1
                    op.success(f"Banner expired email sent to {user.email} for {len(titles)} listing(s)")
                else:
                    op.fail(f"Failed to send banner expired email to {user.email}")

            op.success(f"Sent {sent_count} banner expired email(s) for {len(listings)} listing(s)")
            return True
        except Exception as e:
            op.fail(f"Error in send_banner_expired_emails: {str(e)}")
            return False

    @staticmethod
    def send_hot_sales_expired_emails(ids):
        """
        Send email notifications to users whose Hot Sales promotions have expired.
        """
        op = OperationLogger("EmailHelper.send_hot_sales_expired_emails", ids=ids)
        op.start()
        try:
            listings = Listing.objects.filter(id__in=ids, is_deleted=False).select_related('user')
            if not listings:
                op.fail("No listings found for the provided IDs")
                return

            user_listings = {}
            for listing in listings:
                user_listings.setdefault(listing.user, []).append(listing)

            base_url = settings.BASE_FRONTEND_URL
            dashboard_url = f"{base_url}/student/main.html#listings"

            sent_count = 0
            for user, user_listings_list in user_listings.items():
                titles = [l.title for l in user_listings_list]
                context = {
                    'first_name': user.first_name or user.email,
                    'titles': titles,
                    'base_url': base_url,
                    'dashboard_url': dashboard_url,
                }
                html_content = render_to_string('emails/hot_sales_expired_email.html', context)
                plain_text = f"""
    Hello {user.first_name or user.email},

    The Hot Sales promotion for the following listing(s) on CampusConnect has expired:

    {', '.join(titles)}

    You can renew the Hot Sales promotion from your listing management page.

    Manage your listings: {dashboard_url}

    Best regards,
    CampusConnect Team
                """
                success = EmailHelper.send_email(
                    subject="Your Hot Sales promotions have expired on CampusConnect",
                    message=plain_text,
                    recipient_list=[user.email],
                    html_message=html_content,
                    fail_silently=False
                )
                if success:
                    sent_count += 1
                    op.success(f"Hot Sales expired email sent to {user.email} for {len(titles)} listing(s)")
                else:
                    op.fail(f"Failed to send Hot Sales expired email to {user.email}")

            op.success(f"Sent {sent_count} Hot Sales expired email(s) for {len(listings)} listing(s)")
            return True
        except Exception as e:
            op.fail(f"Error in send_hot_sales_expired_emails: {str(e)}")
            return False


    @staticmethod
    def send_2fa_otp_email(email, first_name, otp):
        """
        Send a 2FA OTP email to the user.
        """
        op = OperationLogger(f"EmailHelper.send_2fa_otp_email for {email}")
        op.start()
        try:
            base_url = settings.BASE_FRONTEND_URL
            context = {
                'first_name': first_name or 'Student',
                'otp': otp,
                'base_url': base_url,
            }
            html_content = render_to_string('emails/2fa_otp_email.html', context)
            plain_text = f"""
    Hello {first_name or 'Student'},

    Your one-time verification code for CampusConnect is:

    {otp}

    This code expires in 3 minutes and can only be used once.

    If you didn't request this, please ignore this email.

    Best regards,
    CampusConnect Team
    """
            success = EmailHelper.send_email(
                subject="Your CampusConnect 2FA Code",
                message=plain_text,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False
            )
            if success:
                op.success(f"2FA OTP email sent to {email}")
            else:
                op.fail(f"Failed to send 2FA OTP email to {email}")
            return success
        except Exception as e:
            op.fail(f"Error sending 2FA OTP email: {str(e)}")
            return False


    @staticmethod
    def send_login_notification_email(email, first_name):
        """
        Send a login notification email to the user.
        """
        op = OperationLogger(f"EmailHelper.send_login_notification_email for {email}")
        op.start()
        try:
            base_url = settings.BASE_FRONTEND_URL
            context = {
                'first_name': first_name or 'Student',
                'base_url': base_url,
                'login_time': timezone.now().strftime("%B %d, %Y at %I:%M %p"),
            }
            html_content = render_to_string('emails/login_notification_email.html', context)
            plain_text = f""" 
Hello {first_name or 'Student'},
We noticed a login to your CampusConnect account. If this was you, no action is needed. If you did not log in, please secure your account immediately.
Best regards,
CampusConnect Team
            """
            success = EmailHelper.send_email(
                subject="Login Notification for Your CampusConnect Account",
                message=plain_text,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False
            )
            if success:
                op.success(f"Login notification email sent to {email}")
            else:
                op.fail(f"Failed to send login notification email to {email}")
            return success
        except Exception as e:
            op.fail(f"Error sending login notification email: {str(e)}")
            return False