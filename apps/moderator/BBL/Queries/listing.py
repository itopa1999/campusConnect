from django.db.models import Q, Prefetch
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from apps.campus.models import Listing
from apps.moderator.models import FlaggedContent, ModeratorAction
from utils.base_result import BaseResultWithData
from utils.enums import ListingStatusTypeEnum, ContentTypeEnum
from utils.log_helpers import OperationLogger


class ListingQuery:
    @staticmethod
    def get_all_listings(request, filters=None) -> BaseResultWithData:
        """
            Retrieve all listings with optional filters.
            filters should be a dict (e.g., request.GET) with possible keys:
            status, category_id, listing_type, search, is_flagged, is_deleted, date_from, date_to.
        """
        op = OperationLogger("ModeratorListingQuery.get_all_listings", user=request.user.id)
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

        queryset = Listing.objects.select_related('user', 'category').prefetch_related('hotspots')

        # Status filter
        status = filters.get('status')
        if status:
            queryset = queryset.filter(status__iexact=status)

        # Category filter
        category_id = filters.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Listing type filter
        listing_type = filters.get('listing_type')
        if listing_type:
            queryset = queryset.filter(listing_type=listing_type)

        # Search by title or user email/full name
        search = filters.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )

        # Flagged status
        is_flagged = filters.get('is_flagged')
        if is_flagged is not None:
            if is_flagged.lower() in ('true', '1', 'yes'):
                flagged_ids = FlaggedContent.objects.filter(
                    content_type=ContentTypeEnum.LISTING.value,
                    is_resolved=False,
                    is_deleted=False
                ).values_list('content_id', flat=True)
                queryset = queryset.filter(id__in=flagged_ids)
            else:
                flagged_ids = FlaggedContent.objects.filter(
                    content_type=ContentTypeEnum.LISTING.value,
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
            queryset = queryset.filter(created_at__gte=date_from)
        date_to = filters.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        # ─── Annotate flagged status ──────────────────────────
        flagged_listing_ids = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
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
        for listing in page_obj:
            is_flagged = listing.id in flagged_listing_ids
            items.append({
                'id': listing.id,
                'title': listing.title,
                'description': listing.description,
                'price': float(listing.price) if listing.price else 0,
                'category': listing.category.name if listing.category else '',
                'category_id': listing.category_id,
                'image':request.build_absolute_uri(listing.image.url) if listing.image else None,
                'user': {
                    'id': listing.user.id,
                    'email': listing.user.email,
                    'full_name': listing.user.get_full_name() or listing.user.email,
                },
                'listing_type': listing.listing_type,
                'status': listing.status,
                'badge': listing.badge,
                'is_ads_banner': listing.is_ads_banner,
                'is_hot_sales': listing.is_hot_sales,
                'auto_reactivate': listing.auto_reactivate,
                'expires_at': listing.expires_at.isoformat() if listing.expires_at else None,
                'created_at': listing.created_at.isoformat(),
                'is_flagged': is_flagged,
                'is_deleted': listing.is_deleted,
            })

        op.success(f"Retrieved {len(items)} listings")
        return BaseResultWithData(
            message="Listings retrieved successfully",
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
    def get_listing_detail(request, listing_id) -> BaseResultWithData:
        """
        Get detailed listing information including moderation history.
        """
        op = OperationLogger("ModeratorListingQuery.get_listing_detail", listing_id=listing_id)
        op.start()

        try:
            listing = Listing.objects.select_related('user', 'category').prefetch_related('hotspots').get(
                id=listing_id,
            )
        except Listing.DoesNotExist:
            op.fail(f"Listing {listing_id} not found")
            return BaseResultWithData(
                message="Listing not found",
                data=None,
                status_code=404
            )

        # Get flagged status
        listing_flagged = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=listing.id,
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
            for action in listing_flagged
        ]

        # Get moderation history
        history = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=listing.id,
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
            'id': listing.id,
            'title': listing.title,
            'description': listing.description,
            'price': float(listing.price) if listing.price else 0,
            'category': listing.category.name if listing.category else '',
            'category_id': listing.category_id,
            'user': {
                'id': listing.user.id,
                'email': listing.user.email,
                'full_name': listing.user.get_full_name() or listing.user.email,
                'phone': listing.user.phone,
                'department': listing.user.department,
                'faculty': listing.user.faculty,
                'level': listing.user.level,
                'matric_no': listing.user.matric_number,
                'average_rating': float(listing.user.average_rating),
            },
            'listing_type': listing.listing_type,
            'status': listing.status,
            'badge': listing.badge,
            'is_ads_banner': listing.is_ads_banner,
            'is_hot_sales': listing.is_hot_sales,
            'ads_banner_expires_at': listing.is_ads_banner_expires_at,
            'hot_sales_expires_at': listing.is_hot_sales_expires_at,
            'auto_reactivate': listing.auto_reactivate,
            'expires_at': listing.expires_at.isoformat() if listing.expires_at else None,
            'hotspots': [{'id': h.id, 'name': h.name} for h in listing.hotspots.all()],
            'image': request.build_absolute_uri(listing.image.url) if listing.image else None,
            'created_at': listing.created_at.isoformat(),
            'modified_at':listing.modified_at,
            'is_flagged': listing_flagged.filter(is_resolved=False).exists(),
            'history': history_data,
            'flagged': flagged_data
        }

        op.success(f"Retrieved listing {listing_id}")
        return BaseResultWithData(
            message="Listing details retrieved successfully",
            data=data,
            status_code=200
        )