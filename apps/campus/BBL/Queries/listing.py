from apps.campus.models import Listing
from apps.users.models import User
from utils.base_result import BaseResultWithData
from utils.helpers import UpdatePointsService
from utils.log_helpers import OperationLogger


class GetListingDetailQuery:
    @staticmethod
    def get_listing_detail(user: User, listing_id: int) -> BaseResultWithData:
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

            points = UpdatePointsService.check_points(user)


            data = {
                'id': listing.id,
                'title': listing.title,
                'category': listing.category.name if listing.category else None,
                'category_icon': listing.category.icon if listing.category else None,
                'price': float(listing.price) if listing.price else 0,
                'description': listing.description or "",
                'status': listing.status,
                'badge': listing.badge or "",
                'lisiting_type': listing.listing_type,
                'hotspots': hotspot_ids,
                'hotspot_names': hotspot_names,
                'image': listing.image.url if listing.image else None,
                'created_at': listing.created_at.isoformat(),
                'modified_at': listing.modified_at.isoformat(),
                'expires_at': listing.expires_at.isoformat() if listing.expires_at else None,
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