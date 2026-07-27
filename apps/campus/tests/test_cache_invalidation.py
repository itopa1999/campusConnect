from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

import apps.campus as campus_app_module
from apps.campus.apps import CampusConfig
from apps.campus.models import Category, Listing
from apps.users.models import User
from utils.enums import ListingStatusTypeEnum, ListingTypeEnum


@pytest.mark.django_db
def test_listing_save_triggers_cache_invalidation():
    CampusConfig("campus", campus_app_module).ready()

    user = User.objects.create_user(
        email="cache-test@example.com",
        password="strongpassword",
        first_name="Cache",
        last_name="Tester",
    )
    category = Category.objects.create(name="Test Category", icon="fa-test", description="Test")

    with patch("utils.cache_helper.GlobalCache.delete") as mock_delete, patch(
        "utils.cache_helper.GlobalCache.delete_prefix"
    ) as mock_delete_prefix:
        Listing.objects.create(
            user=user,
            category=category,
            title="Cache invalidation test",
            description="Should trigger cache invalidation",
            price=50.00,
            listing_type=ListingTypeEnum.SELL.value,
            status=ListingStatusTypeEnum.ACTIVE.value,
            expires_at=timezone.now() + timedelta(days=10),
        )

    assert mock_delete.called or mock_delete_prefix.called
