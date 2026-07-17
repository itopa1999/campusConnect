import pytest
from unittest.mock import patch, MagicMock, ANY
import uuid

from django.test import RequestFactory

from apps.campus.BBL.Queries.get_lookup import LookUpQuery
from apps.campus.models import Category, CampusHotspot
from utils.enums import AdvertTypeEnum, BadgeListingType, ListingType


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def test_categories(db):
    """Create several categories with unique names and sort orders."""
    suffix = uuid.uuid4().hex[:6]
    categories = [
        Category.objects.create(name=f"Electronics_{suffix}", icon="fa-laptop", description="Gadgets", sort_order=2),
        Category.objects.create(name=f"Books_{suffix}", icon="fa-book", description="Textbooks", sort_order=1),
        Category.objects.create(name=f"Clothing_{suffix}", icon="fa-tshirt", description="Fashion", sort_order=3),
    ]
    return categories


@pytest.fixture
def test_hotspots(db):
    """Create several hotspots."""
    hotspots = [
        CampusHotspot.objects.create(name="Library", description="Main library", sort_order=2),
        CampusHotspot.objects.create(name="Cafeteria", description="Student center", sort_order=1),
        CampusHotspot.objects.create(name="Lecture Hall", description="New building", sort_order=3),
    ]
    return hotspots


# ── Tests ─────────────────────────────────────────────────────────────

class TestLookUpQuery:

    def test_get_lookup_cache_hit(self, request_factory):
        """When data is cached, return it without hitting the database."""
        cached_data = {
            "categories": [{"id": 1, "name": "Test"}],
            "hotspots": [{"id": 2, "name": "Spot"}],
            "badge_choices": [{"value": "bundle", "label": "Bundle"}],
            "type_choices": [{"value": "sell", "label": "Sell"}],
            "advert_type": [{"value": "banner", "label": "Banner", "points": 2}],
        }
        request = request_factory.get("/fake")

        with patch("apps.campus.BBL.Queries.get_lookup.GlobalCache.get_or_set") as mock_get_or_set:
            mock_get_or_set.return_value = cached_data
            result = LookUpQuery.get_lookup(request)

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

    def test_get_lookup_cache_miss(self, test_categories, test_hotspots, request_factory):
        """When cache is empty, fetch from DB, build the data, cache it, and return."""
        request = request_factory.get("/fake")

        with patch("apps.campus.BBL.Queries.get_lookup.GlobalCache.get_or_set") as mock_get_or_set:
            # Simulate cache miss by executing the callback
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = LookUpQuery.get_lookup(request)

        assert result.is_success is True
        assert result.status_code == 200
        data = result.data

        # ── Categories ──
        categories_data = data["categories"]
        assert len(categories_data) == len(test_categories)
        expected_names = sorted(test_categories, key=lambda c: (c.sort_order, c.name))
        actual_names = [cat["name"] for cat in categories_data]
        assert actual_names == [c.name for c in expected_names]

        for cat_data, db_cat in zip(categories_data, expected_names):
            assert cat_data["id"] == db_cat.id
            assert cat_data["name"] == db_cat.name
            assert cat_data["icon"] == db_cat.icon
            assert cat_data["description"] == db_cat.description

        # ── Hotspots ──
        hotspots_data = data["hotspots"]
        assert len(hotspots_data) == len(test_hotspots)
        expected_hotspots = sorted(test_hotspots, key=lambda h: (h.sort_order, h.name))
        actual_hotspot_names = [hs["name"] for hs in hotspots_data]
        assert actual_hotspot_names == [hs.name for hs in expected_hotspots]

        for hs_data, db_hs in zip(hotspots_data, expected_hotspots):
            assert hs_data["id"] == db_hs.id
            assert hs_data["name"] == db_hs.name
            assert hs_data["description"] == db_hs.description

        # ── Badge choices ──
        badge_choices = data["badge_choices"]
        expected_badges = [{"value": choice[0], "label": choice[1]} for choice in BadgeListingType.choices()]
        assert badge_choices == expected_badges

        # ── Type choices ──
        type_choices = data["type_choices"]
        expected_types = [{"value": choice[0], "label": choice[1]} for choice in ListingType.choices()]
        assert type_choices == expected_types

        # ── Advert types ──
        advert_types = data["advert_type"]
        expected_adverts = AdvertTypeEnum.choices()
        assert advert_types == expected_adverts

        # Cache should have been called with the correct key and the callback
        mock_get_or_set.assert_called_once_with(
            key=ANY,
            callback=ANY,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_lookup_ordering(self, db, request_factory):
        """Test that sort_order is respected even with equal sort_order (fallback to name)."""
        suffix = uuid.uuid4().hex[:6]
        Category.objects.create(name=f"Books_{suffix}", sort_order=1)
        Category.objects.create(name=f"Zoo_{suffix}", sort_order=1)
        Category.objects.create(name=f"Electronics_{suffix}", sort_order=2)

        request = request_factory.get("/fake")

        with patch("apps.campus.BBL.Queries.get_lookup.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = LookUpQuery.get_lookup(request)

        categories = result.data["categories"]
        names = [c["name"] for c in categories]
        # The first two should be "Books_{suffix}" and "Zoo_{suffix}" (alphabetical)
        assert names[0] == f"Books_{suffix}"
        assert names[1] == f"Zoo_{suffix}"

    def test_get_lookup_deleted_items_excluded(self, test_categories, test_hotspots, request_factory):
        """Soft-deleted categories and hotspots should be excluded."""
        # Delete one category and one hotspot
        deleted_cat = test_categories[0]
        deleted_cat.is_deleted = True
        deleted_cat.save()

        deleted_hs = test_hotspots[0]
        deleted_hs.is_deleted = True
        deleted_hs.save()

        request = request_factory.get("/fake")

        with patch("apps.campus.BBL.Queries.get_lookup.GlobalCache.get_or_set") as mock_get_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_get_or_set.side_effect = side_effect

            result = LookUpQuery.get_lookup(request)

        categories = result.data["categories"]
        hotspots = result.data["hotspots"]

        # Deleted items should not appear
        assert deleted_cat.id not in [c["id"] for c in categories]
        assert deleted_hs.id not in [h["id"] for h in hotspots]

        # Number of items should be reduced
        assert len(categories) == len(test_categories) - 1
        assert len(hotspots) == len(test_hotspots) - 1