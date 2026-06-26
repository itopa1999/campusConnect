from django.utils import timezone
import json
from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from apps.campus.models import CampusHotspot, Listing
from apps.campus.serializers import ListingSerializer
from apps.users.models import User
from utils.base_result import BaseResultWithData
from utils.constant_helper import ConstantHelper
from utils.enums import AdvertTypeEnum, ListingStatusType, ListingType, PointTransactionTypeEnum
from utils.helpers import UpdatePointsService
from utils.log_helpers import OperationLogger


class ListingCommand:
    @staticmethod
    def create_listing(user: User, data: dict) -> BaseResultWithData:
        """
        Create a listing after performing all business validations:
        - At least one hotspot
        - Image size < 3 MB
        - Image extension allowed (jpg, jpeg, png, webp)
        - Price ≥ 0
        - Freebie listings must have price = 0 or null
        - Basic field validations via serializer
        """
        op = OperationLogger("ListingCommand.create_listing", data=data)
        op.start()

        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = dict(data)

        if data.get('image') == '':
            data.pop('image', None)

        # --- 4. Price parsing and validation ---
        raw_price = data.get('price')
        price = None
        if raw_price is not None and raw_price != '':
            try:
                price = Decimal(str(raw_price))
            except (ValueError, TypeError):
                op.fail("Invalid price format")
                return BaseResultWithData(
                    message="Price must be a valid number.",
                    status_code=400
                )
            if price < 0:
                op.fail("Negative price")
                return BaseResultWithData(
                    message="Price cannot be negative.",
                    status_code=400
                )
        data['price'] = price

        def parse_bool(val):
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() == 'true'
            return False

        is_banner = parse_bool(data.get('is_ads_banner', False))
        is_hot = parse_bool(data.get('is_hot_sales', False))

        # Calculate total points needed
        base_points = ConstantHelper.BASE_POINT
        banner_points = AdvertTypeEnum.BANNER.points if is_banner else 0
        hot_points = AdvertTypeEnum.HOT_SALE.points if is_hot else 0
        total_points_needed = base_points + banner_points + hot_points

        # --- 1. Points check ---
        current_points = UpdatePointsService.check_points(user)
        if current_points < total_points_needed:
            op.fail("Insufficient points")
            return BaseResultWithData(
                message=f"Insufficient points. You need at least {ConstantHelper.BASE_POINT} point to post.",
                status_code=400
            )

        # --- 2. Hotspots: parse JSON string and map to 'hotspots' field ---
        hotspot_ids = data.get('hotspot_ids')
        if isinstance(hotspot_ids, str):
            try:
                hotspot_ids = json.loads(hotspot_ids)
            except json.JSONDecodeError:
                hotspot_ids = None

        if not hotspot_ids or not isinstance(hotspot_ids, list) or len(hotspot_ids) == 0:
            op.fail("No meeting spots selected")
            return BaseResultWithData(
                message="Please select at least one meeting spot.",
                status_code=400
            )

        # The serializer expects a field named 'hotspots' (not 'hotspot_ids')
        data['hotspots'] = hotspot_ids
        # Optionally remove the old key to avoid confusion
        data.pop('hotspot_ids', None)

        # --- 3. Image validation (if provided) ---
        image = data.get('image')
        if image:
            if image.size > ConstantHelper.IMAGE_SIZE:
                op.fail("Image too large")
                return BaseResultWithData(
                    message=f"Image file size must not exceed {ConstantHelper.IMAGE_SIZE} MB.",
                    status_code=400
                )
            allowed_extensions = ('.jpg', '.jpeg', '.png', '.webp')
            if not image.name.lower().endswith(allowed_extensions):
                op.fail("Invalid image format")
                return BaseResultWithData(
                    message="Only JPG, PNG, and WEBP images are allowed.",
                    status_code=400
                )

        

        # --- 5. Freebie specific rule ---
        listing_type = data.get('listing_type')
        if listing_type == ListingType.FREEBIE.value and price not in (None, 0):
            op.fail(f"{ListingType.FREEBIE.value} price must be 0")
            return BaseResultWithData(
                message=f"{ListingType.FREEBIE.value} must have price set to 0.",
                status_code=400
            )

        # --- 6. The 'category' field is already named 'category' in the frontend,
        #     and the serializer expects 'category', so no mapping needed.
        #     However, we ensure it exists.
        if not data.get('category'):
            op.fail("Category missing")
            return BaseResultWithData(
                message="Category is required.",
                status_code=400
            )

        # --- 7. Serializer validation ---
        serializer = ListingSerializer(data=data, context={'user': user})
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            op.fail("Serializer validation failed", exc={'errors': e.detail})
            return BaseResultWithData(
                message="Validation failed.",
                data={'errors': e.detail},
                status_code=400
            )

        # --- 8. Save within a transaction ---
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
                op.success(f"Listing created: {listing.id}")
                return BaseResultWithData(
                    message="Listing created successfully, It will appear in the marketplace within a few minutes.",
                    data={'listing_id': listing.id},
                    status_code=201
                )
        except Exception as e:
            op.fail("Unexpected error during creation", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        
    @staticmethod
    def update_listing(user: User, listing_id: int, data: dict, partial: bool = False) -> BaseResultWithData:
        op = OperationLogger("UpdateListingCommand.update_listing", data={'listing_id': listing_id, **data})
        op.start()

        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).select_related('category').first()

            if not listing:
                op.fail("Listing not found")
                return BaseResultWithData(
                    message="Listing not found or you do not have permission.",
                    status_code=404
                )

            # Check edit restriction (skip if only status changes – but we don't have status in data)
            fields_to_update = set(data.keys())
            if fields_to_update and listing.modified_at:
                days_since = (timezone.now() - listing.modified_at).days
                if days_since < ConstantHelper.EDIT_DATE:
                    op.fail("Edit restriction")
                    return BaseResultWithData(
                        message=f"You can only edit this listing once every {ConstantHelper.EDIT_DATE} days. Last edit was {listing.modified_at.strftime('%Y-%m-%d')}.",
                        status_code=400
                    )

            # ─── 1. Handle category ─────────────────────────────────────
            # The frontend may send 'category_id' or 'category'
            if 'category_id' in data:
                data['category'] = data.pop('category_id')
            # Ensure category is an integer
            if 'category' in data:
                try:
                    data['category'] = int(data['category'])
                except (ValueError, TypeError):
                    op.fail("Invalid category ID")
                    return BaseResultWithData(
                        message="Category must be a valid ID.",
                        status_code=400
                    )

            # ─── 2. Handle hotspots ─────────────────────────────────────
            # Remove 'hotspots' from data so it doesn't reach the serializer
            hotspot_ids = None
            if 'hotspots' in data:
                raw_hotspots = data.pop('hotspots')
                if isinstance(raw_hotspots, str):
                    try:
                        hotspot_ids = json.loads(raw_hotspots)
                    except json.JSONDecodeError:
                        hotspot_ids = None
                else:
                    hotspot_ids = raw_hotspots

                if not hotspot_ids or not isinstance(hotspot_ids, list) or len(hotspot_ids) == 0:
                    op.fail("No meeting spots selected")
                    return BaseResultWithData(
                        message="Please select at least one meeting spot.",
                        status_code=400
                    )

                # Validate all hotspots exist
                existing_hotspots = CampusHotspot.objects.filter(id__in=hotspot_ids, is_deleted=False)
                if existing_hotspots.count() != len(hotspot_ids):
                    op.fail("Invalid hotspot IDs")
                    return BaseResultWithData(
                        message="One or more meeting spots are invalid.",
                        status_code=400
                    )

            # ─── 3. Price parsing ──────────────────────────────────────
            if 'price' in data:
                raw_price = data['price']
                if raw_price is None or raw_price == '':
                    data['price'] = None
                else:
                    try:
                        data['price'] = Decimal(str(raw_price))
                    except (ValueError, TypeError):
                        op.fail("Invalid price")
                        return BaseResultWithData(
                            message="Price must be a valid number.",
                            status_code=400
                        )
                    if data['price'] < 0:
                        op.fail("Negative price")
                        return BaseResultWithData(
                            message="Price cannot be negative.",
                            status_code=400
                        )

            # ─── 4. Listing type validation ────────────────────────────
            if 'listing_type' in data and data['listing_type'] not in ListingType.values():
                op.fail("Invalid listing type")
                return BaseResultWithData(
                    message="Invalid listing type.",
                    status_code=400
                )

            if data.get('listing_type') == ListingType.FREEBIE.value:
                if 'price' in data and data['price'] not in (None, 0):
                    op.fail("Freebie price must be 0")
                    return BaseResultWithData(
                        message="Freebie listings must have price set to 0.",
                        status_code=400
                    )

            # ─── 5. Serializer validation ──────────────────────────────
            # Always use partial=True so missing fields are allowed
            serializer = ListingSerializer(listing, data=data, partial=True, context={'user': user})
            try:
                serializer.is_valid(raise_exception=True)
            except serializers.ValidationError as e:
                op.fail("Serializer validation failed", exc={'errors': e.detail})
                return BaseResultWithData(
                    message="Validation failed.",
                    data={'errors': e.detail},
                    status_code=400
                )

            # ─── 6. Save within transaction ────────────────────────────
            with transaction.atomic():
                updated_listing = serializer.save()
                # Handle hotspots if provided
                if hotspot_ids is not None:
                    updated_listing.hotspots.set(hotspot_ids)
                    updated_listing.save(update_fields=['modified_at'])

                op.success(f"Listing {listing_id} updated")
                return BaseResultWithData(
                    message="Listing updated successfully.",
                    data={'id': updated_listing.id},
                    status_code=200
                )

        except Exception as e:
            op.fail("Unexpected error", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        
    
    @staticmethod
    def delete_listing(user: User, listing_id: int) -> BaseResultWithData:
        op = OperationLogger("DeleteListingCommand.delete_listing", data={'listing_id': listing_id})
        op.start()

        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).first()

            if not listing:
                op.fail("Listing not found")
                return BaseResultWithData(
                    message="Listing not found or you do not have permission.",
                    status_code=404
                )

            with transaction.atomic():
                listing.is_deleted = True
                listing.save(update_fields=['is_deleted'])

            op.success(f"Listing {listing_id} deleted")
            return BaseResultWithData(
                message="Listing deleted successfully.",
                status_code=200
            )

        except Exception as e:
            op.fail("Unexpected error", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        
    
    @staticmethod
    def reactivate_listing(user: User, listing_id: int) -> BaseResultWithData:
        op = OperationLogger("ReactivateListingCommand.reactivate_listing", data={'listing_id': listing_id})
        op.start()

        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).first()

            if not listing:
                op.fail("Listing not found")
                return BaseResultWithData(
                    message="Listing not found or you do not have permission.",
                    status_code=404
                )

            if listing.status.lower() != ListingStatusType.SOLD.value.lower() and listing.status.lower() != ListingStatusType.EXPIRED.value.lower():
                op.fail("Invalid status")
                return BaseResultWithData(
                    message="Only sold or expired listings can be reactivated.",
                    status_code=400
                )

            # Check points
            points = UpdatePointsService.check_points(user)
            if points < ConstantHelper.BASE_POINT:
                op.fail("Insufficient points")
                return BaseResultWithData(
                    message=f"Insufficient points. You need {ConstantHelper.BASE_POINT} point to reactivate.",
                    status_code=400
                )

            with transaction.atomic():
                listing.status = ListingStatusType.ACTIVE.value
                listing.save(update_fields=['status'])

                UpdatePointsService.update_points(
                    user=user,
                    points=ConstantHelper.BASE_POINT,
                    action=ConstantHelper.POINT_SUBTRACTION,
                    transaction_type=PointTransactionTypeEnum.REACTIVATION.value,
                    description=f"Reactivated listing: {listing.title}",
                    reference=f"listing_{listing_id}"
                )

            op.success(f"Listing {listing_id} reactivated")
            return BaseResultWithData(
                message="Listing reactivated successfully.",
                data={'id': listing.id},
                status_code=200
            )

        except Exception as e:
            op.fail("Unexpected error", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        
    
    @staticmethod
    def mark_sold(user: User, listing_id: int) -> BaseResultWithData:
        op = OperationLogger("ReactivateListingCommand.mark_sold", data={'listing_id': listing_id})
        op.start()

        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).first()

            if not listing:
                op.fail("Listing not found")
                return BaseResultWithData(
                    message="Listing not found or you do not have permission.",
                    status_code=404
                )
            
            with transaction.atomic():
                listing.status = ListingStatusType.SOLD.value
                listing.save(update_fields=['status'])

            op.success(f"Listing {listing_id} mark as sold")
            return BaseResultWithData(
                message="Listing mark as sold successfully.",
                data={'id': listing.id},
                status_code=200
            )

        except Exception as e:
            op.fail("Unexpected error", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        
    
    @staticmethod
    def image_upload(user: User, listing_id: int, image_file) -> BaseResultWithData:
        op = OperationLogger("ListingCommand.image_upload", data={'listing_id': listing_id})
        op.start()

        try:
            listing = Listing.objects.filter(
                id=listing_id,
                user=user,
                is_deleted=False
            ).first()

            if not listing:
                op.fail("Listing not found")
                return BaseResultWithData(
                    message="Listing not found or you do not have permission.",
                    status_code=404
                )

            # Validate image (size, extension)
            if image_file.size > ConstantHelper.IMAGE_SIZE:
                op.fail("Image too large")
                return BaseResultWithData(
                    message=f"Image size must not exceed {ConstantHelper.IMAGE_SIZE} MB.",
                    status_code=400
                )
            allowed_extensions = ('.jpg', '.jpeg', '.png', '.webp')
            if not image_file.name.lower().endswith(allowed_extensions):
                op.fail("Invalid image format")
                return BaseResultWithData(
                    message="Only JPG, PNG, and WEBP images are allowed.",
                    status_code=400
                )

            with transaction.atomic():
                listing.image = image_file
                listing.save(update_fields=['image'])

            op.success(f"Image uploaded for listing {listing_id}")
            return BaseResultWithData(
                message="Image uploaded successfully.",
                data={'id': listing.id},
                status_code=200
            )

        except Exception as e:
            op.fail("Unexpected error", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )