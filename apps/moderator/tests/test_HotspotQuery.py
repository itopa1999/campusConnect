import pytest
import datetime
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone
from django.core.paginator import Paginator
from unittest.mock import Mock
from apps.campus.models import CampusHotspot, Listing, Category
from apps.moderator.BBL.Queries.hotspot import HotspotQuery
from utils.enums import ListingStatusType

User = get_user_model()


# ---------- Fixtures ----------
@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='user@example.com',
        password='testpass',
        first_name='Test',
        last_name='User',
        is_deleted=False,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(
        name='Electronics',
        slug='electronics',
        description='All things electronic'
    )


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def request_with_user(request_factory, user):
    req = request_factory.get('/')
    req.user = user
    req.META = {'REMOTE_ADDR': '127.0.0.1'}
    return req


@pytest.fixture
def hotspots(db):
    """Create 5 hotspots with different sort_order."""
    hs1 = CampusHotspot.objects.create(name='Library', sort_order=10)
    hs2 = CampusHotspot.objects.create(name='Cafeteria', sort_order=5)
    hs3 = CampusHotspot.objects.create(name='Gym', sort_order=15)
    hs4 = CampusHotspot.objects.create(name='Student Center', sort_order=0)
    hs5 = CampusHotspot.objects.create(name='Bookstore', sort_order=8)
    # Return in expected order: by sort_order asc, then name asc
    return [hs4, hs2, hs5, hs1, hs3]  # Student Center, Cafeteria, Bookstore, Library, Gym


@pytest.fixture
def hotspot_with_listings(db, user, category):
    """Create a hotspot with 3 active listings and 1 deleted listing."""
    hotspot = CampusHotspot.objects.create(name='Main Hall', sort_order=1)
    # 3 active listings
    listings = []
    for i in range(3):
        listing = Listing.objects.create(
            title=f'Listing {i}',
            description=f'Desc {i}',
            price=10 + i,
            user=user,
            category=category,
            status=ListingStatusType.ACTIVE.value,
            expires_at=timezone.now() + datetime.timedelta(days=10),
            is_deleted=False,
        )
        listing.hotspots.add(hotspot)
        listings.append(listing)
    # 1 deleted listing (should be excluded from count)
    deleted_listing = Listing.objects.create(
        title='Deleted',
        description='Deleted',
        price=0,
        user=user,
        category=category,
        status=ListingStatusType.ACTIVE.value,
        expires_at=timezone.now() + datetime.timedelta(days=10),
        is_deleted=True,
    )
    deleted_listing.hotspots.add(hotspot)
    return hotspot, listings


# ---------- Tests for get_all_hotspots ----------
@pytest.mark.django_db
class TestHotspotQueryGetAll:

    def test_get_all_hotspots_success(self, request_with_user, hotspots):
        result = HotspotQuery.get_all_hotspots(request_with_user, {})
        assert result.status_code == 200
        assert result.message == "hotspots retrieved successfully"
        data = result.data
        assert data['total_items'] == 5
        assert data['per_page'] == 20
        assert data['page'] == 1
        assert data['total_pages'] == 1
        items = data['items']
        expected_names = ['Student Center', 'Cafeteria', 'Bookstore', 'Library', 'Gym']
        assert [item['name'] for item in items] == expected_names
        # Check fields
        for item in items:
            assert 'id' in item
            assert 'name' in item
            assert 'description' in item
            assert 'sort_order' in item
            assert 'is_deleted' in item
            assert 'listing_count' in item
            assert item['listing_count'] == 0  # no listings attached initially

    def test_get_all_hotspots_with_search(self, request_with_user, hotspots):
        result = HotspotQuery.get_all_hotspots(request_with_user, {'search': 'book'})
        assert result.status_code == 200
        items = result.data['items']
        assert len(items) == 1
        assert items[0]['name'] == 'Bookstore'

    def test_get_all_hotspots_search_no_match(self, request_with_user, hotspots):
        result = HotspotQuery.get_all_hotspots(request_with_user, {'search': 'xyz'})
        assert result.status_code == 200
        assert result.data['total_items'] == 0
        assert result.data['items'] == []

    def test_get_all_hotspots_pagination(self, request_with_user, hotspots):
        # per_page=2, page=1
        result = HotspotQuery.get_all_hotspots(request_with_user, {'per_page': 2})
        assert result.status_code == 200
        data = result.data
        assert data['per_page'] == 2
        assert data['total_pages'] == 3  # 5 / 2 = 3
        assert data['page'] == 1
        assert len(data['items']) == 2
        # page 2
        result2 = HotspotQuery.get_all_hotspots(request_with_user, {'per_page': 2, 'page': 2})
        assert result2.data['page'] == 2
        assert len(result2.data['items']) == 2

    def test_get_all_hotspots_invalid_page(self, request_with_user, hotspots):
        result = HotspotQuery.get_all_hotspots(request_with_user, {'page': 'invalid'})
        assert result.status_code == 200
        assert result.data['page'] == 1

    def test_get_all_hotspots_page_out_of_range(self, request_with_user, hotspots):
        result = HotspotQuery.get_all_hotspots(request_with_user, {'page': 999, 'per_page': 2})
        assert result.status_code == 200
        assert result.data['page'] == 3  # last page

    def test_get_all_hotspots_per_page_limits(self, request_with_user, hotspots):
        # less than 1 -> 1
        result = HotspotQuery.get_all_hotspots(request_with_user, {'per_page': 0})
        assert result.data['per_page'] == 1
        # greater than 100 -> 100
        result = HotspotQuery.get_all_hotspots(request_with_user, {'per_page': 200})
        assert result.data['per_page'] == 100

    def test_get_all_hotspots_listing_count_annotation(self, request_with_user, hotspot_with_listings):
        hotspot, listings = hotspot_with_listings
        result = HotspotQuery.get_all_hotspots(request_with_user, {})
        items = result.data['items']
        # Only one hotspot exists
        assert len(items) == 1
        assert items[0]['id'] == hotspot.id
        assert items[0]['listing_count'] == 3  # only non-deleted listings

    def test_get_all_hotspots_ordering(self, request_with_user, hotspots):
        # Already verified in first test, but we can assert explicitly
        result = HotspotQuery.get_all_hotspots(request_with_user, {})
        names = [item['name'] for item in result.data['items']]
        assert names == ['Student Center', 'Cafeteria', 'Bookstore', 'Library', 'Gym']


