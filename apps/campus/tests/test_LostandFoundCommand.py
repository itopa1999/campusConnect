import pytest
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError   # <-- added

from rest_framework import serializers

from apps.campus.BBL.Commands.lost_and_found import LostandFoundCommand
from apps.campus.models import LostAndFound, Claim
from utils.enums import LostAndFoundStatusEnum
from utils.constant_helper import ConstantHelper

# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def lost_item_data():
    """Valid data for creating a lost item report."""
    return {
        "item_name": "Lost Wallet",
        "description": "Black leather wallet with ID",
        "location": "Main Library",
        "date_found": "2025-01-15",
        "verification1": "What is the color?",
        "answer1": "Black",
        "verification2": "What is inside?",
        "answer2": "Student ID",
        "full_name": "John Doe",
        "email": "john@example.com",
        "department": "Computer Science",
        "phone": "08012345678",
    }

@pytest.fixture
def lost_item(db, lost_item_data):
    data = lost_item_data.copy()
    data.pop('image', None)
    item = LostAndFound.objects.create(**data)
    return item

@pytest.fixture
def claim_data(lost_item):
    return {
        "lost_item_id": lost_item.id,
        "answer1": "Black",
        "answer2": "Student ID",
        "full_name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "08098765432",
    }

@pytest.fixture
def mock_email_task():
    with patch("apps.campus.BBL.Commands.lost_and_found.background_task_send_lost_item_claim_email.delay") as mock1, \
         patch("apps.campus.BBL.Commands.lost_and_found.background_task_send_founder_details_to_claimer_email.delay") as mock2:
        yield mock1, mock2

# ── Test: create_item ────────────────────────────────────────────────

