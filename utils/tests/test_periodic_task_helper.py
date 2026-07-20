import datetime
from unittest.mock import MagicMock, call

import pytest
from django.utils import timezone

from utils.constant_helper import ConstantHelper
from utils.enums import ListingStatusType, NotificationEnum, PointTransactionTypeEnum
from utils.helpers import UpdatePointsService
from utils.periodic_task_helper import PeriodTasksHelper, BATCH_SIZE
from apps.users.models import User


@pytest.fixture
def fixed_now():
    """Fixed current time for predictable expiry checks."""
    return timezone.datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.UTC)


@pytest.fixture
def mock_timezone_now(mocker, fixed_now):
    """Freeze timezone.now() to fixed_now for all tests."""
    return mocker.patch("django.utils.timezone.now", return_value=fixed_now)


@pytest.fixture
def mock_listing(mocker):
    """
    Return a factory that creates mock Listing objects with a real User instance
    (so that Django model checks, like _state, pass).
    """
    def _factory(
        listing_id,
        title="Test Listing",
        auto_reactivate=False,
        points=5,
        status=ListingStatusType.ACTIVE.value,
        is_deleted=False,
        expires_at=None,
        is_ads_banner=False,
        is_ads_banner_expires_at=None,
        is_hot_sales=False,
        is_hot_sales_expires_at=None,
    ):
        # Create a real User instance (not saved) – has _state
        user = User(id=999)
        user.points = points

        listing = mocker.MagicMock()
        listing.id = listing_id
        listing.title = title
        listing.user = user
        listing.auto_reactivate = auto_reactivate
        listing.status = status
        listing.is_deleted = is_deleted
        listing.expires_at = expires_at
        listing.is_ads_banner = is_ads_banner
        listing.is_ads_banner_expires_at = is_ads_banner_expires_at
        listing.is_hot_sales = is_hot_sales
        listing.is_hot_sales_expires_at = is_hot_sales_expires_at
        return listing
    return _factory


@pytest.fixture
def mock_queryset_chain(mocker):
    """Patch Listing.objects to return a controllable list of listings."""
    def _patch(listings):
        mock_manager = mocker.MagicMock()
        mock_manager.select_related.return_value = mock_manager
        mock_manager.filter.return_value = mock_manager
        mock_manager.__getitem__.return_value = listings
        mock_manager.__iter__ = lambda self: iter(listings)
        mocker.patch("apps.campus.models.Listing.objects", mock_manager)
        return mock_manager
    return _patch


@pytest.fixture
def mock_transaction(mocker):
    mock_atomic = mocker.patch("django.db.transaction.atomic")
    mock_on_commit = mocker.patch("django.db.transaction.on_commit")
    return mock_atomic, mock_on_commit


@pytest.fixture
def mock_notification_bulk_create(mocker):
    return mocker.patch("apps.users.models.Notification.objects.bulk_create")


@pytest.fixture
def mock_update_points(mocker):
    return mocker.patch("utils.helpers.UpdatePointsService.update_points")


@pytest.fixture
def mock_background_tasks(mocker):
    return {
        "expired": mocker.patch("utils.Tasks.backgroundTask.background_task_send_expired_listing_emails.delay"),
        "auto_reactivate": mocker.patch("utils.Tasks.backgroundTask.background_task_send_auto_reactivate_listing_emails.delay"),
        "banner": mocker.patch("utils.Tasks.backgroundTask.background_task_send_banner_expired_emails.delay"),
        "hot_sales": mocker.patch("utils.Tasks.backgroundTask.background_task_send_hot_sales_expired_emails.delay"),
    }


@pytest.fixture
def mock_op_logger(mocker):
    mock_op = mocker.MagicMock()
    mocker.patch("utils.periodic_task_helper.OperationLogger", return_value=mock_op)
    return mock_op


# ----------------------------------------------------------------------
# Tests for process_check_expired_listings
# ----------------------------------------------------------------------

