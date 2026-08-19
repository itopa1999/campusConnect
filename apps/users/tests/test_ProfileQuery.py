import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory

from apps.users.BBL.Queries.profile import ProfileQuery
from apps.users.models import User
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

    def test_get_profile_detail_cache_hit(self, request_factory, test_user):
        """Return cached data if available."""
        cached_data = {"id": 1, "email": "test@example.com"}
        with patch("apps.users.BBL.Queries.profile.GlobalCache.aget_or_set") as mock_aget_or_set:
            mock_aget_or_set.return_value = cached_data
            request = request_factory.get("/")
            result = ProfileQuery.get_profile_detail(request, test_user)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.data == cached_data
        mock_aget_or_set.assert_called_once()
        # Check that the callback is not executed because cache hit

    def test_get_profile_detail_cache_miss(self, request_factory, test_user):
        """Fetch from serializer, cache, and return."""
        expected_data = {"id": 1, "email": "test@example.com"}
        with patch("apps.users.BBL.Queries.profile.GlobalCache.aget_or_set") as mock_aget_or_set:
            # Simulate cache miss: aget_or_set calls the callback
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch("apps.users.BBL.Queries.profile.ProfileSerializer") as mock_serializer:
                mock_serializer.return_value.data = expected_data
                request = request_factory.get("/")
                result = ProfileQuery.get_profile_detail(request, test_user)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.data == expected_data
        mock_serializer.assert_called_once_with(test_user, context={'request': request})
        mock_aget_or_set.assert_called_once()

    def test_get_profile_detail_serializer_exception(self, request_factory, test_user):
        """If serializer raises an exception, it should propagate."""
        with patch("apps.users.BBL.Queries.profile.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()  # callback will raise
            mock_aget_or_set.side_effect = side_effect

            with patch("apps.users.BBL.Queries.profile.ProfileSerializer") as mock_serializer:
                mock_serializer.side_effect = Exception("Serializer error")
                with pytest.raises(Exception) as excinfo:
                    ProfileQuery.get_profile_detail(request_factory.get("/"), test_user)
                assert "Serializer error" in str(excinfo.value)

    def test_get_profile_detail_cache_key_format(self, request_factory, test_user):
        """Ensure the cache key is formatted correctly."""
        expected_key = CacheKeysEnum.format(CacheKeysEnum.PROFILE, user_id=test_user.id)
        with patch("apps.users.BBL.Queries.profile.GlobalCache.aget_or_set") as mock_aget_or_set:
            # Simulate cache miss
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                assert key == expected_key
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch("apps.users.BBL.Queries.profile.ProfileSerializer") as mock_serializer:
                mock_serializer.return_value.data = {"id": 1}
                request = request_factory.get("/")
                ProfileQuery.get_profile_detail(request, test_user)

            mock_aget_or_set.assert_called_once_with(
                key=expected_key,
                callback=mock_aget_or_set.call_args[1]['callback'],
                timeout=86400,
                lock_timeout=30,
                max_wait=5.0,
            )