from asgiref.sync import sync_to_async
from apps.campus.models import Favourite
from apps.campus.utils import get_listing_detail_info
from utils.base_result import BaseResultWithData
from django.core.paginator import Paginator
from django.db.models import Q
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum
import asyncio

class FavouriteQuery:
    @staticmethod
    async def get_favourites(request, filters=None) -> BaseResultWithData:
        user = request.user

        if filters is None:
            filters = request.GET.dict()
        else:
            filters = dict(filters)

        page = int(filters.get('page', 1))
        per_page = int(filters.get('per_page', 10))
        page = max(1, page)
        per_page = max(1, min(100, per_page))

        filter_keys = ['search']
        filter_values = []
        for key in filter_keys:
            value = filters.get(key)
            if value is not None:
                filter_values.append((key, value.strip() if isinstance(value, str) else value))
        filter_values.sort(key=lambda x: x[0])
        filter_str = '&'.join(f"{k}={v}" for k, v in filter_values)

        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.FAVOURITE,
            user_id=user.id,
            page=page,
            per_page=per_page,
            filters=filter_str
        )
        
        @sync_to_async
        def build_favourites_data():
            favourites_qs = Favourite.objects.select_related(
                'listing',
                'listing__sell_details',
                'listing__sell_details__category',
                'listing__service_details',
                'listing__service_details__category',
                'listing__accommodation_details',
            ).filter(
                user=user,
                is_deleted=False,
                listing__is_deleted=False
            ).order_by('-created_at')

            search = filters.get('search')
            if search:
                favourites_qs = favourites_qs.filter(
                    Q(listing__title__icontains=search) |
                    Q(listing__description__icontains=search)
                )

            paginator = Paginator(favourites_qs, per_page)
            page_obj = paginator.get_page(page)

            items = []
            for fav in page_obj:
                listing = fav.listing
                image_url = listing.image.url if listing.image else None

                hotspot_name = listing.hotspots.values_list('name', flat=True).first()
                hotspots = hotspot_name or "Campus"

                price, category_name, category_icon = get_listing_detail_info(listing)

                items.append({
                    'id': listing.id,
                    'title': listing.title,
                    'price': price,
                    'category': {
                        'name': category_name,
                        'icon': category_icon
                    },
                    'image': image_url,
                    'badge': listing.listing_type,
                    'hotspots': hotspots,
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
                callback=build_favourites_data,
                timeout=600,
                lock_timeout=30,
                max_wait=5.0,
            )
        except asyncio.CancelledError:
            raise

        return BaseResultWithData(
            message="Favourites retrieved successfully",
            data=data,
            status_code=200
        )