class TestCheckExpiredListings:

    def test_no_listings(self, mocker, fixed_now, mock_timezone_now, mock_queryset_chain,
                         mock_transaction, mock_notification_bulk_create,
                         mock_update_points, mock_background_tasks,
                         mock_op_logger):
        mock_queryset_chain([])
        result = PeriodTasksHelper.process_check_expired_listings()
        expected = f"Expired 0, auto‑reactivated 0 at {fixed_now}"
        assert result == expected
        mock_op_logger.start.assert_called_once()
        mock_op_logger.success.assert_called_once_with("Expired 0 listings, auto‑reactivated 0 listings.")
        mock_update_points.assert_not_called()
        mock_notification_bulk_create.assert_not_called()
        for task in mock_background_tasks.values():
            task.assert_not_called()

    def test_non_auto_listings_only(self, mocker, fixed_now, mock_timezone_now,
                                     mock_queryset_chain,
                                     mock_transaction, mock_notification_bulk_create,
                                     mock_update_points, mock_background_tasks,
                                     mock_op_logger, mock_listing):
        now = fixed_now
        listing1 = mock_listing(1, title="Expired 1", auto_reactivate=False, expires_at=now)
        listing2 = mock_listing(2, title="Expired 2", auto_reactivate=False, expires_at=now - datetime.timedelta(days=1))
        mock_queryset_chain([listing1, listing2])

        mock_atomic, mock_on_commit = mock_transaction

        result = PeriodTasksHelper.process_check_expired_listings()

        mock_atomic.assert_called_once()
        mock_notification_bulk_create.assert_called_once()
        args, kwargs = mock_notification_bulk_create.call_args
        notifications = args[0] if args else kwargs.get("objs")
        assert len(notifications) == 2
        for notif in notifications:
            assert notif.notification_type == NotificationEnum.LISTING.value
            assert "Expired" in notif.title

        mock_on_commit.assert_called_once()
        on_commit_func = mock_on_commit.call_args[0][0]
        on_commit_func()
        mock_background_tasks["expired"].assert_called_once_with([1, 2])

        mock_update_points.assert_not_called()

        mock_op_logger.success.assert_called_once_with(
            "Expired 2 listings, auto‑reactivated 0 listings."
        )

    def test_auto_listings_with_sufficient_points(self, mocker, fixed_now, mock_timezone_now,
                                                   mock_queryset_chain,
                                                   mock_transaction,
                                                   mock_notification_bulk_create,
                                                   mock_update_points,
                                                   mock_background_tasks,
                                                   mock_op_logger,
                                                   mock_listing):
        now = fixed_now
        listing = mock_listing(
            1,
            title="Auto Listing",
            auto_reactivate=True,
            points=5,
            expires_at=now
        )
        mock_queryset_chain([listing])
        mock_atomic, mock_on_commit = mock_transaction

        result = PeriodTasksHelper.process_check_expired_listings()

        mock_update_points.assert_called_once_with(
            user=listing.user,
            points=1,
            action=ConstantHelper.POINT_SUBTRACTION,
            transaction_type=PointTransactionTypeEnum.REACTIVATION.value,
            description=f'Auto-reactivation of listing "{listing.title}"',
            reference=f"listing_{listing.id}"
        )

        mock_notification_bulk_create.assert_called_once()
        notifications = mock_notification_bulk_create.call_args[0][0]
        assert len(notifications) == 1
        assert notifications[0].title == "Listing Auto‑Reactivated"
        assert "1 point was deducted" in notifications[0].message

        mock_on_commit.assert_called_once()
        on_commit_func = mock_on_commit.call_args[0][0]
        on_commit_func()
        mock_background_tasks["auto_reactivate"].assert_called_once_with([1])
        mock_background_tasks["expired"].assert_not_called()

        mock_op_logger.success.assert_called_once_with(
            "Expired 0 listings, auto‑reactivated 1 listings."
        )

    def test_auto_listings_with_insufficient_points(self, mocker, fixed_now, mock_timezone_now,
                                                     mock_queryset_chain,
                                                     mock_transaction,
                                                     mock_notification_bulk_create,
                                                     mock_update_points,
                                                     mock_background_tasks,
                                                     mock_op_logger,
                                                     mock_listing):
        now = fixed_now
        listing = mock_listing(
            1,
            title="Auto Listing",
            auto_reactivate=True,
            points=0,
            expires_at=now
        )
        mock_queryset_chain([listing])
        mock_atomic, mock_on_commit = mock_transaction

        result = PeriodTasksHelper.process_check_expired_listings()

        mock_update_points.assert_not_called()

        mock_notification_bulk_create.assert_called_once()
        notifications = mock_notification_bulk_create.call_args[0][0]
        assert len(notifications) == 1
        assert notifications[0].title == "Auto‑Reactivation Failed"
        assert "insufficient points" in notifications[0].message

        mock_on_commit.assert_called_once()
        on_commit_func = mock_on_commit.call_args[0][0]
        on_commit_func()
        mock_background_tasks["expired"].assert_called_once_with([1])
        mock_background_tasks["auto_reactivate"].assert_not_called()

        mock_op_logger.success.assert_called_once_with(
            "Expired 1 listings, auto‑reactivated 0 listings."
        )

    def test_mixed_listings(self, mocker, fixed_now, mock_timezone_now,
                            mock_queryset_chain,
                            mock_transaction, mock_notification_bulk_create,
                            mock_update_points, mock_background_tasks,
                            mock_op_logger, mock_listing):
        """Mixed case: non-auto, auto with points, auto without points."""
        now = fixed_now
        listing1 = mock_listing(1, title="Non-auto", auto_reactivate=False, expires_at=now)
        listing2 = mock_listing(2, title="Auto with points", auto_reactivate=True, points=3, expires_at=now)
        listing3 = mock_listing(3, title="Auto without points", auto_reactivate=True, points=0, expires_at=now)

        mock_queryset_chain([listing1, listing2, listing3])
        mock_atomic, mock_on_commit = mock_transaction

        result = PeriodTasksHelper.process_check_expired_listings()

        mock_update_points.assert_called_once_with(
            user=listing2.user,
            points=1,
            action=ConstantHelper.POINT_SUBTRACTION,
            transaction_type=PointTransactionTypeEnum.REACTIVATION.value,
            description=f'Auto-reactivation of listing "{listing2.title}"',
            reference=f"listing_{listing2.id}"
        )

        # Three separate bulk_create calls: one per notification group
        assert mock_notification_bulk_create.call_count == 3
        total_notifications = 0
        for call_arg in mock_notification_bulk_create.call_args_list:
            total_notifications += len(call_arg[0][0])
        assert total_notifications == 3

        titles = []
        for call_arg in mock_notification_bulk_create.call_args_list:
            for notif in call_arg[0][0]:
                titles.append(notif.title)
        assert "Listing Expired" in titles
        assert "Listing Auto‑Reactivated" in titles
        assert "Auto‑Reactivation Failed" in titles

        # Three on_commit calls: one for each group (non-auto, auto-with, auto-without)
        assert mock_on_commit.call_count == 3
        # Execute all on_commit lambdas to trigger background tasks
        for call_obj in mock_on_commit.call_args_list:
            call_obj[0][0]()
        # Expired task should be called twice (non-auto and auto-without)
        # Auto-reactivate task should be called once (auto-with)
        assert mock_background_tasks["expired"].call_count == 2
        assert mock_background_tasks["auto_reactivate"].call_count == 1
        # Check that expired was called with [1] and [3] (order may vary)
        mock_background_tasks["expired"].assert_has_calls([call([1]), call([3])], any_order=True)
        mock_background_tasks["auto_reactivate"].assert_called_once_with([2])

        mock_op_logger.success.assert_called_once_with(
            "Expired 2 listings, auto‑reactivated 1 listings."
        )

    def test_batching(self, mocker, fixed_now, mock_timezone_now,
                      mock_queryset_chain,
                      mock_transaction, mock_notification_bulk_create,
                      mock_update_points, mock_background_tasks,
                      mock_op_logger, mock_listing):
        mocker.patch("utils.periodic_task_helper.BATCH_SIZE", 2)

        listings = []
        for i in range(1, 6):
            listings.append(
                mock_listing(i, title=f"Listing {i}", auto_reactivate=False, expires_at=fixed_now)
            )

        mock_manager = mocker.patch("apps.campus.models.Listing.objects")
        mock_manager.select_related.return_value = mock_manager
        mock_manager.filter.return_value = mock_manager

        batches = [listings[0:2], listings[2:4], listings[4:5]]
        batch_iter = iter(batches)

        def getitem_side_effect(slice_obj):
            try:
                return next(batch_iter)
            except StopIteration:
                return []
        mock_manager.__getitem__.side_effect = getitem_side_effect

        mock_atomic, mock_on_commit = mock_transaction

        result = PeriodTasksHelper.process_check_expired_listings()

        assert mock_notification_bulk_create.call_count == 3
        total_notifications = 0
        for call_arg in mock_notification_bulk_create.call_args_list:
            total_notifications += len(call_arg[0][0])
        assert total_notifications == 5

        assert mock_on_commit.call_count == 3
        for call_obj in mock_on_commit.call_args_list:
            call_obj[0][0]()
        assert mock_background_tasks["expired"].call_count == 3

        mock_op_logger.success.assert_called_once_with(
            "Expired 5 listings, auto‑reactivated 0 listings."
        )


