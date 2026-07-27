import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.core.paginator import Paginator
from apps.campus.models import Category, Listing
from apps.moderator.BBL.Queries.category import CategoryQuery  # adjust import path
from utils.enums import ListingStatusTypeEnum

User = get_user_model()


# ---------- Fixtures ----------
@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='test@example.com',
        password='testpass',
        first_name='Test',
        last_name='User'
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
def categories(db):
    # Create 5 categories with different sort_order
    cat1 = Category.objects.create(name='Books', sort_order=10)
    cat2 = Category.objects.create(name='Electronics', sort_order=5)
    cat3 = Category.objects.create(name='Clothing', sort_order=15)
    cat4 = Category.objects.create(name='Toys', sort_order=0)  # lowest sort_order
    cat5 = Category.objects.create(name='Furniture', sort_order=8)
    return [cat4, cat2, cat5, cat1, cat3]  # expected order by sort_order then name


@pytest.fixture
def category_with_listings(db, user):
    # Create a category with 3 listings
    cat = Category.objects.create(name='Gadgets', sort_order=1)
    listings = []
    for i in range(3):
        listing = Listing.objects.create(
            title=f'Gadget {i}',
            description=f'Gadget {i} desc',
            price=10 + i,
            user=user,
            category=cat,
            status=ListingStatusTypeEnum.ACTIVE.value,
            is_deleted=False
        )
        listings.append(listing)
    return cat, listings


@pytest.fixture
def category_with_deleted_listings(db, user):
    # Category with some deleted listings – count should ignore them
    cat = Category.objects.create(name='DeletedGadgets', sort_order=2)
    for i in range(2):
        Listing.objects.create(
            title=f'Active {i}',
            description='Active',
            price=10,
            user=user,
            category=cat,
            status=ListingStatusTypeEnum.ACTIVE.value,
            is_deleted=False
        )
    Listing.objects.create(
        title='Deleted',
        description='Deleted',
        price=10,
        user=user,
        category=cat,
        status=ListingStatusTypeEnum.ACTIVE.value,
        is_deleted=True
    )
    return cat


# ---------- Tests for get_all_categories ----------
@pytest.mark.django_db
class TestCategoryQueryGetAll:

    def test_get_all_categories_success(self, request_with_user, categories):
        result = CategoryQuery.get_all_categories(request_with_user, {})
        assert result.status_code == 200
        assert result.message == "Categories retrieved successfully"
        data = result.data
        assert data['total_items'] == 5
        assert data['per_page'] == 20
        assert data['page'] == 1
        assert data['total_pages'] == 1
        items = data['items']
        # Should be ordered by sort_order, then name
        expected_names = ['Toys', 'Electronics', 'Furniture', 'Books', 'Clothing']
        assert [item['name'] for item in items] == expected_names
        # Check all fields present
        for item in items:
            assert 'id' in item
            assert 'slug' in item
            assert 'icon' in item
            assert 'description' in item
            assert 'sort_order' in item
            assert 'is_deleted' in item
            assert 'listing_count' in item

    def test_get_all_categories_with_search(self, request_with_user, categories):
        result = CategoryQuery.get_all_categories(request_with_user, {'search': 'book'})
        assert result.status_code == 200
        items = result.data['items']
        assert len(items) == 1
        assert items[0]['name'] == 'Books'

    def test_get_all_categories_search_no_match(self, request_with_user, categories):
        result = CategoryQuery.get_all_categories(request_with_user, {'search': 'xyz'})
        assert result.status_code == 200
        assert result.data['total_items'] == 0
        assert result.data['items'] == []

    def test_get_all_categories_pagination_default(self, request_with_user, categories):
        # Force small per_page for testing
        result = CategoryQuery.get_all_categories(request_with_user, {'per_page': 2})
        assert result.status_code == 200
        data = result.data
        assert data['per_page'] == 2
        assert data['total_pages'] == 3  # 5 items / 2 = 3 pages
        assert data['page'] == 1
        assert len(data['items']) == 2
        # Page 2
        result2 = CategoryQuery.get_all_categories(request_with_user, {'per_page': 2, 'page': 2})
        assert result2.status_code == 200
        assert result2.data['page'] == 2
        assert len(result2.data['items']) == 2

    def test_get_all_categories_invalid_page(self, request_with_user, categories):
        result = CategoryQuery.get_all_categories(request_with_user, {'page': 'invalid'})
        assert result.status_code == 200
        assert result.data['page'] == 1  # falls back to page 1

    def test_get_all_categories_page_out_of_range(self, request_with_user, categories):
        result = CategoryQuery.get_all_categories(request_with_user, {'page': 999, 'per_page': 2})
        assert result.status_code == 200
        assert result.data['page'] == 3  # should be last page (total_pages=3)

    def test_get_all_categories_per_page_limits(self, request_with_user, categories):
        # Less than 1 -> 1
        result = CategoryQuery.get_all_categories(request_with_user, {'per_page': 0})
        assert result.status_code == 200
        assert result.data['per_page'] == 1
        # Greater than 100 -> 100
        result = CategoryQuery.get_all_categories(request_with_user, {'per_page': 200})
        assert result.status_code == 200
        assert result.data['per_page'] == 100

    def test_get_all_categories_listing_count(self, request_with_user, category_with_deleted_listings):
        cat = category_with_deleted_listings
        result = CategoryQuery.get_all_categories(request_with_user, {})
        items = result.data['items']
        # Only one category
        assert len(items) == 1
        assert items[0]['listing_count'] == 2  # only non-deleted listings

    def test_get_all_categories_ordering(self, request_with_user, categories):
        # Check ordering: sort_order asc, then name asc
        result = CategoryQuery.get_all_categories(request_with_user, {})
        items = result.data['items']
        expected_order = ['Toys', 'Electronics', 'Furniture', 'Books', 'Clothing']
        assert [item['name'] for item in items] == expected_order


