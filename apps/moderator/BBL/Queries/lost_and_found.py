from django.db.models import Q, Prefetch
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from apps.campus.models import Claim, LostAndFound
from apps.moderator.models import FlaggedContent, ModeratorAction
from utils.base_result import BaseResultWithData
from utils.enums import ContentTypeEnum
from utils.log_helpers import OperationLogger


class LostAndFoundQuery:
    @staticmethod
    def get_all_lost_items(request, filters=None) -> BaseResultWithData:
        """
            Retrieve all lost_items with optional filters.
            filters should be a dict (e.g., request.GET) with possible keys:
            status, category_id, lost_item_type, search, is_flagged, is_deleted, date_from, date_to.
        """
        op = OperationLogger("ModeratorLostAndFoundQuery.get_all_lost_items", user=request.user.id)
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

        queryset = LostAndFound.objects.all_including_deleted()

        # ─── Apply filters ──────────────────────────────────────
        # Status filter
        status = filters.get('status')
        if status:
            queryset = queryset.filter(status__iexact=status)


        search = filters.get('search')
        if search:
            queryset = queryset.filter(
                Q(item_name__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search) |
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )

        # Flagged status
        is_flagged = filters.get('is_flagged')
        if is_flagged is not None:
            if is_flagged.lower() in ('true', '1', 'yes'):
                flagged_ids = FlaggedContent.objects.filter(
                    content_type=ContentTypeEnum.LOST_ITEM.value,
                    is_resolved=False,
                    is_deleted=False
                ).values_list('content_id', flat=True)
                queryset = queryset.filter(id__in=flagged_ids)
            else:
                flagged_ids = FlaggedContent.objects.filter(
                    content_type=ContentTypeEnum.LOST_ITEM.value,
                    is_resolved=False,
                    is_deleted=False
                ).values_list('content_id', flat=True)
                queryset = queryset.exclude(id__in=flagged_ids)

        # Deleted status
        is_deleted = filters.get('is_deleted')
        if is_deleted is not None:
            if is_deleted.lower() in ('true', '1', 'yes'):
                queryset = queryset.filter(is_deleted=True)
            else:
                queryset = queryset.filter(is_deleted=False)

        # Date range
        date_from = filters.get('date_from')
        if date_from:
            queryset = queryset.filter(date_found__gte=date_from)
        date_to = filters.get('date_to')
        if date_to:
            queryset = queryset.filter(date_found__lte=date_to)

        # ─── Annotate flagged status ──────────────────────────
        flagged_lost_item_ids = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.LOST_ITEM.value,
            is_resolved=False,
        ).values_list('content_id', flat=True)

        # ─── Pagination ────────────────────────────────────────
        paginator = Paginator(queryset, per_page)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        items = []
        for lost_item in page_obj:
            is_flagged = lost_item.id in flagged_lost_item_ids
            items.append({
                'id': lost_item.id,
                'item_name': lost_item.item_name,
                'description': lost_item.description,
                'location': lost_item.location,
                'status': lost_item.status,
                'date_found': lost_item.date_found,
                'image':request.build_absolute_uri(lost_item.image.url) if lost_item.image else None,
                'user_full_name': lost_item.full_name,
                'created_at': lost_item.created_at.isoformat(),
                'is_flagged': is_flagged,
                'is_deleted': lost_item.is_deleted,
            })

        op.success(f"Retrieved {len(items)} lost_items")
        return BaseResultWithData(
            message="lost_items retrieved successfully",
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
    def get_lost_item_detail(request, lost_item_id) -> BaseResultWithData:
        """
        Get detailed lost_item information including moderation history.
        """
        op = OperationLogger("ModeratorLostAndFoundQuery.get_lost_item_detail", lost_item_id=lost_item_id)
        op.start()

        try:
            lost_item = LostAndFound.objects.all_including_deleted().get(
                id=lost_item_id,
            )
        except LostAndFound.DoesNotExist:
            op.fail(f"lost_item {lost_item_id} not found")
            return BaseResultWithData(
                message="lost_item not found",
                data=None,
                status_code=404
            )

        # Get flagged status
        lost_item_flagged = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.LOST_ITEM.value,
            content_id=lost_item.id,
        ).select_related('flagged_by').order_by('-created_at')

        flagged_data = [
            {
                'id': action.id,
                'moderator': action.flagged_by.get_full_name() or action.flagged_by.email,
                'reason': action.reason,
                'is_resolved':action.is_resolved,
                'resolved_by': action.resolved_by,
                'resolved_at': action.resolved_at,
                'resolution_note': action.resolution_note,
                'created_at': action.created_at.isoformat(),
            }
            for action in lost_item_flagged
        ]

        # Get moderation history
        history = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.LOST_ITEM.value,
            content_id=lost_item.id,
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

        claims = Claim.objects.all_including_deleted().filter(lost_item = lost_item)
        claims_data = [
            {
                'id': claim.id,
                'claim_user': {
                    'full_name': claim.full_name,
                    'email': claim.email,
                    'phone': claim.phone
                },
                'answer1': claim.answer1,
                'answer2': claim.answer2,
                'is_deleted': claim.is_deleted,
                'created_at': claim.created_at.isoformat(),
            }
            for claim in claims
        ]

        data = {
            'id': lost_item.id,
            'item_name': lost_item.item_name,
            'description': lost_item.description,
            'location': lost_item.location,
            'status': lost_item.status,
            'date_found': lost_item.date_found,
            'found_user': {
                'email': lost_item.email,
                'full_name': lost_item.full_name,
                'phone': lost_item.phone,
                'department': lost_item.department,
            },
            'verification1': lost_item.verification1,
            'answer1': lost_item.answer1,
            'verification2': lost_item.verification2,
            'answer2': lost_item.answer2,
            'claimed_by': lost_item.claimed_by,
            'image': request.build_absolute_uri(lost_item.image.url) if lost_item.image else None,
            'created_at': lost_item.created_at.isoformat(),
            'modified_at':lost_item.modified_at,
            'is_flagged': lost_item_flagged.filter(is_resolved=False).exists(),
            'history': history_data,
            'claims_data': claims_data,
            'flagged': flagged_data
        }

        op.success(f"Retrieved lost_item {lost_item_id}")
        return BaseResultWithData(
            message="lost_item details retrieved successfully",
            data=data,
            status_code=200
        )