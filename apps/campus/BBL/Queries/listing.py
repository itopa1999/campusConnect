from apps.campus.models import Listing, Review
from apps.users.models import User
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.constant_helper import ConstantHelper
from django.db.models import Avg, Count, Prefetch, Q
from utils.enums import CacheKeysEnum, GroupNames, ListingStatusType
from utils.helpers import humanize_date
from django.core.paginator import Paginator


class ListingQuery:
    @staticmethod
    def get_listing_detail(request, user: User, listing_id: int) -> BaseResultWithData:
        """
        Fetch full details of a listing owned by the user.
        """

        if not listing_id:
            return BaseResultWithData(
                message="Listing Id is required",
                status_code=400
            )

        cache_key = CacheKeysEnum.format(CacheKeysEnum.LISTING_DETAIL, user_id=user.id, listing_id=listing_id)

        def build_listing_detail_data():
            """Heavy computation callback – runs only on cache miss."""
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).select_related('category').prefetch_related(
                'hotspots',
                Prefetch('reviews', queryset=Review.objects.filter(is_deleted=False).select_related('from_user'))
            ).annotate(
                review_count=Count('reviews', filter=Q(reviews__is_deleted=False)),
                avg_rating=Avg('reviews__rating', filter=Q(reviews__is_deleted=False))
            ).first()

            if not listing:
                return None  # Will be cached as CACHE_NULL

            # Prepare hotspot IDs and names using prefetched hotspots
            hotspots = list(listing.hotspots.all())
            hotspot_ids = [h.id for h in hotspots]
            hotspot_names = [h.name for h in hotspots]

            # --- Reviews for this listing (prefetched) ---
            review_count = getattr(listing, 'review_count', 0) or 0
            avg_rating = getattr(listing, 'avg_rating', 0.0) or 0.0

            reviews_list = []
            for rev in list(listing.reviews.all()):
                reviews_list.append({
                    'from_user': rev.from_user.get_full_name() or rev.from_user.email,
                    'rating': rev.rating,
                    'comment': rev.comment or "",
                    'created_at': humanize_date(rev.created_at),
                })

            image_url = None
            if listing.image:
                image_url = request.build_absolute_uri(listing.image.url)

            return {
                'id': listing.id,
                'title': listing.title,
                'category': listing.category.name if listing.category else None,
                'category_icon': listing.category.icon if listing.category else None,
                'price': float(listing.price) if listing.price else 0,
                'description': listing.description or "",
                'status': listing.status,
                'badge': listing.badge or "",
                'is_hot_sale': listing.is_hot_sales,
                'is_ads_banner': listing.is_ads_banner,
                'auto_reactivate': listing.auto_reactivate,
                'lisiting_type': listing.listing_type,
                'hotspots': hotspot_ids,
                'hotspot_names': hotspot_names,
                'image': image_url,
                'created_at': humanize_date(listing.created_at),
                'modified_at': listing.modified_at.isoformat(),
                'expires_at': listing.expires_at.isoformat() if listing.expires_at else None,
                'editing_period_day': ConstantHelper.EDIT_DATE,
                'review_count': review_count,
                'avg_rating': float(avg_rating),
                'reviews': reviews_list,
            }

        try:
            data = GlobalCache.get_or_set(
                key=cache_key,
                callback=build_listing_detail_data,
                timeout=3600,
                lock_timeout=30,
                max_wait=5.0,
            )

            if data is None:
                return BaseResultWithData(
                    message="Listing not found.",
                    status_code=404
                )

            return BaseResultWithData(
                message="Listing detail retrieved successfully",
                data=data,
                status_code=200
            )

        except Exception as e:
            return BaseResultWithData(
                message=f"An error occurred: {str(e)}",
                status_code=500
            )
        
    @staticmethod
    def get_categorized_listings(request, user):
        section = request.GET.get('section')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 8))

        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1

        try:
            per_page = int(per_page)
        except (ValueError, TypeError):
            per_page = 8

        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100

        if section not in ['banner', 'hot_sales', 'departmental', 'for_you']:
            return BaseResultWithData(
                message='Invalid section parameter',
                status_code=400
            )

        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.CATEGORIZED_LISTINGS,
            user_id=user.id,
            section=section,
            page=page,
            per_page = per_page
        )

        def build_categorized_listings_data():
            """Heavy computation callback – runs only on cache miss."""
            base_qs = Listing.objects.filter(
                status=ListingStatusType.ACTIVE.value,
                is_deleted=False,
                user__is_active=True
            ).exclude(user__groups__name=GroupNames.ADMIN.value).select_related('user', 'category')
            base_qs = base_qs.prefetch_related('hotspots')

            if section == 'banner':
                qs = base_qs.filter(is_ads_banner=True)
            elif section == 'hot_sales':
                qs = base_qs.filter(is_hot_sales=True)
            elif section == 'departmental':
                if not user.department:
                    return {
                        'items': [],
                        'page': 1,
                        'per_page': per_page,
                        'total_pages': 0,
                        'total_items': 0
                    }
                qs = base_qs.filter(user__department__icontains=user.department)
            elif section == 'for_you':
                qs = base_qs.exclude(is_ads_banner=True).exclude(is_hot_sales=True)
                if user.department:
                    qs = qs.exclude(user__department__icontains=user.department)
            else:
                return {
                    'items': [],
                    'page': 1,
                    'per_page': per_page,
                    'total_pages': 0,
                    'total_items': 0
                }

            qs = qs.order_by('-created_at')

            paginator = Paginator(qs, per_page)
            page_obj = paginator.get_page(page)

            items = []
            for listing in page_obj:
                image_url = None
                if listing.image:
                    image_url = request.build_absolute_uri(listing.image.url)
                hotspots = list(listing.hotspots.all())
                items.append({
                    'id': listing.id,
                    'title': listing.title,
                    'price': float(listing.price) if listing.price else 0,
                    'category': listing.category.name if listing.category else '',
                    'image': image_url if listing.image else None,
                    'badge': listing.listing_type,
                    'hotspots': [h.name for h in hotspots]
                })

            return {
                'items': items,
                'page': page_obj.number,
                'per_page': per_page,
                'total_pages': page_obj.paginator.num_pages,
                'total_items': page_obj.paginator.count
            }

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_categorized_listings_data,
            timeout=600,           
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Categorized listings retrieved successfully",
            data=data,
            status_code=200
        )
    

    @staticmethod
    def listing_details(request, listing_id: int) -> BaseResultWithData:
        """
        Fetch public details of a listing for viewing by any user.
        Respects the seller's visibility setting.
        """
        if not listing_id:
            return BaseResultWithData(
                message="Listing ID is required.",
                status_code=400
            )

        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.PUBLIC_LISTING_DETAILS,
            user_id=request.user.id,
            listing_id=listing_id
        )

        def build_public_listing_details():
            """Heavy computation callback – runs only on cache miss."""
            listing = Listing.objects.filter(
                id=listing_id,
                is_deleted=False,
                status=ListingStatusType.ACTIVE.value
            ).select_related('user', 'category').prefetch_related(
                'hotspots',
                Prefetch('reviews', queryset=Review.objects.filter(is_deleted=False).select_related('from_user')),
                Prefetch('user__user_badges')
            ).annotate(
                review_count=Count('reviews', filter=Q(reviews__is_deleted=False)),
                avg_rating=Avg('reviews__rating', filter=Q(reviews__is_deleted=False))
            ).first()

            if not listing:
                return None  # Will be cached as CACHE_NULL

            seller = listing.user
            visibility = seller.visibility

            image_url = None
            if listing.image:
                image_url = request.build_absolute_uri(listing.image.url)

            hotspots = [h.name for h in list(listing.hotspots.all())]

            # ─── Reviews for this listing ──────────────────────────
            review_count = getattr(listing, 'review_count', 0) or 0
            avg_rating = getattr(listing, 'avg_rating', 0.0) or 0.0

            reviews_list = []
            for rev in list(listing.reviews.all()):
                reviews_list.append({
                    'from': rev.from_user.get_full_name() or rev.from_user.email,
                    'rating': rev.rating,
                    'comment': rev.comment or "",
                    'date': humanize_date(rev.created_at),
                })

            # ─── Seller information (with privacy) ──────────────────
            seller_data = {
                'id': seller.id,
                'name': seller.get_full_name() if visibility else None,
                'profile_picture': request.build_absolute_uri(seller.profile_picture.url) if seller.profile_picture and visibility else None,
                'phone': seller.phone if visibility else None,
                'department': seller.department if visibility else None,
                'level': seller.level if visibility else None,
                'matric_no': seller.matric_number if visibility else None,
                'member_since': seller.date_joined.year if seller.date_joined else None,
                'average_rating': float(seller.average_rating) if seller.average_rating else 0.0,
                'total_reviews': seller.reviews_received.filter(is_deleted=False).count(),
                'email_verified': seller.email_verified,
                'hall_verified': seller.hall_verified,
                'student_id_verified': seller.student_id_verified,
                'badges': [badge.name for badge in seller.user_badges.all()],
                'visibility': visibility,
                'is_owner': request.user.id == seller.id if request.user.is_authenticated else False,
            }

            # ─── Compute trust score ──────────────────────────────
            trust_score = round((float(seller.average_rating) / 5.0) * 100, 1) if seller.average_rating else 0.0
            seller_data['trust_score'] = trust_score

            # ─── Build response data ────────────────────────────────
            return {
                'id': listing.id,
                'title': listing.title,
                'description': listing.description or "",
                'price': float(listing.price) if listing.price else 0,
                'category': listing.category.name if listing.category else None,
                'badge': listing.badge or "",
                'listing_type': listing.listing_type,
                'is_hot_sale': listing.is_hot_sales,
                'location': hotspots[0] if hotspots else "Campus",
                'hotspots': hotspots,
                'image': image_url,
                'created_at': humanize_date(listing.created_at),
                'seller': seller_data,
                'reviews': reviews_list,
                'review_count': review_count,
                'avg_rating': float(avg_rating),
            }

        try:
            data = GlobalCache.get_or_set(
                key=cache_key,
                callback=build_public_listing_details,
                timeout=3600,
                lock_timeout=30,
                max_wait=5.0,
            )

            if data is None:
                return BaseResultWithData(
                    message="Listing not found or not available.",
                    status_code=404
                )

            return BaseResultWithData(
                message="Listing details retrieved successfully",
                data=data,
                status_code=200
            )

        except Exception as e:
            return BaseResultWithData(
                message=f"An error occurred: {str(e)}",
                status_code=500
            )