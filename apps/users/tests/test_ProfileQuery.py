import pytest
from unittest.mock import patch, MagicMock, ANY
from django.test import RequestFactory
from django.core.exceptions import ObjectDoesNotExist

from apps.users.BBL.Queries.profile import ProfileQuery
from apps.users.models import User
from apps.users.serializers import ProfileSerializer
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
        phone="08012345678",
    )
    return user

@pytest.fixture
def mock_cache():
    with patch("apps.users.BBL.Queries.profile.GlobalCache") as mock:
        yield mock

@pytest.fixture
def mock_serializer():
    with patch("apps.users.BBL.Queries.profile.ProfileSerializer") as mock:
        mock_instance = MagicMock()
        mock_instance.data = {"id": 1, "email": "test@example.com"}
        mock.return_value = mock_instance
        yield mock


# ── Tests ─────────────────────────────────────────────────────────────

class TestProfileQuery:

    def test_get_profile_detail_cache_hit(self, mock_cache, request_factory, test_user):
        """Return cached data if available."""
        cached_data = {"id": 1, "email": "test@example.com"}
        mock_cache.get.return_value = cached_data

        request = request_factory.get("/")
        result = ProfileQuery.get_profile_detail(request, test_user)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.data == cached_data
        mock_cache.get.assert_called_once_with(
            CacheKeysEnum.format(CacheKeysEnum.PROFILE, user_id=test_user.id)
        )
        # Cache set should not be called
        mock_cache.set.assert_not_called()

    def test_get_profile_detail_cache_miss(self, mock_cache, mock_serializer, request_factory, test_user):
        """Fetch from serializer, cache, and return."""
        mock_cache.get.return_value = None

        request = request_factory.get("/")
        result = ProfileQuery.get_profile_detail(request, test_user)

        assert result.is_success is True
        assert result.status_code == 200
        expected_data = {"id": 1, "email": "test@example.com"}
        assert result.data == expected_data

        # Serializer should have been called with user and context
        mock_serializer.assert_called_once_with(test_user, context={'request': request})

        # Cache should have been set
        cache_key = CacheKeysEnum.format(CacheKeysEnum.PROFILE, user_id=test_user.id)
        mock_cache.set.assert_called_once_with(cache_key, expected_data)

    def test_get_profile_detail_serializer_exception(self, mock_cache, request_factory, test_user):
        """If serializer raises an exception, it should propagate (not caught)."""
        mock_cache.get.return_value = None
        with patch("apps.users.BBL.Queries.profile.ProfileSerializer") as mock_serializer:
            mock_serializer.side_effect = Exception("Serializer error")
            with pytest.raises(Exception) as excinfo:
                ProfileQuery.get_profile_detail(request_factory.get("/"), test_user)
            assert "Serializer error" in str(excinfo.value)

    def test_get_profile_detail_cache_key_format(self, mock_cache, request_factory, test_user):
        """Ensure the cache key is formatted correctly."""
        mock_cache.get.return_value = None
        with patch("apps.users.BBL.Queries.profile.ProfileSerializer") as mock_serializer:
            mock_serializer.return_value.data = {"id": 1}
            request = request_factory.get("/")
            ProfileQuery.get_profile_detail(request, test_user)

        expected_key = CacheKeysEnum.format(CacheKeysEnum.PROFILE, user_id=test_user.id)
        mock_cache.get.assert_called_once_with(expected_key)
        mock_cache.set.assert_called_once_with(expected_key, {"id": 1})