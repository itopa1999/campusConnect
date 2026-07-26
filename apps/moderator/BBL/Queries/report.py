from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import get_user_model

from apps.users.models import ContactReport
from apps.moderator.models import ModeratorAction
from utils.base_result import BaseResultWithData
from utils.enums import ReportStatusEnum, ContentTypeEnum
from utils.log_helpers import OperationLogger

User = get_user_model()


class ReportQuery:
    @staticmethod
    def get_all_reports(request, filters=None) -> BaseResultWithData:
        """
        Retrieve all reports with optional filters.
        Filters: status, issue_type, assigned_to, escalated_to_admin,
        search (reporter_name, reporter_email, message), date range.
        """
        op = OperationLogger("ModeratorReportQuery.get_all_reports", user=request.user.id)
        op.start()

        if filters is None:
            filters = request.GET.dict()
        else:
            filters = dict(filters)

        page = filters.get('page', 1)
        per_page = filters.get('per_page', 20)
        try:
            page = int(page)
            per_page = int(per_page)
            if per_page < 1:
                per_page = 1
            if per_page > 100:
                per_page = 100
        except (ValueError, TypeError):
            page = 1
            per_page = 20

        queryset = ContactReport.objects.filter(is_deleted=False).select_related('assigned_to', 'resolved_by')

        # ─── Apply filters ──────────────────────────────────────
        # Status
        status = filters.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Issue type
        issue_type = filters.get('issue_type')
        if issue_type:
            queryset = queryset.filter(issue_type=issue_type)

        # Assigned to
        assigned_to = filters.get('assigned_to')
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        # Escalated to admin
        escalated = filters.get('escalated_to_admin')
        if escalated is not None:
            queryset = queryset.filter(escalated_to_admin=escalated)

        # Search (reporter name, email, message)
        search = filters.get('search')
        if search:
            queryset = queryset.filter(
                Q(reporter_name__icontains=search) |
                Q(reporter_email__icontains=search) |
                Q(message__icontains=search) |
                Q(listing_identifier__icontains=search) |
                Q(reported_user_email__icontains=search)
            )

        # Date range
        date_from = filters.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        date_to = filters.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        # ─── Pagination ────────────────────────────────────────
        paginator = Paginator(queryset, per_page)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        items = []
        for report in page_obj:
            items.append({
                'id': report.id,
                'reporter_name': report.reporter_name,
                'reporter_email': report.reporter_email,
                'issue_type': report.issue_type,
                'issue_type_display': report.get_issue_type_display(),
                'listing_identifier': report.listing_identifier,
                'reported_user_email': report.reported_user_email,
                'message': report.message[:300],
                'status': report.status,
                'status_display': report.get_status_display(),
                'assigned_to': {
                    'id': report.assigned_to.id,
                    'email': report.assigned_to.email,
                    'full_name': report.assigned_to.get_full_name() or report.assigned_to.email,
                } if report.assigned_to else None,
                'resolved_by': {
                    'id': report.resolved_by.id,
                    'email': report.resolved_by.email,
                    'full_name': report.resolved_by.get_full_name() or report.resolved_by.email,
                } if report.resolved_by else None,
                'resolved_at': report.resolved_at.isoformat() if report.resolved_at else None,
                'escalated_to_admin': report.escalated_to_admin,
                'escalated_at': report.escalated_at.isoformat() if report.escalated_at else None,
                'created_at': report.created_at.isoformat(),
                'is_reviewed': report.is_reviewed,
            })

        op.success(f"Retrieved {len(items)} reports")
        return BaseResultWithData(
            message="Reports retrieved successfully",
            data={
                'items': items,
                'pagination': {
                    "page": page_obj.number,
                    "per_page": per_page,
                    "total_pages": paginator.num_pages,
                    "total_items": paginator.count,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                }
            },
            status_code=200
        )

    @staticmethod
    def get_report_detail(request, report_id) -> BaseResultWithData:
        """
        Get detailed report information including moderation history.
        """
        op = OperationLogger("ModeratorReportQuery.get_report_detail", report_id=report_id)
        op.start()

        try:
            report = ContactReport.objects.select_related('assigned_to', 'resolved_by').get(
                id=report_id,
                is_deleted=False
            )
        except ContactReport.DoesNotExist:
            op.fail(f"Report {report_id} not found")
            return BaseResultWithData(
                message="Report not found",
                data=None,
                status_code=404
            )

        history = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.REPORT.value,
            content_id=report.id,
            is_deleted=False
        ).select_related('moderator').order_by('-created_at')

        history_data = [
            {
                'id': action.id,
                'moderator': action.moderator.get_full_name() or action.moderator.email,
                'action': action.get_action_type_display(),
                'reason': action.reason,
                'metadata': action.metadata,
                'ip_address': action.ip_address,
                'created_at': action.created_at.isoformat(),
            }
            for action in history
        ]

        data = {
            'id': report.id,
            'reporter_name': report.reporter_name,
            'reporter_email': report.reporter_email,
            'issue_type': report.issue_type,
            'issue_type_display': report.get_issue_type_display(),
            'listing_identifier': report.listing_identifier,
            'reported_user_email': report.reported_user_email,
            'message': report.message,
            'status': report.status,
            'status_display': report.get_status_display(),
            'assigned_to': {
                'id': report.assigned_to.id,
                'email': report.assigned_to.email,
                'full_name': report.assigned_to.get_full_name() or report.assigned_to.email,
            } if report.assigned_to else None,
            'resolved_by': {
                'id': report.resolved_by.id,
                'email': report.resolved_by.email,
                'full_name': report.resolved_by.get_full_name() or report.resolved_by.email,
            } if report.resolved_by else None,
            'resolved_at': report.resolved_at.isoformat() if report.resolved_at else None,
            'resolution_notes': report.resolution_notes,
            'escalated_to_admin': report.escalated_to_admin,
            'escalated_at': report.escalated_at.isoformat() if report.escalated_at else None,
            'escalated_note': report.escalated_note,
            'created_at': report.created_at.isoformat(),
            'admin_notes': report.admin_notes,
            'is_reviewed': report.is_reviewed,
            'history': history_data,
        }

        op.success(f"Retrieved report {report_id}")
        return BaseResultWithData(
            message="Report details retrieved successfully",
            data=data,
            status_code=200
        )