# ----------------------------------------------------------------------
# Tests for process_check_banner_ads_expired_listings
# ----------------------------------------------------------------------

class TestCheckBannerAdsExpiredListings:

    def test_no_listings(self, mocker, fixed_now, mock_timezone_now,
                         mock_queryset_chain, mock_transaction,
                         mock_notification_bulk_create,
                         mock_background_tasks, mock_op_logger):
        mock_queryset_chain([])
        result = PeriodTasksHelper.process_check_banner_ads_expired_listings()
        expected = f"Disabled 0 expired banner ads at {fixed_now}"
        assert result == expected
        mock_op_logger.success.assert_called_once_with("Total banner promotions disabled: 0")
        mock_notification_bulk_create.assert_not_called()
        mock_background_tasks["banner"].assert_not_called()

    def test_with_listings(self, mocker, fixed_now, mock_timezone_now,
                           mock_queryset_chain, mock_transaction,
                           mock_notification_bulk_create,
                           mock_background_tasks, mock_op_logger,
                           mock_listing):
        now = fixed_now
        listing1 = mock_listing(1, title="Banner 1", is_ads_banner=True,
                                is_ads_banner_expires_at=now)
        listing2 = mock_listing(2, title="Banner 2", is_ads_banner=True,
                                is_ads_banner_expires_at=now - datetime.timedelta(days=2))
        mock_queryset_chain([listing1, listing2])
        mock_atomic, mock_on_commit = mock_transaction

        result = PeriodTasksHelper.process_check_banner_ads_expired_listings()

        mock_notification_bulk_create.assert_called_once()
        notifications = mock_notification_bulk_create.call_args[0][0]
        assert len(notifications) == 2
        for notif in notifications:
            assert notif.title == "Banner Promotion Expired"
            assert "banner promotion" in notif.message.lower()

        mock_on_commit.assert_called_once()
        on_commit_func = mock_on_commit.call_args[0][0]
        on_commit_func()
        mock_background_tasks["banner"].assert_called_once_with([1, 2])

        batch_call = call("Disabled banner for 2 expired promotions in this batch.")
        total_call = call("Total banner promotions disabled: 2")
        assert mock_op_logger.success.call_args_list == [batch_call, total_call]
        mock_op_logger.success.assert_called_with("Total banner promotions disabled: 2")


