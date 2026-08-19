from django.utils import timezone
import json
from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from apps.campus.models import CampusHotspot, Category, Listing, SubCategory
from apps.campus.serializers import ListingSerializer
from apps.users.models import User
from utils.base_result import BaseResultWithData
from utils.constant_helper import ConstantHelper
from utils.enums import AdvertTypeEnum, BadgeChoiceEnum, ListingStatusTypeEnum, NotificationEnum, PointTransactionTypeEnum
from utils.helpers import BadgeService, UpdatePointsService, create_notification, parse_bool
from utils.log_helpers import OperationLogger
from PIL import Image
from django.core.files.storage import default_storage

class ListingCommand:
    @staticmethod
    def create_listing(user: User, data: dict) -> BaseResultWithData:
        op = OperationLogger(f"ListingCommand.create_listing for user: {user.first_name or user.email}", data=data)
        op.start()

        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = dict(data)

        if data.get('image') == '':
            data.pop('image', None)

        # --- 1. Points check ---
        is_banner = parse_bool(data.get('is_ads_banner', False))
        is_hot = parse_bool(data.get('is_hot_sales', False))
        base_points = ConstantHelper.BASE_POINT
        banner_points = AdvertTypeEnum.BANNER.points if is_banner else 0
        hot_points = AdvertTypeEnum.HOT_SALE.points if is_hot else 0
        total_points_needed = base_points + banner_points + hot_points

        current_points = UpdatePointsService.check_points(user)
        if current_points < total_points_needed:
            op.fail(f"Insufficient points for listing: {data.get('title')}")
            return BaseResultWithData(
                message=f"Insufficient points. You need at least {ConstantHelper.BASE_POINT} point to post.",
                status_code=400
            )

        # --- 2. Hotspots validation ---
        hotspot_ids = data.get('hotspot_ids')
        if isinstance(hotspot_ids, str):
            try:
                hotspot_ids = json.loads(hotspot_ids)
            except json.JSONDecodeError:
                hotspot_ids = None

        if not hotspot_ids or not isinstance(hotspot_ids, list) or len(hotspot_ids) == 0:
            op.fail(f"No meeting spots selected for listing: {data.get('title')}")
            return BaseResultWithData(
                message="Please select at least one meeting spot.",
                status_code=400
            )

        # Validate all hotspots exist
        existing_hotspots = CampusHotspot.objects.filter(id__in=hotspot_ids, is_deleted=False)
        if existing_hotspots.count() != len(hotspot_ids):
            op.fail(f"Invalid hotspot IDs for listing: {data.get('title')}")
            return BaseResultWithData(
                message="One or more meeting spots are invalid.",
                status_code=400
            )

        data['hotspots'] = hotspot_ids
        data.pop('hotspot_ids', None)

        # --- 3. Image validation ---
        image = data.get('image')
        if image:
            if image.size > ConstantHelper.IMAGE_SIZE:
                op.fail(f"Image too large for listing: {data.get('title')}")
                return BaseResultWithData(
                    message=f"Image file size must not exceed {ConstantHelper.IMAGE_SIZE} MB.",
                    status_code=400
                )
            allowed_extensions = ('.jpg', '.jpeg', '.png', '.webp')
            if not image.name.lower().endswith(allowed_extensions):
                op.fail(f"Invalid image format for listing: {data.get('title')}")
                return BaseResultWithData(
                    message="Only JPG, PNG, and WEBP images are allowed.",
                    status_code=400
                )

        # --- 4. Category validation (if provided) ---
        category_id = data.get('category')
        if category_id:
            try:
                category = Category.objects.get(id=category_id, is_deleted=False)
            except Category.DoesNotExist:
                op.fail(f"Invalid category ID: {category_id}")
                return BaseResultWithData(
                    message="Selected category does not exist.",
                    status_code=400
                )
            # Validate category listing_type matches? optional

        # --- 5. Subcategory validation (if provided) ---
        subcategory_id = data.get('subcategory')
        if subcategory_id:
            try:
                subcategory = SubCategory.objects.get(id=subcategory_id, is_deleted=False)
            except SubCategory.DoesNotExist:
                op.fail(f"Subcategory not found: {subcategory_id}")
                return BaseResultWithData(
                    message="Selected subcategory does not exist.",
                    status_code=400
                )
            # Ensure subcategory belongs to category (if category provided)
            if category_id and int(subcategory.category_id) != int(category_id):
                op.fail(f"Subcategory {subcategory_id} does not belong to category {category_id}")
                return BaseResultWithData(
                    message="The selected subcategory does not belong to the selected category.",
                    status_code=400
                )

        # --- 6. Serializer validation and creation ---
        serializer = ListingSerializer(data=data, context={'user': user})
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            op.fail(f"Listing: {data.get('title')}, Serializer validation failed", exc={'errors': e.detail})
            return BaseResultWithData(
                message="Validation failed.",
                data={'errors': e.detail},
                status_code=400
            )

        try:
            with transaction.atomic():
                listing = serializer.save(user=user)
                UpdatePointsService.update_points(
                    user=user,
                    points=total_points_needed,
                    action=ConstantHelper.POINT_SUBTRACTION,
                    transaction_type=PointTransactionTypeEnum.LISTING_CREATION.value,
                    description=f"Created listing: {listing.title}",
                    reference=f"listing_{listing.id}"
                )

                create_notification(
                    user=user,
                    notification_type=NotificationEnum.LISTING.value,
                    title="Listing Created",
                    message=f"Your listing '{listing.title}' has been successfully created.",
                    action_url=f"/student/my-listing-details.html?id={listing.id}&title={listing.title}"
                )

                op.success(f"Listing created: {listing.id} for user: {user.first_name or user.email}")
                return BaseResultWithData(
                    message="Listing created successfully, It will appear in the marketplace once approved",
                    data={'listing_id': listing.id, 'notification': True},
                    status_code=201
                )
        except Exception as e:
            op.fail(f"Listing: {data.get('title')} Unexpected error during creation", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )

    @staticmethod
    def update_listing(user: User, listing_id: int, data: dict, partial: bool = False) -> BaseResultWithData:
        op = OperationLogger(f"UpdateListingCommand.update_listing for user: {user.first_name or user.email}", data={'listing_id': listing_id, **data})
        op.start()

        if listing_id is None:
            op.fail(f"user: {user.first_name or user.email} Listing ID is required")
            return BaseResultWithData(
                message="Listing ID is required.",
                status_code=400
            )

        try:
            listing = Listing.objects.filter(id=listing_id, user=user, is_deleted=False).first()
            if not listing:
                op.fail(f"Listing not found for listing: {listing_id}")
                return BaseResultWithData(
                    message="Listing not found",
                    status_code=404
                )

            # Edit restriction (optional)
            if ConstantHelper.EDIT_DATE > 0 and data and listing.modified_at:
                days_since = (timezone.now() - listing.modified_at).days
                if days_since < ConstantHelper.EDIT_DATE:
                    op.fail(f"Edit restriction for listing: {listing.title}")
                    return BaseResultWithData(
                        message=f"You can only edit this listing once every {ConstantHelper.EDIT_DATE} days. Last edit was {listing.modified_at.strftime('%Y-%m-%d')}.",
                        status_code=400
                    )

            hotspot_ids = data.get('hotspots')
            if hotspot_ids is not None:
                if isinstance(hotspot_ids, str):
                    try:
                        hotspot_ids = json.loads(hotspot_ids)
                    except json.JSONDecodeError:
                        hotspot_ids = None
                if not hotspot_ids or not isinstance(hotspot_ids, list) or len(hotspot_ids) == 0:
                    op.fail(f"No meeting spots selected for listing: {listing.title}")
                    return BaseResultWithData(
                        message="Please select at least one meeting spot.",
                        status_code=400
                    )
                existing_hotspots = CampusHotspot.objects.filter(id__in=hotspot_ids, is_deleted=False)
                if existing_hotspots.count() != len(hotspot_ids):
                    op.fail(f"Invalid hotspot IDs for listing: {listing.title}")
                    return BaseResultWithData(
                        message="One or more meeting spots are invalid.",
                        status_code=400
                    )
            else:
                pass

            category_id = data.get('category')
            if category_id:
                try:
                    Category.objects.get(id=category_id, is_deleted=False)
                except Category.DoesNotExist:
                    op.fail(f"Invalid category ID: {category_id}")
                    return BaseResultWithData(
                        message="Selected category does not exist.",
                        status_code=400
                    )

            subcategory_id = data.get('subcategory')
            if subcategory_id:
                try:
                    subcategory = SubCategory.objects.get(id=subcategory_id, is_deleted=False)
                except SubCategory.DoesNotExist:
                    op.fail(f"Subcategory not found: {subcategory_id}")
                    return BaseResultWithData(
                        message="Selected subcategory does not exist.",
                        status_code=400
                    )
                if category_id and subcategory.category_id != int(category_id):
                    op.fail(f"Subcategory {subcategory_id} does not belong to category {category_id}")
                    return BaseResultWithData(
                        message="The selected subcategory does not belong to the selected category.",
                        status_code=400
                    )

            # --- Pass to serializer ---
            serializer = ListingSerializer(listing, data=data, partial=True, context={'user': user})
            try:
                serializer.is_valid(raise_exception=True)
            except serializers.ValidationError as e:
                op.fail(f"Listing: {listing.title}, Serializer validation failed", exc={'errors': e.detail})
                return BaseResultWithData(
                    message="Validation failed.",
                    data={'errors': e.detail},
                    status_code=400
                )

            with transaction.atomic():
                updated_listing = serializer.save()
                # Notify user
                create_notification(
                    user=user,
                    notification_type=NotificationEnum.LISTING.value,
                    title="Listing Updated",
                    message=f"Your listing '{updated_listing.title}' has been successfully Updated.",
                    action_url=f"/student/my-listing-details.html?id={updated_listing.id}&title={updated_listing.title}"
                )

                op.success(f"Listing: {listing_id} updated for user: {user.first_name or user.email}")
                return BaseResultWithData(
                    message="Listing updated successfully.",
                    data={'id': updated_listing.id, 'notification': True},
                    status_code=200
                )

        except Exception as e:
            op.fail(f"Listing: {listing_id}: Unexpected error", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
                
    
    @staticmethod
    def delete_listing(user: User, listing_id: int) -> BaseResultWithData:
        op = OperationLogger(f"DeleteListingCommand.delete_listing for user: {user.first_name or user.email}", data={'listing_id': listing_id})
        op.start()

        if listing_id is None:
            op.fail(f"user: {user.first_name or user.email} Listing ID is required")
            return BaseResultWithData(
                message="Listing ID is required.",
                status_code=400
            )

        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).first()

            if not listing:
                op.fail(f"Listing not found for listing: {listing_id}")
                return BaseResultWithData(
                    message="Listing not found",
                    status_code=404
                )

            with transaction.atomic():
                listing.is_deleted = True
                listing.save(update_fields=['is_deleted'])

                create_notification(
                    user=user,
                    notification_type=NotificationEnum.LISTING.value,
                    title="Listing Deleted",
                    message=f"Your listing '{listing.title}' has been successfully Deleted.",
                    action_url=f"/student/my-listing-details.html?id={listing.id}&title={listing.title}"
                )

            op.success(f"Listing: {listing_id} deleted for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Listing deleted successfully.",
                data = {'notification': True},
                status_code=200
            )

        except Exception as e:
            op.fail(f"Unexpected error for listing: {listing_id}", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        
    
    @staticmethod
    def reactivate_listing(user: User, listing_id: int) -> BaseResultWithData:
        op = OperationLogger(f"ReactivateListingCommand.reactivate_listing for user: {user.first_name or user.email}", data={'listing_id': listing_id})
        op.start()

        if listing_id is None:
            op.fail(f"user: {user.first_name or user.email}: Listing ID is required")
            return BaseResultWithData(
                message="Listing ID is required.",
                status_code=400
            )

        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).first()

            if not listing:
                op.fail(f"Listing not found for listing: {listing_id}")
                return BaseResultWithData(
                    message="Listing not found",
                    status_code=404
                )

            if listing.status.lower() != ListingStatusTypeEnum.SOLD.value.lower() and listing.status.lower() != ListingStatusTypeEnum.EXPIRED.value.lower():
                op.fail(f"Invalid status for listing: {listing.title}")
                return BaseResultWithData(
                    message="Only sold or expired listings can be reactivated.",
                    status_code=400
                )

            # Check points
            points = UpdatePointsService.check_points(user)
            if points < ConstantHelper.BASE_POINT:
                op.fail(f"Insufficient points for listing: {listing.title}")
                return BaseResultWithData(
                    message=f"Insufficient points. You need {ConstantHelper.BASE_POINT} point to reactivate.",
                    status_code=400
                )

            with transaction.atomic():
                listing.status = ListingStatusTypeEnum.ACTIVE.value
                listing.expires_at = None
                listing.save(update_fields=['status', 'expires_at'])

                UpdatePointsService.update_points(
                    user=user,
                    points=ConstantHelper.BASE_POINT,
                    action=ConstantHelper.POINT_SUBTRACTION,
                    transaction_type=PointTransactionTypeEnum.REACTIVATION.value,
                    description=f"Reactivated listing: {listing.title}",
                    reference=f"listing_{listing_id}"
                )

                create_notification(
                    user=user,
                    notification_type=NotificationEnum.LISTING.value,
                    title="Reactivated listing",
                    message=f"Your listing '{listing.title}' has been reactivated successfully.",
                    action_url=f"/student/my-listing-details.html?id={listing.id}&title={listing.title}"
                )

            op.success(f"Listing: {listing_id} reactivated for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Listing reactivated successfully.",
                data={'id': listing.id, 'notification': True},
                status_code=200
            )

        except Exception as e:
            op.fail(f"Unexpected error for listing ID: {listing_id}", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        
    
    @staticmethod
    def mark_sold(user: User, listing_id: int) -> BaseResultWithData:
        op = OperationLogger(f"ReactivateListingCommand.mark_sold for user: {user.first_name or user.email}", data={'listing_id': listing_id})
        op.start()

        if listing_id is None:
            op.fail(f"user: {user.first_name or user.email}: Listing ID is required")
            return BaseResultWithData(
                message="Listing ID is required.",
                status_code=400
            )

        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).first()

            if not listing:
                op.fail(f"Listing not found for listing ID: {listing_id}")
                return BaseResultWithData(
                    message="Listing not found",
                    status_code=404
                )
            
            with transaction.atomic():
                listing.status = ListingStatusTypeEnum.SOLD.value
                listing.save(update_fields=['status'])

                user.sold_items += 1
                user.save(update_fields=['sold_items'])

                if user.sold_items >= ConstantHelper.SOLD_ITEMS_COUNT_FOR_TOP_SELLER_BADGE:
                    BadgeService.add(
                        user,
                        BadgeChoiceEnum.TOP_SELLER.value
                    )

                create_notification(
                    user=user,
                    notification_type=NotificationEnum.LISTING.value,
                    title="Listing status changed",
                    message=f"Your listing '{listing.title}' has been mark as sold successfully.",
                    action_url=f"/student/my-listing-details.html?id={listing.id}&title={listing.title}"
                )

            op.success(f"Listing: {listing_id} mark as sold for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Listing mark as sold successfully.",
                data={'id': listing.id, 'notification': True},
                status_code=200
            )

        except Exception as e:
            op.fail(f"Unexpected error for listing ID: {listing_id}", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        
    
    @staticmethod
    def image_upload(user: User, listing_id: int, image_file) -> BaseResultWithData:
        op = OperationLogger(f"ListingCommand.image_upload for user: {user.first_name or user.email}", data={'listing_id': listing_id})
        op.start()

        if listing_id is None:
            op.fail(f"user: {user.first_name or user.email}: Listing ID is required")
            return BaseResultWithData(
                message="Listing ID is required.",
                status_code=400
            )

        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).first()

            if not listing:
                op.fail(f"Listing not found for listing ID: {listing_id}")
                return BaseResultWithData(
                    message="Listing not found.",
                    status_code=404
                )

            # Validate image (size, extension)
            if image_file.size > ConstantHelper.IMAGE_SIZE:
                op.fail(f"Image too large for listing: {listing.title}")
                return BaseResultWithData(
                    message=f"Image size must not exceed {ConstantHelper.IMAGE_SIZE} MB.",
                    status_code=400
                )
            allowed_extensions = ('.jpg', '.jpeg', '.png', '.webp')
            if not image_file.name.lower().endswith(allowed_extensions):
                op.fail(f"Invalid image format for listing: {listing.title}")
                return BaseResultWithData(
                    message="Only JPG, PNG, and WEBP images are allowed.",
                    status_code=400
                )
            
            try:
                img = Image.open(image_file)
                img.verify()
                image_file.seek(0)
            except Exception:
                op.fail(f"Invalid image file for listing: {listing.title}")
                return BaseResultWithData(
                    message="The uploaded file is not a valid image.",
                    status_code=400
                )

            with transaction.atomic():
                if listing.image and listing.image.name:
                    try:
                        listing.image.delete(save=False)
                    except Exception as e:
                        op.fail(f"Could not delete old picture for listing: {listing.title}: {e}")
                        return BaseResultWithData(
                            message="Could not remove the previous listing picture.",
                            status_code=500
                        )
                listing.image = image_file
                listing.save(update_fields=['image'])

            op.success(f"Image uploaded for listing: {listing_id}, user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Image uploaded successfully.",
                data={'id': listing.id},
                status_code=200
            )

        except Exception as e:
            op.fail(f"Unexpected error for listing ID: {listing_id}", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )


    @staticmethod
    def update_ads(user: User, listing_id: int, data: dict, partial: bool = False) -> BaseResultWithData:
        op = OperationLogger(f"UpdateListingCommand.update_ads for user: {user.first_name or user.email}", data={'listing_id': listing_id, **data})
        op.start()

        if listing_id is None:
            op.fail(f"user: {user.first_name or user.email}: Listing ID is required")
            return BaseResultWithData(
                message="Listing ID is required.",
                status_code=400
            )

        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).first()

            if not listing:
                op.fail(f"Listing not found for listing ID: {listing_id}")
                return BaseResultWithData(
                    message="Listing not found",
                    status_code=404
                )

            updating_banner = 'is_ads_banner' in data
            updating_hot = 'is_hot_sales' in data

            if not updating_banner and not updating_hot:
                op.fail(f"No valid fields to update for listing: {listing.title}")
                return BaseResultWithData(
                    message="No valid fields to update. Provide 'is_ads_banner' or 'is_hot_sales'.",
                    status_code=400
                )
            
            if listing.status.lower() != ListingStatusTypeEnum.ACTIVE.value.lower():
                op.fail(f"Invalid listing status for listing: {listing.title}")
                return BaseResultWithData(
                    message="Ads can only be set for active listings.",
                    status_code=400
                )

            with transaction.atomic():
                total_points_to_deduct = 0
                update_fields = []
                description_parts = []

                # Handle banner update
                if updating_banner:
                    new_banner_value = parse_bool(data['is_ads_banner'])
                    
                    if new_banner_value and not listing.is_ads_banner:
                        points_needed = AdvertTypeEnum.BANNER.points
                        current_points = UpdatePointsService.check_points(user)
                        
                        if current_points < points_needed:
                            op.fail(f"Insufficient points for banner for listing: {listing.title}")
                            return BaseResultWithData(
                                message=f"Insufficient points. You need {points_needed} points to enable banner.",
                                status_code=400
                            )
                        
                        total_points_to_deduct += points_needed
                        description_parts.append("banner enabled")
                    
                    listing.is_ads_banner = new_banner_value
                    update_fields.append('is_ads_banner')

                # Handle hot sales update
                if updating_hot:
                    new_hot_value = parse_bool(data['is_hot_sales'])
                    
                    # Only deduct points if enabling hot sales (not disabling)
                    if new_hot_value and not listing.is_hot_sales:
                        points_needed = AdvertTypeEnum.HOT_SALE.points
                        current_points = UpdatePointsService.check_points(user)
                        
                        if current_points < points_needed:
                            op.fail(f"Insufficient points for hot sales for listing: {listing.title}")
                            return BaseResultWithData(
                                message=f"Insufficient points. You need {points_needed} points to enable hot sales.",
                                status_code=400
                            )
                        
                        total_points_to_deduct += points_needed
                        description_parts.append("hot sales enabled")
                    
                    listing.is_hot_sales = new_hot_value
                    update_fields.append('is_hot_sales')

                # Save the listing
                listing.save(update_fields=update_fields)

                # Deduct points if any
                if total_points_to_deduct > 0:
                    UpdatePointsService.update_points(
                        user=user,
                        points=total_points_to_deduct,
                        action=ConstantHelper.POINT_SUBTRACTION,
                        transaction_type=PointTransactionTypeEnum.LISTING_UPDATE.value,
                        description=f"{listing.title} ({', '.join(description_parts)})",
                        reference=f"listing_{listing_id}"
                    )

                create_notification(
                    user=user,
                    notification_type=NotificationEnum.LISTING.value,
                    title="Listing Ads updated",
                    message=f"Your listing '{listing.title}' ({', '.join(description_parts)})",
                    action_url=f"/student/my-listing-details.html?id={listing.id}&title={listing.title}"
                )

                op.success(f"Listing: {listing_id} ads updated for user: {user.first_name or user.email}")
                return BaseResultWithData(
                    message="Listing ads updated successfully.",
                    data={
                        'id': listing.id,
                        'is_ads_banner': listing.is_ads_banner,
                        'is_hot_sales': listing.is_hot_sales,
                        'notification': True
                    },
                    status_code=200
                )

        except Exception as e:
            op.fail(f"Unexpected error for listing ID: {listing_id}", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        

    @staticmethod
    def listing_auto_reactivation(user: User, listing_id: int, data: dict, partial: bool = False) -> BaseResultWithData:
        op = OperationLogger(f"UpdateListingCommand.listing_auto_reactivation for user: {user.first_name or user.email}", data={'listing_id': listing_id, **data})
        op.start()

        if listing_id is None:
            op.fail(f"user: {user.first_name or user.email}: Listing ID is required")
            return BaseResultWithData(
                message="Listing ID is required.",
                status_code=400
            )

        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).first()

            if not listing:
                op.fail(f"Listing not found for listing ID: {listing_id}")
                return BaseResultWithData(
                    message="Listing not found",
                    status_code=404
                )

            
            auto_reactivate = parse_bool(data.get('auto_reactivate', False))

            if listing.status not in [ListingStatusTypeEnum.ACTIVE.value, ListingStatusTypeEnum.EXPIRED.value]:
                op.fail(f"Invalid listing status for listing: {listing.title}")
                return BaseResultWithData(
                    message="Auto-reactivation can only be set for active or expired listings.",
                    status_code=400
                )
            
            if auto_reactivate:
                current_points = UpdatePointsService.check_points(user)
                if current_points < 1:
                    op.fail(f"Insufficient points for listing: {listing.title}")
                    return BaseResultWithData(
                        message="You need at least 1 point to enable auto-reactivation.",
                        status_code=400
                    )
                
            with transaction.atomic():
                listing.auto_reactivate = auto_reactivate
                listing.save(update_fields=['auto_reactivate'])

                create_notification(
                    user=user,
                    notification_type=NotificationEnum.LISTING.value,
                    title="Listing Auto-reactivation",
                    message=f"Auto-reactivation {'enabled' if auto_reactivate else 'disabled'} successfully for {listing.title}.",
                    action_url=f"/student/my-listing-details.html?id={listing.id}&title={listing.title}"
                )

            op.success(f"Auto-reactivation toggled to {auto_reactivate} for listing: {listing_id}, user: {user.first_name or user.email}")
            return BaseResultWithData(
                message=f"Auto-reactivation {'enabled' if auto_reactivate else 'disabled'} successfully.",
                data={'auto_reactivate': listing.auto_reactivate, 'notification': True},
                status_code=200
            )
        
        except Exception as e:
            op.fail(f"Unexpected error for listing ID: {listing_id}", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )