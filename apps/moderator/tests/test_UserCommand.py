import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.db import IntegrityError
from django.utils import timezone
from apps.moderator.models import UserModeration, ModeratorAction
from apps.moderator.BBL.Commands.user import UserCommand
from utils.enums import ContentTypeEnum, ModeratorActionTypeEnum

User = get_user_model()


# ---------- Fixtures ----------
@pytest.fixture
def moderator(db):
    return User.objects.create_user(
        email='moderator@example.com',
        password='testpass123',
        first_name='Mod',
        last_name='erator',
        is_staff=True
    )


@pytest.fixture
def target_user(db):
    return User.objects.create_user(
        email='target@example.com',
        password='testpass123',
        first_name='Target',
        last_name='User',
        is_active=True,
        is_deleted=False
    )


@pytest.fixture
def target_user_with_moderation(db, target_user):
    # Create moderation record for target user
    moderation = UserModeration.objects.create(
        user=target_user,
        warning_count=0,
        is_suspended=False,
        is_banned=False
    )
    return target_user, moderation


@pytest.fixture
def suspended_user(db):
    user = User.objects.create_user(
        email='suspended@example.com',
        password='testpass123',
        first_name='Suspended',
        is_active=False,
        is_deleted=False
    )
    moderation = UserModeration.objects.create(
        user=user,
        warning_count=0,
        is_suspended=True,
        suspended_until=timezone.now() + timezone.timedelta(hours=24)
    )
    return user, moderation


@pytest.fixture
def banned_user(db):
    user = User.objects.create_user(
        email='banned@example.com',
        password='testpass123',
        first_name='Banned',
        is_active=False,
        is_deleted=False
    )
    moderation = UserModeration.objects.create(
        user=user,
        warning_count=0,
        is_banned=True,
        banned_at=timezone.now(),
        ban_reason='Test ban'
    )
    return user, moderation


@pytest.fixture
def deleted_user(db):
    user = User.objects.create_user(
        email='deleted@example.com',
        password='testpass123',
        first_name='Deleted',
        is_active=True,
        is_deleted=True
    )
    return user


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def moderator_request(request_factory, moderator):
    req = request_factory.get('/')
    req.user = moderator
    req.META = {'REMOTE_ADDR': '127.0.0.1'}
    return req


