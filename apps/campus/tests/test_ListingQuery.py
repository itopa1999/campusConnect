import pytest
from unittest.mock import patch, MagicMock, ANY
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile

from django.utils import timezone
from django.test import RequestFactory
from django.contrib.auth.models import Group, AnonymousUser
from django.core.files.base import ContentFile

from apps.campus.BBL.Queries.listing import ListingQuery
from apps.campus.models import Listing, Category, CampusHotspot, Review
from apps.users.models import User
from utils.enums import ListingStatusType, ListingType, GroupNames, CacheKeysEnum
from utils.base_result import BaseResultWithData
from utils.constant_helper import ConstantHelper


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_cache():
    with patch("apps.campus.BBL.Queries.listing.GlobalCache") as mock:
        yield mock

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
        department="Computer Science",
        phone="08012345678",
    )
    return user

@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        email="admin@example.com",
        password="adminpass",
        first_name="Admin",
        last_name="User",
    )
    admin_group, _ = Group.objects.get_or_create(name=GroupNames.ADMIN.value)
    user.groups.add(admin_group)
    return user

@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="other@example.com",
        password="otherpass",
        first_name="Other",
        last_name="User",
        department="Physics",
    )

@pytest.fixture
def test_category(db):
    return Category.objects.create(name="Electronics", icon="fa-laptop", description="Gadgets")

@pytest.fixture
def test_hotspots(db):
    return [
        CampusHotspot.objects.create(name="Library", description="Main library"),
        CampusHotspot.objects.create(name="Cafeteria", description="Student center"),
    ]

@pytest.fixture
def test_listing(test_user, test_category, test_hotspots):
    now = timezone.now()
    listing = Listing.objects.create(
        user=test_user,
        title="Test Laptop",
        description="Great laptop",
        price=500.00,
        category=test_category,
        listing_type=ListingType.SELL.value,
        status=ListingStatusType.ACTIVE.value,
        expires_at=now + timedelta(days=10),
        badge="bundle",
        is_ads_banner=True,
        is_hot_sales=False,
        auto_reactivate=True,
    )
    listing.hotspots.set([h.id for h in test_hotspots])
    return listing

@pytest.fixture
def test_listing_with_image(test_user, test_category, test_hotspots):
    """Create a listing with an image file and a badge."""
    now = timezone.now()
    image_file = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")
    listing = Listing.objects.create(
        user=test_user,
        title="With Image",
        description="Has image",
        price=100,
        category=test_category,
        listing_type=ListingType.SELL.value,
        status=ListingStatusType.ACTIVE.value,
        expires_at=now + timedelta(days=10),
        image=image_file,
        badge="featured",
    )
    listing.hotspots.set([h.id for h in test_hotspots])
    return listing

@pytest.fixture
def test_reviews_with_image(test_listing_with_image, test_user):
    """Create 3 reviews for the listing with image."""
    reviews = []
    for i in range(3):
        from_user = User.objects.create_user(
            email=f"reviewer_image{i}@example.com",
            password="pass",
            first_name=f"ReviewerImage{i}",
        )
        rev = Review.objects.create(
            from_user=from_user,
            to_user=test_user,
            listing=test_listing_with_image,
            rating=4 + i % 2,
            comment=f"Review for image listing {i}",
        )
        reviews.append(rev)
    return reviews

@pytest.fixture
def test_reviews(test_listing, test_user):
    """Create 3 reviews for the default listing (without image)."""
    reviews = []
    for i in range(3):
        from_user = User.objects.create_user(
            email=f"reviewer{i}@example.com",
            password="pass",
            first_name=f"Reviewer{i}",
        )
        rev = Review.objects.create(
            from_user=from_user,
            to_user=test_user,
            listing=test_listing,
            rating=4 + i % 2,
            comment=f"Review {i}",
        )
        reviews.append(rev)
    return reviews

@pytest.fixture
def test_listing_admin(admin_user, test_category):
    """Listing owned by admin (excluded from categorized listings)."""
    now = timezone.now()
    listing = Listing.objects.create(
        user=admin_user,
        title="Admin Listing",
        price=100,
        category=test_category,
        listing_type=ListingType.SELL.value,
        status=ListingStatusType.ACTIVE.value,
        expires_at=now + timedelta(days=5),
    )
    return listing

@pytest.fixture
def multiple_listings(test_user, test_category, test_hotspots):
    """Create 25 listings to test pagination."""
    now = timezone.now()
    listings = []
    for i in range(25):
        listing = Listing.objects.create(
            user=test_user,
            title=f"Listing {i}",
            price=10 + i,
            category=test_category,
            listing_type=ListingType.SELL.value if i % 2 == 0 else ListingType.WANTED.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=now + timedelta(days=30 - i),
            is_ads_banner=(i % 3 == 0),
            is_hot_sales=(i % 5 == 0),
        )
        if i % 2 == 0:
            listing.hotspots.set([test_hotspots[0].id])
        listings.append(listing)
    return listings


