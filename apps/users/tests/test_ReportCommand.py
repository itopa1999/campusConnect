import pytest
from unittest.mock import patch
from django.test import RequestFactory

from apps.users.BBL.Commands.report_command import ReportCommand
from apps.users.models import ContactReport
from utils.enums import IssueTypeEnum


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def request_factory():
    return RequestFactory()

@pytest.fixture
def valid_report_data():
    return {
        "reporter_name": "Jane Doe",
        "reporter_email": "jane@example.com",
        "issue_type": IssueTypeEnum.REPORT_LISTING.value,
        "listing_identifier": "Listing 123",
        "reported_user_email": "",
        "message": "This listing is suspicious.",
    }

@pytest.fixture
def mock_email_task():
    with patch("apps.users.BBL.Commands.report_command.background_task_send_report_recieved_email.delay") as mock:
        yield mock


# ── Tests ─────────────────────────────────────────────────────────────

class TestReportCommandAdd:

    def test_add_success_listing_report(self, db, request_factory, valid_report_data, mock_email_task):
        """Happy path: successful report of a listing."""
        request = request_factory.post("/")
        result = ReportCommand.Add(request, valid_report_data)
        assert result.is_success is True
        assert result.status_code == 201
        assert "report_id" in result.data
        assert result.data["issue_type"] == IssueTypeEnum.REPORT_LISTING.value

        report = ContactReport.objects.get(id=result.data["report_id"])
        assert report.reporter_name == "Jane Doe"
        assert report.reporter_email == "jane@example.com"
        assert report.issue_type == IssueTypeEnum.REPORT_LISTING.value
        assert report.listing_identifier == "Listing 123"
        assert report.reported_user_email == ""
        assert report.message == "This listing is suspicious."
        assert report.is_reviewed is False

        mock_email_task.assert_called_once_with(
            "jane@example.com", "Jane Doe", IssueTypeEnum.REPORT_LISTING.value
        )

    def test_add_success_user_report(self, db, request_factory, valid_report_data, mock_email_task):
        """Happy path: successful report of a user."""
        data = valid_report_data.copy()
        data["issue_type"] = IssueTypeEnum.REPORT_USER.value
        data["reported_user_email"] = "reported@example.com"
        data.pop("listing_identifier", None)  # not needed for user report

        request = request_factory.post("/")
        result = ReportCommand.Add(request, data)
        assert result.is_success is True
        assert result.status_code == 201

        report = ContactReport.objects.get(id=result.data["report_id"])
        assert report.issue_type == IssueTypeEnum.REPORT_USER.value
        assert report.reported_user_email == "reported@example.com"
        # listing_identifier may be empty string (depends on model default)
        assert report.listing_identifier == ""

        mock_email_task.assert_called_once_with(
            "jane@example.com", "Jane Doe", IssueTypeEnum.REPORT_USER.value
        )

    def test_add_missing_reporter_name(self, db, request_factory):
        """Missing reporter_name should return 400."""
        data = {
            "reporter_email": "jane@example.com",
            "issue_type": IssueTypeEnum.REPORT_LISTING.value,
            "listing_identifier": "Listing 123",
            "message": "msg"
        }
        request = request_factory.post("/")
        result = ReportCommand.Add(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Reporter name is required" in result.message

    def test_add_missing_reporter_email(self, db, request_factory):
        """Missing reporter_email should return 400."""
        data = {
            "reporter_name": "Jane",
            "issue_type": IssueTypeEnum.REPORT_LISTING.value,
            "listing_identifier": "Listing 123",
            "message": "msg"
        }
        request = request_factory.post("/")
        result = ReportCommand.Add(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Reporter email is required" in result.message

    def test_add_invalid_issue_type(self, db, request_factory):
        """Invalid issue_type should return 400."""
        data = {
            "reporter_name": "Jane",
            "reporter_email": "jane@example.com",
            "issue_type": "invalid",
            "listing_identifier": "Listing 123",
            "message": "msg"
        }
        request = request_factory.post("/")
        result = ReportCommand.Add(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Invalid or missing issue type" in result.message

    def test_add_missing_listing_identifier_for_listing_report(self, db, request_factory):
        """Listing report requires listing_identifier."""
        data = {
            "reporter_name": "Jane",
            "reporter_email": "jane@example.com",
            "issue_type": IssueTypeEnum.REPORT_LISTING.value,
            "message": "msg"
        }
        request = request_factory.post("/")
        result = ReportCommand.Add(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Listing URL or title is required" in result.message

    def test_add_missing_reported_user_email_for_user_report(self, db, request_factory):
        """User report requires reported_user_email."""
        data = {
            "reporter_name": "Jane",
            "reporter_email": "jane@example.com",
            "issue_type": IssueTypeEnum.REPORT_USER.value,
            "message": "msg"
        }
        request = request_factory.post("/")
        result = ReportCommand.Add(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Email of the reported user is required" in result.message

    def test_add_empty_message(self, db, request_factory):
        """Empty message should return 400."""
        data = {
            "reporter_name": "Jane",
            "reporter_email": "jane@example.com",
            "issue_type": IssueTypeEnum.REPORT_LISTING.value,
            "listing_identifier": "Listing 123",
            "message": ""
        }
        request = request_factory.post("/")
        result = ReportCommand.Add(request, data)
        assert result.is_success is False
        assert result.status_code == 400
        assert "Message cannot be empty" in result.message

    def test_add_trim_whitespace(self, db, request_factory, mock_email_task):
        """Fields with leading/trailing whitespace should be stripped."""
        data = {
            "reporter_name": "  Jane Doe  ",
            "reporter_email": "  jane@example.com  ",
            "issue_type": IssueTypeEnum.REPORT_LISTING.value,
            "listing_identifier": "  Listing 123  ",
            "reported_user_email": "",
            "message": "  This is a report.  "
        }
        request = request_factory.post("/")
        result = ReportCommand.Add(request, data)
        assert result.is_success is True

        report = ContactReport.objects.get(id=result.data["report_id"])
        assert report.reporter_name == "Jane Doe"
        assert report.reporter_email == "jane@example.com"
        assert report.listing_identifier == "Listing 123"
        assert report.message == "This is a report."

    def test_add_email_task_failure(self, db, request_factory, valid_report_data):
        """If email task fails, report should still be created and success returned."""
        with patch("apps.users.BBL.Commands.report_command.background_task_send_report_recieved_email.delay") as mock_task:
            mock_task.side_effect = Exception("Email service down")
            request = request_factory.post("/")
            result = ReportCommand.Add(request, valid_report_data)

        assert result.is_success is True
        assert result.status_code == 201
        # Report should exist
        assert ContactReport.objects.filter(reporter_email="jane@example.com").exists()
        # Email task was called but failed – the command logs the error and continues

    def test_add_general_exception(self, db, request_factory, valid_report_data):
        """Unexpected database error should return 500."""
        with patch("apps.users.BBL.Commands.report_command.ContactReport.objects.create", side_effect=Exception("DB error")):
            request = request_factory.post("/")
            result = ReportCommand.Add(request, valid_report_data)

        assert result.is_success is False
        assert result.status_code == 500
        assert "Unable to submit report" in result.message