class TestCreateItem:

    def test_create_item_success(self, db, lost_item_data):
        result = LostandFoundCommand.create_item(lost_item_data)
        assert result.is_success is True
        assert result.status_code == 201
        assert "id" in result.data
        item = LostAndFound.objects.get(id=result.data["id"])
        assert item.item_name == "Lost Wallet"
        assert item.email == "john@example.com"

    def test_create_item_missing_fields(self, db, lost_item_data):
        data = lost_item_data.copy()
        data.pop("item_name")
        result = LostandFoundCommand.create_item(data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Missing required fields" in result.message
        assert "item_name" in result.message

    def test_create_item_image_too_large(self, db, lost_item_data):
        image = SimpleUploadedFile("large.jpg", b"x" * (ConstantHelper.IMAGE_SIZE + 1), content_type="image/jpeg")
        data = lost_item_data.copy()
        data["image"] = image
        result = LostandFoundCommand.create_item(data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Image file size must not exceed" in result.message

    def test_create_item_invalid_image_format(self, db, lost_item_data):
        image = SimpleUploadedFile("test.gif", b"GIF87a", content_type="image/gif")
        data = lost_item_data.copy()
        data["image"] = image
        result = LostandFoundCommand.create_item(data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Only JPG, PNG, and WEBP images are allowed" in result.message

    @patch("apps.campus.BBL.Commands.lost_and_found.LostAndFoundSerializer")
    def test_create_item_serializer_validation_error(self, mock_serializer, db, lost_item_data):
        mock_serializer.return_value.is_valid.side_effect = serializers.ValidationError({"item_name": "Invalid"})
        result = LostandFoundCommand.create_item(lost_item_data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Validation failed" in result.message

    def test_create_item_with_empty_image_string(self, db, lost_item_data):
        data = lost_item_data.copy()
        data["image"] = ""
        result = LostandFoundCommand.create_item(data)
        assert result.is_success is True
        item = LostAndFound.objects.get(id=result.data["id"])
        assert item.image == ""

# ── Test: create_claim ───────────────────────────────────────────────

class TestCreateClaim:

    def test_create_claim_success(self, rf, db, lost_item, claim_data, mock_email_task):
        request = rf.post("/fake-url")
        result = LostandFoundCommand.create_claim(request, claim_data)
        assert result.is_success is True
        assert result.status_code == 200
        assert "If your answer is right" in result.message

        claim = Claim.objects.get(lost_item=lost_item, email="jane@example.com")
        assert claim.full_name == "Jane Smith"
        assert claim.answer1 == "Black"
        mock_email_task[0].assert_called_once()

    def test_create_claim_missing_fields(self, rf, db, lost_item):
        data = {"lost_item_id": lost_item.id}
        request = rf.post("/fake-url")
        result = LostandFoundCommand.create_claim(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Missing required fields" in result.message

    def test_create_claim_item_not_found(self, rf, db):
        data = {"lost_item_id": 9999, "answer1": "a", "answer2": "b", "full_name": "X", "email": "x@x.com"}
        request = rf.post("/fake-url")
        result = LostandFoundCommand.create_claim(request, data)
        assert result.is_success is False
        assert result.status_code == 404
        assert "does not exist" in result.message

    def test_create_claim_item_not_open(self, rf, db, lost_item):
        lost_item.status = LostAndFoundStatusEnum.CLAIMED.value
        lost_item.save()
        data = {
            "lost_item_id": lost_item.id,
            "answer1": "Black",
            "answer2": "Student ID",
            "full_name": "Jane",
            "email": "jane@example.com",
        }
        request = rf.post("/fake-url")
        result = LostandFoundCommand.create_claim(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "already been claimed" in result.message

    def test_create_claim_max_limit_reached(self, rf, db, lost_item):
        Claim.objects.create(
            lost_item=lost_item,
            answer1="a", answer2="b",
            full_name="Jane", email="jane@example.com"
        )
        Claim.objects.create(
            lost_item=lost_item,
            answer1="c", answer2="d",
            full_name="Jane", email="jane@example.com"
        )
        data = {
            "lost_item_id": lost_item.id,
            "answer1": "Black",
            "answer2": "Student ID",
            "full_name": "Jane",
            "email": "jane@example.com",
        }
        request = rf.post("/fake-url")
        result = LostandFoundCommand.create_claim(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "maximum number of claims" in result.message

    @patch("apps.campus.BBL.Commands.lost_and_found.ClaimSerializer")
    def test_create_claim_serializer_validation_error(self, mock_serializer, rf, db, lost_item, claim_data):
        mock_serializer.return_value.is_valid.side_effect = serializers.ValidationError({"email": "Invalid"})
        request = rf.post("/fake-url")
        result = LostandFoundCommand.create_claim(request, claim_data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Validation failed" in result.message

    def test_create_claim_email_task_fails(self, rf, db, lost_item, claim_data):
        """If email task fails with OperationalError, command should still succeed."""
        with patch("apps.campus.BBL.Commands.lost_and_found.background_task_send_lost_item_claim_email.delay") as mock_task:
            mock_task.side_effect = OperationalError("Email service down")
            request = rf.post("/fake-url")
            result = LostandFoundCommand.create_claim(request, claim_data)
            assert result.is_success is True
            assert result.status_code == 200
            assert Claim.objects.filter(lost_item=lost_item, email="jane@example.com").exists()

# ── Test: approve_claim ──────────────────────────────────────────────

class TestApproveClaim:

    def test_approve_claim_success(self, rf, db, lost_item, mock_email_task):
        claim = Claim.objects.create(
            lost_item=lost_item,
            answer1="Black",
            answer2="Student ID",
            full_name="Jane",
            email="jane@example.com"
        )
        request = rf.get(f"/fake-url?claim_id={claim.id}&page=2&email={claim.email}")
        result = LostandFoundCommand.approve_claim(request)
        assert result.is_success is True
        assert result.status_code == 200
        assert "Details has been forwarded" in result.message

        lost_item.refresh_from_db()
        assert lost_item.status == LostAndFoundStatusEnum.CLAIMED.value
        assert lost_item.claimed_by == "Jane"
        mock_email_task[1].assert_called_once()

    def test_approve_claim_missing_params(self, rf, db):
        result = LostandFoundCommand.approve_claim(rf.get("/fake-url"))
        assert result.is_success is False
        assert result.status_code == 400
        assert "missing claim_id or email" in result.message

    def test_approve_claim_not_found(self, rf, db):
        result = LostandFoundCommand.approve_claim(rf.get("/fake-url?claim_id=9999&page=2&email=x@x,com"))
        assert result.is_success is False
        assert result.status_code == 400
        assert "Claim not found" in result.message

    def test_approve_claim_item_already_claimed(self, rf, db, lost_item):
        lost_item.status = LostAndFoundStatusEnum.CLAIMED.value
        lost_item.save()
        claim = Claim.objects.create(
            lost_item=lost_item,
            answer1="a", answer2="b",
            full_name="Jane", email="jane@example.com"
        )
        result = LostandFoundCommand.approve_claim(rf.get(f"/fake-url?claim_id={claim.id}&page=2&email={claim.email}"))
        assert result.is_success is False
        assert result.status_code == 400
        assert "already been claimed" in result.message

    def test_approve_claim_email_task_fails(self, rf, db, lost_item):
        claim = Claim.objects.create(
            lost_item=lost_item,
            answer1="a", answer2="b",
            full_name="Jane", email="jane@example.com"
        )
        with patch("apps.campus.BBL.Commands.lost_and_found.background_task_send_founder_details_to_claimer_email.delay") as mock_task:
            mock_task.side_effect = OperationalError("Email error")
            result = LostandFoundCommand.approve_claim(rf.get(f"/fake-url?claim_id={claim.id}&page=2&email={claim.email}"))
            assert result.is_success is True
            assert result.status_code == 200
            lost_item.refresh_from_db()
            assert lost_item.status == LostAndFoundStatusEnum.CLAIMED.value