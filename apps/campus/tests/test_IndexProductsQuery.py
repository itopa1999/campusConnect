import pytest
from unittest.mock import patch, ANY
from datetime import timedelta

from django.utils import timezone
from django.test import RequestFactory

from apps.campus.BBL.Queries.index_products import IndexProductsQuery
from apps.campus.models import Listing, Category, CampusHotspot
from apps.users.models import User
from utils.enums import ListingStatusType, ListingType, GroupNames


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db):
    """Create an admin user (in the Admin group)."""
    user = User.objects.create_user(
        email="admin@example.com",
        password="adminpass",
        first_name="Admin",
        last_name="User"
    )
    from django.contrib.auth.models import Group
    admin_group, _ = Group.objects.get_or_create(name=GroupNames.ADMIN.value)
    user.groups.add(admin_group)
    return user

@pytest.fixture
def non_admin_user(db):
    """Create a regular user (not in Admin group)."""
    user = User.objects.create_user(
        email="user@example.com",
        password="userpass"
    )
    return user

@pytest.fixture
def test_category(db):
    return Category.objects.create(name="Electronics", description="Gadgets")

@pytest.fixture
def test_hotspot(db):
    return CampusHotspot.objects.create(name="Library", description="Main library")

@pytest.fixture
def admin_listings(admin_user, test_category, test_hotspot):
    """Create 8 active listings by admin (to test limit)."""
    now = timezone.now()
    listings = []
    for i in range(8):
        listing = Listing.objects.create(
            user=admin_user,
            title=f"Admin Listing {i+1}",
            description=f"Description {i+1}",
            price=100 + i * 10,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=now + timedelta(days=30 - i),
            badge="bundle" if i % 2 == 0 else "",
        )
        listing.hotspots.add(test_hotspot)
        listings.append(listing)
    return listings

@pytest.fixture
def non_admin_listings(non_admin_user, test_category, test_hotspot):
    """Create 3 active listings by non-admin (should be excluded)."""
    now = timezone.now()
    listings = []
    for i in range(3):
        listing = Listing.objects.create(
            user=non_admin_user,
            title=f"Non-Admin Listing {i+1}",
            price=50,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=now + timedelta(days=10),
        )
        listing.hotspots.add(test_hotspot)
        listings.append(listing)
    return listings

@pytest.fixture
def expired_listings(admin_user, test_category, test_hotspot):
    """Create 2 expired listings (should be excluded)."""
    now = timezone.now()
    listings = []
    for i in range(2):
        listing = Listing.objects.create(
            user=admin_user,
            title=f"Expired {i+1}",
            price=30,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.EXPIRED.value,
            expires_at=now - timedelta(days=1),
        )
        listing.hotspots.add(test_hotspot)
        listings.append(listing)
    return listings

@pytest.fixture
def request_factory():
    return RequestFactory()


# ── Tests ─────────────────────────────────────────────────────────────

