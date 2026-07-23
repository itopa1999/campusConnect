from django.db.models import Q, Prefetch, Count, Avg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import get_user_model

from apps.moderator.models import UserModeration, ModeratorAction
from apps.campus.models import Listing, Review
from utils.base_result import BaseResultWithData
from utils.enums import ContentTypeEnum, ModeratorActionTypeEnum
from utils.log_helpers import OperationLogger

User = get_user_model()


class UserQuery:
    @staticmethod
    def get_all_users(request, filters=None):
        """
        Retrieve all users with optional filters.
        Filters: search (name/email), is_suspended, is_banned, is_active, is_deleted,
        date_joined_from/to, department.
        """
        op = OperationLogger("ModeratorUserQuery.get_all_users", user=request.user.id)
        op.start()

        page = filters.get('page', 1) if filters else request.GET.get('page', 1)
        per_page = filters.get('per_page', 20) if filters else request.GET.get('per_page', 20)
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

        # Use all including deleted if filter asks for it
        if filters and filters.get('is_deleted') is True:
            queryset = User.objects.all_including_deleted()
        else:
            queryset = User.objects.filter(is_deleted=False)

        queryset = queryset.prefetch_related('moderation').select_related('moderation')

        # ─── Apply filters ──────────────────────────────────────
        if filters:
            # Search by email, first_name, last_name
            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    Q(email__icontains=search) |
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search)
                )

            # Department
            department = filters.get('department')
            if department:
                queryset = queryset.filter(department__icontains=department)

            # Suspended
            is_suspended = filters.get('is_suspended')
            if is_suspended is not None:
                if is_suspended:
                    queryset = queryset.filter(moderation__is_suspended=True)
                else:
                    queryset = queryset.filter(moderation__is_suspended=False)

            # Banned
            is_banned = filters.get('is_banned')
            if is_banned is not None:
                if is_banned:
                    queryset = queryset.filter(moderation__is_banned=True)
                else:
                    queryset = queryset.filter(moderation__is_banned=False)

            # Active (Django is_active)
            is_active = filters.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active)

            # Deleted (if not already handled)
            is_deleted = filters.get('is_deleted')
            if is_deleted is not None and is_deleted is not True:
                queryset = queryset.filter(is_deleted=is_deleted)

            # Date joined range
            date_from = filters.get('date_from')
            if date_from:
                queryset = queryset.filter(date_joined__gte=date_from)
            date_to = filters.get('date_to')
            if date_to:
                queryset = queryset.filter(date_joined__lte=date_to)

        # ─── Pagination ────────────────────────────────────────
        paginator = Paginator(queryset, per_page)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        items = []
        for user in page_obj:
            # Get moderation data
            moderation = getattr(user, 'moderation', None)
            if moderation:
                warning_count = moderation.warning_count
                is_suspended = moderation.is_suspended
                suspended_until = moderation.suspended_until
                is_banned = moderation.is_banned
            else:
                warning_count = 0
                is_suspended = False
                suspended_until = None
                is_banned = False

            items.append({
                'id': user.id,
                'image': request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
                'email': user.email,
                'full_name': user.get_full_name() or user.email,
                'department': user.department,
                'faculty': user.faculty,
                'level': user.level,
                'points': user.points,
                'average_rating': float(user.average_rating),
                'email_verified': user.email_verified,
                'is_active': user.is_active,
                'is_deleted': user.is_deleted,
                'is_suspended': is_suspended,
                'suspended_until': suspended_until.isoformat() if suspended_until else None,
                'is_banned': is_banned,
                'warning_count': warning_count,
                'date_joined': user.date_joined.isoformat(),
            })

        op.success(f"Retrieved {len(items)} users")
        return BaseResultWithData(
            message="Users retrieved successfully",
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
    def get_user_detail(request, user_id):
        """
        Get detailed user information including listings, reviews, moderation history.
        """
        op = OperationLogger("ModeratorUserQuery.get_user_detail", user_id=user_id)
        op.start()

        try:
            user = User.objects.all_including_deleted().select_related('moderation').get(id=user_id)
        except User.DoesNotExist:
            op.fail(f"User {user_id} not found")
            return BaseResultWithData(
                message="User not found",
                data=None,
                status_code=404
            )

        moderation = getattr(user, 'moderation', None)

        # Listings
        listings = user.listings.filter(is_deleted=False)
        listings_data = [
            {
                'id': listing.id,
                'category': listing.category.name if listing.category else '',
                'category_id': listing.category_id,
                'title': listing.title,
                'description': listing.description,
                'price': float(listing.price) if listing.price else 0,
                'image':request.build_absolute_uri(listing.image.url) if listing.image else None,
                'listing_type': listing.listing_type,
                'status': listing.status,
                'is_ads_banner': listing.is_ads_banner,
                'is_hot_sales': listing.is_hot_sales,
                'auto_reactivate': listing.auto_reactivate, 
                'expires_at': listing.expires_at.isoformat() if listing.expires_at else None,
                'is_deleted': listing.is_deleted,
                'created_at': listing.created_at.isoformat(),
            }
            for listing in listings
        ]
        listings_count = listings.count()

        # Reviews received from listing
        reviews = user.reviews_received.filter(is_deleted=False)
        reviews_data = [
            {
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
                'is_deleted': review.is_deleted,
                'created_at': review.created_at.isoformat(),
            }
            for review in reviews
        ]
        reviews_count = reviews.count()


        # Moderation history
        history = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.USER.value,
            content_id=user.id,
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
            'id': user.id,
            'email': user.email,
            'image': request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
            'full_name': user.get_full_name() or user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone,
            'department': user.department,
            'faculty': user.faculty,
            'level': user.level,
            'points': user.points,
            'average_rating': float(user.average_rating),
            'email_verified': user.email_verified,
            'student_id_verified': user.student_id_verified,
            'is_active': user.is_active,
            'is_deleted': user.is_deleted,
            'warning_count': moderation.warning_count if moderation else 0,
            'is_suspended': moderation.is_suspended if moderation else False,
            'suspended_until': moderation.suspended_until.isoformat() if moderation and moderation.suspended_until else None,
            'is_banned': moderation.is_banned if moderation else False,
            'banned_at': moderation.banned_at.isoformat() if moderation and moderation.banned_at else None,
            'ban_reason': moderation.ban_reason if moderation else '',
            'moderation_notes': moderation.notes if moderation else '',
            'history': history_data,
            'listings_count': listings_count,
            'listings_data' : listings_data,
            'reviews_count': reviews_count,
            'reviews_data':reviews_data,
            'date_joined': user.date_joined.isoformat(),
        }

        op.success(f"Retrieved user {user_id}")
        return BaseResultWithData(
            message="User details retrieved successfully",
            data=data,
            status_code=200
        )