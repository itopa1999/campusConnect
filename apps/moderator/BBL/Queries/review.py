from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from apps.campus.models import Review
from apps.moderator.models import FlaggedContent, ModeratorAction
from utils.base_result import BaseResultWithData
from utils.enums import ContentTypeEnum
from utils.log_helpers import OperationLogger


class ReviewQuery:
    @staticmethod
    def get_all_reviews(request, filters=None) -> BaseResultWithData:
        """
        Retrieve all reviews with optional filters.
        Filters: from_user, to_user, listing, rating, is_flagged, is_deleted,
        search (comment, user names/emails), date range.
        """
        op = OperationLogger("ModeratorReviewQuery.get_all_reviews", user=request.user.id)
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

        queryset = Review.objects.select_related('from_user', 'to_user', 'listing')
            
        # ─── Apply filters ──────────────────────────────────────
        # From user
        from_user_id = filters.get('from_user_id')
        if from_user_id:
            queryset = queryset.filter(from_user_id=from_user_id)

        # To user
        to_user_id = filters.get('to_user_id')
        if to_user_id:
            queryset = queryset.filter(to_user_id=to_user_id)

        # Listing
        listing_id = filters.get('listing_id')
        if listing_id:
            queryset = queryset.filter(listing_id=listing_id)

        # Rating
        rating = filters.get('rating')
        if rating:
            queryset = queryset.filter(rating=rating)

        # Search (comment, from_user, to_user)
        search = filters.get('search')
        if search:
            queryset = queryset.filter(
                Q(comment__icontains=search) |
                Q(from_user__email__icontains=search) |
                Q(from_user__first_name__icontains=search) |
                Q(from_user__last_name__icontains=search) |
                Q(to_user__email__icontains=search) |
                Q(to_user__first_name__icontains=search) |
                Q(to_user__last_name__icontains=search)
            )

        # Flagged status
        is_flagged = filters.get('is_flagged')
        if is_flagged is not None:
            flagged_ids = FlaggedContent.objects.filter(
                content_type=ContentTypeEnum.REVIEW.value,
                is_resolved=False,
                is_deleted=False
            ).values_list('content_id', flat=True)
            if is_flagged:
                queryset = queryset.filter(id__in=flagged_ids)
            else:
                queryset = queryset.exclude(id__in=flagged_ids)

        # Deleted status
        is_deleted = filters.get('is_deleted')
        if is_deleted is not None:
            queryset = queryset.filter(is_deleted=is_deleted)

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
        for review in page_obj:
            is_flagged = FlaggedContent.objects.filter(
                content_type=ContentTypeEnum.REVIEW.value,
                content_id=review.id,
                is_resolved=False,
                is_deleted=False
            ).exists()

            items.append({
                'id': review.id,
                'from_user': {
                    'id': review.from_user.id,
                    'email': review.from_user.email,
                    'full_name': review.from_user.get_full_name() or review.from_user.email,
                },
                'to_user': {
                    'id': review.to_user.id,
                    'email': review.to_user.email,
                    'full_name': review.to_user.get_full_name() or review.to_user.email,
                },
                'listing': {
                    'id': review.listing.id if review.listing else None,
                    'title': review.listing.title if review.listing else None,
                },
                'rating': review.rating,
                'comment': review.comment,
                'is_flagged': is_flagged,
                'is_deleted': review.is_deleted,
                'created_at': review.created_at.isoformat(),
            })

        op.success(f"Retrieved {len(items)} reviews")
        return BaseResultWithData(
            message="Reviews retrieved successfully",
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
    def get_review_detail(request, review_id) -> BaseResultWithData:
        """
        Get detailed review information including moderation history.
        """
        op = OperationLogger("ModeratorReviewQuery.get_review_detail", review_id=review_id)
        op.start()

        try:
            review = Review.objects.select_related('from_user', 'to_user', 'listing').get(id=review_id)
        except Review.DoesNotExist:
            op.fail(f"Review {review_id} not found")
            return BaseResultWithData(
                message="Review not found",
                data=None,
                status_code=404
            )

        is_flagged = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=review.id,
            is_resolved=False,
            is_deleted=False
        ).exists()

        history = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=review.id,
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
            'id': review.id,
            'from_user': {
                'id': review.from_user.id,
                'email': review.from_user.email,
                'full_name': review.from_user.get_full_name() or review.from_user.email,
            },
            'to_user': {
                'id': review.to_user.id,
                'email': review.to_user.email,
                'full_name': review.to_user.get_full_name() or review.to_user.email,
            },
            'listing': {
                'id': review.listing.id if review.listing else None,
                'title': review.listing.title if review.listing else None,
            },
            'rating': review.rating,
            'comment': review.comment,
            'is_flagged': is_flagged,
            'is_deleted': review.is_deleted,
            'created_at': review.created_at.isoformat(),
            'history': history_data,
        }

        op.success(f"Retrieved review {review_id}")
        return BaseResultWithData(
            message="Review details retrieved successfully",
            data=data,
            status_code=200
        )