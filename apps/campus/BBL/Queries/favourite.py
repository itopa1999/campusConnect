
from apps.campus.models import Favourite
from utils.base_result import BaseResultWithData
from django.core.paginator import Paginator
from django.db.models import Q
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum

class FavouriteQuery:
    @staticmethod
    def get_favourites(request, filters = None) -> BaseResultWithData:
        """
        Retrieve paginated favourites for the current user.
        Each item includes: id, title, price, category, image (absolute URL), badge, hotspots.
        """
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

        # --- Build cache key (filters only for search) ---
        filter_keys = ['price', 'category_name', 'listing_type', 'search', 'badge', 'date_from', 'date_to']
        filter_values = []
        for key in filter_keys:
            value = filters.get(key)
            if value is not None:
                filter_values.append((key, value.strip() if isinstance(value, str) else value))
        filter_values.sort(key=lambda x: x[0])
        filter_str = '&'.join(f"{k}={v}" for k, v in filter_values)

        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.FAVOURITE,
            user_id = user.id,
            page=page,
            per_page=per_page,
            filters=filter_str
        )
        
        def build_favourites_data():
            favourites_qs = Favourite.objects.select_related(
                'listing', 'listing__category'
            ).filter(
                user=user,
                is_deleted=False,
                listing__is_deleted=False
            ).order_by('-created_at')

            price = filters.get('price')
            if price is not None:
                try:
                    max_price = float(price)
                    favourites_qs = favourites_qs.filter(listing__price__lte=max_price)
                except ValueError:
                    pass

            category_name = filters.get('category_name')
            if category_name:
                favourites_qs = favourites_qs.filter(listing__category__name__icontains=category_name)

            listing_type = filters.get('listing_type')
            if listing_type:
                favourites_qs = favourites_qs.filter(listing__listing_type__icontains=listing_type)

            search = filters.get('search')
            if search:
                favourites_qs = favourites_qs.filter(
                    Q(listing__title__icontains=search) |
                    Q(listing__description__icontains=search)
                )

            badge = filters.get('badge')
            if badge:
                qs = favourites_qs.filter(listing__badge__icontains=badge)

            date_from = filters.get('date_from')
            if date_from:
                qs = qs.filter(created_at__gte=date_from)
            date_to = filters.get('date_to')
            if date_to:
                qs = qs.filter(created_at__lte=date_to)

            paginator = Paginator(favourites_qs, per_page)
            page_obj = paginator.get_page(page)

            items = []
            for fav in page_obj:
                listing = fav.listing
                image_url = None
                if listing.image:
                    if request:
                        image_url = request.build_absolute_uri(listing.image.url)
                    else:
                        image_url = listing.image.url

                hotspot_name = listing.hotspots.values_list('name', flat=True).first()
                hotspots = hotspot_name or "Campus"

                items.append({
                    'id': listing.id,
                    'title': listing.title,
                    'price': float(listing.price) if listing.price is not None else 0.0,
                    'category': listing.category.name if listing.category else '',
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

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_favourites_data,
            timeout=600,
            lock_timeout=30,
            max_wait=5.0,
        )
        return BaseResultWithData(
            message="Favourites retrieved successfully",
            data=data,
            status_code=200
        )