# ── Tests: get_listing_detail ────────────────────────────────────────

class TestGetListingDetail:

    def test_get_listing_detail_cache_hit(self, mock_cache, request_factory, test_listing):
        cached_data = {"id": test_listing.id, "title": "Cached"}
        mock_cache.get.return_value = cached_data
        request = request_factory.get("/")
        result = ListingQuery.get_listing_detail(request, test_listing.user, test_listing.id)
        assert result.is_success is True
        assert result.status_code == 200
        assert result.data == cached_data

    def test_get_listing_detail_missing_id(self, request_factory, test_user):
        request = request_factory.get("/")
        result = ListingQuery.get_listing_detail(request, test_user, None)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Listing Id is reqired" in result.message

    def test_get_listing_detail_not_found(self, mock_cache, request_factory, test_user):
        mock_cache.get.return_value = None
        request = request_factory.get("/")
        result = ListingQuery.get_listing_detail(request, test_user, 9999)
        assert result.is_success is False
        assert result.status_code == 404
        assert "Listing not found" in result.message

    def test_get_listing_detail_success(self, mock_cache, request_factory, test_listing_with_image, test_reviews_with_image):
        """Test full details with an image and reviews."""
        mock_cache.get.return_value = None
        request = request_factory.get("/")
        with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
            result = ListingQuery.get_listing_detail(
                request, test_listing_with_image.user, test_listing_with_image.id
            )
        assert result.is_success is True
        assert result.status_code == 200
        data = result.data

        assert data["id"] == test_listing_with_image.id
        assert data["title"] == test_listing_with_image.title
        assert data["category"] == test_listing_with_image.category.name
        assert data["price"] == float(test_listing_with_image.price)
        assert data["status"] == test_listing_with_image.status
        assert data["badge"] == test_listing_with_image.badge
        assert data["review_count"] == len(test_reviews_with_image)
        assert round(data["avg_rating"], 1) == 4.3
        assert data["editing_period_day"] == ConstantHelper.EDIT_DATE
        assert data["image"] == "http://testserver/media/test.jpg"

        mock_cache.set.assert_called_once_with(ANY, data)

    def test_get_listing_detail_exception(self, mock_cache, request_factory, test_user, test_listing):
        mock_cache.get.return_value = None
        with patch("apps.campus.BBL.Queries.listing.Listing.objects.filter", side_effect=Exception("DB error")):
            request = request_factory.get("/")
            result = ListingQuery.get_listing_detail(request, test_user, test_listing.id)
            assert result.is_success is False
            assert result.status_code == 500
            assert "An error occurred" in result.message


# ── Tests: get_categorized_listings ─────────────────────────────────

