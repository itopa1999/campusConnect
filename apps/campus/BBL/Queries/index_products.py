from django.utils import timezone
from apps.campus.models import Listing
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum, GroupNames, ListingStatusType

class IndexProductsQuery:
    @staticmethod
    def get_index_product(request, limit=6):
        """Return the 6 most recent active listings for the homepage."""
        cache_key = CacheKeysEnum.INDEX_PRODUCTS.value
        cached_data = GlobalCache.get(cache_key)
        if cached_data:
            return BaseResultWithData(
                message="Index products retrieved successfully",
                data=cached_data,
                status_code=200
            )
        
        now = timezone.now()

        queryset = Listing.objects.filter(
            status=ListingStatusType.ACTIVE.value,
            is_deleted=False,
            expires_at__gt=now,
            user__groups__name=GroupNames.ADMIN.value
        ).select_related('category', 'user').prefetch_related('hotspots').order_by('-created_at')[:limit]

        listings_data = []
        for listing in queryset:
            location = listing.hotspots.first().name if listing.hotspots.exists() else "Campus"
            image_url = None
            if listing.image:
                image_url = request.build_absolute_uri(listing.image.url)
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

        data = {'listings': listings_data}
        
        GlobalCache.set(cache_key, data)

        return BaseResultWithData(
            message="Index products retrieved successfully",
            data=data,
            status_code=200
        )