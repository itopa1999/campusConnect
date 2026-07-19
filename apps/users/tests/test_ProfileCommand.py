import pytest
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.utils import timezone

from apps.users.BBL.Commands.profile import ProfileCommand
from apps.users.models import User
from utils.constant_helper import ConstantHelper


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
        department="Computer Science",
        faculty="Science",
        level=3,
        matric_number="MAT/12345",
        notification=True,
        visibility=True,
    )
    return user

@pytest.fixture
def another_user(db):
    return User.objects.create_user(
        email="another@example.com",
        password="testpass",
        phone="08087654321",
        matric_number="MAT/67890",
    )

@pytest.fixture
def mock_image_file():
    return SimpleUploadedFile("test.jpg", b"fake_jpg_content", content_type="image/jpeg")

@pytest.fixture
def mock_large_image():
    return SimpleUploadedFile("large.jpg", b"x" * (ConstantHelper.IMAGE_SIZE + 1), content_type="image/jpeg")

@pytest.fixture
def mock_invalid_extension():
    return SimpleUploadedFile("test.gif", b"GIF87a", content_type="image/gif")


# ── Tests: update_profile ────────────────────────────────────────────

class TestProfileCommandUpdateProfile:

    def test_update_profile_success(self, db, request_factory, test_user):
        """Happy path: update multiple fields."""
        request = request_factory.post("/")
        data = {
            "phone": "08099999999",
            "department": "Physics",
            "faculty": "Natural Sciences",
            "level": 4,
            "matric_number": "MAT/54321",
            "notification": False,
            "visibility": False,
            "full_name": "New Full Name",
        }
        # Patch the edit restriction check so it passes
        with patch("apps.users.BBL.Commands.profile.ConstantHelper.USER_EDIT_DAY", 0):
            result = ProfileCommand.update_profile(request, test_user, data)
        assert result.is_success is True
        assert result.status_code == 200
        test_user.refresh_from_db()
        assert test_user.phone == "08099999999"
        assert test_user.department == "Physics"
        assert test_user.faculty == "Natural Sciences"
        assert test_user.level == 4
        assert test_user.matric_number == "MAT/54321"
        assert test_user.notification is False
        assert test_user.visibility is False
        assert test_user.first_name == "New"
        assert test_user.last_name == "Full Name"

    def test_update_profile_level_out_of_range(self, db, request_factory, test_user):
        """Level outside 1-7 should fail."""
        request = request_factory.post("/")
        data = {"level": 8}
        with patch("apps.users.BBL.Commands.profile.ConstantHelper.USER_EDIT_DAY", 0):
            result = ProfileCommand.update_profile(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Invalid level" in result.message

    def test_update_profile_level_too_low(self, db, request_factory, test_user):
        """Level below 1 should fail."""
        request = request_factory.post("/")
        data = {"level": 0}
        with patch("apps.users.BBL.Commands.profile.ConstantHelper.USER_EDIT_DAY", 0):
            result = ProfileCommand.update_profile(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Invalid level" in result.message

    def test_update_profile_level_success(self, db, request_factory, test_user):
        """Valid level should succeed."""
        request = request_factory.post("/")
        data = {"level": 5}
        with patch("apps.users.BBL.Commands.profile.ConstantHelper.USER_EDIT_DAY", 0):
            result = ProfileCommand.update_profile(request, test_user, data)
        assert result.is_success is True
        assert result.status_code == 200
        test_user.refresh_from_db()
        assert test_user.level == 5

    def test_update_profile_edit_restriction(self, db, request_factory, test_user):
        """Editing too soon should fail."""
        test_user.modified_at = timezone.now()
        test_user.save()
        request = request_factory.post("/")
        data = {"phone": "08099999999"}
        with patch("apps.users.BBL.Commands.profile.ConstantHelper.USER_EDIT_DAY", 7):
            result = ProfileCommand.update_profile(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "You can only edit once every" in result.message

    def test_update_profile_duplicate_phone(self, db, request_factory, test_user, another_user):
        """Duplicate phone should fail."""
        request = request_factory.post("/")
        data = {"phone": another_user.phone}
        with patch("apps.users.BBL.Commands.profile.ConstantHelper.USER_EDIT_DAY", 0):
            result = ProfileCommand.update_profile(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Phone number already in use" in result.message

    def test_update_profile_duplicate_matric(self, db, request_factory, test_user, another_user):
        """Duplicate matric number should fail."""
        request = request_factory.post("/")
        data = {"matric_number": another_user.matric_number}
        with patch("apps.users.BBL.Commands.profile.ConstantHelper.USER_EDIT_DAY", 0):
            result = ProfileCommand.update_profile(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Matric number already in use" in result.message

    def test_update_profile_full_name_split(self, db, request_factory, test_user):
        """Full name should be split into first and last name."""
        request = request_factory.post("/")
        data = {"full_name": "John"}
        with patch("apps.users.BBL.Commands.profile.ConstantHelper.USER_EDIT_DAY", 0):
            result = ProfileCommand.update_profile(request, test_user, data)
        assert result.is_success is True
        test_user.refresh_from_db()
        assert test_user.first_name == "John"
        assert test_user.last_name == ""

        # Test with three-part name
        data = {"full_name": "John Michael Doe"}
        with patch("apps.users.BBL.Commands.profile.ConstantHelper.USER_EDIT_DAY", 0):
            result = ProfileCommand.update_profile(request, test_user, data)
        assert result.is_success is True
        test_user.refresh_from_db()
        assert test_user.first_name == "John"
        assert test_user.last_name == "Michael Doe"

    def test_update_profile_boolean_fields(self, db, request_factory, test_user):
        """Test updating boolean fields."""
        request = request_factory.post("/")
        data = {"notification": False, "visibility": False}
        with patch("apps.users.BBL.Commands.profile.ConstantHelper.USER_EDIT_DAY", 0):
            result = ProfileCommand.update_profile(request, test_user, data)
        assert result.is_success is True
        test_user.refresh_from_db()
        assert test_user.notification is False
        assert test_user.visibility is False

    def test_update_profile_exception(self, db, request_factory, test_user):
        """Catch unexpected exception and return 500."""
        request = request_factory.post("/")
        data = {"phone": "08099999999"}
        with patch("apps.users.BBL.Commands.profile.ConstantHelper.USER_EDIT_DAY", 0), \
             patch("apps.users.BBL.Commands.profile.User.objects.filter", side_effect=Exception("DB error")):
            result = ProfileCommand.update_profile(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 500
        assert "An unexpected error occurred" in result.message


# ── Tests: update_profile_picture ────────────────────────────────────

class TestProfileCommandUpdateProfilePicture:

    def test_update_profile_picture_success(self, db, request_factory, test_user, mock_image_file):
        """Happy path: upload a valid profile picture."""
        request = request_factory.post("/")
        data = {"profile_picture": mock_image_file}
        with patch("apps.users.BBL.Commands.profile.Image.open") as mock_image_open:
            mock_image = MagicMock()
            mock_image.verify.return_value = None
            mock_image_open.return_value = mock_image
            result = ProfileCommand.update_profile_picture(request, test_user, data)
        assert result.is_success is True
        assert result.status_code == 200
        test_user.refresh_from_db()
        assert test_user.profile_picture is not None

    def test_update_profile_picture_no_file(self, db, request_factory, test_user):
        """Missing file should return 400."""
        request = request_factory.post("/")
        data = {}  # no profile_picture
        result = ProfileCommand.update_profile_picture(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "No image file provided" in result.message

    def test_update_profile_picture_too_large(self, db, request_factory, test_user, mock_large_image):
        """File too large should return 400."""
        request = request_factory.post("/")
        data = {"profile_picture": mock_large_image}
        result = ProfileCommand.update_profile_picture(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Image file size must not exceed" in result.message

    def test_update_profile_picture_invalid_extension(self, db, request_factory, test_user, mock_invalid_extension):
        """Invalid file extension should return 400."""
        request = request_factory.post("/")
        data = {"profile_picture": mock_invalid_extension}
        result = ProfileCommand.update_profile_picture(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Only JPG, PNG, and WEBP images are allowed" in result.message

    def test_update_profile_picture_invalid_image(self, db, request_factory, test_user, mock_image_file):
        """Image validation fails should return 400."""
        request = request_factory.post("/")
        data = {"profile_picture": mock_image_file}
        with patch("apps.users.BBL.Commands.profile.Image.open") as mock_image_open:
            mock_image_open.side_effect = Exception("Invalid image")
            result = ProfileCommand.update_profile_picture(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "not a valid image" in result.message

    def test_update_profile_picture_delete_old_picture(self, db, request_factory, test_user, mock_image_file):
        """Old profile picture should be deleted when new one is uploaded."""
        # Set an existing picture
        test_user.profile_picture = SimpleUploadedFile("old.jpg", b"old_content")
        test_user.save()
        request = request_factory.post("/")
        data = {"profile_picture": mock_image_file}
        with patch("apps.users.BBL.Commands.profile.default_storage") as mock_storage, \
             patch("apps.users.BBL.Commands.profile.Image.open") as mock_image_open:
            mock_image = MagicMock()
            mock_image.verify.return_value = None
            mock_image_open.return_value = mock_image
            result = ProfileCommand.update_profile_picture(request, test_user, data)
        assert result.is_success is True
        mock_storage.delete.assert_called_once()

    def test_update_profile_picture_delete_old_fails(self, db, request_factory, test_user, mock_image_file):
        """Even if old picture deletion fails, upload should still succeed."""
        test_user.profile_picture = SimpleUploadedFile("old.jpg", b"old_content")
        test_user.save()
        request = request_factory.post("/")
        data = {"profile_picture": mock_image_file}
        with patch("apps.users.BBL.Commands.profile.default_storage") as mock_storage, \
             patch("apps.users.BBL.Commands.profile.Image.open") as mock_image_open:
            mock_image = MagicMock()
            mock_image.verify.return_value = None
            mock_image_open.return_value = mock_image
            mock_storage.delete.side_effect = Exception("Delete error")
            result = ProfileCommand.update_profile_picture(request, test_user, data)
        assert result.is_success is True
        # The code logs the failure but still succeeds

    def test_update_profile_picture_exception(self, db, request_factory, test_user, mock_image_file):
        """Catch unexpected exception and return 500."""
        request = request_factory.post("/")
        data = {"profile_picture": mock_image_file}
        with patch("apps.users.BBL.Commands.profile.Image.open") as mock_image_open, \
             patch("apps.users.BBL.Commands.profile.transaction.atomic", side_effect=Exception("DB error")):
            mock_image = MagicMock()
            mock_image.verify.return_value = None
            mock_image_open.return_value = mock_image
            result = ProfileCommand.update_profile_picture(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 500
        assert "An unexpected error occurred" in result.message


# ── Tests: upload_student_id ─────────────────────────────────────────

class TestProfileCommandUploadStudentId:

    def test_upload_student_id_success(self, db, request_factory, test_user, mock_image_file):
        """Happy path: upload a valid student ID (if not already verified)."""
        test_user.student_id_verified = False
        test_user.save()
        request = request_factory.post("/")
        data = {"student_id": mock_image_file}
        with patch("apps.users.BBL.Commands.profile.Image.open") as mock_image_open:
            mock_image = MagicMock()
            mock_image.verify.return_value = None
            mock_image_open.return_value = mock_image
            result = ProfileCommand.upload_student_id(request, test_user, data)
        assert result.is_success is True
        assert result.status_code == 200
        test_user.refresh_from_db()
        assert test_user.student_id_photo is not None

    def test_upload_student_id_already_verified(self, db, request_factory, test_user):
        """If already verified, return 400."""
        test_user.student_id_verified = True
        test_user.save()
        request = request_factory.post("/")
        data = {"student_id": SimpleUploadedFile("test.jpg", b"content")}
        result = ProfileCommand.upload_student_id(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Student ID already verified" in result.message

    def test_upload_student_id_no_file(self, db, request_factory, test_user):
        """Missing file should return 400."""
        test_user.student_id_verified = False
        test_user.save()
        request = request_factory.post("/")
        data = {}  # no student_id
        result = ProfileCommand.upload_student_id(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "No image file provided" in result.message

    def test_upload_student_id_too_large(self, db, request_factory, test_user, mock_large_image):
        """File too large should return 400."""
        test_user.student_id_verified = False
        test_user.save()
        request = request_factory.post("/")
        data = {"student_id": mock_large_image}
        result = ProfileCommand.upload_student_id(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Image file size must not exceed" in result.message

    def test_upload_student_id_invalid_extension(self, db, request_factory, test_user, mock_invalid_extension):
        """Invalid file extension should return 400."""
        test_user.student_id_verified = False
        test_user.save()
        request = request_factory.post("/")
        data = {"student_id": mock_invalid_extension}
        result = ProfileCommand.upload_student_id(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Only JPG, PNG, and WEBP images are allowed" in result.message

    def test_upload_student_id_invalid_image(self, db, request_factory, test_user, mock_image_file):
        """Image validation fails should return 400."""
        test_user.student_id_verified = False
        test_user.save()
        request = request_factory.post("/")
        data = {"student_id": mock_image_file}
        with patch("apps.users.BBL.Commands.profile.Image.open") as mock_image_open:
            mock_image_open.side_effect = Exception("Invalid image")
            result = ProfileCommand.upload_student_id(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "not a valid image" in result.message

    def test_upload_student_id_delete_old_picture(self, db, request_factory, test_user, mock_image_file):
        """Old student ID photo should be deleted."""
        test_user.student_id_verified = False
        test_user.student_id_photo = SimpleUploadedFile("old_id.jpg", b"old_content")
        test_user.save()
        request = request_factory.post("/")
        data = {"student_id": mock_image_file}
        with patch("apps.users.BBL.Commands.profile.default_storage") as mock_storage, \
             patch("apps.users.BBL.Commands.profile.Image.open") as mock_image_open:
            mock_image = MagicMock()
            mock_image.verify.return_value = None
            mock_image_open.return_value = mock_image
            result = ProfileCommand.upload_student_id(request, test_user, data)
        assert result.is_success is True
        mock_storage.delete.assert_called_once()

    def test_upload_student_id_exception(self, db, request_factory, test_user, mock_image_file):
        """Catch unexpected exception and return 500."""
        test_user.student_id_verified = False
        test_user.save()
        request = request_factory.post("/")
        data = {"student_id": mock_image_file}
        with patch("apps.users.BBL.Commands.profile.Image.open") as mock_image_open, \
             patch("apps.users.BBL.Commands.profile.transaction.atomic", side_effect=Exception("DB error")):
            mock_image = MagicMock()
            mock_image.verify.return_value = None
            mock_image_open.return_value = mock_image
            result = ProfileCommand.upload_student_id(request, test_user, data)
        assert result.is_success is False
        assert result.status_code == 500
        assert "An unexpected error occurred" in result.message
