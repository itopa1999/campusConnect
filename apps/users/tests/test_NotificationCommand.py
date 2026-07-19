import pytest
from unittest.mock import patch

from apps.users.BBL.Commands.notification import NotificationCommand
from apps.users.models import Notification, User


# ── Fixtures ──────────────────────────────────────────────────────────

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
    with patch("apps.users.BBL.Commands.notification.GlobalCache") as mock:
        yield mock


# ── Tests ─────────────────────────────────────────────────────────────

class TestNotificationCommand:

    # ── mark_as_read ──────────────────────────────────────────────────

    def test_mark_as_read_success(self, test_user, db):
        notification = Notification.objects.create(
            user=test_user,
            title="Test",
            message="Test message",
            is_read=False,
        )
        result = NotificationCommand.mark_as_read(test_user, notification.id)
        assert result.is_success is True
        assert result.status_code == 200
        assert result.message == "Notification marked as read successfully"
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_mark_as_read_not_found(self, test_user):
        result = NotificationCommand.mark_as_read(test_user, 999)
        assert result.is_success is False
        assert result.status_code == 404
        assert result.message == "Notification not found"

    def test_mark_as_read_other_user_notification(self, test_user, db):
        other_user = User.objects.create_user(email="other@example.com", password="pass")
        notification = Notification.objects.create(
            user=other_user,
            title="Other's",
            message="",
            is_read=False,
        )
        result = NotificationCommand.mark_as_read(test_user, notification.id)
        assert result.is_success is False
        assert result.status_code == 404
        notification.refresh_from_db()
        assert notification.is_read is False

    def test_mark_as_read_deleted_notification(self, test_user, db):
        notification = Notification.objects.create(
            user=test_user,
            title="Deleted",
            message="",
            is_read=False,
            is_deleted=True,
        )
        result = NotificationCommand.mark_as_read(test_user, notification.id)
        assert result.is_success is False
        assert result.status_code == 404
        notification.refresh_from_db()
        assert notification.is_read is False

    # ── mark_all_as_read ─────────────────────────────────────────────

    def test_mark_all_as_read_success(self, test_user, mock_cache, db):
        for i in range(3):
            Notification.objects.create(
                user=test_user,
                title=f"Notif {i}",
                is_read=(i % 2 == 0),  # one unread
            )
        result = NotificationCommand.mark_all_as_read(test_user)
        assert result.is_success is True
        assert result.status_code == 200
        assert result.message == "1 notifications marked as read successfully"
        assert Notification.objects.filter(user=test_user, is_read=False).count() == 0
        mock_cache.delete_prefix.assert_any_call(f"notifications_{test_user.id}")
        mock_cache.delete_prefix.assert_any_call(f"notifications_header_{test_user.id}")

    def test_mark_all_as_read_no_unread(self, test_user, mock_cache, db):
        Notification.objects.create(user=test_user, title="Read", is_read=True)
        result = NotificationCommand.mark_all_as_read(test_user)
        assert result.is_success is True
        assert result.message == "0 notifications marked as read successfully"
        mock_cache.delete_prefix.assert_any_call(f"notifications_{test_user.id}")
        mock_cache.delete_prefix.assert_any_call(f"notifications_header_{test_user.id}")

    def test_mark_all_as_read_only_own_notifications(self, test_user, mock_cache, db):
        other_user = User.objects.create_user(email="other@example.com", password="pass")
        Notification.objects.create(user=other_user, title="Other", is_read=False)
        Notification.objects.create(user=test_user, title="Own", is_read=False)
        result = NotificationCommand.mark_all_as_read(test_user)
        assert result.message == "1 notifications marked as read successfully"
        other_notif = Notification.objects.get(user=other_user)
        assert other_notif.is_read is False
        own_notif = Notification.objects.get(user=test_user)
        assert own_notif.is_read is True

    # ── delete_notification ──────────────────────────────────────────

    def test_delete_notification_success(self, test_user, db):
        notification = Notification.objects.create(
            user=test_user,
            title="To delete",
            message="",
            is_deleted=False,
        )
        result = NotificationCommand.delete_notification(test_user, notification.id)
        assert result.is_success is True
        assert result.status_code == 200
        assert result.message == "Notification deleted successfully"
        notification.refresh_from_db()
        assert notification.is_deleted is True

    def test_delete_notification_not_found(self, test_user):
        result = NotificationCommand.delete_notification(test_user, 999)
        assert result.is_success is False
        assert result.status_code == 404
        assert result.message == "Notification not found"

    def test_delete_notification_other_user(self, test_user, db):
        other_user = User.objects.create_user(email="other@example.com", password="pass")
        notification = Notification.objects.create(
            user=other_user,
            title="Other's",
            message="",
            is_deleted=False,
        )
        result = NotificationCommand.delete_notification(test_user, notification.id)
        assert result.is_success is False
        assert result.status_code == 404
        notification.refresh_from_db()
        assert notification.is_deleted is False

    def test_delete_notification_already_deleted(self, test_user, db):
        notification = Notification.objects.create(
            user=test_user,
            title="Already deleted",
            message="",
            is_deleted=True,
        )
        result = NotificationCommand.delete_notification(test_user, notification.id)
        assert result.is_success is False
        assert result.status_code == 404

    # ── delete_all_notifications ─────────────────────────────────────

    def test_delete_all_notifications_success(self, test_user, mock_cache, db):
        for i in range(3):
            Notification.objects.create(
                user=test_user,
                title=f"Notif {i}",
                is_deleted=False,
            )
        result = NotificationCommand.delete_all_notifications(test_user)
        assert result.is_success is True
        assert result.status_code == 200
        assert result.message == "3 notifications deleted successfully"

        # Use all_including_deleted to see soft-deleted records
        deleted_count = Notification.objects.all_including_deleted().filter(
            user=test_user, is_deleted=True
        ).count()
        assert deleted_count == 3
        active_count = Notification.objects.filter(user=test_user, is_deleted=False).count()
        assert active_count == 0

        mock_cache.delete_prefix.assert_any_call(f"notifications_{test_user.id}")
        mock_cache.delete_prefix.assert_any_call(f"notifications_header_{test_user.id}")

    def test_delete_all_notifications_no_notifications(self, test_user, mock_cache):
        result = NotificationCommand.delete_all_notifications(test_user)
        assert result.is_success is True
        assert result.status_code == 200
        assert result.message == "0 notifications deleted successfully"
        mock_cache.delete_prefix.assert_any_call(f"notifications_{test_user.id}")
        mock_cache.delete_prefix.assert_any_call(f"notifications_header_{test_user.id}")

    def test_delete_all_notifications_other_users_ignored(self, test_user, mock_cache, db):
        other_user = User.objects.create_user(email="other@example.com", password="pass")
        Notification.objects.create(user=other_user, title="Other")
        Notification.objects.create(user=test_user, title="Own")
        result = NotificationCommand.delete_all_notifications(test_user)
        assert result.is_success is True
        assert result.message == "1 notifications deleted successfully"

        # Other user's notification should NOT be deleted
        other_notif = Notification.objects.get(user=other_user)
        assert other_notif.is_deleted is False

        # Own notification should be soft-deleted (use all_including_deleted)
        own_notif = Notification.objects.all_including_deleted().get(user=test_user)
        assert own_notif.is_deleted is True

    def test_delete_all_notifications_deletes_all_regardless_of_read_status(self, test_user, mock_cache, db):
        Notification.objects.create(user=test_user, title="Read", is_read=True)
        Notification.objects.create(user=test_user, title="Unread", is_read=False)
        result = NotificationCommand.delete_all_notifications(test_user)
        assert result.is_success is True
        assert result.message == "2 notifications deleted successfully"

        deleted_count = Notification.objects.all_including_deleted().filter(
            user=test_user, is_deleted=True
        ).count()
        assert deleted_count == 2