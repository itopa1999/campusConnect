import pytest
from unittest.mock import patch, MagicMock, ANY
from celery.exceptions import OperationalError
from django.core.exceptions import ObjectDoesNotExist
from django.test import RequestFactory
from django.utils import timezone

from apps.users.models import User, VerificationToken
from utils.enums import TokenType, BadgeChoiceEnum, FeatureFlagEnum, GroupNames
from utils.base_result import BaseResultWithData
from utils.constant_helper import ConstantHelper

# Adjust import path as needed – assuming the command lives in apps/users/BBL/Commands/account_command.py
from apps.users.BBL.Commands.account_command import AccountCommand


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def request_factory():
    return RequestFactory()

@pytest.fixture
def mock_email_tasks():
    """Mock the background email tasks."""
    with patch("apps.users.BBL.Commands.account_command.background_task_send_verification_email.delay") as mock_verify, \
         patch("apps.users.BBL.Commands.account_command.background_task_send_account_verify_email.delay") as mock_account_verify:
        yield mock_verify, mock_account_verify

@pytest.fixture
def mock_feature_flag():
    """Mock is_feature_active to return True for account bonus."""
    with patch("apps.users.BBL.Commands.account_command.is_feature_active") as mock:
        mock.return_value = True
        yield mock

@pytest.fixture
def test_user(db):
    """Create a user with email not verified."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
        phone="08012345678",
        email_verified=False,
        is_active=True,
    )
    return user

@pytest.fixture
def verified_user(db):
    """Create a user with email already verified."""
    user = User.objects.create_user(
        email="verified@example.com",
        password="testpass123",
        first_name="Verified",
        last_name="User",
        phone="08087654321",
        email_verified=True,
        is_active=True,
    )
    return user

@pytest.fixture
def verification_token(test_user):
    """Create a valid verification token (integer)."""
    token = VerificationToken.generate_token()
    return VerificationToken.objects.create(
        user=test_user,
        token=token,
        token_type=TokenType.EMAIL_VERIFICATION.value,
    )

@pytest.fixture
def expired_token(test_user):
    """Create an expired verification token (integer)."""
    token = VerificationToken.generate_token()
    return VerificationToken.objects.create(
        user=test_user,
        token=token,
        token_type=TokenType.EMAIL_VERIFICATION.value,
        expires_at=timezone.now() - timezone.timedelta(days=1),
    )


# ── Tests: Execute (registration) ────────────────────────────────────

class TestAccountCommandExecute:

    def test_execute_success(self, db, request_factory, mock_email_tasks, mock_feature_flag):
        """Happy path: create a new user with valid data."""
        request = request_factory.post("/")
        data = {
            "email": "new@example.com",
            "phone": "08023456789",
            "first_name": "New",
            "last_name": "User",
            "password": "strongpassword123",
        }
        result = AccountCommand.Execute(request, data)
        assert result.is_success is True
        assert result.status_code == 201
        assert "user_id" in result.data
        user = User.objects.get(id=result.data["user_id"])
        assert user.email == "new@example.com"
        assert user.phone == "08023456789"
        assert user.email_verified is False
        assert user.is_active is True
        assert user.user_badges.filter(name=BadgeChoiceEnum.UN_VERIFIED.value).exists()
        mock_email_tasks[0].assert_called_once()

    def test_execute_duplicate_email(self, db, request_factory, test_user):
        """Duplicate email should fail."""
        request = request_factory.post("/")
        data = {
            "email": test_user.email,
            "phone": "08099999999",
            "first_name": "Duplicate",
            "last_name": "User",
            "password": "strongpass",
        }
        result = AccountCommand.Execute(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Email already registered" in result.message

    def test_execute_duplicate_phone(self, db, request_factory, test_user):
        """Duplicate phone should fail."""
        request = request_factory.post("/")
        data = {
            "email": "different@example.com",
            "phone": test_user.phone,
            "first_name": "Duplicate",
            "last_name": "User",
            "password": "strongpass",
        }
        result = AccountCommand.Execute(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Phone already registered" in result.message

    def test_execute_invalid_phone(self, db, request_factory):
        """Invalid Nigerian phone number should fail."""
        request = request_factory.post("/")
        data = {
            "email": "new@example.com",
            "phone": "12345",  # invalid
            "first_name": "New",
            "last_name": "User",
            "password": "strongpass",
        }
        result = AccountCommand.Execute(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Invalid Nigerian phone number" in result.message

    def test_execute_weak_password(self, db, request_factory):
        """Password shorter than 8 characters should fail."""
        request = request_factory.post("/")
        data = {
            "email": "new@example.com",
            "phone": "08023456789",
            "first_name": "New",
            "last_name": "User",
            "password": "123",  # weak
        }
        result = AccountCommand.Execute(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Password must be at least 8 characters" in result.message

    def test_execute_email_task_fails(self, db, request_factory, mock_feature_flag):
        """If email task fails with celery's OperationalError, account should still be created."""
        with patch("apps.users.BBL.Commands.account_command.background_task_send_verification_email.delay") as mock_task:
            mock_task.side_effect = OperationalError("Email service down")
            request = request_factory.post("/")
            data = {
                "email": "new@example.com",
                "phone": "08023456789",
                "first_name": "New",
                "last_name": "User",
                "password": "strongpassword123",
            }
            result = AccountCommand.Execute(request, data)
            assert result.is_success is True
            assert result.status_code == 201
            assert User.objects.filter(email="new@example.com").exists()

    def test_execute_general_exception(self, db, request_factory):
        """Catch any unexpected exception and return 400."""
        with patch("apps.users.BBL.Commands.account_command.User.objects.create_user", side_effect=Exception("DB error")):
            request = request_factory.post("/")
            data = {
                "email": "new@example.com",
                "phone": "08023456789",
                "first_name": "New",
                "last_name": "User",
                "password": "strongpassword123",
            }
            result = AccountCommand.Execute(request, data)
            assert result.is_success is False
            assert result.status_code == 400
            assert "Error creating account" in result.message


# ── Tests: VerifyEmail ───────────────────────────────────────────────

class TestAccountCommandVerifyEmail:

    def test_verify_email_success(self, db, request_factory, verification_token, mock_email_tasks):
        """Happy path: verify a valid token."""
        request = request_factory.get("/")
        result = AccountCommand.VerifyEmail(request, verification_token.token)
        assert result.is_success is True
        assert result.status_code == 200
        user = verification_token.user
        user.refresh_from_db()
        assert user.email_verified is True
        assert user.is_active is True
        assert not user.user_badges.filter(name=BadgeChoiceEnum.UN_VERIFIED.value).exists()
        assert user.user_badges.filter(name=BadgeChoiceEnum.VERIFIED.value).exists()
        verification_token.refresh_from_db()
        assert verification_token.is_used is True
        mock_email_tasks[1].assert_called_once()

    def test_verify_email_invalid_token(self, db, request_factory):
        """Invalid token (string) should be caught and return 500."""
        request = request_factory.get("/")
        result = AccountCommand.VerifyEmail(request, "invalidtoken")
        assert result.is_success is False
        assert result.status_code == 500
        assert "Error verifying email" in result.message

    def test_verify_email_expired_token(self, db, request_factory, expired_token):
        """Expired token should fail."""
        request = request_factory.get("/")
        result = AccountCommand.VerifyEmail(request, expired_token.token)
        assert result.is_success is False
        assert result.status_code == 400
        assert "has expired" in result.message

    def test_verify_email_token_already_used(self, db, request_factory, verification_token):
        """Token already used should fail."""
        verification_token.is_used = True
        verification_token.save()
        request = request_factory.get("/")
        result = AccountCommand.VerifyEmail(request, verification_token.token)
        assert result.is_success is False
        assert result.status_code == 400
        assert "used" in result.message or "expired" in result.message

    def test_verify_email_task_fails(self, db, request_factory, verification_token):
        """If email task fails with celery's OperationalError, verification still succeeds."""
        with patch("apps.users.BBL.Commands.account_command.background_task_send_account_verify_email.delay") as mock_task:
            mock_task.side_effect = OperationalError("Email error")
            request = request_factory.get("/")
            result = AccountCommand.VerifyEmail(request, verification_token.token)
            assert result.is_success is True
            assert result.status_code == 200
            user = verification_token.user
            user.refresh_from_db()
            assert user.email_verified is True

    def test_verify_email_exception(self, db, request_factory, verification_token):
        """Catch unexpected exception and return 500."""
        with patch("apps.users.BBL.Commands.account_command.VerificationToken.objects.filter", side_effect=Exception("DB error")):
            request = request_factory.get("/")
            result = AccountCommand.VerifyEmail(request, verification_token.token)
            assert result.is_success is False
            assert result.status_code == 500
            assert "Error verifying email" in result.message