# ---------- Test class ----------
@pytest.mark.django_db
class TestUserCommand:

    # ---------- issue_warning ----------
    def test_issue_warning_success(self, moderator_request, target_user):
        data = {'reason': 'Spam content'}
        result = UserCommand.issue_warning(moderator_request, target_user.id, data)
        assert result.status_code == 200
        assert result.message == "Warning issued successfully"
        assert result.data['warning_count'] == 1

        # Check moderation record
        moderation = UserModeration.objects.get(user=target_user)
        assert moderation.warning_count == 1

        # Check audit log
        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.USER.value,
            content_id=target_user.id,
            action_type=ModeratorActionTypeEnum.WARNING.value
        ).first()
        assert action is not None
        assert action.reason == 'Spam content'
        assert action.metadata['warning_count'] == 1
        assert action.metadata['user_email'] == target_user.email

    def test_issue_warning_missing_reason(self, moderator_request, target_user):
        data = {}
        result = UserCommand.issue_warning(moderator_request, target_user.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required for issuing a warning"
        # No moderation record should be created
        assert not UserModeration.objects.filter(user=target_user).exists()

    def test_issue_warning_user_not_found(self, moderator_request):
        data = {'reason': 'test'}
        result = UserCommand.issue_warning(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "User not found"

    def test_issue_warning_multiple_warnings(self, moderator_request, target_user_with_moderation):
        target_user, moderation = target_user_with_moderation
        # First warning
        data1 = {'reason': 'First warning'}
        result1 = UserCommand.issue_warning(moderator_request, target_user.id, data1)
        assert result1.status_code == 200
        assert result1.data['warning_count'] == 1

        # Second warning
        data2 = {'reason': 'Second warning'}
        result2 = UserCommand.issue_warning(moderator_request, target_user.id, data2)
        assert result2.status_code == 200
        assert result2.data['warning_count'] == 2

        moderation.refresh_from_db()
        assert moderation.warning_count == 2

        # Two audit logs should exist
        actions = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.USER.value,
            content_id=target_user.id,
            action_type=ModeratorActionTypeEnum.WARNING.value
        )
        assert actions.count() == 2

    def test_issue_warning_soft_deleted_user(self, moderator_request, deleted_user):
        data = {'reason': 'Warning for deleted user'}
        result = UserCommand.issue_warning(moderator_request, deleted_user.id, data)
        # Should still work because we use all_including_deleted()
        assert result.status_code == 200
        moderation = UserModeration.objects.get(user=deleted_user)
        assert moderation.warning_count == 1

    # ---------- toggle_suspend_user ----------
    def test_toggle_suspend_user_suspend_success(self, moderator_request, target_user):
        data = {'reason': 'Violating rules', 'duration_hours': 48}
        result = UserCommand.toggle_suspend_user(moderator_request, target_user.id, data)
        assert result.status_code == 200
        assert "suspended until" in result.message
        assert result.data['is_suspended'] is True
        assert 'suspended_until' in result.data

        # Check moderation record
        moderation = UserModeration.objects.get(user=target_user)
        assert moderation.is_suspended is True
        assert moderation.suspended_until is not None

        # Check user active status
        target_user.refresh_from_db()
        assert target_user.is_active is False

        # Check audit log
        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.USER.value,
            content_id=target_user.id,
            action_type=ModeratorActionTypeEnum.SUSPEND.value
        ).first()
        assert action is not None
        assert action.reason == 'Violating rules'
        assert action.metadata['duration_hours'] == 48

    def test_toggle_suspend_user_suspend_default_duration(self, moderator_request, target_user):
        data = {'reason': 'Violating rules'}  # No duration provided
        result = UserCommand.toggle_suspend_user(moderator_request, target_user.id, data)
        assert result.status_code == 200
        assert "suspended until" in result.message

        moderation = UserModeration.objects.get(user=target_user)
        assert moderation.is_suspended is True
        # Duration should default to 24 hours
        assert moderation.suspended_until > timezone.now() + timezone.timedelta(hours=23)
        assert moderation.suspended_until <= timezone.now() + timezone.timedelta(hours=25)

    def test_toggle_suspend_user_suspend_invalid_duration(self, moderator_request, target_user):
        data = {'reason': 'Test', 'duration_hours': 'invalid'}
        result = UserCommand.toggle_suspend_user(moderator_request, target_user.id, data)
        assert result.status_code == 200
        # Should fallback to 24 hours
        moderation = UserModeration.objects.get(user=target_user)
        assert moderation.is_suspended is True
        assert moderation.suspended_until > timezone.now() + timezone.timedelta(hours=23)

    def test_toggle_suspend_user_unsuspend_success(self, moderator_request, suspended_user):
        user, moderation = suspended_user
        data = {'reason': 'User apologized'}
        result = UserCommand.toggle_suspend_user(moderator_request, user.id, data)
        assert result.status_code == 200
        assert result.message == "User unsuspended"
        assert result.data['is_suspended'] is False

        moderation.refresh_from_db()
        assert moderation.is_suspended is False
        assert moderation.suspended_until is None

        user.refresh_from_db()
        assert user.is_active is True

        # Check audit log - should be REINSTATE
        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.USER.value,
            content_id=user.id,
            action_type=ModeratorActionTypeEnum.REINSTATE.value
        ).first()
        assert action is not None
        assert action.metadata['action'] == 'unsuspend'

    def test_toggle_suspend_user_missing_reason(self, moderator_request, target_user):
        data = {}
        result = UserCommand.toggle_suspend_user(moderator_request, target_user.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required for suspending/unsuspending"
        # User should remain active
        target_user.refresh_from_db()
        assert target_user.is_active is True

    def test_toggle_suspend_user_not_found(self, moderator_request):
        data = {'reason': 'test'}
        result = UserCommand.toggle_suspend_user(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "User not found"

    # ---------- toggle_ban_user ----------
    def test_toggle_ban_user_ban_success(self, moderator_request, target_user):
        data = {'reason': 'Permanent ban for severe violations'}
        result = UserCommand.toggle_ban_user(moderator_request, target_user.id, data)
        assert result.status_code == 200
        assert result.message == "User banned permanently"
        assert result.data['is_banned'] is True
        assert 'banned_at' in result.data

        moderation = UserModeration.objects.get(user=target_user)
        assert moderation.is_banned is True
        assert moderation.banned_at is not None
        assert moderation.ban_reason == 'Permanent ban for severe violations'

        target_user.refresh_from_db()
        assert target_user.is_active is False

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.USER.value,
            content_id=target_user.id,
            action_type=ModeratorActionTypeEnum.BAN.value
        ).first()
        assert action is not None
        assert action.reason == 'Permanent ban for severe violations'

    def test_toggle_ban_user_unban_success(self, moderator_request, banned_user):
        user, moderation = banned_user
        data = {'reason': 'User appealed successfully'}
        result = UserCommand.toggle_ban_user(moderator_request, user.id, data)
        assert result.status_code == 200
        assert result.message == "User unbanned"
        assert result.data['is_banned'] is False

        moderation.refresh_from_db()
        assert moderation.is_banned is False
        assert moderation.banned_at is None

        user.refresh_from_db()
        assert user.is_active is True

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.USER.value,
            content_id=user.id,
            action_type=ModeratorActionTypeEnum.REINSTATE.value
        ).first()
        assert action is not None
        assert action.metadata['action'] == 'unban'

    def test_toggle_ban_user_missing_reason(self, moderator_request, target_user):
        data = {}
        result = UserCommand.toggle_ban_user(moderator_request, target_user.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required for banning/unbanning"
        target_user.refresh_from_db()
        assert target_user.is_active is True

    def test_toggle_ban_user_not_found(self, moderator_request):
        data = {'reason': 'test'}
        result = UserCommand.toggle_ban_user(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "User not found"

    # ---------- toggle_delete_user ----------
    def test_toggle_delete_user_soft_delete(self, moderator_request, target_user):
        data = {'reason': 'User requested deletion'}
        result = UserCommand.toggle_delete_user(moderator_request, target_user.id, data)
        assert result.status_code == 200
        assert result.message == "User deleted successfully"
        assert result.data['is_deleted'] is True

        target_user.refresh_from_db()
        assert target_user.is_deleted is True

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.USER.value,
            content_id=target_user.id,
            action_type=ModeratorActionTypeEnum.DELETE.value
        ).first()
        assert action is not None
        assert action.reason == 'User requested deletion'
        assert action.metadata['old_is_deleted'] is False
        assert action.metadata['new_is_deleted'] is True

    def test_toggle_delete_user_restore(self, moderator_request, deleted_user):
        data = {'reason': 'Restore user account'}
        result = UserCommand.toggle_delete_user(moderator_request, deleted_user.id, data)
        assert result.status_code == 200
        assert result.message == "User restored successfully"
        assert result.data['is_deleted'] is False

        deleted_user.refresh_from_db()
        assert deleted_user.is_deleted is False

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.USER.value,
            content_id=deleted_user.id,
            action_type=ModeratorActionTypeEnum.REINSTATE.value
        ).first()
        assert action is not None
        assert action.reason == 'Restore user account'

    def test_toggle_delete_user_missing_reason(self, moderator_request, target_user):
        data = {}
        result = UserCommand.toggle_delete_user(moderator_request, target_user.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required for toggling delete status"
        target_user.refresh_from_db()
        assert target_user.is_deleted is False

    def test_toggle_delete_user_not_found(self, moderator_request):
        data = {'reason': 'test'}
        result = UserCommand.toggle_delete_user(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "User not found"

    def test_toggle_suspend_user_unsuspend_clears_fields(self, moderator_request, suspended_user):
        user, moderation = suspended_user
        data = {'reason': 'Test unsuspend'}
        result = UserCommand.toggle_suspend_user(moderator_request, user.id, data)
        assert result.status_code == 200
        moderation.refresh_from_db()
        user.refresh_from_db()

        assert moderation.is_suspended is False
        assert moderation.suspended_until is None
        assert user.is_active is True

    # ---------- Atomicity Tests ----------
    def test_issue_warning_atomicity(self, moderator_request, target_user, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test'}
            with pytest.raises(IntegrityError):
                UserCommand.issue_warning(moderator_request, target_user.id, data)
            # No moderation record should be created
            assert not UserModeration.objects.filter(user=target_user).exists()

    def test_toggle_suspend_user_atomicity(self, moderator_request, target_user, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test', 'duration_hours': 24}
            with pytest.raises(IntegrityError):
                UserCommand.toggle_suspend_user(moderator_request, target_user.id, data)
            # No moderation record should be created
            assert not UserModeration.objects.filter(user=target_user).exists()
            # User should remain active
            target_user.refresh_from_db()
            assert target_user.is_active is True

    def test_toggle_ban_user_atomicity(self, moderator_request, target_user, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test'}
            with pytest.raises(IntegrityError):
                UserCommand.toggle_ban_user(moderator_request, target_user.id, data)
            # No moderation record should be created
            assert not UserModeration.objects.filter(user=target_user).exists()
            target_user.refresh_from_db()
            assert target_user.is_active is True

    def test_toggle_delete_user_atomicity(self, moderator_request, target_user, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test'}
            with pytest.raises(IntegrityError):
                UserCommand.toggle_delete_user(moderator_request, target_user.id, data)
            target_user.refresh_from_db()
            assert target_user.is_deleted is False