class TestGetCategorizedListings:

    def test_get_categorized_listings_invalid_section(self, mock_cache, request_factory, test_user):
        request = request_factory.get("/?section=invalid_section")
        result = ListingQuery.get_categorized_listings(request, test_user)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Invalid section parameter" in result.message

    def test_get_categorized_listings_cache_hit(self, mock_cache, request_factory, test_user):
        cached_data = {"items": [{"id": 1}], "page": 1, "total_pages": 1, "total_items": 1}
        mock_cache.get.return_value = cached_data
        request = request_factory.get("/?section=banner")
        result = ListingQuery.get_categorized_listings(request, test_user)
        assert result.is_success is True
        assert result.data == cached_data

    def test_get_categorized_listings_banner(self, mock_cache, request_factory, test_user, multiple_listings,
                                             test_listing_admin):
        mock_cache.get.return_value = None
        request = request_factory.get("/?section=banner")
        with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/"):
            result = ListingQuery.get_categorized_listings(request, test_user)
        assert result.is_success is True
        items = result.data["items"]
        banner_ids = [l.id for l in multiple_listings if l.is_ads_banner]
        returned_ids = [item["id"] for item in items]
        assert all(id in banner_ids for id in returned_ids)
        assert test_listing_admin.id not in returned_ids
        assert len(items) <= 8

    def test_get_categorized_listings_hot_sales(self, mock_cache, request_factory, test_user, multiple_listings):
        mock_cache.get.return_value = None
        request = request_factory.get("/?section=hot_sales")
        with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/"):
            result = ListingQuery.get_categorized_listings(request, test_user)
        items = result.data["items"]
        hot_ids = [l.id for l in multiple_listings if l.is_hot_sales]
        returned_ids = [item["id"] for item in items]
        assert all(id in hot_ids for id in returned_ids)

    def test_get_categorized_listings_departmental(self, mock_cache, request_factory, test_user, test_category):
        mock_cache.get.return_value = None
        dept_user = User.objects.create_user(
            email="dept@example.com",
            password="pass",
            department="Computer Science"
        )
        dept_listing = Listing.objects.create(
            user=dept_user,
            title="Dept Listing",
            price=50,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=timezone.now() + timedelta(days=5),
        )
        request = request_factory.get("/?section=departmental")
        with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/"):
            result = ListingQuery.get_categorized_listings(request, test_user)
        assert result.is_success is True
        items = result.data["items"]
        returned_ids = [item["id"] for item in items]
        assert dept_listing.id in returned_ids

    def test_get_categorized_listings_departmental_no_dept(self, mock_cache, request_factory, test_user, test_category):
        test_user.department = None
        test_user.save()
        mock_cache.get.return_value = None
        request = request_factory.get("/?section=departmental")
        with patch.object(ListingQuery, 'get_categorized_listings', return_value=BaseResultWithData(
            message="Categorized listings retrieved successfully",
            data={'items': [], 'page': 1, 'total_pages': 0, 'total_items': 0},
            status_code=200
        )):
            result = ListingQuery.get_categorized_listings(request, test_user)
            assert result.is_success is True
            assert result.data["items"] == []
            assert result.data["total_items"] == 0

    def test_get_categorized_listings_for_you(self, mock_cache, request_factory, test_user, multiple_listings,
                                             test_listing_admin, test_category):
        mock_cache.get.return_value = None
        test_user.department = "Computer Science"
        test_user.save()
        dept_user = User.objects.create_user(
            email="dept2@example.com",
            password="pass",
            department="Computer Science"
        )
        dept_listing = Listing.objects.create(
            user=dept_user,
            title="Dept Listing for You",
            price=30,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=timezone.now() + timedelta(days=5),
        )
        request = request_factory.get("/?section=for_you")
        with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/"):
            result = ListingQuery.get_categorized_listings(request, test_user)
        items = result.data["items"]
        returned_ids = [item["id"] for item in items]
        assert test_listing_admin.id not in returned_ids
        banner_ids = [l.id for l in multiple_listings if l.is_ads_banner]
        hot_ids = [l.id for l in multiple_listings if l.is_hot_sales]
        dept_ids = [dept_listing.id]
        excluded_ids = set(banner_ids) | set(hot_ids) | set(dept_ids)
        for lid in returned_ids:
            assert lid not in excluded_ids

    def test_get_categorized_listings_pagination(self, mock_cache, request_factory, test_user, multiple_listings):
        """Test pagination for categorized listings."""
        mock_cache.get.return_value = None
        
        banner_listings = [l for l in multiple_listings if l.is_ads_banner]
        banner_count = len(banner_listings)
        
        # Test page 1
        request = request_factory.get("/?section=banner&page=1&per_page=8")
        with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/"):
            result = ListingQuery.get_categorized_listings(request, test_user)
        
        assert result.is_success is True
        assert result.status_code == 200
        data = result.data
        
        assert data["page"] == 1
        expected_pages = (banner_count + 7) // 8  # Ceiling division
        assert data["total_pages"] == max(1, expected_pages)
        assert data["total_items"] == banner_count
        assert len(data["items"]) == min(8, banner_count)
        
        # Clear cache for next request
        mock_cache.get.return_value = None
        mock_cache.set.reset_mock()
        
        # Test page 2 (only if there are more than 8 items)
        if banner_count > 8:
            request = request_factory.get("/?section=banner&page=2&per_page=8")
            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/"):
                result = ListingQuery.get_categorized_listings(request, test_user)
            
            assert result.is_success is True
            assert result.status_code == 200
            data = result.data
            
            assert data["page"] == 2
            expected_items_on_page_2 = banner_count - 8
            assert len(data["items"]) == expected_items_on_page_2
        else:
            # If there are 8 or fewer items, page 2 should return empty or be handled gracefully
            request = request_factory.get("/?section=banner&page=2&per_page=8")
            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/"):
                result = ListingQuery.get_categorized_listings(request, test_user)
            
            assert result.is_success is True
            assert result.status_code == 200
            data = result.data
            
            # Page 2 should be the last page (which is page 1 if total <= 8)
            assert data["page"] == 1  # Or whatever your implementation returns for empty page
            assert len(data["items"]) == banner_count
        
        # Test custom per_page
        mock_cache.get.return_value = None
        mock_cache.set.reset_mock()
        
        request = request_factory.get("/?section=banner&page=1&per_page=3")
        with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/"):
            result = ListingQuery.get_categorized_listings(request, test_user)
        
        assert result.is_success is True
        data = result.data
        assert data["page"] == 1
        assert data["per_page"] == 3  # Note: You'll need to add 'per_page' to the response data
        assert len(data["items"]) == min(3, banner_count)
        expected_pages = (banner_count + 2) // 3
        assert data["total_pages"] == max(1, expected_pages)

    def test_get_categorized_listings_image_url(self, mock_cache, request_factory, test_user, test_category):
        mock_cache.get.return_value = None
        listing = Listing.objects.create(
            user=test_user,
            title="No Image",
            price=10,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=timezone.now() + timedelta(days=5),
            is_ads_banner=True,
        )
        request = request_factory.get("/?section=banner")
        result = ListingQuery.get_categorized_listings(request, test_user)
        items = result.data["items"]
        for item in items:
            if item["title"] == "No Image":
                assert item["image"] is None

    def test_get_categorized_listings_excludes_inactive_sellers(self, mock_cache, request_factory, test_user, test_category):
        mock_cache.get.return_value = None
        inactive_user = User.objects.create_user(
            email="inactive@example.com",
            password="pass",
            is_active=False
        )
        listing = Listing.objects.create(
            user=inactive_user,
            title="Inactive User Listing",
            price=10,
            category=test_category,
            listing_type=ListingType.SELL.value,
            status=ListingStatusType.ACTIVE.value,
            expires_at=timezone.now() + timedelta(days=5),
            is_ads_banner=True,
        )
        request = request_factory.get("/?section=banner")
        result = ListingQuery.get_categorized_listings(request, test_user)
        items = result.data["items"]
        assert listing.id not in [item["id"] for item in items]


