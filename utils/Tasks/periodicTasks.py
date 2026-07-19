from celery import shared_task
from utils.periodic_task_helper import PeriodTasksHelper


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5,
)
def check_expired_listings(self):
    PeriodTasksHelper.process_check_expired_listings()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5,
)
def check_banner_ads_expired_listings(self):
    PeriodTasksHelper.process_check_banner_ads_expired_listings()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5,
)
def check_hot_sales_ads_expired_listings(self):
    PeriodTasksHelper.process_check_hot_sales_ads_expired_listings()


# TODO 1. email for reminder for listing that we expires 3-5 days. 

