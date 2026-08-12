from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator
from apps.campus.models import Listing, Review
from apps.moderator.models import FlaggedContent
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum, ContentTypeEnum, ListingStatusTypeEnum, ListingTypeEnum
from utils.helpers import calculate_profile_completion, format_naira, humanize_date


class DashboardQuery:
    @staticmethod
    def get_dashboard(request) -> BaseResultWithData:
        user = request.user
        cache_key = CacheKeysEnum.format(CacheKeysEnum.DASHBOARD, user_id=user.id)

        def build_dashboard_data():
            now = timezone.now()

            counts = Listing.objects.filter(user=user, is_deleted=False).aggregate(
                total_active=Count('id', filter=Q(status=ListingStatusTypeEnum.ACTIVE.value, expires_at__gt=now)),
                total_expired=Count('id', filter=Q(status=ListingStatusTypeEnum.EXPIRED.value)),
                total_marked_sold=Count('id', filter=Q(status=ListingStatusTypeEnum.SOLD.value)),
                total_pending=Count('id', filter=Q(status=ListingStatusTypeEnum.PENDING.value)),
                total_rejected=Count('id', filter=Q(status=ListingStatusTypeEnum.REJECT.value)),
                total_hidden=Count('id', filter=Q(status=ListingStatusTypeEnum.HIDDEN.value))
            )

            # ── Trust score ──
            trust_score = round((float(user.average_rating) / 5.0) * 100, 1) if user.average_rating else 0.0

            # ── Profile completion ──
            profile_data = calculate_profile_completion(user)
            profile_completion = profile_data['percentage']
            missing_fields = profile_data['missing_fields']

            flagged_listing_count = FlaggedContent.objects.filter(
                content_type=ContentTypeEnum.LISTING.value,
                is_resolved=False,
            ).count()
            
            return {
                'first_name': user.first_name or user.email.split('@')[0],
                **counts,
                'total_items_sold': user.sold_items,
                'trust_score': trust_score,
                'profile_completion': profile_completion,
                'missing_fields': missing_fields,
                'flagged_listing_count': flagged_listing_count,
            }

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_dashboard_data,
            timeout=300,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Dashboard data retrieved successfully",
            data=data,
            status_code=200
        )
    
    @staticmethod
    def get_dashboard_reviews(request, filters=None) -> BaseResultWithData:
        user = request.user
        filters = filters or request.GET.dict()
        page = int(filters.get('page', 1))
        per_page = min(max(int(filters.get('per_page', 10)), 1), 100)

        filter_keys = ['search']
        filter_parts = []
        for key in filter_keys:
            value = filters.get(key)
            if value is not None and value != '':
                filter_parts.append(f"{key}={value}")
        filter_parts.sort()
        filter_str = '&'.join(filter_parts)
        cache_key = CacheKeysEnum.format(CacheKeysEnum.DASHBOARD_REVIEW, user_id=user.id, page=page, per_page=per_page, filters = filter_str)
        def build_reviews_data():
            qs = Review.objects.filter(
                to_user=user,
                is_deleted=False
            ).select_related('from_user', 'listing') \
            .only('rating', 'comment', 'created_at',
                'from_user__first_name', 'from_user__last_name', 'from_user__email',
                'listing__title') \
            .order_by('-created_at')

            search = filters.get("search")
            if search:
                if search.isdigit():
                    qs = qs.filter(Q(rating=int(search)))
                else:
                    qs = qs.filter(
                        Q(from_user__last_name__icontains=search)
                        | Q(comment__icontains=search) |
                        Q(listing__title__icontains=search) |
                        Q(from_user__first_name__icontains=search)
                    )
            paginator = Paginator(qs, per_page)
            page_obj = paginator.get_page(page)
            reviews = [
                {
                    'from': r.from_user.get_full_name() or r.from_user.email,
                    'rating': r.rating,
                    'comment': r.comment or "",
                    'listing_name': r.listing.title,
                    'date': humanize_date(r.created_at)
                }
                for r in page_obj
            ]

            return {
                'reviews': reviews,
                'pagination': {
                    'page': page_obj.number,
                    'per_page': per_page,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            } 

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_reviews_data,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Dashboard review listing data retrieved successfully",
            data=data,
            status_code=200
        )



    @staticmethod
    def get_expiring_listing(request) -> BaseResultWithData:
        user = request.user
        cache_key = CacheKeysEnum.format(CacheKeysEnum.DASHBOARD_UPCOMING_EXPIRATION_LISTING, user_id=user.id)
        def build_dashboard_data():
            now = timezone.now()
            listings = Listing.objects.filter(
                user=user,
                status=ListingStatusTypeEnum.ACTIVE.value,
                is_deleted=False,
                expires_at__gt=now,
                expires_at__lte=now + timedelta(days=7)
            ).prefetch_related('hotspots') \
            .only('title', 'description', 'expires_at', 'auto_reactivate') \
            .order_by('expires_at')

            upcoming = []
            for listing in listings:
                days_left = (listing.expires_at - now).days
                upcoming.append({
                    'id': listing.id,
                    'title': listing.title,
                    'description': listing.description or "",
                    'expires_at_humanized': f"Expires in {days_left} day{'s' if days_left != 1 else ''}",
                    'hostpost_names': [hs.name for hs in listing.hotspots.all()[:2]],
                    'auto_reactivate': listing.auto_reactivate,
                })

            return {
            'upcoming_expiring_listings': upcoming,
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
        filters = filters or request.GET.dict()
        page = int(filters.get('page', 1))
        per_page = min(max(int(filters.get('per_page', 10)), 1), 100)  

        filter_keys = ['search']
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
            qs = Listing.objects.filter(user=user, is_deleted=False) \
             .select_related('category') \
             .prefetch_related('hotspots') \
             .only('id', 'title', 'description', 'price', 'badge',
                   'is_hot_sales', 'is_ads_banner', 'listing_type',
                   'auto_reactivate', 'status', 'image', 'created_at',
                   'category__name') \
             .order_by('-created_at')

            search = filters.get("search")
            if search:
                qs = qs.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search) |
                    Q(category__name__iexact=search) |
                    Q(listing_type__icontains=search) |
                    Q(badge__iexact=search) 
                )

                try:
                    datetime.strptime(search, '%Y-%m-%d')
                    qs |= Q(created_at__date__gte=search) | Q(created_at__date__lte=search)
                except ValueError:
                    try:
                        datetime.strptime(search, '%d-%m-%Y')
                        qs |= Q(created_at__date__gte=search) | Q(created_at__date__lte=search)
                    except ValueError:
                        pass

            paginator = Paginator(qs, per_page)
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
                    'price': 'Free' if listing.listing_type == ListingTypeEnum.FREEBIE.value else format_naira(listing.price),
                    'category': listing.category.name,
                    'badge': listing.badge,
                    'is_hot_sale': listing.is_hot_sales,
                    'is_ads_banner': listing.is_ads_banner,
                    'listing_type': listing.listing_type,
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