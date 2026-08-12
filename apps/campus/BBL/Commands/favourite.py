from apps.campus.models import Favourite, Listing
from apps.users.models import User
from utils.base_result import BaseResultWithData
from utils.enums import NotificationEnum
from utils.helpers import create_notification
from utils.log_helpers import OperationLogger
from django.db import transaction
from django.utils import timezone

class FavouriteCommand:
    @staticmethod
    def toggle_favourite(user: User, listing_id: int) -> BaseResultWithData:
        """
        Toggle favourite status for a listing.
        - If active favourite exists → soft delete it (unfavourite)
        - If soft-deleted favourite exists → restore it (favourite again)
        - Otherwise → create a new favourite
        """
        op = OperationLogger(f"ListingCommand.toggle_favourite for user: {user.email}", data={'listing_id': listing_id})
        op.start()

        try:
            listing = Listing.objects.get(id=listing_id, is_deleted=False)
        except Listing.DoesNotExist:
            op.fail(f"Listing not found: {listing_id}")
            return BaseResultWithData(
                message="Listing not found.",
                status_code=404
            )

        existing_favourite = Favourite.objects.all_including_deleted().filter(
            user=user,
            listing=listing
        ).first()

        with transaction.atomic():
            if existing_favourite:
                if existing_favourite.is_deleted:
                    existing_favourite.is_deleted = False
                    existing_favourite.save(update_fields=['is_deleted'])
                    action = 'added'
                    message = "Listing added to favourites."
                else:
                    existing_favourite.is_deleted = True
                    existing_favourite.save(update_fields=['is_deleted'])
                    action = 'removed'
                    message = "Listing removed from favourites."
            else:
                Favourite.objects.create(
                    user=user,
                    listing=listing
                )
                action = 'added'
                message = "Listing added to favourites."

        favourites_count = Favourite.objects.filter(user=user, is_deleted=False).count()

        create_notification(
            user=user,
            notification_type=NotificationEnum.LISTING.value,
            title="Favourite Updated",
            message=f"Your favourite status for '{listing.title}' has been {action}.",
            action_url="/student/favourites.html"
        )

        op.success(f"Favourite {action} for listing {listing_id} by user {user.email}")
        return BaseResultWithData(
            message=message,
            data={
                'listing_id': listing_id,
                'action': action,
                'favourites_count': favourites_count,
                'notification': True
            },
            status_code=200
        )