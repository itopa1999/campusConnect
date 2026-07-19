import pytest
from unittest.mock import patch, ANY
from django.test import RequestFactory

from apps.users.BBL.Queries.notification import NotificationQueries
from apps.users.models import Notification, User
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
def mock_humanize():
    with patch("apps.users.BBL.Queries.notification.humanize_date") as mock:
        mock.return_value = "2 hours ago"
        yield mock


# ── Tests ─────────────────────────────────────────────────────────────

class TestNotificationQueries:

    # ── get_notification ──────────────────────────────────────────────

    def test_get_notification_cache_hit(self, request_factory, test_user):
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
        request = request_factory.get("/?page=1")

        with patch("apps.users.BBL.Queries.notification.GlobalCache.get_or_set") as mock_get_or_set:
            mock_get_or_set.return_value = cached_data
            result = NotificationQueries.get_notification(request, test_user)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.data == cached_data
        mock_get_or_set.assert_called_once_with(
            key=CacheKeysEnum.format(CacheKeysEnum.NOTIFICATIONS, user_id=test_user.id, page=1, per_page = 10),
            callback=ANY,
            timeout=300,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_notification_cache_miss(self, mock_humanize, request_factory, test_user, db):
        """Fetch from database, paginate, cache, and return."""
        # Create some notifications
        for i in range(3):
            Notification.objects.create(
                user=test_user,
                title=f"Notif {i}",
                message=f"Message {i}",
                is_read=(i % 2 == 0),
            )

        request = request_factory.get("/?page=1&per_page=2")

        with patch("apps.users.BBL.Queries.notification.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

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
        assert notifications[0]["is_read"] is True
        assert notifications[1]["is_read"] is False

        assert mock_humanize.call_count == 2

        mock_get_or_set.assert_called_once_with(
            key=ANY,
            callback=ANY,
            timeout=300,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_notification_pagination_page_not_integer(self, request_factory, test_user, db):
        """When page is not an integer, fallback to page 1."""
        for i in range(5):
            Notification.objects.create(user=test_user, title=f"Notif {i}")

        request = request_factory.get("/?page=invalid&per_page=2")

        with patch("apps.users.BBL.Queries.notification.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = NotificationQueries.get_notification(request, test_user)

        assert result.is_success is True
        assert result.data["page"] == 1

    def test_get_notification_pagination_empty_page(self, request_factory, test_user, db):
        """When page is out of range, fallback to last page."""
        for i in range(3):
            Notification.objects.create(user=test_user, title=f"Notif {i}")

        request = request_factory.get("/?page=10&per_page=2")

        with patch("apps.users.BBL.Queries.notification.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = NotificationQueries.get_notification(request, test_user)

        assert result.is_success is True
        assert result.data["page"] == 2
        assert result.data["total_pages"] == 2

    def test_get_notification_filters_deleted(self, request_factory, test_user, db):
        """Should exclude notifications with is_deleted=True."""
        notif1 = Notification.objects.create(user=test_user, title="Active")
        notif2 = Notification.objects.create(user=test_user, title="Deleted", is_deleted=True)

        request = request_factory.get("/?page=1&per_page=10")

        with patch("apps.users.BBL.Queries.notification.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = NotificationQueries.get_notification(request, test_user)

        assert result.is_success is True
        notifications = result.data["notifications"]
        assert len(notifications) == 1
        assert notifications[0]["title"] == "Active"

    def test_get_notification_unread_count(self, request_factory, test_user, db):
        """unread_messages_counts should count all unread notifications (not just current page)."""
        for i in range(5):
            Notification.objects.create(
                user=test_user,
                title=f"Notif {i}",
                is_read=(i % 2 == 0)
            )

        request = request_factory.get("/?page=1&per_page=2")

        with patch("apps.users.BBL.Queries.notification.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = NotificationQueries.get_notification(request, test_user)

        assert result.is_success is True
        assert result.data["unread_messages_counts"] == 2

    # ── get_notifications_header ──────────────────────────────────────

    def test_get_notifications_header_cache_hit(self, request_factory, test_user):
        """Return cached data if available."""
        cached_data = {
            "notifications": [{"id": 1, "title": "Header"}],
            "unread_messages_counts": 0,
        }
        request = request_factory.get("/")

        with patch("apps.users.BBL.Queries.notification.GlobalCache.get_or_set") as mock_get_or_set:
            mock_get_or_set.return_value = cached_data
            result = NotificationQueries.get_notifications_header(request, test_user)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.data == cached_data
        mock_get_or_set.assert_called_once_with(
            key=CacheKeysEnum.format(CacheKeysEnum.NOTIFICATION_HEADER, user_id=test_user.id),
            callback=ANY,
            timeout=120,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_notifications_header_cache_miss(self, mock_humanize, request_factory, test_user, db):
        """Fetch latest 5 notifications, cache, and return."""
        # Create 7 notifications
        for i in range(7):
            Notification.objects.create(
                user=test_user,
                title=f"Notif {i}",
                message=f"Msg {i}",
                is_read=(i % 2 == 0),
            )

        request = request_factory.get("/")

        with patch("apps.users.BBL.Queries.notification.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = NotificationQueries.get_notifications_header(request, test_user)

        assert result.is_success is True
        assert result.status_code == 200

        data = result.data
        notifications = data["notifications"]
        assert len(notifications) == 5
        assert notifications[0]["title"] == "Notif 6"
        assert notifications[4]["title"] == "Notif 2"
        assert data["unread_messages_counts"] == 3

        assert mock_humanize.call_count == 5

        mock_get_or_set.assert_called_once_with(
            key=CacheKeysEnum.format(CacheKeysEnum.NOTIFICATION_HEADER, user_id=test_user.id),
            callback=ANY,
            timeout=120,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_notifications_header_filters_deleted(self, request_factory, test_user, db):
        """Should exclude deleted notifications."""
        Notification.objects.create(user=test_user, title="Active")
        Notification.objects.create(user=test_user, title="Deleted", is_deleted=True)

        request = request_factory.get("/")

        with patch("apps.users.BBL.Queries.notification.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = NotificationQueries.get_notifications_header(request, test_user)

        assert result.is_success is True
        notifications = result.data["notifications"]
        assert len(notifications) == 1
        assert notifications[0]["title"] == "Active"

    def test_get_notifications_header_unread_count_all(self, request_factory, test_user, db):
        """unread_messages_counts should count all unread notifications, not just header items."""
        for i in range(10):
            Notification.objects.create(
                user=test_user,
                title=f"Notif {i}",
                is_read=(i % 3 == 0)
            )

        request = request_factory.get("/")

        with patch("apps.users.BBL.Queries.notification.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = NotificationQueries.get_notifications_header(request, test_user)

        assert result.is_success is True
        assert result.data["unread_messages_counts"] == 6
        assert len(result.data["notifications"]) == 5