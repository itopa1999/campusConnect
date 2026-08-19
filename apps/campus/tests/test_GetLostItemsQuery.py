import pytest
from unittest.mock import patch, ANY
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.test import RequestFactory
from apps.campus.BBL.Queries.lost_and_found import GetLostItemsQuery
from apps.campus.models import LostAndFound
from utils.enums import LostAndFoundStatusEnum


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def lost_items(db):
    """Create 15 lost items with OPEN status."""
    now = timezone.now()
    items = []
    for i in range(15):
        status = LostAndFoundStatusEnum.OPEN.value
        item = LostAndFound.objects.create(
            item_name=f"Item {i}",
            description=f"Description {i}",
            location=f"Location {i}",
            date_found=now - timedelta(days=i),
            verification1=f"Question 1 for {i}",
            answer1=f"Answer 1 for {i}",
            verification2=f"Question 2 for {i}",
            answer2=f"Answer 2 for {i}",
            full_name=f"Finder {i}",
            email=f"finder{i}@example.com",
            department="Computer Science",
            phone="08012345678",
            status=status,
            is_deleted=False,
        )
        items.append(item)
    return items


@pytest.fixture
def lost_item_with_image(db):
    """Create a lost item with an image."""
    image_file = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")
    now = timezone.now()
    item = LostAndFound.objects.create(
        item_name="Item with Image",
        description="Has image",
        location="Campus",
        date_found=now,
        verification1="Color?",
        answer1="Red",
        verification2="Size?",
        answer2="Medium",
        full_name="Finder",
        email="finder@example.com",
        department="Science",
        image=image_file,
    )
    return item


# ── Tests ─────────────────────────────────────────────────────────────

class TestGetLostItemsQuery:

    def test_get_items_cache_hit(self, request_factory):
        """Return cached data if available."""
        cached_data = {"items": [{"id": 1}], "pagination": {"current_page": 1}}
        request = request_factory.get("/?page=1&per_page=10")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            mock_aget_or_set.return_value = cached_data
            result = GetLostItemsQuery.get_items(request)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.data == cached_data
        mock_aget_or_set.assert_called_once_with(
            key=ANY,
            callback=ANY,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_items_success(self, request_factory, lost_items):
        """Retrieve paginated lost items with default parameters."""
        request = request_factory.get("/?page=1&per_page=10")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            # Simulate cache miss by executing the callback
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
                result = GetLostItemsQuery.get_items(request)

        assert result.is_success is True
        assert result.status_code == 200
        data = result.data

        items = data["items"]
        pagination = data["pagination"]

        assert len(items) == 10
        assert items[0]["item_name"] == lost_items[-1].item_name
        assert "answer1" not in items[0]
        assert "answer2" not in items[0]
        assert "verification1" in items[0]
        assert "verification2" in items[0]

        assert pagination["total_pages"] == 2
        assert pagination["total_items"] == 15
        assert pagination["per_page"] == 10
        assert pagination["has_next"] is True
        assert pagination["has_previous"] is False

    def test_get_items_page_2(self, request_factory, lost_items):
        """Retrieve second page of results."""
        request = request_factory.get("/?page=2&per_page=10")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
                result = GetLostItemsQuery.get_items(request)

        data = result.data
        items = data["items"]
        pagination = data["pagination"]

        assert len(items) == 5
        assert items[0]["item_name"] == lost_items[-11].item_name
        assert pagination["has_next"] is False
        assert pagination["has_previous"] is True

    def test_get_items_custom_per_page(self, request_factory, lost_items):
        """Test custom per_page parameter."""
        request = request_factory.get("/?page=1&per_page=5")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
                result = GetLostItemsQuery.get_items(request)

        data = result.data
        items = data["items"]
        pagination = data["pagination"]

        assert len(items) == 5
        assert pagination["total_pages"] == 3
        assert pagination["per_page"] == 5

    def test_get_items_invalid_page(self, request_factory, lost_items):
        """Invalid page (string) should default to page 1."""
        request = request_factory.get("/?page=invalid&per_page=10")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
                result = GetLostItemsQuery.get_items(request)

        assert result.is_success is True
        assert result.status_code == 200
        data = result.data
        assert data is not None

    def test_get_items_page_beyond_last(self, request_factory, lost_items):
        """Page beyond total should return last page."""
        request = request_factory.get("/?page=999&per_page=10")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
                result = GetLostItemsQuery.get_items(request)

        data = result.data
        assert len(data["items"]) == 5

    def test_get_items_image_url(self, request_factory, lost_item_with_image):
        """Test that image URL is built correctly when image exists."""
        request = request_factory.get("/?page=1&per_page=10")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
                result = GetLostItemsQuery.get_items(request)

        data = result.data
        found = False
        for item in data["items"]:
            if item["item_name"] == "Item with Image":
                assert item["image"] == "http://testserver/media/test.jpg"
                found = True
                break
        assert found, "Item with image not found in result"

    def test_get_items_image_url_null(self, request_factory, lost_items):
        """When no image, image field should be None."""
        request = request_factory.get("/?page=1&per_page=10")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
                result = GetLostItemsQuery.get_items(request)

        for item in result.data["items"]:
            assert item["image"] is None

    def test_get_items_excludes_answers(self, request_factory, lost_items):
        """Ensure answer1 and answer2 are never included in the response."""
        request = request_factory.get("/?page=1&per_page=10")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
                result = GetLostItemsQuery.get_items(request)

        for item in result.data["items"]:
            assert "answer1" not in item
            assert "answer2" not in item

    def test_get_items_exception(self, request_factory):
        """Return 500 on unexpected database error."""
        request = request_factory.get("/?page=1&per_page=10")

        with patch("apps.campus.BBL.Queries.lost_and_found.LostAndFound.objects.filter", side_effect=Exception("DB error")):
            with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
                # aget_or_set will call the callback, which raises the exception
                mock_aget_or_set.side_effect = Exception("DB error")  # Simulate the exception bubbling up
                result = GetLostItemsQuery.get_items(request)

        assert result.is_success is False
        assert result.status_code == 500
        assert "An unexpected error occurred" in result.message

    def test_get_items_empty_result(self, request_factory, db):
        """When no items exist, return empty list with pagination metadata."""
        LostAndFound.objects.all().delete()
        request = request_factory.get("/?page=1&per_page=10")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
                result = GetLostItemsQuery.get_items(request)

        data = result.data
        assert data["items"] == []
        pagination = data["pagination"]
        assert pagination["total_items"] == 0
        assert pagination["total_pages"] == 1
        assert pagination["has_next"] is False
        assert pagination["has_previous"] is False

    def test_get_items_negative_per_page(self, request_factory, lost_items):
        """Negative per_page should default to 1."""
        request = request_factory.get("/?page=1&per_page=-5")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
                result = GetLostItemsQuery.get_items(request)

        data = result.data
        assert data["pagination"]["per_page"] == 1

    def test_get_items_per_page_exceeds_max(self, request_factory, lost_items):
        """per_page > 100 should be capped at 100."""
        request = request_factory.get("/?page=1&per_page=200")

        with patch("apps.campus.BBL.Queries.lost_and_found.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            with patch.object(request, 'build_absolute_uri', return_value="http://testserver/media/test.jpg"):
                result = GetLostItemsQuery.get_items(request)

        data = result.data
        assert data["pagination"]["per_page"] == 100