import pytest
from http import HTTPStatus
from unittest.mock import patch

from apps.users.BBL.Queries.PaystackConfirm import PaystackConfirmQuery


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def valid_reference():
    return "PAY-1234567890"

@pytest.fixture
def mock_verify_success():
    """Mock verify_paystack_payment returning a successful response."""
    return {
        "success": True,
        "message": "Payment verified successfully",
        "purchase": {
            "purchase_id": 42,
            "points_awarded": 100,
            "amount_paid": "10.00",
        }
    }

@pytest.fixture
def mock_verify_failure():
    """Mock verify_paystack_payment returning a failure response."""
    return {
        "success": False,
        "error": "Payment not completed",
    }


# ── Tests ─────────────────────────────────────────────────────────────

class TestPaystackConfirmQuery:

    def test_execute_missing_reference(self):
        """When reference is missing, return 400."""
        result = PaystackConfirmQuery.execute(None)
        assert result.is_success is False
        assert result.status_code == HTTPStatus.BAD_REQUEST
        assert result.message == "No reference provided"
        assert result.data is None

    def test_execute_success(self, valid_reference, mock_verify_success):
        """Happy path: reference provided, verification succeeds."""
        with patch("apps.users.BBL.Queries.PaystackConfirm.verify_paystack_payment") as mock_verify:
            mock_verify.return_value = mock_verify_success
            result = PaystackConfirmQuery.execute(valid_reference)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.message == "Payment verified successfully"
        assert result.data["reference"] == valid_reference
        # The code uses set literals {value} so we compare to sets.
        assert result.data["purchase_id"] == {mock_verify_success["purchase"]["purchase_id"]}
        assert result.data["points_awarded"] == {mock_verify_success["purchase"]["points_awarded"]}
        assert result.data["amount_paid"] == {mock_verify_success["purchase"]["amount_paid"]}
        mock_verify.assert_called_once_with(valid_reference)

    def test_execute_verification_failure(self, valid_reference, mock_verify_failure):
        """When verification fails, return 400 with error message."""
        with patch("apps.users.BBL.Queries.PaystackConfirm.verify_paystack_payment") as mock_verify:
            mock_verify.return_value = mock_verify_failure
            result = PaystackConfirmQuery.execute(valid_reference)

        assert result.is_success is False
        assert result.status_code == 400
        assert result.message == "Payment not completed"
        assert result.data["reference"] == valid_reference
        mock_verify.assert_called_once_with(valid_reference)

    def test_execute_verify_raises_exception(self, valid_reference):
        """If verify_paystack_payment raises an exception, it should propagate (not caught)."""
        with patch("apps.users.BBL.Queries.PaystackConfirm.verify_paystack_payment") as mock_verify:
            mock_verify.side_effect = Exception("Network error")
            with pytest.raises(Exception) as excinfo:
                PaystackConfirmQuery.execute(valid_reference)
            assert "Network error" in str(excinfo.value)

    def test_execute_verify_returns_missing_keys(self, valid_reference):
        """If verify returns success but missing purchase keys, code will KeyError."""
        with patch("apps.users.BBL.Queries.PaystackConfirm.verify_paystack_payment") as mock_verify:
            mock_verify.return_value = {
                "success": True,
                "message": "OK",
                "purchase": {"purchase_id": 1}  # missing points_awarded, amount_paid
            }
            with pytest.raises(KeyError):
                PaystackConfirmQuery.execute(valid_reference)

    def test_execute_verify_returns_success_without_purchase(self, valid_reference):
        """If verification returns success but purchase is missing, code will TypeError."""
        with patch("apps.users.BBL.Queries.PaystackConfirm.verify_paystack_payment") as mock_verify:
            mock_verify.return_value = {"success": True, "message": "OK"}  # no purchase key
            with pytest.raises(TypeError) as excinfo:
                PaystackConfirmQuery.execute(valid_reference)
            assert "'NoneType' object is not subscriptable" in str(excinfo.value)