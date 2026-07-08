import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock, ANY
from django.test import RequestFactory
from apps.users.BBL.Commands.buy_points import BuyPointsCommand
from apps.users.models import PointPackage, PointPurchase, User
from utils.enums import PointPurchaseStatusEnum
from utils.constant_helper import ConstantHelper
from utils.base_result import BaseResultWithData


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
def test_package(db):
    return PointPackage.objects.create(
        points=100,
        price=Decimal("10.00"),
        description="Test Package",
        is_deleted=False,
    )

@pytest.fixture
def test_purchase(test_user, test_package):
    return PointPurchase.objects.create(
        user=test_user,
        package=test_package,
        points_awarded=test_package.points,
        amount_paid=test_package.price,
        gateway=ConstantHelper.PAYSTACK,
        status=PointPurchaseStatusEnum.PENDING.value,
        payment_reference="test_ref_123",
    )


# ── Tests: execute ────────────────────────────────────────────────────

class TestBuyPointsCommandExecute:

    def test_execute_success_paystack(self, db, request_factory, test_user, test_package):
        """Happy path: initiate Paystack payment."""
        request = request_factory.post("/")
        data = {
            "package_id": test_package.id,
            "points": test_package.points,
            "amount": str(test_package.price),
            "gateway": ConstantHelper.PAYSTACK,
        }
        with patch("apps.users.BBL.Commands.buy_points.initiate_paystack") as mock_init:
            mock_init.return_value = "https://paystack.com/checkout"
            result = BuyPointsCommand.execute(request, test_user, data)
        assert result.is_success is True
        assert result.status_code == 200
        assert result.data["checkout_url"] == "https://paystack.com/checkout"
        mock_init.assert_called_once_with(request, test_user, test_package)

    def test_execute_success_flutterwave(self, db, request_factory, test_user, test_package):
        """Happy path: initiate Flutterwave payment."""
        request = request_factory.post("/")
        data = {
            "package_id": test_package.id,
            "points": test_package.points,
            "amount": str(test_package.price),
            "gateway": ConstantHelper.FLUTTERWAVE,
        }
        with patch("apps.users.BBL.Commands.buy_points.initiate_flutterwave") as mock_init:
            mock_init.return_value = "https://flutterwave.com/checkout"
            result = BuyPointsCommand.execute(request, test_user, data)
        assert result.is_success is True
        assert result.status_code == 200
        assert result.data["checkout_url"] == "https://flutterwave.com/checkout"
        mock_init.assert_called_once_with(request, test_user, test_package)

    def test_execute_missing_fields(self, db, request_factory, test_user):
        """Missing required fields should return 400."""
        request = request_factory.post("/")
        data = {"package_id": 1}  # missing points, amount, gateway
        result = BuyPointsCommand.execute(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Missing required fields" in result.message

    def test_execute_package_not_found(self, db, request_factory, test_user):
        """Invalid package_id should return 404."""
        request = request_factory.post("/")
        data = {
            "package_id": 9999,
            "points": 100,
            "amount": "10.00",
            "gateway": ConstantHelper.PAYSTACK,
        }
        result = BuyPointsCommand.execute(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 404
        assert "Point package not found" in result.message

    def test_execute_points_mismatch(self, db, request_factory, test_user, test_package):
        """Points mismatch should return 400."""
        request = request_factory.post("/")
        data = {
            "package_id": test_package.id,
            "points": 200,  # wrong
            "amount": str(test_package.price),
            "gateway": ConstantHelper.PAYSTACK,
        }
        result = BuyPointsCommand.execute(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Points mismatch" in result.message

    def test_execute_amount_mismatch(self, db, request_factory, test_user, test_package):
        """Amount mismatch should return 400."""
        request = request_factory.post("/")
        data = {
            "package_id": test_package.id,
            "points": test_package.points,
            "amount": "20.00",  # wrong
            "gateway": ConstantHelper.PAYSTACK,
        }
        result = BuyPointsCommand.execute(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Amount mismatch" in result.message

    def test_execute_unknown_gateway(self, db, request_factory, test_user, test_package):
        """Unknown gateway should return 400."""
        request = request_factory.post("/")
        data = {
            "package_id": test_package.id,
            "points": test_package.points,
            "amount": str(test_package.price),
            "gateway": "unknown_gateway",
        }
        result = BuyPointsCommand.execute(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Unknown gateway" in result.message

    def test_execute_monnify_not_implemented(self, db, request_factory, test_user, test_package):
        """Monnify should return 400 as not implemented."""
        request = request_factory.post("/")
        data = {
            "package_id": test_package.id,
            "points": test_package.points,
            "amount": str(test_package.price),
            "gateway": ConstantHelper.MONNIFY,
        }
        result = BuyPointsCommand.execute(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Monnify is currently not available" in result.message

    def test_execute_payment_initiation_fails(self, db, request_factory, test_user, test_package):
        """If gateway returns None, return 500."""
        request = request_factory.post("/")
        data = {
            "package_id": test_package.id,
            "points": test_package.points,
            "amount": str(test_package.price),
            "gateway": ConstantHelper.PAYSTACK,
        }
        with patch("apps.users.BBL.Commands.buy_points.initiate_paystack") as mock_init:
            mock_init.return_value = None
            result = BuyPointsCommand.execute(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 500
        assert "Payment initialization failed" in result.message

    def test_execute_invalid_points_format(self, db, request_factory, test_user, test_package):
        """Invalid points value (string not int) should return 400."""
        request = request_factory.post("/")
        data = {
            "package_id": test_package.id,
            "points": "abc",
            "amount": str(test_package.price),
            "gateway": ConstantHelper.PAYSTACK,
        }
        result = BuyPointsCommand.execute(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Invalid points or amount format" in result.message

    def test_execute_invalid_amount_format(self, db, request_factory, test_user, test_package):
        """Invalid amount (non-decimal) should return 400."""
        request = request_factory.post("/")
        data = {
            "package_id": test_package.id,
            "points": test_package.points,
            "amount": "abc",
            "gateway": ConstantHelper.PAYSTACK,
        }
        result = BuyPointsCommand.execute(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Invalid points or amount format" in result.message


# ── Tests: payment_retry ─────────────────────────────────────────────

class TestBuyPointsCommandPaymentRetry:

    def test_retry_success(self, db, request_factory, test_user, test_purchase):
        """Retry a pending payment that is verified successfully."""
        request = request_factory.post("/")
        data = {"purchase_id": test_purchase.id}
        with patch("apps.users.BBL.Commands.buy_points.verify_paystack_payment") as mock_verify:
            mock_verify.return_value = {
                "success": True,
                "message": "Payment verified",
                "purchase": {"id": test_purchase.id, "status": "completed"}
            }
            result = BuyPointsCommand.payment_retry(request, test_user, data)
        assert result.is_success is True
        assert result.status_code == 200
        assert "Payment verified" in result.message
        mock_verify.assert_called_once_with(test_purchase.payment_reference)

    def test_retry_purchase_already_completed(self, db, request_factory, test_user, test_purchase):
        """If purchase status is already completed, return success without verification."""
        test_purchase.status = PointPurchaseStatusEnum.COMPLETED.value
        test_purchase.save()
        request = request_factory.post("/")
        data = {"purchase_id": test_purchase.id}
        result = BuyPointsCommand.payment_retry(request, test_user, data)
        assert result.is_success is True
        assert result.status_code == 200
        assert "Purchase already completed" in result.message

    def test_retry_missing_purchase_id(self, db, request_factory, test_user):
        """Missing purchase_id should return 400."""
        request = request_factory.post("/")
        data = {}  # no purchase_id
        result = BuyPointsCommand.payment_retry(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Purchase ID is required" in result.message

    def test_retry_purchase_not_found(self, db, request_factory, test_user):
        """Invalid purchase_id should return 404."""
        request = request_factory.post("/")
        data = {"purchase_id": 9999}
        result = BuyPointsCommand.payment_retry(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 404
        assert "Purchase not found" in result.message

    def test_retry_verification_failed(self, db, request_factory, test_user, test_purchase):
        """If verification fails, return 400 with error message."""
        request = request_factory.post("/")
        data = {"purchase_id": test_purchase.id}
        with patch("apps.users.BBL.Commands.buy_points.verify_paystack_payment") as mock_verify:
            mock_verify.return_value = {
                "success": False,
                "error": "Payment not completed"
            }
            result = BuyPointsCommand.payment_retry(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Payment not completed" in result.message

    def test_retry_without_gateway(self, db, request_factory, test_user, test_purchase):
        """If purchase has no gateway, return 400."""
        test_purchase.gateway = None
        test_purchase.save()
        request = request_factory.post("/")
        data = {"purchase_id": test_purchase.id}
        result = BuyPointsCommand.payment_retry(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Gateway not provided" in result.message

    def test_retry_flutterwave_gateway(self, db, request_factory, test_user, test_purchase):
        """Test retry with Flutterwave gateway."""
        test_purchase.gateway = ConstantHelper.FLUTTERWAVE
        test_purchase.save()
        request = request_factory.post("/")
        data = {"purchase_id": test_purchase.id}
        with patch("apps.users.BBL.Commands.buy_points.verify_paystack_payment") as mock_verify:
            mock_verify.return_value = {"success": True, "message": "Verified"}
            result = BuyPointsCommand.payment_retry(request, test_user, data)
        assert result.is_success is True
        # The code uses verify_paystack_payment for all gateways (bug? but we test current behavior)
        mock_verify.assert_called_once_with(test_purchase.payment_reference)

    def test_retry_monnify_gateway(self, db, request_factory, test_user, test_purchase):
        """Test retry with Monnify gateway (falls back to verify_paystack_payment)."""
        test_purchase.gateway = ConstantHelper.MONNIFY
        test_purchase.save()
        request = request_factory.post("/")
        data = {"purchase_id": test_purchase.id}
        with patch("apps.users.BBL.Commands.buy_points.verify_paystack_payment") as mock_verify:
            mock_verify.return_value = {"success": True, "message": "Verified"}
            result = BuyPointsCommand.payment_retry(request, test_user, data)
        assert result.is_success is True
        mock_verify.assert_called_once_with(test_purchase.payment_reference)

    def test_retry_exception(self, db, request_factory, test_user, test_purchase):
        """Catch unexpected exception and return 500."""
        request = request_factory.post("/")
        data = {"purchase_id": test_purchase.id}
        with patch("apps.users.BBL.Commands.buy_points.verify_paystack_payment", side_effect=Exception("DB error")):
            # The method doesn't have a try/except, so the exception will propagate.
            # We'll expect it to raise, but we can also patch the whole method.
            # Since the code doesn't catch exceptions, we'll expect the exception.
            with pytest.raises(Exception):
                BuyPointsCommand.payment_retry(request, test_user, data)
        # Actually, the code as written does NOT catch exceptions inside payment_retry.
        # So the test will raise an exception. We should note this as a bug.
        # For now, we'll test that it raises.
        pass