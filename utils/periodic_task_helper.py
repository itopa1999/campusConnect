# periodic_task_helper.py

from django.db import transaction
from django.utils import timezone
from apps.campus.models import Listing
from apps.users.models import Notification, User
# from utils.Tasks.backgroundTask import background_task_send_auto_reactivate_listing_emails, background_task_send_banner_expired_emails, background_task_send_expired_listing_emails, background_task_send_hot_sales_expired_emails
from utils.constant_helper import ConstantHelper
from utils.enums import ListingStatusTypeEnum, NotificationEnum, PointTransactionTypeEnum
from utils.helpers import UpdatePointsService
from utils.log_helpers import OperationLogger
import datetime

BATCH_SIZE = 1000

class PeriodTasksHelper:
    @staticmethod
    def process_check_expired_listings():
        from utils.Tasks.backgroundTask import background_task_send_expired_listing_emails
        from utils.Tasks.backgroundTask import background_task_send_auto_reactivate_listing_emails
        op = OperationLogger("TaskScheduler.check_expired_listings")
        op.start()

        total_expired = 0
        total_auto_reactivated = 0
        now = timezone.now()

        while True:
            listings = list(
                Listing.objects.select_related("user")
                .filter(
                    status=ListingStatusTypeEnum.ACTIVE.value,
                    is_deleted=False,
                    expires_at__lte=now,
                )[:BATCH_SIZE]
            )

            if not listings:
                break

            # Split into auto and non‑auto
            auto_listings = [l for l in listings if l.auto_reactivate]
            non_auto_listings = [l for l in listings if not l.auto_reactivate]

            # ─── 1. Process non‑auto listings (expire) ───
            if non_auto_listings:
                non_auto_ids = [l.id for l in non_auto_listings]
                with transaction.atomic():
                    Listing.objects.filter(id__in=non_auto_ids).update(
                        status=ListingStatusTypeEnum.EXPIRED.value
                    )
                    notifications = [
                        Notification(
                            user=l.user,
                            notification_type=NotificationEnum.LISTING.value,
                            title="Listing Expired",
                            message=f'Your listing "{l.title}" has expired. Reactivate it with 1 point.',
                            action_url=f"/dash/my-listing-details.html?id={l.id}&title={l.title}",
                        )
                        for l in non_auto_listings
                    ]
                    Notification.objects.bulk_create(notifications, batch_size=500)
                    total_expired += len(non_auto_listings)

                transaction.on_commit(
                    lambda ids=non_auto_ids: background_task_send_expired_listing_emails.delay(ids)
                )

            # ─── 2. Process auto‑reactivate listings ───
            if auto_listings:
                # Collect user points from the fetched objects
                can_reactivate = []
                cannot_reactivate = []
                for listing in auto_listings:
                    # listing.user is already loaded via select_related
                    if listing.user.points >= 1:
                        can_reactivate.append(listing)
                    else:
                        cannot_reactivate.append(listing)

                # ─── 2a. Reactivate those with points ───
                if can_reactivate:
                    ids = [l.id for l in can_reactivate]
                    new_expiry = now + datetime.timedelta(days=30)
                    with transaction.atomic():
                        # Deduct points and create transaction records
                        for listing in can_reactivate:
                            UpdatePointsService.update_points(
                                user=listing.user,
                                points=1,
                                action=ConstantHelper.POINT_SUBTRACTION,
                                transaction_type=PointTransactionTypeEnum.REACTIVATION.value,
                                description=f'Auto-reactivation of listing "{listing.title}"',
                                reference=f"listing_{listing.id}"
                            )
                        # Extend expiry
                        Listing.objects.filter(id__in=ids).update(
                            expires_at=new_expiry
                        )
                        # Notify
                        notifications = [
                            Notification(
                                user=l.user,
                                notification_type=NotificationEnum.LISTING.value,
                                title="Listing Auto‑Reactivated",
                                message=f'Your listing "{l.title}" has been automatically reactivated. 1 point was deducted.',
                                action_url=f"/dash/my-listing-details.html?id={l.id}&title={l.title}",
                            )
                            for l in can_reactivate
                        ]
                        Notification.objects.bulk_create(notifications, batch_size=500)
                        total_auto_reactivated += len(can_reactivate)

                    transaction.on_commit(
                        lambda ids=ids: background_task_send_auto_reactivate_listing_emails.delay(ids)
                    )

                # ─── 2b. Expire those without points ───
                if cannot_reactivate:
                    ids = [l.id for l in cannot_reactivate]
                    with transaction.atomic():
                        Listing.objects.filter(id__in=ids).update(
                            status=ListingStatusTypeEnum.EXPIRED.value
                        )
                        notifications = [
                            Notification(
                                user=l.user,
                                notification_type=NotificationEnum.LISTING.value,
                                title="Auto‑Reactivation Failed",
                                message=f'Your listing "{l.title}" could not be auto‑reactivated due to insufficient points. Please add points and reactivate manually.',
                                action_url=f"/dash/my-listing-details.html?id={l.id}&title={l.title}",
                            )
                            for l in cannot_reactivate
                        ]
                        Notification.objects.bulk_create(notifications, batch_size=500)
                        total_expired += len(cannot_reactivate)

                    transaction.on_commit(
                        lambda ids=ids: background_task_send_expired_listing_emails.delay(ids)
                    )

            if len(listings) < BATCH_SIZE:
                break

        op.success(f"Expired {total_expired} listings, auto‑reactivated {total_auto_reactivated} listings.")
        return f"Expired {total_expired}, auto‑reactivated {total_auto_reactivated} at {timezone.now()}"
    


    @staticmethod
    def process_check_banner_ads_expired_listings():
        """
        Disable banner ads for listings where the banner promotion has expired.
        """
        from utils.Tasks.backgroundTask import background_task_send_banner_expired_emails
        op = OperationLogger("TaskScheduler.process_check_banner_ads_expired_listings")
        op.start()

        total_disabled = 0
        now = timezone.now()

        while True:
            listings = list(
                Listing.objects.select_related("user")
                .filter(
                    status=ListingStatusTypeEnum.ACTIVE.value,
                    is_ads_banner=True,
                    is_deleted=False,
                    is_ads_banner_expires_at__lte=now,
                )[:BATCH_SIZE]
            )

            if not listings:
                break

            with transaction.atomic():
                # Disable the banner flag
                ids = [l.id for l in listings]
                Listing.objects.filter(id__in=ids).update(
                    is_ads_banner=False,
                    is_ads_banner_expires_at=None,
                )

                # Notify users about banner expiry
                notifications = [
                    Notification(
                        user=l.user,
                        notification_type=NotificationEnum.LISTING.value,
                        title="Banner Promotion Expired",
                        message=f'The banner promotion for your listing "{l.title}" has expired. You can renew it from the listing management page.',
                        action_url=f"/dash/my-listing-details.html?id={l.id}&title={l.title}",
                    )
                    for l in listings
                ]
                Notification.objects.bulk_create(notifications, batch_size=500)
                total_disabled += len(listings)

            transaction.on_commit(
                lambda ids=ids: background_task_send_banner_expired_emails.delay(ids)
            )

            op.success(f"Disabled banner for {len(listings)} expired promotions in this batch.")

            if len(listings) < BATCH_SIZE:
                break

        op.success(f"Total banner promotions disabled: {total_disabled}")
        return f"Disabled {total_disabled} expired banner ads at {timezone.now()}"
    


    @staticmethod
    def process_check_hot_sales_ads_expired_listings():
        """
        Disable Hot Sales promotion for listings where the promotion has expired.
        """
        from utils.Tasks.backgroundTask import background_task_send_hot_sales_expired_emails
        op = OperationLogger("TaskScheduler.process_check_hot_sales_ads_expired_listings")
        op.start()

        total_disabled = 0
        now = timezone.now()

        while True:
            listings = list(
                Listing.objects.select_related("user")
                .filter(
                    status=ListingStatusTypeEnum.ACTIVE.value,
                    is_hot_sales=True,
                    is_deleted=False,
                    is_hot_sales_expires_at__lte=now,
                )[:BATCH_SIZE]
            )

            if not listings:
                break

            with transaction.atomic():
                ids = [l.id for l in listings]
                Listing.objects.filter(id__in=ids).update(
                    is_hot_sales=False,
                    is_hot_sales_expires_at=None,
                )

                notifications = [
                    Notification(
                        user=l.user,
                        notification_type=NotificationEnum.LISTING.value,
                        title="Hot Sales Promotion Expired",
                        message=f'The Hot Sales promotion for your listing "{l.title}" has expired. You can renew it from the listing management page.',
                        action_url=f"/dash/my-listing-details.html?id={l.id}&title={l.title}",
                    )
                    for l in listings
                ]
                Notification.objects.bulk_create(notifications, batch_size=500)
                total_disabled += len(listings)

            transaction.on_commit(
                lambda ids=ids: background_task_send_hot_sales_expired_emails.delay(ids)
            )

            op.success(f"Disabled Hot Sales for {len(listings)} expired promotions in this batch.")

            if len(listings) < BATCH_SIZE:
                break

        op.success(f"Total Hot Sales promotions disabled: {total_disabled}")
        return f"Disabled {total_disabled} expired Hot Sales ads at {timezone.now()}"