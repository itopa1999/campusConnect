import pytest
from unittest.mock import patch, MagicMock, ANY
from celery.exceptions import OperationalError
from django.test import RequestFactory
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from apps.users.BBL.Commands.auth_command import AuthCommand
from apps.users.models import User, VerificationToken
from utils.enums import TokenType, BadgeChoiceEnum


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def request_factory():
    return RequestFactory()

@pytest.fixture
def mock_email_tasks():
    """Mock all email background tasks."""
    with patch("apps.users.BBL.Commands.auth_command.background_task_send_password_reset_email.delay") as mock_reset, \
         patch("apps.users.BBL.Commands.auth_command.background_task_send_notification_email.delay") as mock_notify, \
         patch("apps.users.BBL.Commands.auth_command.background_task_send_change_password_email.delay") as mock_change:
        yield mock_reset, mock_notify, mock_change

@pytest.fixture
def test_user(db):
    """Create a verified, active user."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
        phone="08012345678",
        email_verified=True,
        is_active=True,
    )
    return user

@pytest.fixture
def unverified_user(db):
    """Create a user with email not verified."""
    user = User.objects.create_user(
        email="unverified@example.com",
        password="testpass123",
        first_name="Unverified",
        last_name="User",
        phone="08087654321",
        email_verified=False,
        is_active=True,
    )
    return user

@pytest.fixture
def inactive_user(db):
    """Create an inactive user."""
    user = User.objects.create_user(
        email="inactive@example.com",
        password="testpass123",
        first_name="Inactive",
        last_name="User",
        phone="08011223344",
        email_verified=True,
        is_active=False,
    )
    return user

@pytest.fixture
def mock_refresh_token():
    """Mock RefreshToken class and its methods."""
    with patch("apps.users.BBL.Commands.auth_command.RefreshToken") as mock_refresh:
        mock_token = MagicMock()
        # Mock access_token so str(access_token) returns a string
        mock_access = MagicMock()
        mock_access.__str__ = MagicMock(return_value="new_access_token")
        mock_token.access_token = mock_access
        # Mock the refresh token itself so str(refresh) returns a string
        mock_token.__str__ = MagicMock(return_value="new_refresh_token")
        # When RefreshToken is instantiated with a token string, return mock_token
        mock_refresh.return_value = mock_token
        # When RefreshToken.for_user(user) is called, return mock_token
        mock_refresh.for_user.return_value = mock_token
        yield mock_refresh, mock_token


# ── Tests: login (Execute) ───────────────────────────────────────────

class TestAuthCommandExecute:

    def test_login_success(self, db, request_factory, test_user, mock_refresh_token):
        """Happy path: login with valid credentials."""
        request = request_factory.post("/")
        data = {"email": test_user.email, "password": "testpass123"}
        result = AuthCommand.Execute(request, data)
        assert result.is_success is True
        assert result.status_code == 200
        assert "access_token" in result.data
        assert "refresh_token" in result.data
        assert result.data["user_id"] == test_user.id
        assert result.data["email"] == test_user.email
        assert result.data["is_email_verified"] is True
        mock_refresh_token[0].for_user.assert_called_once_with(test_user)

    def test_login_user_not_found(self, db, request_factory):
        """Invalid email should return 400."""
        request = request_factory.post("/")
        data = {"email": "nonexistent@example.com", "password": "testpass123"}
        result = AuthCommand.Execute(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Invalid email or password" in result.message

    def test_login_wrong_password(self, db, request_factory, test_user):
        """Wrong password should return 400."""
        request = request_factory.post("/")
        data = {"email": test_user.email, "password": "wrongpass"}
        result = AuthCommand.Execute(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Invalid email or password" in result.message

    def test_login_unverified_email(self, db, request_factory, unverified_user):
        """Unverified email should return 400."""
        request = request_factory.post("/")
        data = {"email": unverified_user.email, "password": "testpass123"}
        result = AuthCommand.Execute(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Email not verified" in result.message

    def test_login_inactive_account(self, db, request_factory, inactive_user):
        """Inactive account should return 400."""
        request = request_factory.post("/")
        data = {"email": inactive_user.email, "password": "testpass123"}
        result = AuthCommand.Execute(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "account has been deactivated" in result.message

    def test_login_exception(self, db, request_factory):
        """Catch unexpected exception and return 500."""
        with patch("apps.users.BBL.Commands.auth_command.User.objects.filter", side_effect=Exception("DB error")):
            request = request_factory.post("/")
            data = {"email": "test@example.com", "password": "testpass123"}
            result = AuthCommand.Execute(request, data)
            assert result.is_success is False
            assert result.status_code == 500
            assert "Error during login" in result.message


# ── Tests: ForgotPassword ────────────────────────────────────────────

class TestAuthCommandForgotPassword:

    def test_forgot_password_success(self, db, request_factory, test_user, mock_email_tasks):
        """Happy path: send password reset link."""
        request = request_factory.post("/")
        data = {"email": test_user.email}
        with patch("apps.users.BBL.Commands.auth_command.AccountCommand._create_verification_token") as mock_token:
            mock_token.return_value = MagicMock(token="12345")
            result = AuthCommand.ForgotPassword(request, data)
        assert result.is_success is True
        assert result.status_code == 200
        assert "If an account with that email exists" in result.message
        mock_email_tasks[0].assert_called_once()  # password reset email
        mock_token.assert_called_once_with(test_user, token_type=TokenType.PASSWORD_RESET.value)

    def test_forgot_password_user_not_found(self, db, request_factory):
        """User not found – still return 200 (security) but with error message? Actually code returns 400."""
        # The code currently returns 400 with "Account with email doesn't exists"
        request = request_factory.post("/")
        data = {"email": "nonexistent@example.com"}
        result = AuthCommand.ForgotPassword(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Account with email doesn't exists" in result.message

    def test_forgot_password_unverified_email(self, db, request_factory, unverified_user):
        """Unverified email should fail."""
        request = request_factory.post("/")
        data = {"email": unverified_user.email}
        result = AuthCommand.ForgotPassword(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Email not verified" in result.message

    def test_forgot_password_email_task_fails(self, db, request_factory, test_user, mock_email_tasks):
        """If email task fails with OperationalError, still return success."""
        mock_email_tasks[0].side_effect = OperationalError("Email error")
        request = request_factory.post("/")
        data = {"email": test_user.email}
        with patch("apps.users.BBL.Commands.auth_command.AccountCommand._create_verification_token") as mock_token:
            mock_token.return_value = MagicMock(token="12345")
            result = AuthCommand.ForgotPassword(request, data)
        assert result.is_success is True
        assert result.status_code == 200

    def test_forgot_password_exception(self, db, request_factory):
        """Catch unexpected exception and return 500."""
        with patch("apps.users.BBL.Commands.auth_command.User.objects.filter", side_effect=Exception("DB error")):
            request = request_factory.post("/")
            data = {"email": "test@example.com"}
            result = AuthCommand.ForgotPassword(request, data)
            assert result.is_success is False
            assert result.status_code == 500
            assert "Error processing password reset" in result.message


# ── Tests: VerifyForgetPasswordEmail ────────────────────────────────

class TestAuthCommandVerifyForgetPasswordEmail:

    def test_verify_token_success(self, db, request_factory, test_user):
        """Valid token should succeed."""
        token = VerificationToken.objects.create(
            user=test_user,
            token=12345,
            token_type=TokenType.PASSWORD_RESET.value,
        )
        request = request_factory.get("/")
        result = AuthCommand.VerifyForgetPasswordEmail(request, token.token)
        assert result.is_success is True
        assert result.status_code == 200
        assert result.data["user_id"] == test_user.id
        assert result.data["email"] == test_user.email

    def test_verify_token_invalid(self, db, request_factory):
        """Invalid token should fail."""
        request = request_factory.get("/")
        result = AuthCommand.VerifyForgetPasswordEmail(request, "invalidtoken")
        # The code will raise ValueError and return 500 (bug), but we test current behavior
        assert result.is_success is False
        assert result.status_code == 500
        assert "Error verifying password reset token" in result.message

    def test_verify_token_expired(self, db, request_factory, test_user):
        """Expired token should fail."""
        token = VerificationToken.objects.create(
            user=test_user,
            token=12345,
            token_type=TokenType.PASSWORD_RESET.value,
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        request = request_factory.get("/")
        result = AuthCommand.VerifyForgetPasswordEmail(request, token.token)
        assert result.is_success is False
        assert result.status_code == 400
        assert "expired" in result.message

    def test_verify_token_exception(self, db, request_factory, test_user):
        """Catch unexpected exception and return 500."""
        token = VerificationToken.objects.create(
            user=test_user,
            token=12345,
            token_type=TokenType.PASSWORD_RESET.value,
        )
        with patch("apps.users.BBL.Commands.auth_command.AccountCommand._verify_token", side_effect=Exception("DB error")):
            request = request_factory.get("/")
            result = AuthCommand.VerifyForgetPasswordEmail(request, token.token)
            assert result.is_success is False
            assert result.status_code == 500
            assert "Error verifying password reset token" in result.message


# ── Tests: ConfirmResetPassword ──────────────────────────────────────

class TestAuthCommandConfirmResetPassword:

    def test_confirm_reset_success(self, db, request_factory, test_user, mock_email_tasks):
        """Happy path: reset password."""
        request = request_factory.post("/")
        data = {
            "user_id": test_user.id,
            "email": test_user.email,
            "password": "newpass123",
            "confirm_password": "newpass123",
        }
        result = AuthCommand.ConfirmResetPassword(request, data)
        assert result.is_success is True
        assert result.status_code == 200
        test_user.refresh_from_db()
        assert test_user.check_password("newpass123") is True
        mock_email_tasks[1].assert_called_once()  # notification email

    def test_confirm_reset_password_mismatch(self, db, request_factory, test_user):
        """Password and confirm mismatch should fail."""
        request = request_factory.post("/")
        data = {
            "user_id": test_user.id,
            "email": test_user.email,
            "password": "newpass123",
            "confirm_password": "different",
        }
        result = AuthCommand.ConfirmResetPassword(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Password and confirm password do not match" in result.message

    def test_confirm_reset_user_not_found(self, db, request_factory):
        """User not found or inactive should fail."""
        request = request_factory.post("/")
        data = {
            "user_id": 9999,
            "email": "nonexistent@example.com",
            "password": "newpass123",
            "confirm_password": "newpass123",
        }
        result = AuthCommand.ConfirmResetPassword(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Account has issues" in result.message

    def test_confirm_reset_email_task_fails(self, db, request_factory, test_user, mock_email_tasks):
        """If email task fails with OperationalError, still return success."""
        mock_email_tasks[1].side_effect = OperationalError("Email error")
        request = request_factory.post("/")
        data = {
            "user_id": test_user.id,
            "email": test_user.email,
            "password": "newpass123",
            "confirm_password": "newpass123",
        }
        result = AuthCommand.ConfirmResetPassword(request, data)
        assert result.is_success is True
        assert result.status_code == 200

    def test_confirm_reset_exception(self, db, request_factory):
        """Catch unexpected exception and return 500."""
        with patch("apps.users.BBL.Commands.auth_command.User.objects.filter", side_effect=Exception("DB error")):
            request = request_factory.post("/")
            data = {
                "user_id": 1,
                "email": "test@example.com",
                "password": "newpass123",
                "confirm_password": "newpass123",
            }
            result = AuthCommand.ConfirmResetPassword(request, data)
            assert result.is_success is False
            assert result.status_code == 500
            assert "Error resetting password" in result.message


# ── Tests: ChangePassword ────────────────────────────────────────────

class TestAuthCommandChangePassword:

    def test_change_password_success(self, db, request_factory, test_user, mock_email_tasks):
        """Happy path: change password."""
        request = request_factory.post("/")
        request.user = test_user
        data = {
            "current_password": "testpass123",
            "new_password": "newpass456",
        }
        result = AuthCommand.ChangePassword(request, data)
        assert result.is_success is True
        assert result.status_code == 200
        test_user.refresh_from_db()
        assert test_user.check_password("newpass456") is True
        mock_email_tasks[2].assert_called_once()  # change password email

    def test_change_password_wrong_current(self, db, request_factory, test_user):
        """Wrong current password should fail."""
        request = request_factory.post("/")
        request.user = test_user
        data = {
            "current_password": "wrongpass",
            "new_password": "newpass456",
        }
        result = AuthCommand.ChangePassword(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Current password is incorrect" in result.message

    def test_change_password_short_new(self, db, request_factory, test_user):
        """New password too short should fail."""
        request = request_factory.post("/")
        request.user = test_user
        data = {
            "current_password": "testpass123",
            "new_password": "123",
        }
        result = AuthCommand.ChangePassword(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "New password must be at least 8 characters" in result.message

    def test_change_password_email_task_fails(self, db, request_factory, test_user, mock_email_tasks):
        """If email task fails with OperationalError, still return success."""
        mock_email_tasks[2].side_effect = OperationalError("Email error")
        request = request_factory.post("/")
        request.user = test_user
        data = {
            "current_password": "testpass123",
            "new_password": "newpass456",
        }
        result = AuthCommand.ChangePassword(request, data)
        assert result.is_success is True
        assert result.status_code == 200

    def test_change_password_exception(self, db, request_factory, test_user):
        """Catch unexpected exception and return 500."""
        with patch("apps.users.BBL.Commands.auth_command.User.check_password", side_effect=Exception("DB error")):
            request = request_factory.post("/")
            request.user = test_user
            data = {
                "current_password": "testpass123",
                "new_password": "newpass456",
            }
            result = AuthCommand.ChangePassword(request, data)
            assert result.is_success is False
            assert result.status_code == 500
            assert "Error changing password" in result.message


# ── Tests: RefreshToken ──────────────────────────────────────────────

class TestAuthCommandRefreshToken:

    def test_refresh_token_success(self, db, request_factory, test_user, mock_refresh_token):
        """Happy path: refresh token."""
        request = request_factory.post("/")
        data = {"refresh_token": "old_refresh_token"}
        # Mock the RefreshToken instance
        mock_refresh, mock_token = mock_refresh_token
        mock_token.payload = {"user_id": test_user.id}

        result = AuthCommand.RefreshToken(request, data)
        assert result.is_success is True
        assert result.status_code == 200
        assert result.data["access_token"] == "new_access_token"
        assert result.data["refresh_token"] == "new_refresh_token"
        mock_refresh.assert_called_with("old_refresh_token")
        mock_refresh.for_user.assert_called_once_with(test_user)

    def test_refresh_token_invalid(self, db, request_factory):
        """Invalid refresh token should fail."""
        with patch("apps.users.BBL.Commands.auth_command.RefreshToken") as mock_refresh:
            mock_refresh.side_effect = InvalidToken("Invalid token")
            request = request_factory.post("/")
            data = {"refresh_token": "invalid"}
            result = AuthCommand.RefreshToken(request, data)
            assert result.is_success is False
            assert result.status_code == 400
            assert "Invalid or expired refresh token" in result.message

    def test_refresh_token_missing_user_id(self, db, request_factory):
        """Token payload missing user_id should fail."""
        with patch("apps.users.BBL.Commands.auth_command.RefreshToken") as mock_refresh:
            mock_token = MagicMock()
            mock_token.payload = {}  # no user_id
            mock_refresh.return_value = mock_token
            request = request_factory.post("/")
            data = {"refresh_token": "old"}
            result = AuthCommand.RefreshToken(request, data)
            assert result.is_success is False
            assert result.status_code == 400
            assert "Invalid token payload" in result.message

    def test_refresh_token_user_not_found(self, db, request_factory):
        """User not found or not eligible should fail."""
        with patch("apps.users.BBL.Commands.auth_command.RefreshToken") as mock_refresh:
            mock_token = MagicMock()
            mock_token.payload = {"user_id": 9999}
            mock_refresh.return_value = mock_token
            request = request_factory.post("/")
            data = {"refresh_token": "old"}
            result = AuthCommand.RefreshToken(request, data)
            assert result.is_success is False
            assert result.status_code == 404
            assert "User account not found" in result.message

    def test_refresh_token_blacklist_enabled(self, db, request_factory, test_user, mock_refresh_token):
        """Test blacklist when SIMPLE_JWT['BLACKLIST_AFTER_ROTATION'] is True."""
        # Patch settings
        with patch("apps.users.BBL.Commands.auth_command.settings") as mock_settings:
            mock_settings.SIMPLE_JWT = {"BLACKLIST_AFTER_ROTATION": True}
            mock_refresh, mock_token = mock_refresh_token
            mock_token.payload = {"user_id": test_user.id}
            request = request_factory.post("/")
            data = {"refresh_token": "old"}
            result = AuthCommand.RefreshToken(request, data)
            assert result.is_success is True
            mock_token.blacklist.assert_called_once()

    def test_refresh_token_exception(self, db, request_factory):
        """Catch unexpected exception and return 500."""
        with patch("apps.users.BBL.Commands.auth_command.RefreshToken", side_effect=Exception("DB error")):
            request = request_factory.post("/")
            data = {"refresh_token": "old"}
            result = AuthCommand.RefreshToken(request, data)
            assert result.is_success is False
            assert result.status_code == 500
            assert "Unable to refresh token" in result.message