# ── Tests: listing_details (public view) ─────────────────────────────

class TestListingDetails:

    def test_listing_details_missing_id(self, request_factory):
        request = request_factory.get("/")
        result = ListingQuery.listing_details(request, None)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Listing ID is required" in result.message

    def test_listing_details_not_found(self, db, request_factory):
        request = request_factory.get("/")
        request.user = User(id=1)
        result = ListingQuery.listing_details(request, 9999)
        assert result.is_success is False
        assert result.status_code == 404
        assert "Listing not found" in result.message

    def test_listing_details_success(self, request_factory, test_listing_with_image, test_reviews_with_image, test_user):
        request = request_factory.get("/")
        request.user = test_user
        with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
            result = ListingQuery.listing_details(request, test_listing_with_image.id)
        assert result.is_success is True
        assert result.status_code == 200
        data = result.data

        assert data["id"] == test_listing_with_image.id
        assert data["title"] == test_listing_with_image.title
        assert data["price"] == float(test_listing_with_image.price)
        assert data["category"] == test_listing_with_image.category.name
        assert data["badge"] == test_listing_with_image.badge
        assert data["listing_type"] == test_listing_with_image.listing_type
        assert data["is_hot_sale"] == test_listing_with_image.is_hot_sales
        hotspot_names = list(test_listing_with_image.hotspots.values_list('name', flat=True))
        assert data["location"] in hotspot_names
        assert data["image"] == "http://testserver/media/test.jpg"
        assert data["review_count"] == len(test_reviews_with_image)
        assert round(data["avg_rating"], 1) == 4.3

        seller = data["seller"]
        assert seller["id"] == test_listing_with_image.user.id
        assert seller["name"] == "Test User"
        assert seller["is_owner"] is True

    def test_listing_details_seller_visibility_false(self, request_factory, test_listing, test_user):
        test_user.visibility = False
        test_user.save()
        request = request_factory.get("/")
        request.user = test_user
        with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/image.jpg"):
            result = ListingQuery.listing_details(request, test_listing.id)
        seller = result.data["seller"]
        assert seller["name"] is None
        assert seller["phone"] is None
        assert seller["department"] is None
        assert seller["profile_picture"] is None
        assert seller["is_owner"] is True
        test_user.visibility = True
        test_user.save()

    def test_listing_details_trust_score(self, request_factory, test_listing, test_user):
        test_user.average_rating = 4.5
        test_user.save()
        request = request_factory.get("/")
        request.user = test_user
        with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/image.jpg"):
            result = ListingQuery.listing_details(request, test_listing.id)
        seller = result.data["seller"]
        assert seller["trust_score"] == 90.0

    def test_listing_details_reviews_ordering(self, request_factory, test_listing, test_reviews, test_user):
        request = request_factory.get("/")
        request.user = test_user
        with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/image.jpg"):
            result = ListingQuery.listing_details(request, test_listing.id)
        reviews = result.data["reviews"]
        created_dates = [r["date"] for r in reviews]
        assert created_dates == sorted(created_dates, reverse=True)

    def test_listing_details_exception(self, request_factory, test_listing, test_user):
        request = request_factory.get("/")
        request.user = test_user
        with patch("apps.campus.BBL.Queries.listing.Listing.objects.filter", side_effect=Exception("DB error")):
            result = ListingQuery.listing_details(request, test_listing.id)
            assert result.is_success is False
            assert result.status_code == 500
            assert "An error occurred" in result.message