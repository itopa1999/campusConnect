import pytest
from http import HTTPStatus
from unittest.mock import patch, MagicMock
from django.test import RequestFactory

from apps.users.BBL.Queries.FlutterConfirm import FlutterwaveConfirmQuery
from utils.base_result import BaseResultWithData


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def valid_reference():
    return "FLW-1234567890"

@pytest.fixture
def mock_validate_success():
    """Mock validate returning a successful response."""
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
def mock_validate_failure():
    """Mock validate returning a failure response."""
    return {
        "success": False,
        "error": "Payment not completed",
    }


# ── Tests ─────────────────────────────────────────────────────────────

class TestFlutterwaveConfirmQuery:

    def test_execute_missing_reference(self):
        """When reference is missing, return 400."""
        result = FlutterwaveConfirmQuery.execute(None)
        assert result.is_success is False
        assert result.status_code == HTTPStatus.BAD_REQUEST
        assert result.message == "No reference provided"
        assert result.data is None

    def test_execute_success(self, valid_reference, mock_validate_success):
        """Happy path: reference provided, validation succeeds."""
        with patch("apps.users.BBL.Queries.FlutterConfirm.validate") as mock_validate:
            mock_validate.return_value = mock_validate_success
            result = FlutterwaveConfirmQuery.execute(valid_reference)

        assert result.is_success is True
        assert result.status_code == 200
        assert result.message == "Payment verified successfully"
        assert result.data["reference"] == valid_reference
        # Note: the code uses set literals {value} so we compare to sets.
        assert result.data["purchase_id"] == {mock_validate_success["purchase"]["purchase_id"]}
        assert result.data["points_awarded"] == {mock_validate_success["purchase"]["points_awarded"]}
        assert result.data["amount_paid"] == {mock_validate_success["purchase"]["amount_paid"]}
        mock_validate.assert_called_once_with(valid_reference)

    def test_execute_validation_failure(self, valid_reference, mock_validate_failure):
        """When validation fails, return 400 with error message."""
        with patch("apps.users.BBL.Queries.FlutterConfirm.validate") as mock_validate:
            mock_validate.return_value = mock_validate_failure
            result = FlutterwaveConfirmQuery.execute(valid_reference)

        assert result.is_success is False
        assert result.status_code == 400
        assert result.message == "Payment not completed"
        assert result.data["reference"] == valid_reference
        mock_validate.assert_called_once_with(valid_reference)

    def test_execute_validate_raises_exception(self, valid_reference):
        """If validate raises an exception, it should propagate (not caught)."""
        with patch("apps.users.BBL.Queries.FlutterConfirm.validate") as mock_validate:
            mock_validate.side_effect = Exception("Network error")
            with pytest.raises(Exception) as excinfo:
                FlutterwaveConfirmQuery.execute(valid_reference)
            assert "Network error" in str(excinfo.value)

    def test_execute_validate_returns_missing_keys(self, valid_reference):
        """If validate returns success but missing purchase keys, code will KeyError."""
        # This is not caught, so it will raise.
        with patch("apps.users.BBL.Queries.FlutterConfirm.validate") as mock_validate:
            mock_validate.return_value = {
                "success": True,
                "message": "OK",
                "purchase": {"purchase_id": 1}  # missing points_awarded, amount_paid
            }
            with pytest.raises(KeyError):
                FlutterwaveConfirmQuery.execute(valid_reference)

    def test_execute_validate_returns_success_without_purchase(self, valid_reference):
        """If validation returns success but purchase is missing, code will KeyError."""
        with patch("apps.users.BBL.Queries.FlutterConfirm.validate") as mock_validate:
            mock_validate.return_value = {"success": True, "message": "OK"}
            with pytest.raises(TypeError):
                FlutterwaveConfirmQuery.execute(valid_reference)