# ── Tests: ResendEmail ───────────────────────────────────────────────

class TestAccountCommandResendEmail:

    def test_resend_email_success(self, db, request_factory, test_user, mock_email_tasks):
        """Resend verification email to an unverified user."""
        request = request_factory.post("/")
        data = {"email": test_user.email}
        result = AccountCommand.ResendEmail(request, data)
        assert result.is_success is True
        assert result.status_code == 200
        assert "Account created successfully" in result.message
        token_count = VerificationToken.objects.filter(
            user=test_user, token_type=TokenType.EMAIL_VERIFICATION.value, is_used=False
        ).count()
        assert token_count == 1
        mock_email_tasks[0].assert_called_once()

    def test_resend_email_user_not_found(self, db, request_factory):
        """If user not found, still return 200 (for security)."""
        request = request_factory.post("/")
        data = {"email": "nonexistent@example.com"}
        result = AccountCommand.ResendEmail(request, data)
        assert result.is_success is True
        assert result.status_code == 200
        assert "If this email is registered" in result.message

    def test_resend_email_user_already_verified(self, db, request_factory, verified_user):
        """If user already verified, still return 200 (for security)."""
        request = request_factory.post("/")
        data = {"email": verified_user.email}
        result = AccountCommand.ResendEmail(request, data)
        assert result.is_success is True
        assert result.status_code == 200
        assert "If this email is registered" in result.message
        token_count = VerificationToken.objects.filter(user=verified_user).count()
        assert token_count == 0

    def test_resend_email_task_fails(self, db, request_factory, test_user):
        """If email task fails with celery's OperationalError, still return success."""
        with patch("apps.users.BBL.Commands.account_command.background_task_send_verification_email.delay") as mock_task:
            mock_task.side_effect = OperationalError("Email error")
            request = request_factory.post("/")
            data = {"email": test_user.email}
            result = AccountCommand.ResendEmail(request, data)
            assert result.is_success is True
            assert result.status_code == 200
            assert VerificationToken.objects.filter(
                user=test_user, token_type=TokenType.EMAIL_VERIFICATION.value, is_used=False
            ).exists()


# ── Test helper methods (indirectly) ────────────────────────────────

class TestAccountCommandHelpers:

    def test_create_verification_token_creates_token(self, db, test_user):
        """_create_verification_token should create a new token and invalidate old ones."""
        old_token_val = 12345
        old_token = VerificationToken.objects.create(
            user=test_user,
            token=old_token_val,
            token_type=TokenType.EMAIL_VERIFICATION.value,
            is_used=False,
        )
        new_token = AccountCommand._create_verification_token(test_user)
        assert new_token is not None
        assert new_token.token != old_token_val
        old_token.refresh_from_db()
        assert old_token.is_used is True

    def test_verify_token_valid(self, db, verification_token):
        """_verify_token should return True for a valid token."""
        is_valid, result = AccountCommand._verify_token(verification_token.token, TokenType.EMAIL_VERIFICATION.value)
        assert is_valid is True
        assert result == verification_token
        verification_token.refresh_from_db()
        assert verification_token.is_used is True

    def test_verify_token_invalid(self, db):
        """_verify_token should return False for invalid token (non-existent integer)."""
        is_valid, result = AccountCommand._verify_token(99999, TokenType.EMAIL_VERIFICATION.value)
        assert is_valid is False
        assert "Invalid token" in result

    def test_verify_token_expired(self, db, expired_token):
        """_verify_token should return False for expired token."""
        is_valid, result = AccountCommand._verify_token(expired_token.token, TokenType.EMAIL_VERIFICATION.value)
        assert is_valid is False
        assert "expired" in result