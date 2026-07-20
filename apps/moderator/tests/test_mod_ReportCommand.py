from apps.moderator.BBL.Commands.report import ReportCommand
import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.db import IntegrityError
from django.utils import timezone
from apps.users.models import ContactReport
from apps.moderator.models import ModeratorAction
from utils.enums import ReportStatusEnum, ContentTypeEnum, ModeratorActionTypeEnum

User = get_user_model()


# ---------- Fixtures ----------
@pytest.fixture
def moderator(db):
    return User.objects.create_user(
        email='moderator@example.com',
        password='testpass123',
        first_name='Mod',
        last_name='erator',
        is_staff=True
    )


@pytest.fixture
def assignee(db):
    return User.objects.create_user(
        email='assignee@example.com',
        password='testpass123',
        first_name='Assignee',
        is_active=True,
        is_deleted=False
    )


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def moderator_request(request_factory, moderator):
    req = request_factory.get('/')
    req.user = moderator
    req.META = {'REMOTE_ADDR': '127.0.0.1'}
    return req


@pytest.fixture
def pending_report(db):
    return ContactReport.objects.create(
        reporter_email='reporter@example.com',
        issue_type='spam',
        message='Spam content',
        status=ReportStatusEnum.PENDING.value,
        is_deleted=False
    )


@pytest.fixture
def resolved_report(db, moderator):
    return ContactReport.objects.create(
        reporter_email='reporter@example.com',
        issue_type='harassment',
        message='Harassment report',
        status=ReportStatusEnum.RESOLVED.value,
        resolved_by=moderator,
        resolved_at=timezone.now(),
        resolution_notes='Resolved',
        is_deleted=False
    )


@pytest.fixture
def escalated_report(db):
    return ContactReport.objects.create(
        reporter_email='reporter@example.com',
        issue_type='other',
        message='Escalated issue',
        status=ReportStatusEnum.ESCALATED.value,
        escalated_to_admin=True,
        escalated_at=timezone.now(),
        escalated_note='Escalated',
        is_deleted=False
    )


@pytest.fixture
def in_review_report(db, assignee):
    return ContactReport.objects.create(
        reporter_email='reporter@example.com',
        issue_type='fraud',
        message='Fraud report',
        status=ReportStatusEnum.IN_REVIEW.value,
        assigned_to=assignee,
        is_deleted=False
    )


@pytest.fixture
def deleted_report(db):
    return ContactReport.objects.create(
        reporter_email='deleted@example.com',
        issue_type='spam',
        message='Deleted report',
        status=ReportStatusEnum.PENDING.value,
        is_deleted=True
    )