# ----------------------------------------------------------------------
# Tests for process_check_hot_sales_ads_expired_listings
# ----------------------------------------------------------------------

class TestCheckHotSalesAdsExpiredListings:

    def test_no_listings(self, mocker, fixed_now, mock_timezone_now,
                         mock_queryset_chain, mock_transaction,
                         mock_notification_bulk_create,
                         mock_background_tasks, mock_op_logger):
        mock_queryset_chain([])
        result = PeriodTasksHelper.process_check_hot_sales_ads_expired_listings()
        expected = f"Disabled 0 expired Hot Sales ads at {fixed_now}"
        assert result == expected
        mock_op_logger.success.assert_called_once_with("Total Hot Sales promotions disabled: 0")
        mock_notification_bulk_create.assert_not_called()
        mock_background_tasks["hot_sales"].assert_not_called()

    def test_with_listings(self, mocker, fixed_now, mock_timezone_now,
                           mock_queryset_chain, mock_transaction,
                           mock_notification_bulk_create,
                           mock_background_tasks, mock_op_logger,
                           mock_listing):
        now = fixed_now
        listing1 = mock_listing(1, title="Hot 1", is_hot_sales=True,
                                is_hot_sales_expires_at=now)
        listing2 = mock_listing(2, title="Hot 2", is_hot_sales=True,
                                is_hot_sales_expires_at=now - datetime.timedelta(days=1))
        mock_queryset_chain([listing1, listing2])
        mock_atomic, mock_on_commit = mock_transaction

        result = PeriodTasksHelper.process_check_hot_sales_ads_expired_listings()

        mock_notification_bulk_create.assert_called_once()
        notifications = mock_notification_bulk_create.call_args[0][0]
        assert len(notifications) == 2
        for notif in notifications:
            assert notif.title == "Hot Sales Promotion Expired"
            assert "Hot Sales promotion" in notif.message

        mock_on_commit.assert_called_once()
        on_commit_func = mock_on_commit.call_args[0][0]
        on_commit_func()
        mock_background_tasks["hot_sales"].assert_called_once_with([1, 2])

        batch_call = call("Disabled Hot Sales for 2 expired promotions in this batch.")
        total_call = call("Total Hot Sales promotions disabled: 2")
        assert mock_op_logger.success.call_args_list == [batch_call, total_call]
        mock_op_logger.success.assert_called_with("Total Hot Sales promotions disabled: 2")