class TestIndexProductsQuery:

    def test_get_index_products_cache_hit(self, request_factory):
        """When cached data exists, return it without DB query."""
        cached_data = {"listings": [{"id": 1, "title": "Cached"}]}
        request = request_factory.get("/")

        with patch("apps.campus.BBL.Queries.index_products.GlobalCache.get_or_set") as mock_get_or_set:
            mock_get_or_set.return_value = cached_data
            result = IndexProductsQuery.get_index_product(request)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.data == cached_data
        mock_get_or_set.assert_called_once_with(
            key=ANY,
            callback=ANY,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_index_products_cache_miss(self, admin_listings, non_admin_listings,
                                           expired_listings, request_factory):
        """Cache miss: fetch only active admin listings, limit to 6, order by created_at desc."""
        request = request_factory.get("/")

        with patch("apps.campus.BBL.Queries.index_products.GlobalCache.get_or_set") as mock_get_or_set:
            # Simulate cache miss by executing the callback
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = IndexProductsQuery.get_index_product(request)

        assert result.is_success is True
        assert result.status_code == 200
        data = result.data
        listings_data = data["listings"]

        # Should contain only admin listings, active, not expired, limited to 6
        assert len(listings_data) == 6

        # Ordered by created_at desc (most recent first)
        ids = [item["id"] for item in listings_data]
        assert ids == sorted(ids, reverse=True)

        # Check a sample item has required fields
        sample = listings_data[0]
        assert "id" in sample
        assert "title" in sample
        assert "price" in sample
        assert "category" in sample
        assert "location" in sample
        assert "description" in sample
        assert "badge" in sample
        assert "type" in sample
        assert "image" in sample

        # Non-admin and expired listings should be excluded
        non_admin_ids = [l.id for l in non_admin_listings]
        expired_ids = [l.id for l in expired_listings]
        returned_ids = [item["id"] for item in listings_data]
        assert not any(id in returned_ids for id in non_admin_ids)
        assert not any(id in returned_ids for id in expired_ids)

    def test_get_index_products_location(self, admin_user, test_category, test_hotspot,
                                         request_factory):
        """Location should be first hotspot name, or 'Campus' if none."""
        # Listing with hotspot
        listing_with_hs = Listing.objects.create(
            user=admin_user,
            title="With HS",
            price=10,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=timezone.now() + timedelta(days=5),
        )
        listing_with_hs.hotspots.add(test_hotspot)

        # Listing without hotspot
        listing_no_hs = Listing.objects.create(
            user=admin_user,
            title="No HS",
            price=20,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=timezone.now() + timedelta(days=5),
        )

        request = request_factory.get("/")

        with patch("apps.campus.BBL.Queries.index_products.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = IndexProductsQuery.get_index_product(request)

        listings = result.data["listings"]
        for item in listings:
            if item["title"] == "With HS":
                assert item["location"] == test_hotspot.name
            elif item["title"] == "No HS":
                assert item["location"] == "Campus"

    def test_get_index_products_image_url(self, admin_user, test_category, request_factory):
        """Image URL should be None when no image exists."""
        # Create a listing without image (most realistic in test)
        no_image_listing = Listing.objects.create(
            user=admin_user,
            title="No Image",
            price=5,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=timezone.now() + timedelta(days=5),
        )

        request = request_factory.get("/")

        with patch("apps.campus.BBL.Queries.index_products.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = IndexProductsQuery.get_index_product(request)

        for item in result.data["listings"]:
            if item["title"] == "No Image":
                assert item["image"] is None

    def test_get_index_products_limit(self, admin_user, test_category, request_factory):
        """Test that the limit parameter works (default 6, can be overridden)."""
        # Create 10 active admin listings
        now = timezone.now()
        for i in range(10):
            Listing.objects.create(
                user=admin_user,
                title=f"Listing {i}",
                price=10,
                category=test_category,
                listing_type=ListingType.SELL.value,
                status=ListingStatusType.ACTIVE.value,
                expires_at=now + timedelta(days=10 - i),
            )

        request = request_factory.get("/")

        with patch("apps.campus.BBL.Queries.index_products.GlobalCache.get_or_set") as mock_get_or_set:
            # We need to test that the limit is passed correctly.
            # We'll spy on the queryset slicing by checking the callback result length.
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            # Default limit 6
            result = IndexProductsQuery.get_index_product(request)
            assert len(result.data["listings"]) == 6

            # Override limit to 3
            result = IndexProductsQuery.get_index_product(request, limit=3)
            assert len(result.data["listings"]) == 3

    def test_get_index_products_no_admin_listings(self, non_admin_user, test_category,
                                                  request_factory):
        """If there are no admin listings, return empty list."""
        # Only non-admin listings exist
        Listing.objects.create(
            user=non_admin_user,
            title="User Listing",
            price=10,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=timezone.now() + timedelta(days=5),
        )

        request = request_factory.get("/")

        with patch("apps.campus.BBL.Queries.index_products.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = IndexProductsQuery.get_index_product(request)

        assert result.is_success is True
        assert result.data["listings"] == []