# ---------- Test class ----------
@pytest.mark.django_db
class TestReportCommand:

    # ---------- resolve_report ----------
    def test_resolve_report_success(self, moderator_request, pending_report):
        data = {'resolution_notes': 'Fixed the issue'}
        result = ReportCommand.resolve_report(moderator_request, pending_report.id, data)
        assert result.status_code == 200
        assert result.message == "Report resolved successfully"
        assert result.data['status'] == ReportStatusEnum.RESOLVED.value

        pending_report.refresh_from_db()
        assert pending_report.status == ReportStatusEnum.RESOLVED.value
        assert pending_report.resolved_by == moderator_request.user
        assert pending_report.resolved_at is not None
        assert pending_report.resolution_notes == 'Fixed the issue'

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.REPORT.value,
            content_id=pending_report.id,
            action_type=ModeratorActionTypeEnum.RESOLVE_REPORT.value
        ).first()
        assert action is not None
        assert action.reason == 'Fixed the issue'
        assert action.metadata['old_status'] == ReportStatusEnum.PENDING.value
        assert action.metadata['new_status'] == ReportStatusEnum.RESOLVED.value

    def test_resolve_report_missing_notes(self, moderator_request, pending_report):
        data = {}
        result = ReportCommand.resolve_report(moderator_request, pending_report.id, data)
        assert result.status_code == 400
        assert result.message == "Resolution notes are required to resolve a report"
        pending_report.refresh_from_db()
        assert pending_report.status == ReportStatusEnum.PENDING.value

    def test_resolve_report_not_found(self, moderator_request):
        data = {'resolution_notes': 'test'}
        result = ReportCommand.resolve_report(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "Report not found"

    def test_resolve_report_already_resolved(self, moderator_request, resolved_report):
        data = {'resolution_notes': 'Again'}
        result = ReportCommand.resolve_report(moderator_request, resolved_report.id, data)
        assert result.status_code == 400
        assert result.message == "Report already resolved"
        resolved_report.refresh_from_db()
        assert resolved_report.status == ReportStatusEnum.RESOLVED.value

    def test_resolve_report_deleted(self, moderator_request, deleted_report):
        data = {'resolution_notes': 'test'}
        result = ReportCommand.resolve_report(moderator_request, deleted_report.id, data)
        assert result.status_code == 404
        assert result.message == "Report not found"

    # ---------- escalate_report ----------
    def test_escalate_report_success(self, moderator_request, pending_report):
        data = {'escalated_note': 'Needs admin attention'}
        result = ReportCommand.escalate_report(moderator_request, pending_report.id, data)
        assert result.status_code == 200
        assert result.message == "Report escalated to admin"
        assert result.data['escalated_to_admin'] is True

        pending_report.refresh_from_db()
        assert pending_report.escalated_to_admin is True
        assert pending_report.escalated_at is not None
        assert pending_report.escalated_note == 'Needs admin attention'
        assert pending_report.status == ReportStatusEnum.ESCALATED.value

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.REPORT.value,
            content_id=pending_report.id,
            action_type=ModeratorActionTypeEnum.ESCALATE.value
        ).first()
        assert action is not None
        assert action.reason == 'Needs admin attention'
        assert action.metadata['old_status'] == ReportStatusEnum.PENDING.value
        assert action.metadata['new_status'] == ReportStatusEnum.ESCALATED.value

    def test_escalate_report_missing_note(self, moderator_request, pending_report):
        data = {}
        result = ReportCommand.escalate_report(moderator_request, pending_report.id, data)
        assert result.status_code == 400
        assert result.message == "Escalation note is required to escalate a report"
        pending_report.refresh_from_db()
        assert pending_report.escalated_to_admin is False

    def test_escalate_report_not_found(self, moderator_request):
        data = {'escalated_note': 'test'}
        result = ReportCommand.escalate_report(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "Report not found"

    def test_escalate_report_already_escalated(self, moderator_request, escalated_report):
        data = {'escalated_note': 'Again'}
        result = ReportCommand.escalate_report(moderator_request, escalated_report.id, data)
        assert result.status_code == 400
        assert result.message == "Report already escalated"
        escalated_report.refresh_from_db()
        assert escalated_report.escalated_to_admin is True

    def test_escalate_report_deleted(self, moderator_request, deleted_report):
        data = {'escalated_note': 'test'}
        result = ReportCommand.escalate_report(moderator_request, deleted_report.id, data)
        assert result.status_code == 404
        assert result.message == "Report not found"

    # ---------- assign_report ----------
    def test_assign_report_success(self, moderator_request, pending_report, assignee):
        data = {'assigned_to': assignee.id}
        result = ReportCommand.assign_report(moderator_request, pending_report.id, data)
        assert result.status_code == 200
        assert f"assigned to {assignee.get_full_name() or assignee.email}" in result.message
        assert result.data['assigned_to'] == assignee.id

        pending_report.refresh_from_db()
        assert pending_report.assigned_to == assignee
        assert pending_report.status == ReportStatusEnum.IN_REVIEW.value

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.REPORT.value,
            content_id=pending_report.id,
            action_type=ModeratorActionTypeEnum.ASSIGN.value  # ensure this enum exists
        ).first()
        assert action is not None
        assert action.reason == f"Assigned to {assignee.email}"
        assert action.metadata['new_assigned_to'] == assignee.email

    def test_assign_report_missing_assigned_to(self, moderator_request, pending_report):
        data = {}
        result = ReportCommand.assign_report(moderator_request, pending_report.id, data)
        assert result.status_code == 400
        assert result.message == "Assigned moderator ID is required"
        pending_report.refresh_from_db()
        assert pending_report.assigned_to is None

    def test_assign_report_invalid_user(self, moderator_request, pending_report):
        data = {'assigned_to': 999}
        result = ReportCommand.assign_report(moderator_request, pending_report.id, data)
        assert result.status_code == 404
        assert result.message == "User not found or inactive"
        pending_report.refresh_from_db()
        assert pending_report.assigned_to is None

    def test_assign_report_inactive_user(self, moderator_request, pending_report):
        inactive_user = User.objects.create_user(
            email='inactive@example.com',
            password='test',
            is_active=False
        )
        data = {'assigned_to': inactive_user.id}
        result = ReportCommand.assign_report(moderator_request, pending_report.id, data)
        assert result.status_code == 404
        assert result.message == "User not found or inactive"

    def test_assign_report_not_found(self, moderator_request, assignee):
        data = {'assigned_to': assignee.id}
        result = ReportCommand.assign_report(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "Report not found"

    def test_assign_report_deleted(self, moderator_request, deleted_report, assignee):
        data = {'assigned_to': assignee.id}
        result = ReportCommand.assign_report(moderator_request, deleted_report.id, data)
        assert result.status_code == 404
        assert result.message == "Report not found"

    # ---------- Edge case: assign already resolved report (possible bug) ----------
    def test_assign_report_already_resolved(self, moderator_request, resolved_report, assignee):
        """
        Potential bug: Command does NOT check if report is resolved.
        It will allow assignment even though it's resolved, which might be unintended.
        We'll test this to reveal the behavior.
        """
        data = {'assigned_to': assignee.id}
        result = ReportCommand.assign_report(moderator_request, resolved_report.id, data)
        # Currently, it will succeed because no status check is performed.
        # If the design should prevent assignment of resolved reports, this is a bug.
        assert result.status_code == 200
        resolved_report.refresh_from_db()
        assert resolved_report.assigned_to == assignee
        assert resolved_report.status == ReportStatusEnum.IN_REVIEW.value  # changed from RESOLVED
        # This might not be desired; you may want to add a check.

    # ---------- toggle_reopen_report ----------
    def test_reopen_report_success(self, moderator_request, resolved_report):
        data = {'reason': 'Need more investigation'}
        result = ReportCommand.toggle_reopen_report(moderator_request, resolved_report.id, data)
        assert result.status_code == 200
        assert result.message == "Report reopened for review"
        assert result.data['status'] == ReportStatusEnum.IN_REVIEW.value

        resolved_report.refresh_from_db()
        assert resolved_report.status == ReportStatusEnum.IN_REVIEW.value
        assert resolved_report.resolved_by is None
        assert resolved_report.resolved_at is None
        assert resolved_report.resolution_notes == ''

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.REPORT.value,
            content_id=resolved_report.id,
            action_type='reopen'  # as currently hardcoded
        ).first()
        assert action is not None
        assert action.reason == 'Need more investigation'
        assert action.metadata['old_status'] == ReportStatusEnum.RESOLVED.value
        assert action.metadata['new_status'] == ReportStatusEnum.IN_REVIEW.value

    def test_reopen_report_missing_reason(self, moderator_request, resolved_report):
        data = {}
        result = ReportCommand.toggle_reopen_report(moderator_request, resolved_report.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required to reopen a report"
        resolved_report.refresh_from_db()
        assert resolved_report.status == ReportStatusEnum.RESOLVED.value

    def test_reopen_report_not_found(self, moderator_request):
        data = {'reason': 'test'}
        result = ReportCommand.toggle_reopen_report(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "Report not found"

    def test_reopen_report_not_resolved(self, moderator_request, pending_report):
        data = {'reason': 'test'}
        result = ReportCommand.toggle_reopen_report(moderator_request, pending_report.id, data)
        assert result.status_code == 400
        assert result.message == "Only resolved reports can be reopened"
        pending_report.refresh_from_db()
        assert pending_report.status == ReportStatusEnum.PENDING.value

    def test_reopen_report_deleted(self, moderator_request, deleted_report):
        data = {'reason': 'test'}
        result = ReportCommand.toggle_reopen_report(moderator_request, deleted_report.id, data)
        assert result.status_code == 404
        assert result.message == "Report not found"

    # ---------- Atomicity Tests ----------
    def test_resolve_report_atomicity(self, moderator_request, pending_report, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'resolution_notes': 'test'}
            with pytest.raises(IntegrityError):
                ReportCommand.resolve_report(moderator_request, pending_report.id, data)
            pending_report.refresh_from_db()
            assert pending_report.status == ReportStatusEnum.PENDING.value
            assert pending_report.resolved_by is None

    def test_escalate_report_atomicity(self, moderator_request, pending_report, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'escalated_note': 'test'}
            with pytest.raises(IntegrityError):
                ReportCommand.escalate_report(moderator_request, pending_report.id, data)
            pending_report.refresh_from_db()
            assert pending_report.escalated_to_admin is False
            assert pending_report.status == ReportStatusEnum.PENDING.value

    def test_assign_report_atomicity(self, moderator_request, pending_report, assignee, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'assigned_to': assignee.id}
            with pytest.raises(IntegrityError):
                ReportCommand.assign_report(moderator_request, pending_report.id, data)
            pending_report.refresh_from_db()
            assert pending_report.assigned_to is None
            assert pending_report.status == ReportStatusEnum.PENDING.value

    def test_reopen_report_atomicity(self, moderator_request, resolved_report, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test'}
            with pytest.raises(IntegrityError):
                ReportCommand.toggle_reopen_report(moderator_request, resolved_report.id, data)
            resolved_report.refresh_from_db()
            assert resolved_report.status == ReportStatusEnum.RESOLVED.value
            assert resolved_report.resolved_by is not None