# ---------- Tests for get_hotspot_id_detail ----------
@pytest.mark.django_db
class TestHotspotQueryDetail:

    def test_get_hotspot_id_detail_success(self, request_with_user, hotspot_with_listings):
        hotspot, listings = hotspot_with_listings
        result = HotspotQuery.get_hotspot_id_detail(request_with_user, hotspot.id)
        assert result.status_code == 200
        assert result.message == "Hotspot details retrieved successfully"
        data = result.data
        assert data['id'] == hotspot.id
        assert data['name'] == hotspot.name
        assert data['description'] == hotspot.description
        assert data['sort_order'] == hotspot.sort_order
        assert data['is_deleted'] == hotspot.is_deleted
        assert data['listings_count'] == 3  # only non-deleted
        assert len(data['listings_data']) == 3
        # Check each listing
        for i, listing_data in enumerate(data['listings_data']):
            listing = listings[i]
            assert listing_data['id'] == listing.id
            assert listing_data['title'] == listing.title
            assert listing_data['price'] == float(listing.price)
            assert listing_data['image'] is None  # no image set
            assert listing_data['created_at'] == listing.created_at.isoformat()
            assert 'status' in listing_data

    def test_get_hotspot_id_detail_not_found(self, request_with_user):
        result = HotspotQuery.get_hotspot_id_detail(request_with_user, 999)
        assert result.status_code == 404
        assert result.message == "Hotspot not found"
        assert result.data is None

    def test_get_hotspot_id_detail_excludes_deleted_listings(self, request_with_user, hotspot_with_listings):
        hotspot, _ = hotspot_with_listings
        # Add another deleted listing
        deleted_listing = Listing.objects.create(
            title='Another Deleted',
            description='Deleted',
            price=0,
            user=request_with_user.user,
            category=Category.objects.first(),  # reuse existing category
            status=ListingStatusType.ACTIVE.value,
            expires_at=timezone.now() + datetime.timedelta(days=10),
            is_deleted=True,
        )
        deleted_listing.hotspots.add(hotspot)
        result = HotspotQuery.get_hotspot_id_detail(request_with_user, hotspot.id)
        data = result.data
        assert data['listings_count'] == 3  # still 3, the deleted one is excluded
        assert len(data['listings_data']) == 3

    def test_get_hotspot_id_detail_image_url(self, request_with_user, hotspot_with_listings, mocker):
        hotspot, listings = hotspot_with_listings
        listing = listings[0]
        # Mock the image field to have a url
        mock_image = mocker.Mock()
        mock_image.url = '/media/test.jpg'
        listing.image = mock_image
        listing.save()

        # Mock request.build_absolute_uri to return a full URL
        def build_absolute_uri(path):
            return f'http://testserver{path}'

        request_with_user.build_absolute_uri = build_absolute_uri

        result = HotspotQuery.get_hotspot_id_detail(request_with_user, hotspot.id)
        data = result.data
        listing_data = data['listings_data'][0]
        expected = 'http://testserver/media/test.jpg'
        assert listing_data['image'] == expected

    def test_get_hotspot_id_detail_image_none(self, request_with_user, hotspot_with_listings):
        hotspot, _ = hotspot_with_listings
        result = HotspotQuery.get_hotspot_id_detail(request_with_user, hotspot.id)
        data = result.data
        for listing_data in data['listings_data']:
            assert listing_data['image'] is None

    def test_get_hotspot_id_detail_price_conversion(self, request_with_user, hotspot_with_listings):
        hotspot, listings = hotspot_with_listings
        result = HotspotQuery.get_hotspot_id_detail(request_with_user, hotspot.id)
        data = result.data
        for i, listing_data in enumerate(data['listings_data']):
            expected_price = float(listings[i].price)
            assert listing_data['price'] == expected_price
            assert isinstance(listing_data['price'], float)

    def test_get_hotspot_id_detail_created_at(self, request_with_user, hotspot_with_listings):
        hotspot, _ = hotspot_with_listings
        result = HotspotQuery.get_hotspot_id_detail(request_with_user, hotspot.id)
        data = result.data
        assert data['created_at'] == hotspot.created_at.isoformat()
        for listing_data in data['listings_data']:
            assert 'created_at' in listing_data