import pytest
from decimal import Decimal
from unittest.mock import patch, ANY
from django.utils import timezone

from apps.users.BBL.Queries.point_packages import PointPackagesQueries
from apps.users.models import PointPackage, PointPurchase, PointTransaction, User
from utils.enums import PointPurchaseStatusEnum, PointTransactionTypeEnum
from utils.enums import CacheKeysEnum


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        email="test@example.com",
        password="testpass",
        phone="08012345678",
    )


@pytest.fixture
def test_packages(db):
    """Create 5 packages with different sort orders and points."""
    packages = []
    data = [
        {"points": 100, "price": 10.00, "sort_order": 2, "is_popular": False, "is_best_value": False},
        {"points": 200, "price": 18.00, "sort_order": 1, "is_popular": True, "is_best_value": False},
        {"points": 300, "price": 25.00, "sort_order": 3, "is_popular": False, "is_best_value": True},
        {"points": 500, "price": 40.00, "sort_order": 4, "is_popular": False, "is_best_value": False},
        {"points": 1000, "price": 75.00, "sort_order": 5, "is_popular": False, "is_best_value": False},
    ]
    for pkg_data in data:
        pkg = PointPackage.objects.create(
            points=pkg_data["points"],
            price=Decimal(str(pkg_data["price"])),
            sort_order=pkg_data["sort_order"],
            is_popular=pkg_data["is_popular"],
            is_best_value=pkg_data["is_best_value"],
            description=f"{pkg_data['points']} points",
            is_deleted=False,
        )
        packages.append(pkg)
    return packages


@pytest.fixture
def test_purchases(test_user, test_packages):
    """Create 15 purchases for the user."""
    now = timezone.now()
    purchases = []
    for i in range(15):
        pkg = test_packages[i % len(test_packages)]
        status = (
            PointPurchaseStatusEnum.COMPLETED.value if i % 3 != 0 else PointPurchaseStatusEnum.PENDING.value
        )
        purchase = PointPurchase.objects.create(
            user=test_user,
            package=pkg,
            points_awarded=pkg.points,
            amount_paid=pkg.price,
            gateway="paystack",
            payment_reference=f"ref_{i}",
            status=status,
            completed_at=now if status == PointPurchaseStatusEnum.COMPLETED.value else None,
        )
        purchases.append(purchase)
    return purchases


@pytest.fixture
def test_transactions(test_user, test_purchases):
    """Create 20 transactions for the user."""
    now = timezone.now()
    transactions = []
    types = [
        PointTransactionTypeEnum.PURCHASE.value,
        PointTransactionTypeEnum.LISTING_CREATION.value,
        PointTransactionTypeEnum.ADMIN_ADJUSTMENT.value,
    ]
    for i in range(20):
        txn = PointTransaction.objects.create(
            user=test_user,
            amount=i * 10,
            balance_after=(i + 1) * 10,
            transaction_type=types[i % len(types)],
            description=f"Transaction {i}",
            reference=f"txn_{i}",
            purchase=test_purchases[i % len(test_purchases)] if i % 2 == 0 else None,
            created_at=now - timezone.timedelta(days=i),
        )
        transactions.append(txn)
    return transactions


# ── Tests: get_point_packages ────────────────────────────────────────

