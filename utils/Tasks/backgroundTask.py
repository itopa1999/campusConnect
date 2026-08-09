from celery import shared_task

from utils.emails_helper import EmailHelper
from utils.task_helper import TaskHelper

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_verification_email(self, email, first_name, link):
    EmailHelper.send_verification_email(email, first_name, link)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_password_reset_email(self, email, first_name, link):
    EmailHelper.send_password_reset_email(email, first_name, link)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_notification_email(self, email, first_name):
    EmailHelper.send_password_reset_confirmation_email(email, first_name)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_account_verify_email(self, email, first_name):
    EmailHelper.send_account_verification_success_email(email, first_name)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_change_password_email(self, email, first_name):
    EmailHelper.send_password_change_confirmation_email(email, first_name)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_report_recieved_email(self, email, first_name, issue_type):
    EmailHelper.send_report_received_email(email, first_name, issue_type)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_lost_item_claim_email(self, item_name, founder_email, founder_full_name, approval_link, verification1, verification2, claimer_full_name, answer1, answer2):
    EmailHelper.send_lost_item_claim_email(item_name, founder_email, founder_full_name, verification1, verification2, approval_link, claimer_full_name, answer1, answer2)
    

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_founder_details_to_claimer_email(self, item_name, founder_email, founder_full_name, founder_phone, claimer_full_name, claimer_email):
    EmailHelper.send_founder_details_to_claimer_email(item_name, founder_email, founder_full_name, founder_phone, claimer_full_name, claimer_email)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_expired_listing_emails(self, ids):
    EmailHelper.send_expired_lisiting_emails(ids)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_auto_reactivate_listing_emails(self, ids):
    EmailHelper.send_auto_reactivate_listing_emails(ids)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_banner_expired_emails(self, ids):
    EmailHelper.send_banner_expired_emails(ids)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_hot_sales_expired_emails(self, ids):
    EmailHelper.send_hot_sales_expired_emails(ids)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_login_notification_email(self, email, first_name):
    EmailHelper.send_login_notification_email(email, first_name)

# 2FA 
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5
)
def background_task_send_2fa_otp_email(self, email, first_name, otp):
    EmailHelper.send_2fa_otp_email(email, first_name, otp)

