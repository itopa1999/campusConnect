from django.utils import timezone
from apps.campus.models import Listing
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum, GroupNamesEnum, ListingStatusTypeEnum


class IndexProductsQuery:
    @staticmethod
    def get_index_product(request, limit=6) -> BaseResultWithData:
        """Return the 6 most recent active listings for the homepage."""
        cache_key = CacheKeysEnum.INDEX_PRODUCTS.value

        def build_index_products_data():
            """Heavy computation callback – runs only on cache miss."""
            now = timezone.now()

            queryset = Listing.objects.filter(
                status=ListingStatusTypeEnum.ACTIVE.value,
                is_deleted=False,
                expires_at__gt=now,
                user__groups__name=GroupNamesEnum.ADMIN.value
            ).select_related('category', 'user').prefetch_related('hotspots').order_by('-created_at')[:limit]

            listings_data = []
            for listing in queryset:
                hotspots = list(listing.hotspots.all())
                location = hotspots[0].name if hotspots else "Campus"
                image_url = None
                if listing.image:
                    image_url = listing.image.url
                listings_data.append({
                    'id': listing.id,
                    'title': listing.title,
                    'price': float(listing.price) if listing.price else 0,
                    'category': listing.category.name,
                    'location': location,
                    'description': listing.description or "",
                    'badge': listing.badge,
                    'type': listing.listing_type,
                    'image': image_url
                })

            return {'listings': listings_data}

        # ── Atomic cache get-or-set with stampede protection ──
        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_index_products_data,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0, 
        )

        return BaseResultWithData(
            message="Index products retrieved successfully",
            data=data,
            status_code=200
        )