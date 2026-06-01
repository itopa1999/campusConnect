from celery import shared_task
from django.core.mail import send_mail

from utils.emails_helper import EmailHelper

@shared_task
def background_task_send_verification_email(email, first_name, link):
    EmailHelper.send_verification_email(email, first_name, link)

@shared_task
def background_task_send_password_reset_email(email, first_name, link):
    EmailHelper.send_password_reset_email(email, first_name, link)