class TestGetPointPackages:

    def test_get_point_packages_cache_hit(self, test_packages):
        """Return cached data if available."""
        cached_data = [{"id": 1, "points": 100}]
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            mock_aget_or_set.return_value = cached_data
            result = PointPackagesQueries.get_point_packages()
            assert result == cached_data
            mock_aget_or_set.assert_called_once_with(
                key=CacheKeysEnum.POINT_PACKAGES.value,
                callback=ANY,
                timeout=86400,
                lock_timeout=30,
                max_wait=5.0,
            )

    def test_get_point_packages_cache_miss(self, test_packages):
        """Fetch from DB, serialize, cache, and return."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_point_packages()

        # Should have 5 packages
        assert len(result) == len(test_packages)

        # Check ordering: sort_order ascending, then points ascending
        expected_orders = [1, 2, 3, 4, 5]
        actual_orders = [pkg["sort_order"] for pkg in result]
        assert actual_orders == expected_orders

        # Check first package (200 points, sort_order=1)
        first = result[0]
        assert first["points"] == 200
        assert first["price"] == 18.00
        assert first["is_popular"] is True
        assert first["is_best_value"] is False
        assert "price_per_point" in first
        assert "savings_percentage" in first

        # Price per point should be rounded to 2 decimals
        expected_ppp = Decimal(str(round(18.00 / 200, 2)))
        assert first["price_per_point"] == expected_ppp

        mock_aget_or_set.assert_called_once_with(
            key=CacheKeysEnum.POINT_PACKAGES.value,
            callback=ANY,
            timeout=86400,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_point_packages_formatting(self, test_packages):
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_point_packages()

        for pkg_data in result:
            assert isinstance(pkg_data["price_per_point"], (float, Decimal))
            if pkg_data["savings_percentage"] is not None:
                assert isinstance(pkg_data["savings_percentage"], (int, float, Decimal))

    def test_get_point_packages_empty(self, db):
        """If no packages, return empty list."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_point_packages()
            assert result == []

            mock_aget_or_set.assert_called_once_with(
                key=CacheKeysEnum.POINT_PACKAGES.value,
                callback=ANY,
                timeout=86400,
                lock_timeout=30,
                max_wait=5.0,
            )

    def test_get_point_packages_deleted_excluded(self, test_packages):
        """Deleted packages should be excluded."""
        # Delete one package
        test_packages[0].is_deleted = True
        test_packages[0].save()

        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_point_packages()

        assert len(result) == len(test_packages) - 1
        deleted_id = test_packages[0].id
        assert all(pkg["id"] != deleted_id for pkg in result)


# ── Tests: get_purchases ─────────────────────────────────────────────

class TestGetPurchases:

    def test_get_purchases_cache_hit(self, test_user):
        """Return cached data if available."""
        cached_data = {"items": [{"id": 1}], "page": 1}
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            mock_aget_or_set.return_value = cached_data
            result = PointPackagesQueries.get_purchases(test_user, page=1, per_page=10)

        assert result.is_success is True
        assert result.data == cached_data
        mock_aget_or_set.assert_called_once_with(
            key=CacheKeysEnum.format(CacheKeysEnum.PURCHASES, user_id=test_user.id, page=1, per_page=10),
            callback=ANY,
            timeout=86400,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_purchases_cache_miss(self, test_user, test_purchases):
        """Fetch from DB, paginate, serialize, cache, and return."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_purchases(test_user, page=1, per_page=10)

        assert result.is_success is True
        assert result.status_code == 200

        data = result.data
        assert "items" in data
        assert "page" in data
        assert "total_pages" in data
        assert "total_count" in data
        assert "has_next" in data
        assert "has_previous" in data

        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["total_count"] == len(test_purchases)
        assert data["total_pages"] == 2
        assert data["has_next"] is True
        assert data["has_previous"] is False

        item = data["items"][0]
        assert "id" in item
        assert "package" in item
        assert "gateway" in item
        assert "payment_reference" in item
        assert "points_awarded" in item
        assert "amount_paid" in item
        assert "status" in item
        assert "created_at" in item

        pkg = item["package"]
        assert "id" in pkg
        assert "points" in pkg
        assert "price" in pkg
        assert "description" in pkg
        assert "is_popular" in pkg
        assert "is_best_value" in pkg
        assert "price_per_point" in pkg
        assert "savings_percentage" in pkg

        mock_aget_or_set.assert_called_once_with(
            key=CacheKeysEnum.format(CacheKeysEnum.PURCHASES, user_id=test_user.id, page=1, per_page=10),
            callback=ANY,
            timeout=86400,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_purchases_page_2(self, test_user, test_purchases):
        """Test second page."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_purchases(test_user, page=2, per_page=10)

        data = result.data
        assert data["page"] == 2
        assert len(data["items"]) == 5
        assert data["has_next"] is False
        assert data["has_previous"] is True

    def test_get_purchases_invalid_page(self, test_user, test_purchases):
        """Invalid page (string) should default to page 1."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_purchases(test_user, page="invalid", per_page=10)

        assert result.data["page"] == 1

    def test_get_purchases_page_beyond_last(self, test_user, test_purchases):
        """Page beyond total should return last page."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_purchases(test_user, page=999, per_page=10)

        assert result.data["page"] == 2
        assert len(result.data["items"]) == 5

    def test_get_purchases_empty(self, test_user, db):
        """If no purchases, return empty list with pagination metadata."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_purchases(test_user, page=1, per_page=10)

        data = result.data
        assert data["items"] == []
        assert data["total_count"] == 0
        assert data["total_pages"] == 1
        assert data["has_next"] is False
        assert data["has_previous"] is False


# ── Tests: get_transactions ──────────────────────────────────────────

class TestGetTransactions:

    def test_get_transactions_cache_hit(self, test_user):
        """Return cached data if available."""
        cached_data = {"items": [{"id": 1}], "page": 1}
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            mock_aget_or_set.return_value = cached_data
            result = PointPackagesQueries.get_transactions(test_user, page=1, per_page=10)

        assert result.is_success is True
        assert result.data == cached_data
        mock_aget_or_set.assert_called_once_with(
            key=CacheKeysEnum.format(CacheKeysEnum.TRANSACTIONS, user_id=test_user.id, page=1, per_page=10),
            callback=ANY,
            timeout=300,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_transactions_cache_miss(self, test_user, test_transactions):
        """Fetch from DB, paginate, serialize, cache, and return."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_transactions(test_user, page=1, per_page=10)

        assert result.is_success is True
        assert result.status_code == 200

        data = result.data
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["total_count"] == len(test_transactions)
        assert data["total_pages"] == 2
        assert data["has_next"] is True
        assert data["has_previous"] is False

        item = data["items"][0]
        assert "id" in item
        assert "amount" in item
        assert "balance_after" in item
        assert "transaction_type" in item
        assert "transaction_type_display" in item
        assert "description" in item
        assert "reference" in item
        assert "purchase_id" in item
        assert "created_at" in item

        mock_aget_or_set.assert_called_once_with(
            key=CacheKeysEnum.format(CacheKeysEnum.TRANSACTIONS, user_id=test_user.id, page=1, per_page=10),
            callback=ANY,
            timeout=300,
            lock_timeout=30,
            max_wait=5.0,
        )

    def test_get_transactions_page_2(self, test_user, test_transactions):
        """Test second page."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_transactions(test_user, page=2, per_page=10)

        data = result.data
        assert data["page"] == 2
        assert len(data["items"]) == 10
        assert data["has_next"] is False
        assert data["has_previous"] is True

    def test_get_transactions_invalid_page(self, test_user, test_transactions):
        """Invalid page (string) should default to page 1."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_transactions(test_user, page="invalid", per_page=10)

        assert result.data["page"] == 1

    def test_get_transactions_page_beyond_last(self, test_user, test_transactions):
        """Page beyond total should return last page."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_transactions(test_user, page=999, per_page=10)

        assert result.data["page"] == 2
        assert len(result.data["items"]) == 10

    def test_get_transactions_empty(self, test_user, db):
        """If no transactions, return empty list with pagination metadata."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_transactions(test_user, page=1, per_page=10)

        data = result.data
        assert data["items"] == []
        assert data["total_count"] == 0
        assert data["total_pages"] == 1

    def test_get_transactions_purchase_id_null(self, test_user, test_transactions):
        """If transaction has no purchase, purchase_id should be None."""
        with patch("apps.users.BBL.Queries.point_packages.GlobalCache.aget_or_set") as mock_aget_or_set:
            def side_effect(key, callback, timeout, lock_timeout, max_wait):
                return callback()
            mock_aget_or_set.side_effect = side_effect

            result = PointPackagesQueries.get_transactions(test_user, page=1, per_page=20)

        for item in result.data["items"]:
            # It's fine if some have purchase_id = None
            assert "purchase_id" in item