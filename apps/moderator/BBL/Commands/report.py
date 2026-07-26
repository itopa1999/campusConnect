from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.users.models import ContactReport
from apps.moderator.models import ModeratorAction
from utils.base_result import BaseResultWithData
from utils.enums import ReportStatusEnum, ContentTypeEnum, ModeratorActionTypeEnum
from utils.log_helpers import OperationLogger

User = get_user_model()


class ReportCommand:
    @staticmethod
    @transaction.atomic
    def resolve_report(request, report_id, validated_data) -> BaseResultWithData:
        """
        Mark a report as resolved.
        """
        op = OperationLogger("ModeratorReportCommand.resolve_report", report_id=report_id)
        op.start()

        resolution_notes = validated_data.get('resolution_notes')
        if not resolution_notes:
            return BaseResultWithData(
                message="Resolution notes are required to resolve a report",
                data=None,
                status_code=400
            )

        try:
            report = ContactReport.objects.select_for_update().get(
                id=report_id,
                is_deleted=False
            )
        except ContactReport.DoesNotExist:
            op.fail("Report not found")
            return BaseResultWithData(
                message="Report not found",
                data=None,
                status_code=404
            )

        if report.status == ReportStatusEnum.RESOLVED.value:
            op.fail("Report already resolved")
            return BaseResultWithData(
                message="Report already resolved",
                data=None,
                status_code=400
            )

        old_status = report.status
        report.status = ReportStatusEnum.RESOLVED.value
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.resolution_notes = resolution_notes
        report.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_notes'])

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.RESOLVE_REPORT.value,
            content_type=ContentTypeEnum.REPORT.value,
            content_id=report.id,
            reason=resolution_notes,
            metadata={
                'old_status': old_status,
                'new_status': report.status,
                'report_issue_type': report.issue_type,
                'reporter_email': report.reporter_email,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"Report {report_id} resolved")
        return BaseResultWithData(
            message="Report resolved successfully",
            data={'report_id': report.id, 'status': report.status},
            status_code=200
        )

    @staticmethod
    @transaction.atomic
    def escalate_report(request, report_id, validated_data) -> BaseResultWithData:
        """
        Escalate a report to admin.
        """
        op = OperationLogger("ModeratorReportCommand.escalate_report", report_id=report_id)
        op.start()

        escalated_note = validated_data.get('escalated_note')
        if not escalated_note:
            return BaseResultWithData(
                message="Escalation note is required to escalate a report",
                data=None,
                status_code=400
            )

        try:
            report = ContactReport.objects.select_for_update().get(
                id=report_id,
                is_deleted=False
            )
        except ContactReport.DoesNotExist:
            op.fail("Report not found")
            return BaseResultWithData(
                message="Report not found",
                data=None,
                status_code=404
            )

        if report.escalated_to_admin:
            op.fail("Report already escalated")
            return BaseResultWithData(
                message="Report already escalated",
                data=None,
                status_code=400
            )

        old_status = report.status
        report.escalated_to_admin = True
        report.escalated_at = timezone.now()
        report.escalated_note = escalated_note
        report.status = ReportStatusEnum.ESCALATED.value
        report.save(update_fields=['escalated_to_admin', 'escalated_at', 'escalated_note', 'status'])

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.ESCALATE.value,
            content_type=ContentTypeEnum.REPORT.value,
            content_id=report.id,
            reason=escalated_note,
            metadata={
                'old_status': old_status,
                'new_status': report.status,
                'report_issue_type': report.issue_type,
                'reporter_email': report.reporter_email,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"Report {report_id} escalated")
        return BaseResultWithData(
            message="Report escalated to admin",
            data={'report_id': report.id, 'escalated_to_admin': True},
            status_code=200
        )

    @staticmethod
    @transaction.atomic
    def assign_report(request, report_id, validated_data) -> BaseResultWithData:
        """
        Assign a report to a moderator.
        """
        op = OperationLogger("ModeratorReportCommand.assign_report", report_id=report_id)
        op.start()

        assigned_to_id = validated_data.get('assigned_to')
        if not assigned_to_id:
            return BaseResultWithData(
                message="Assigned moderator ID is required",
                data=None,
                status_code=400
            )

        try:
            assignee = User.objects.get(id=assigned_to_id, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            op.fail("User not found")
            return BaseResultWithData(
                message="User not found or inactive",
                data=None,
                status_code=404
            )

        try:
            report = ContactReport.objects.select_for_update().get(
                id=report_id,
                is_deleted=False
            )
        except ContactReport.DoesNotExist:
            op.fail("Report not found")
            return BaseResultWithData(
                message="Report not found",
                data=None,
                status_code=404
            )

        old_assigned = report.assigned_to
        report.assigned_to = assignee
        report.status = ReportStatusEnum.IN_REVIEW.value
        report.save(update_fields=['assigned_to', 'status'])

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.ASSIGN.value,  # you may need to add this enum
            content_type=ContentTypeEnum.REPORT.value,
            content_id=report.id,
            reason=f"Assigned to {assignee.email}",
            metadata={
                'old_assigned_to': old_assigned.email if old_assigned else None,
                'new_assigned_to': assignee.email,
                'report_issue_type': report.issue_type,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"Report {report_id} assigned to {assignee.email}")
        return BaseResultWithData(
            message=f"Report assigned to {assignee.get_full_name() or assignee.email}",
            data={'report_id': report.id, 'assigned_to': assignee.id},
            status_code=200
        )

    @staticmethod
    @transaction.atomic
    def toggle_reopen_report(request, report_id, validated_data) -> BaseResultWithData:
        """
        Reopen a resolved report (set status back to pending/in_review).
        """
        op = OperationLogger("ModeratorReportCommand.reopen_report", report_id=report_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required to reopen a report",
                data=None,
                status_code=400
            )

        try:
            report = ContactReport.objects.select_for_update().get(
                id=report_id,
                is_deleted=False
            )
        except ContactReport.DoesNotExist:
            op.fail("Report not found")
            return BaseResultWithData(
                message="Report not found",
                data=None,
                status_code=404
            )

        if report.status != ReportStatusEnum.RESOLVED.value:
            op.fail("Only resolved reports can be reopened")
            return BaseResultWithData(
                message="Only resolved reports can be reopened",
                data=None,
                status_code=400
            )

        old_status = report.status
        report.status = ReportStatusEnum.IN_REVIEW.value
        report.resolved_by = None
        report.resolved_at = None
        report.resolution_notes = ''
        report.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_notes'])

        # Log as a special action – we'll use 'REOPEN' (add to enum or use a generic)
        ModeratorAction.objects.create(
            moderator=request.user,
            action_type='reopen',  # Add this to ModeratorActionTypeEnum
            content_type=ContentTypeEnum.REPORT.value,
            content_id=report.id,
            reason=reason,
            metadata={
                'old_status': old_status,
                'new_status': report.status,
                'report_issue_type': report.issue_type,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"Report {report_id} reopened")
        return BaseResultWithData(
            message="Report reopened for review",
            data={'report_id': report.id, 'status': report.status},
            status_code=200
        )