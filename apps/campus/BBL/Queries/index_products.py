from django.utils import timezone
from apps.campus.models import Listing
from utils.base_result import BaseResultWithData
from utils.enums import ListingStatusType

class IndexProductsQuery:
    @staticmethod
    def get_index_product(request, limit=6):
        """Return the 6 most recent active listings for the homepage."""
        now = timezone.now()

        queryset = Listing.objects.filter(
            status=ListingStatusType.ACTIVE.value,
            is_deleted=False,
            expires_at__gt=now
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

        return BaseResultWithData(
            message="Index products retrieved successfully",
            data={'listings': listings_data},
            status_code=200
        )