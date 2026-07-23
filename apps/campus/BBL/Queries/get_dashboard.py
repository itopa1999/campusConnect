from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator
from apps.campus.models import Listing, Review
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum, ListingStatusType
from utils.helpers import calculate_profile_completion, humanize_date


class DashboardQuery:
    @staticmethod
    def get_dashboard(request) -> BaseResultWithData:
        user = request.user
        cache_key = CacheKeysEnum.format(CacheKeysEnum.DASHBOARD, user_id=user.id)

        def build_dashboard_data():
            now = timezone.now()

            counts = Listing.objects.filter(user=user, is_deleted=False).aggregate(
                total_active=Count('id', filter=Q(status=ListingStatusType.ACTIVE.value, expires_at__gt=now)),
                total_expired=Count('id', filter=Q(status=ListingStatusType.EXPIRED.value)),
                total_marked_sold=Count('id', filter=Q(status=ListingStatusType.SOLD.value)),
                total_pending=Count('id', filter=Q(status=ListingStatusType.PENDING.value))
            )
            total_active = counts.get('total_active') or 0
            total_expired = counts.get('total_expired') or 0
            total_marked_sold = counts.get('total_marked_sold') or 0
            total_pending = counts.get('total_pending') or 0

            # ── Trust score ──
            trust_score = round((float(user.average_rating) / 5.0) * 100, 1) if user.average_rating else 0.0

            # ── Profile completion ──
            profile_completion = calculate_profile_completion(user)

            # ── All reviews ──
            reviews_qs = Review.objects.filter(
                to_user=user,
                is_deleted=False
            ).select_related('from_user', 'listing').order_by('-created_at')

            all_reviews = []
            for review in reviews_qs:
                all_reviews.append({
                    'from': review.from_user.get_full_name() or review.from_user.email,
                    'rating': review.rating,
                    'comment': review.comment or "",
                    'date': humanize_date(review.created_at)
                })

            first_name = user.first_name or user.email.split('@')[0]

            return {
                'user': first_name,
                'first_name': first_name,
                'total_active': total_active,
                'total_marked_sold': total_marked_sold,
                'total_expired': total_expired,
                'total_pending': total_pending,
                'total_sold': user.sold_items,
                'trust_score': trust_score,
                'profile_completion': profile_completion,
                'all_reviews': all_reviews,
            }

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_dashboard_data,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Dashboard data retrieved successfully",
            data=data,
            status_code=200
        )
    

    @staticmethod
    def get_expiring_listing(request) -> BaseResultWithData:
        user = request.user
        cache_key = CacheKeysEnum.format(CacheKeysEnum.DASHBOARD_UPCOMING_EXPIRATION_LISTING, user_id=user.id)
        def build_dashboard_data():
            now = timezone.now()
            # ── Upcoming expirations (next 7 days) ──
            upcoming_expiring = Listing.objects.filter(
                user=user,
                status=ListingStatusType.ACTIVE.value,
                is_deleted=False,
                expires_at__gt=now,
                expires_at__lte=now + timedelta(days=7)
            ).select_related('category').prefetch_related('hotspots').order_by('expires_at')[:5]

            upcoming_expiring_listings = []
            for listing in upcoming_expiring:
                days_left = (listing.expires_at - now).days
                upcoming_expiring_listings.append({
                    'title': listing.title,
                    'description': listing.description or "",
                    'expires_at_humanized': f"Expires in {days_left} day{'s' if days_left != 1 else ''}",
                    'hostpost_names': [hs.name for hs in listing.hotspots.all()[:2]],
                    'auto_reactivate': listing.auto_reactivate,
                })

            return {
            'upcoming_expiring_listings': upcoming_expiring_listings,
            }

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_dashboard_data,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Dashboard expiring listing data retrieved successfully",
            data=data,
            status_code=200
        )

    @staticmethod
    def get_dashboard_listing(request, filters=None) -> BaseResultWithData:
        user = request.user
        if filters is None:
            filters = request.GET.dict()
        else:
            filters = dict(filters)

        page = filters.get('page', 1)
        per_page = filters.get('per_page', 10)
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
        try:
            per_page = int(per_page)
        except (ValueError, TypeError):
            per_page = 10
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        filter_keys = ['reference', 'listing_type', 'search', 'badge', 'date_from', 'date_to']
        filter_parts = []
        for key in filter_keys:
            value = filters.get(key)
            if value is not None and value != '':
                filter_parts.append(f"{key}={value}")
        filter_parts.sort()
        filter_str = '&'.join(filter_parts)

        cache_key = CacheKeysEnum.format(CacheKeysEnum.DASHBOARD_LISTING, user_id=user.id, page=page, per_page=per_page, filters = filter_str)
        def build_dashboard_listing():
            # ── All listings ──
            queryset = Listing.objects.filter(
                user=user,
                is_deleted=False
            ).select_related('category').prefetch_related('hotspots').order_by('-created_at')

            category_name = filters.get("category_name")
            if category_name:
                queryset = queryset.filter(
                    category__name__iexact=category_name
                )
            
            listing_type = filters.get("listing_type")
            if listing_type:
                queryset = queryset.filter(
                    listing_type=listing_type
                )

            badge = filters.get("badge")
            if badge:
                queryset = queryset.filter(
                    badge__iexact=badge
                )

            search = filters.get("search")
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search)
                    | Q(description__icontains=search)
                )

            date_from = filters.get("date_from")
            if date_from:
                queryset = queryset.filter(
                    created_at__date__gte=date_from
                )

            date_to = filters.get("date_to")
            if date_to:
                queryset = queryset.filter(
                    created_at__date__lte=date_to
                )

            paginator = Paginator(queryset, per_page)
            page_obj = paginator.get_page(page)

            all_listings = []
            for listing in page_obj:
                location = [hs.name for hs in listing.hotspots.all()] or ["Campus"]
                image_url = None
                if listing.image:
                    image_url = request.build_absolute_uri(listing.image.url)
                all_listings.append({
                    'id': listing.id,
                    'title': listing.title,
                    'description': listing.description or "",
                    'price': float(listing.price) if listing.price else 0,
                    'category': listing.category.name,
                    'badge': listing.badge,
                    'is_hot_sale': listing.is_hot_sales,
                    'is_ads_banner': listing.is_ads_banner,
                    'lisiting_type': listing.listing_type,
                    'auto_reactivate': listing.auto_reactivate,
                    'location': location,
                    'status': listing.status,
                    'image': image_url,
                    'created_at_humanized': humanize_date(listing.created_at),
                })

            return {
                "all_listings": all_listings,
                "pagination": {
                    "page": page_obj.number,
                    "per_page": per_page,
                    "total_pages": paginator.num_pages,
                    "total_items": paginator.count,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                },
            }

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_dashboard_listing,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Dashboard listings data retrieved successfully",
            data=data,
            status_code=200
        )