import pytest
from datetime import timedelta
from unittest.mock import patch, ANY
from django.utils import timezone
from django.test import RequestFactory

from apps.campus.BBL.Queries.get_dashboard import DashboardQuery
from apps.campus.models import Listing, Review, Category, CampusHotspot
from apps.users.models import User
from utils.enums import ListingStatusType, ListingType


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def test_user(db):
    """Create a test user with some profile fields."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass",
        first_name="Test",
        last_name="User",
        phone="08012345678",
        department="Computer Science",
        level=3,
        matric_number="MAT/12345"
    )
    user.sold_items = 2
    user.average_rating = 4.5
    user.save()
    return user

@pytest.fixture
def test_category(db):
    return Category.objects.create(name="Electronics", description="Gadgets")

@pytest.fixture
def test_hotspots(db):
    return [
        CampusHotspot.objects.create(name="Library", description="Main library"),
        CampusHotspot.objects.create(name="Cafeteria", description="Student center"),
    ]

@pytest.fixture
def active_listings(test_user, test_category, test_hotspots):
    """Create 3 active listings with varying expiration dates."""
    now = timezone.now()
    listings = []
    for i in range(3):
        expires_at = now + timedelta(days=5 + i)  # 5, 6, 7 days from now
        listing = Listing.objects.create(
            user=test_user,
            title=f"Listing {i+1}",
            description=f"Description {i+1}",
            price=100 + i * 50,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=expires_at,
            is_ads_banner=(i % 2 == 0),
            is_hot_sales=(i % 3 == 0),
            badge="bundle" if i == 0 else "",
        )
        listing.hotspots.set([h.id for h in test_hotspots[:1+i % 2]])
        listings.append(listing)
    return listings

@pytest.fixture
def expired_listings(test_user, test_category):
    """Create 2 expired listings."""
    now = timezone.now()
    expired = []
    for i in range(2):
        listing = Listing.objects.create(
            user=test_user,
            title=f"Expired {i+1}",
            description="Expired",
            price=50,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.EXPIRED.value,
            expires_at=now - timedelta(days=1 + i),
        )
        expired.append(listing)
    return expired

@pytest.fixture
def reviews(test_user):
    """Create 3 reviews for the test user."""
    from_user = User.objects.create_user(email="reviewer@example.com", password="pass")
    reviews = []
    for i in range(3):
        review = Review.objects.create(
            from_user=from_user,
            to_user=test_user,
            rating=4 + i % 2,
            comment=f"Great seller! {i}",
            listing=None,
        )
        reviews.append(review)
    return reviews

@pytest.fixture
def request_factory():
    return RequestFactory()


# ── Tests ─────────────────────────────────────────────────────────────

class TestDashboardQuery:

    def test_get_dashboard_cache_miss(self, test_user, active_listings, expired_listings, reviews,
                                      request_factory):
        """Test cache miss: data is built and stored via get_or_set callback."""
        request = request_factory.get("/fake")
        request.user = test_user

        # Patch get_or_set to call the callback immediately (simulate cache miss)
        with patch("apps.campus.BBL.Queries.get_dashboard.GlobalCache.get_or_set") as mock_get_or_set:

            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()  # call the builder

            mock_get_or_set.side_effect = side_effect

            result = DashboardQuery.get_dashboard(request)

        assert result.is_success is True
        assert result.status_code == 200
        data = result.data

        # Basic counts
        assert data["total_active"] == len(active_listings)
        assert data["total_expired"] == len(expired_listings)
        assert data["total_sold"] == test_user.sold_items

        # Trust score
        ratings = [review.rating for review in reviews]
        avg_rating = sum(ratings) / len(ratings)
        expected_trust_score = round((avg_rating / 5.0) * 100, 1)
        assert data["trust_score"] == expected_trust_score

        # Profile completion
        assert isinstance(data["profile_completion"], (int, float))

        # Reviews
        all_reviews = data["all_reviews"]
        assert len(all_reviews) == len(reviews)
        assert all_reviews[0]["from"] is not None
        assert "rating" in all_reviews[0]
        assert "comment" in all_reviews[0]
        assert "date" in all_reviews[0]

        # Verify get_or_set was called with correct parameters
        mock_get_or_set.assert_called_once_with(
            key=ANY,
            callback=ANY,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_dashboard_cache_hit(self, test_user, request_factory):
        """Test that cached data is returned when available."""
        cached_data = {"user": "test", "total_active": 5}
        request = request_factory.get("/fake")
        request.user = test_user

        with patch("apps.campus.BBL.Queries.get_dashboard.GlobalCache.get_or_set") as mock_get_or_set:
            mock_get_or_set.return_value = cached_data  # cache hit

            result = DashboardQuery.get_dashboard(request)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.data == cached_data

        # get_or_set called, but the callback was not executed (cache hit)
        mock_get_or_set.assert_called_once_with(
            key=ANY,
            callback=ANY,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )


    def test_dashboard_trust_score_edge_cases(self, test_user, request_factory):
        """Test trust_score when average_rating is None or zero."""
        test_user.average_rating = 0
        test_user.save()
        request = request_factory.get("/fake")
        request.user = test_user

        with patch("apps.campus.BBL.Queries.get_dashboard.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = DashboardQuery.get_dashboard(request)
            assert result.data["trust_score"] == 0.0

        test_user.average_rating = 0  # already 0, but keep
        test_user.save()
        with patch("apps.campus.BBL.Queries.get_dashboard.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = DashboardQuery.get_dashboard(request)
            assert result.data["trust_score"] == 0.0

    def test_dashboard_profile_completion(self, test_user, request_factory):
        """Test that profile_completion is computed via callback."""
        request = request_factory.get("/fake")
        request.user = test_user

        with patch("apps.campus.BBL.Queries.get_dashboard.GlobalCache.get_or_set") as mock_get_or_set:
            # We need to mock calculate_profile_completion inside the callback.
            # Since the callback is executed inside get_or_set, we patch it at the module level.
            with patch("apps.campus.BBL.Queries.get_dashboard.calculate_profile_completion") as mock_completion:
                mock_completion.return_value = 75.5

                def side_effect(key, callback, timeout, lock_timeout, max_wait):
                    return callback()
                mock_get_or_set.side_effect = side_effect

                result = DashboardQuery.get_dashboard(request)

        assert result.data["profile_completion"] == 75.5
        mock_completion.assert_called_once_with(test_user)