# ---------- Tests for get_category_detail ----------
@pytest.mark.django_db
class TestCategoryQueryDetail:

    def test_get_category_detail_success(self, request_with_user, category_with_listings):
        cat, listings = category_with_listings
        result = CategoryQuery.get_category_detail(request_with_user, cat.id)
        assert result.status_code == 200
        assert result.message == "Category details retrieved successfully"
        data = result.data
        assert data['id'] == cat.id
        assert data['name'] == cat.name
        assert data['slug'] == cat.slug
        assert data['listing_count'] == 3
        assert len(data['listings_data']) == 3
        # Check listing fields
        for listing_data in data['listings_data']:
            assert 'id' in listing_data
            assert 'title' in listing_data
            assert 'price' in listing_data
            assert 'image' in listing_data  # should be None because no image
            assert 'listing_type' in listing_data
            assert 'status' in listing_data
            assert 'created_at' in listing_data

    def test_get_category_detail_not_found(self, request_with_user):
        result = CategoryQuery.get_category_detail(request_with_user, 999)
        assert result.status_code == 404
        assert result.message == "Category not found"
        assert result.data is None

    def test_get_category_detail_excludes_deleted_listings(self, request_with_user, category_with_deleted_listings):
        cat = category_with_deleted_listings
        result = CategoryQuery.get_category_detail(request_with_user, cat.id)
        data = result.data
        assert data['listing_count'] == 2
        assert len(data['listings_data']) == 2
        for listing_data in data['listings_data']:
            assert 'Deleted' not in listing_data['title']

    # def test_get_category_detail_image_url(self, request_with_user, mocker):
    #     cat = Category.objects.create(name='ImgCat')
    #     listing = Listing.objects.create(
    #         title='With Image',
    #         description='Has image',
    #         price=10,
    #         user=request_with_user.user,
    #         category=cat,
    #         status=ListingStatusTypeEnum.ACTIVE.value
    #     )

    #     # Create a mock image that is truthy and has a url
    #     mock_image = mocker.Mock()
    #     mock_image.url = '/media/Lisiting_images/test.jpg'

    #     # Patch the listing's image field with the mock
    #     with mocker.patch.object(listing, 'image', mock_image):
    #         result = CategoryQuery.get_category_detail(request_with_user, cat.id)
    #         data = result.data
    #         listing_data = data['listings_data'][0]
    #         expected_url = request_with_user.build_absolute_uri('/media/Lisiting_images/test.jpg')
    #         assert listing_data['image'] == expected_url

    def test_get_category_detail_image_none(self, request_with_user, category_with_listings):
        cat, _ = category_with_listings
        result = CategoryQuery.get_category_detail(request_with_user, cat.id)
        data = result.data
        for listing_data in data['listings_data']:
            assert listing_data['image'] is None

    def test_get_category_detail_price_conversion(self, request_with_user, category_with_listings):
        cat, _ = category_with_listings
        result = CategoryQuery.get_category_detail(request_with_user, cat.id)
        data = result.data
        for listing_data in data['listings_data']:
            # Price should be float, and if None then 0
            assert isinstance(listing_data['price'], float)
            # The first listing has price 10, second 11, third 12
            # We can check one
            assert listing_data['price'] in [10.0, 11.0, 12.0]

    def test_get_category_detail_created_at(self, request_with_user, category_with_listings):
        cat, _ = category_with_listings
        result = CategoryQuery.get_category_detail(request_with_user, cat.id)
        data = result.data
        assert 'created_at' in data
        # Should be ISO format
        assert data['created_at'] == cat.created_at.isoformat()