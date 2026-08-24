from asgiref.sync import sync_to_async
from apps.campus.models import Favourite, Listing, Review
from apps.campus.utils import get_listing_detail_info
from apps.users.models import User
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.constant_helper import ConstantHelper
from django.db.models import Avg, Count, Prefetch, Q
from utils.enums import CacheKeysEnum, GroupNamesEnum, ListingStatusTypeEnum, ListingTypeEnum
from utils.helpers import humanize_date
from django.core.paginator import Paginator
import asyncio


class ListingQuery:
    @staticmethod
    async def get_listing_detail(request, user: User, listing_id: int) -> BaseResultWithData:
        if not listing_id:
            return BaseResultWithData(
                message="Listing Id is required",
                status_code=400
            )

        cache_key = CacheKeysEnum.format(CacheKeysEnum.LISTING_DETAIL, user_id=user.id, listing_id=listing_id)

        @sync_to_async(thread_sensitive=False)
        def build_listing_detail_data():
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
                return None

            hotspots = list(listing.hotspots.all())
            hotspot_ids = [h.id for h in hotspots]
            hotspot_names = [h.name for h in hotspots]

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

            image_url = listing.image.url if listing.image else None

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
                'listing_type': listing.listing_type,
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
            data = await GlobalCache.aget_or_set(
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

        except asyncio.CancelledError:
            raise
        except Exception as e:
            return BaseResultWithData(
                message=f"An error occurred: {str(e)}",
                status_code=500
            )

    @staticmethod
    async def get_categorized_listings(request, user, filters=None) -> BaseResultWithData:
        if filters is None:
            filters = request.GET.dict() if request else {}
        else:
            filters = dict(filters)

        page = int(filters.get('page', 1))
        per_page = int(filters.get('per_page', 8))
        per_page = max(1, min(per_page, 100))

        raw_section = filters.get('section')
        if not raw_section:
            return BaseResultWithData(
                message='Missing section parameter',
                status_code=400
            )

        section = raw_section.lower()

        listing_type_values = [v.lower() for v in ListingTypeEnum.values()]
        valid_sections = listing_type_values + ['banner', 'departmental', 'search']
        if section not in valid_sections:
            return BaseResultWithData(
                message=f'Invalid section parameter: {raw_section}',
                status_code=400
            )

        if section == 'search':
            filter_keys = ['max_price', 'category_name', 'listing_type', 'search_query', 'condition', 'date_from', 'date_to']
            filter_parts = []
            for key in filter_keys:
                value = filters.get(key)
                if value is not None and value != '':
                    filter_parts.append(f"{key}={value}")
            filter_parts.sort()
            filter_str = '&'.join(filter_parts)
        else:
            filter_str = ''

        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.CATEGORIZED_LISTINGS,
            user_id=user.id,
            section=section,
            page=page if section != 'banner' else 1,
            per_page=per_page if section != 'banner' else 0,
            filters=filter_str
        )

        @sync_to_async(thread_sensitive=False)
        def build_categorized_listings_data():
            base_qs = Listing.objects.filter(
                status__iexact=ListingStatusTypeEnum.ACTIVE.value,
                is_deleted=False,
                user__is_active=True
            ).exclude(user__groups__name=GroupNamesEnum.ADMIN.value)
            base_qs = base_qs.select_related(
                'user',
                'sell_details',
                'sell_details__category',
                'service_details',
                'service_details__category',
                'accommodation_details'
            ).prefetch_related('hotspots')

            if section == 'banner':
                qs = base_qs.filter(is_ads_banner=True).order_by('-created_at')
                items = []
                for listing in qs:
                    image_url = listing.image.url if listing.image and request else None
                    price, category_name, category_icon = get_listing_detail_info(listing)
                    items.append({
                        'id': listing.id,
                        'title': listing.title,
                        'price': price,
                        'category': category_name,
                        'category_icon': category_icon,
                        'image': image_url,
                    })
                return {'items': items}

            listing_type_values = [v.lower() for v in ListingTypeEnum.values()]
            if section in listing_type_values:
                qs = base_qs.filter(listing_type__iexact=section)
            elif section == 'departmental':
                user_dept = getattr(user, 'department', None)
                if user_dept:
                    qs = base_qs.filter(user__department__icontains=user_dept)
                else:
                    qs = base_qs.none()
            elif section == 'search':
                qs = base_qs
                price = filters.get('max_price')
                if price is not None:
                    try:
                        max_price = float(price)
                        qs = qs.filter(
                            Q(sell_details__price__lte=max_price) |
                            Q(service_details__price__lte=max_price) |
                            Q(accommodation_details__rent_price__lte=max_price)
                        )
                    except ValueError:
                        pass

                category_name = filters.get('category_name')
                if category_name:
                    qs = qs.filter(
                        Q(sell_details__category__name__icontains=category_name) |
                        Q(service_details__category__name__icontains=category_name) |
                        Q(accommodation_details__property_type__icontains=category_name)
                    )

                condition = filters.get('condition')
                if condition:
                    qs = qs.filter(sell_details__condition__icontains=condition)

                search = filters.get('search_query')
                if search:
                    qs = qs.filter(
                        Q(title__icontains=search) |
                        Q(description__icontains=search)
                    )

                date_from = filters.get('date_from')
                if date_from:
                    qs = qs.filter(created_at__date__gte=date_from)
                date_to = filters.get('date_to')
                if date_to:
                    qs = qs.filter(created_at__date__lte=date_to)
            else:
                qs = base_qs.none()

            qs = qs.order_by('-created_at')
            paginator = Paginator(qs, per_page)
            page_obj = paginator.get_page(page)

            favourite_listing_ids = set()
            if request and hasattr(request, 'user') and request.user.is_authenticated:
                favourite_listing_ids = set(
                    Favourite.objects.filter(user=request.user)
                    .values_list("listing_id", flat=True)
                )

            listing_ids = [listing.id for listing in page_obj]
            if listing_ids:
                favourite_listing_ids = set(
                    Favourite.objects.filter(
                        user=request.user,
                        listing_id__in=listing_ids
                    ).values_list("listing_id", flat=True)
                )

            items = []
            for listing in page_obj:
                image_url = listing.image.url if listing.image and request else None
                price, category_name, category_icon = get_listing_detail_info(listing)
                hotspots = listing.hotspots.values_list("name", flat=True).first() or "Campus"
                items.append({
                    'id': listing.id,
                    'title': listing.title,
                    'price': price,
                    'category': {
                        'name': category_name,
                        'icon': category_icon,
                    },
                    'image': image_url,
                    'badge': listing.listing_type,
                    'hotspots': hotspots,
                    'is_hot_sales': listing.is_hot_sales,
                    'has_liked': listing.id in favourite_listing_ids
                })

            return {
                'items': items,
                'pagination': {
                    'page': page_obj.number,
                    'per_page': per_page,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                },
            }

        try:
            data = await GlobalCache.aget_or_set(
                key=cache_key,
                callback=build_categorized_listings_data,
                timeout=600,
                lock_timeout=30,
                max_wait=5.0,
            )
        except asyncio.CancelledError:
            raise

        return BaseResultWithData(
            message="Categorized listings retrieved successfully",
            data=data,
            status_code=200
        )

    @staticmethod
    async def listing_details(request, listing_id: int) -> BaseResultWithData:
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

        @sync_to_async(thread_sensitive=False)
        def build_public_listing_details():
            listing = Listing.objects.filter(
                id=listing_id,
                is_deleted=False,
                status__iexact=ListingStatusTypeEnum.ACTIVE.value
            ).exclude(
                user__groups__name=GroupNamesEnum.ADMIN.value
            ).select_related(
                'user',
                'sell_details',
                'sell_details__category',
                'sell_details__subcategory',
                'service_details',
                'service_details__category',
                'service_details__subcategory',
                'accommodation_details'
            ).prefetch_related(
                'hotspots',
                Prefetch('reviews', queryset=Review.objects.filter(is_deleted=False).select_related('from_user')),
                Prefetch('user__user_badges'),
            ).annotate(
                review_count=Count('reviews', filter=Q(reviews__is_deleted=False)),
                avg_rating=Avg('reviews__rating', filter=Q(reviews__is_deleted=False))
            ).first()

            if not listing:
                return None

            listing_type = listing.listing_type.lower()

            image_url = listing.image.url if listing.image else None
            hotspots = hotspots = [
                {
                    'name': h.name,
                    'description': h.description or "",
                }
                for h in listing.hotspots.all()
            ]

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

            seller = listing.user
            visibility = seller.visibility

            total_seller_reviews = Review.objects.filter(
                listing__user=seller,
                is_deleted=False
            ).count()

            seller_data = {
                'id': seller.id,
                'name': seller.get_full_name() if visibility else None,
                'profile_picture': seller.profile_picture.url if seller.profile_picture and visibility else None,
                'phone': seller.phone,
                'department': seller.department,
                'level': seller.level,
                'matric_no': seller.matric_number if visibility else None,
                'member_since': seller.date_joined.year if seller.date_joined else None,
                'average_rating': float(seller.average_rating) if seller.average_rating else 0.0,
                'total_reviews': total_seller_reviews,
                'email_verified': seller.email_verified,
                'hall_verified': seller.hall_verified,
                'student_id_verified': seller.student_id_verified,
                'badges': [badge.name for badge in seller.user_badges.all()],
                'visibility': visibility,
                'is_owner': request.user.id == seller.id if request.user.is_authenticated else False,
            }
            trust_score = round((float(seller.average_rating) / 5.0) * 100, 1) if seller.average_rating else 0.0
            seller_data['trust_score'] = trust_score

            details = {}

            if listing_type.lower() == ListingTypeEnum.SELL.value.lower():
                detail = getattr(listing, 'sell_details', None)
                if detail:
                    details = {
                        'price': float(detail.price) if detail.price else 0,
                        'negotiation': detail.negotiation,
                        'condition': detail.condition,
                        'brand': detail.brand,
                        'model': detail.model,
                        'quantity': detail.quantity,
                        'warranty': detail.warranty,
                        'category': {
                            'id': detail.category.id if detail.category else None,
                            'name': detail.category.name if detail.category else None,
                            'icon': detail.category.icon if detail.category else None,
                        } if detail.category else None,
                        'subcategory': {
                            'id': detail.subcategory.id if detail.subcategory else None,
                            'name': detail.subcategory.name if detail.subcategory else None,
                            'icon': detail.subcategory.icon if detail.subcategory else None,
                        } if detail.subcategory else None,
                    }

            elif listing_type.lower() == ListingTypeEnum.SERVICE.value.lower():
                detail = getattr(listing, 'service_details', None)
                if detail:
                    details = {
                        'price': float(detail.price) if detail.price else 0,
                        'negotiation': detail.negotiation,
                        'delivery_time': detail.delivery_time,
                        'service_duration': detail.service_duration,
                        'experience': detail.experience,
                        'portfolio': detail.portfolio,
                        'online_available': detail.online_available,
                        'category': {
                            'id': detail.category.id if detail.category else None,
                            'name': detail.category.name if detail.category else None,
                            'icon': detail.category.icon if detail.category else None,
                        } if detail.category else None,
                        'subcategory': {
                            'id': detail.subcategory.id if detail.subcategory else None,
                            'name': detail.subcategory.name if detail.subcategory else None,
                            'icon': detail.subcategory.icon if detail.subcategory else None,
                        } if detail.subcategory else None,
                    }

            elif listing_type.lower() == ListingTypeEnum.ACCOMMODATION.value.lower():
                detail = getattr(listing, 'accommodation_details', None)
                if detail:
                    details = {
                        'purpose': detail.purpose,
                        'property_type': detail.property_type,
                        'bedrooms': detail.bedrooms,
                        'bathrooms': detail.bathrooms,
                        'furnished': detail.furnished,
                        'rent_price': float(detail.rent_price) if detail.rent_price else 0,
                        'available_from': detail.available_from,
                        'lease_duration': detail.lease_duration,
                        'electricity': detail.electricity,
                        'water': detail.water,
                        'security': detail.security,
                        'parking': detail.parking,
                        'distance_to_campus': detail.distance_to_campus,
                        'preferred_gender': detail.preferred_gender,
                        'preferred_student_type': detail.preferred_student_type,
                        'max_occupants': detail.max_occupants,
                        'roommate_notes': detail.roommate_notes,
                    }

            else:
                details = {}

            return {
                'id': listing.id,
                'listing_type': listing.listing_type,
                'title': listing.title,
                'description': listing.description or "",
                'image': image_url,
                'hotspots': hotspots,
                'is_hot_sale': listing.is_hot_sales,
                'is_ads_banner': listing.is_ads_banner,
                'is_favourite': Favourite.objects.filter(user = request.user, listing = listing).exists(),
                'created_at': humanize_date(listing.created_at),
                'expires_at': listing.expires_at.isoformat() if listing.expires_at else None,
                'auto_reactivate': listing.auto_reactivate,
                'seller': seller_data,
                'details': details,
                'reviews': reviews_list,
                'review_count': review_count,
                'avg_rating': float(avg_rating),
                'negotiation': details.get('negotiation', False) if details else False,
            }

        try:
            data = await GlobalCache.aget_or_set(
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

        except asyncio.CancelledError:
            raise
        except Exception as e:
            return BaseResultWithData(
                message=f"An error occurred: {str(e)}",
                status_code=500
            )