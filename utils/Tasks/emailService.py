from celery import shared_task
from django.core.mail import send_mail

from utils.emails_helper import EmailHelper

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 10},
)
def background_task_send_verification_email(self, email, first_name, link):
    EmailHelper.send_verification_email(email, first_name, link)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 10},
)
def background_task_send_password_reset_email(self, email, first_name, link):
    EmailHelper.send_password_reset_email(email, first_name, link)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 10},
)
def background_task_send_notification_email(self, email, first_name):
    EmailHelper.send_password_reset_confirmation_email(email, first_name)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 10},
)
def background_task_send_account_verify_email(self, email, first_name):
    EmailHelper.send_account_verification_success_email(email, first_name)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 10},
)
def background_task_send_change_password_email(self, email, first_name):
    EmailHelper.send_password_change_confirmation_email(email, first_name)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 10},
)
def background_task_send_report_recieved_email(self, email, first_name, issue_type):
    EmailHelper.send_report_received_email(email, first_name, issue_type)