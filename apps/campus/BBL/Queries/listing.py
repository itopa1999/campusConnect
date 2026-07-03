from apps.campus.models import Listing
from apps.users.models import User
from utils.base_result import BaseResultWithData
from utils.constant_helper import ConstantHelper
from django.db.models import Avg, Count

class GetListingDetailQuery:
    @staticmethod
    def get_listing_detail(request, user: User, listing_id: int) -> BaseResultWithData:
        """
        Fetch full details of a listing owned by the user.
        """

        if not listing_id:
            return BaseResultWithData(
                    message="Listing Id is reqired",
                    status_code=400
                )
        
        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).select_related('category').prefetch_related('hotspots').first()

            if not listing:
                return BaseResultWithData(
                    message="Listing not found.",
                    status_code=404
                )

            # Prepare hotspot IDs and names
            hotspot_ids = list(listing.hotspots.values_list('id', flat=True))
            hotspot_names = list(listing.hotspots.values_list('name', flat=True))

            # --- Reviews for this listing (only active, not deleted) ---
            reviews_qs = listing.reviews.filter(is_deleted=False).select_related('from_user')
            review_stats = reviews_qs.aggregate(
                review_count=Count('id'),
                avg_rating=Avg('rating')
            )
            review_count = review_stats['review_count'] or 0
            avg_rating = review_stats['avg_rating'] or 0.0

            reviews_list = []
            for rev in reviews_qs:
                reviews_list.append({
                    'from_user': rev.from_user.get_full_name() or rev.from_user.email,
                    'rating': rev.rating,
                    'comment': rev.comment or "",
                    'created_at': rev.created_at.isoformat(),
                })

            image_url = None
            if listing.image:
                image_url = request.build_absolute_uri(listing.image.url)

            data = {
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
                'created_at': listing.created_at.isoformat(),
                'modified_at': listing.modified_at.isoformat(),
                'expires_at': listing.expires_at.isoformat() if listing.expires_at else None,
                'editing_period_day': ConstantHelper.EDIT_DATE,
                'review_count': review_count,
                'avg_rating': float(avg_rating),
                'reviews': reviews_list,
            }

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