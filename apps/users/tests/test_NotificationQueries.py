import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from django.core.paginator import Paginator, Page, EmptyPage, PageNotAnInteger

from apps.users.BBL.Queries.notification import NotificationQueries
from apps.users.models import Notification, User
from utils.base_result import BaseResultWithData
from utils.enums import CacheKeysEnum


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def test_user(db):
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass",
        first_name="Test",
        last_name="User",
    )
    return user


@pytest.fixture
def mock_cache():
    with patch("apps.users.BBL.Queries.notification.GlobalCache") as mock:
        yield mock


@pytest.fixture
def mock_humanize():
    with patch("apps.users.BBL.Queries.notification.humanize_date") as mock:
        mock.return_value = "2 hours ago"
        yield mock


# ── Tests ─────────────────────────────────────────────────────────────

class TestNotificationQueries:

    # ── get_notification ──────────────────────────────────────────────

    def test_get_notification_cache_hit(self, mock_cache, request_factory, test_user):
        """Return cached data if available."""
        cached_data = {
            "notifications": [{"id": 1, "title": "Test"}],
            "unread_messages_counts": 0,
            "page": 1,
            "total_pages": 1,
            "total_count": 1,
            "has_next": False,
            "has_previous": False,
        }
        mock_cache.get.return_value = cached_data

        request = request_factory.get("/?page=1")
        result = NotificationQueries.get_notification(request, test_user)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.data == cached_data
        mock_cache.get.assert_called_once_with(
            CacheKeysEnum.format(CacheKeysEnum.NOTIFICATIONS, user_id=test_user.id, page=1)
        )
        mock_cache.set.assert_not_called()

    def test_get_notification_cache_miss(self, mock_cache, mock_humanize, request_factory, test_user, db):
        """Fetch from database, paginate, cache, and return."""
        mock_cache.get.return_value = None

        # Create some notifications
        for i in range(3):
            Notification.objects.create(
                user=test_user,
                title=f"Notif {i}",
                message=f"Message {i}",
                is_read=(i % 2 == 0),
            )

        request = request_factory.get("/?page=1&per_page=2")
        result = NotificationQueries.get_notification(request, test_user)

        assert result.is_success is True
        assert result.status_code == 200

        data = result.data
        assert data["page"] == 1
        assert data["total_pages"] == 2
        assert data["total_count"] == 3
        assert data["has_next"] is True
        assert data["has_previous"] is False
        assert data["unread_messages_counts"] == 1

        notifications = data["notifications"]
        assert len(notifications) == 2
        assert notifications[0]["title"] == "Notif 2"
        assert notifications[1]["title"] == "Notif 1"
        # i=2 is read, i=1 is unread
        assert notifications[0]["is_read"] is True
        assert notifications[1]["is_read"] is False

        assert mock_humanize.call_count == 2

        cache_key = CacheKeysEnum.format(CacheKeysEnum.NOTIFICATIONS, user_id=test_user.id, page=1)
        mock_cache.set.assert_called_once_with(cache_key, data)



    def test_get_notification_pagination_page_not_integer(self, mock_cache, request_factory, test_user, db):
        """When page is not an integer, fallback to page 1."""
        mock_cache.get.return_value = None

        for i in range(5):
            Notification.objects.create(user=test_user, title=f"Notif {i}")

        request = request_factory.get("/?page=invalid&per_page=2")
        result = NotificationQueries.get_notification(request, test_user)

        assert result.is_success is True
        assert result.data["page"] == 1

    def test_get_notification_pagination_empty_page(self, mock_cache, request_factory, test_user, db):
        """When page is out of range, fallback to last page."""
        mock_cache.get.return_value = None

        for i in range(3):
            Notification.objects.create(user=test_user, title=f"Notif {i}")

        request = request_factory.get("/?page=10&per_page=2")
        # page 10 is out of range, should fallback to last page (page 2 with per_page=2)
        result = NotificationQueries.get_notification(request, test_user)

        assert result.is_success is True
        assert result.data["page"] == 2
        assert result.data["total_pages"] == 2

    def test_get_notification_filters_deleted(self, mock_cache, request_factory, test_user, db):
        """Should exclude notifications with is_deleted=True."""
        mock_cache.get.return_value = None

        notif1 = Notification.objects.create(user=test_user, title="Active")
        notif2 = Notification.objects.create(user=test_user, title="Deleted", is_deleted=True)

        request = request_factory.get("/?page=1&per_page=10")
        result = NotificationQueries.get_notification(request, test_user)

        assert result.is_success is True
        notifications = result.data["notifications"]
        assert len(notifications) == 1
        assert notifications[0]["title"] == "Active"

    def test_get_notification_unread_count(self, mock_cache, request_factory, test_user, db):
        """unread_messages_counts should count all unread notifications (not just current page)."""
        mock_cache.get.return_value = None

        for i in range(5):
            Notification.objects.create(
                user=test_user,
                title=f"Notif {i}",
                is_read=(i % 2 == 0)  # 2,4 are read; 0,2,4 read => 3 read, 2 unread
            )

        request = request_factory.get("/?page=1&per_page=2")
        result = NotificationQueries.get_notification(request, test_user)

        assert result.is_success is True
        # Total unread across all notifications: 2 (i=1 and i=3)
        assert result.data["unread_messages_counts"] == 2

    # ── get_notifications_header ──────────────────────────────────────

    def test_get_notifications_header_cache_hit(self, mock_cache, request_factory, test_user):
        """Return cached data if available."""
        cached_data = {
            "notifications": [{"id": 1, "title": "Header"}],
            "unread_messages_counts": 0,
        }
        mock_cache.get.return_value = cached_data

        request = request_factory.get("/")
        result = NotificationQueries.get_notifications_header(request, test_user)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.data == cached_data
        mock_cache.get.assert_called_once_with(
            CacheKeysEnum.format(CacheKeysEnum.NOTIFICATION_HEADER, user_id=test_user.id)
        )
        mock_cache.set.assert_not_called()

    def test_get_notifications_header_cache_miss(self, mock_cache, mock_humanize, request_factory, test_user, db):
        """Fetch latest 5 notifications, cache, and return."""
        mock_cache.get.return_value = None

        # Create 7 notifications
        for i in range(7):
            Notification.objects.create(
                user=test_user,
                title=f"Notif {i}",
                message=f"Msg {i}",
                is_read=(i % 2 == 0),
            )

        request = request_factory.get("/")
        result = NotificationQueries.get_notifications_header(request, test_user)

        assert result.is_success is True
        assert result.status_code == 200

        data = result.data
        notifications = data["notifications"]
        assert len(notifications) == 5  # only latest 5
        # Should be ordered descending by created_at, so latest first
        # The latest is i=6, then i=5, etc.
        assert notifications[0]["title"] == "Notif 6"
        assert notifications[4]["title"] == "Notif 2"

        # Unread count should be total unread across all 7 (not limited to 5)
        # i=0 read, i=1 unread, i=2 read, i=3 unread, i=4 read, i=5 unread, i=6 read
        # Unread: 1,3,5 => 3
        assert data["unread_messages_counts"] == 3

        # humanize_date called for each of the 5
        assert mock_humanize.call_count == 5

        # Cache set
        cache_key = CacheKeysEnum.format(CacheKeysEnum.NOTIFICATION_HEADER, user_id=test_user.id)
        mock_cache.set.assert_called_once_with(cache_key, data)

    def test_get_notifications_header_filters_deleted(self, mock_cache, request_factory, test_user, db):
        """Should exclude deleted notifications."""
        mock_cache.get.return_value = None

        Notification.objects.create(user=test_user, title="Active")
        Notification.objects.create(user=test_user, title="Deleted", is_deleted=True)

        request = request_factory.get("/")
        result = NotificationQueries.get_notifications_header(request, test_user)

        assert result.is_success is True
        notifications = result.data["notifications"]
        assert len(notifications) == 1
        assert notifications[0]["title"] == "Active"

    def test_get_notifications_header_unread_count_all(self, mock_cache, request_factory, test_user, db):
        """unread_messages_counts should count all unread notifications, not just header items."""
        mock_cache.get.return_value = None

        for i in range(10):
            Notification.objects.create(
                user=test_user,
                title=f"Notif {i}",
                is_read=(i % 3 == 0)  # 0,3,6,9 are read => 6 unread
            )

        request = request_factory.get("/")
        result = NotificationQueries.get_notifications_header(request, test_user)

        assert result.is_success is True
        assert result.data["unread_messages_counts"] == 6
        # Header should still contain only 5 items
        assert len(result.data["notifications"]) == 5