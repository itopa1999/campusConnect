import json
from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from apps.campus.models import Listing
from apps.campus.serializers import ListingSerializer
from apps.users.models import User
from utils.base_result import BaseResultWithData
from utils.enums import ListingType
from utils.helpers import UpdatePointsService
from utils.log_helpers import OperationLogger


class ListingCommand:
    @staticmethod
    def create_listing(user: User, data: dict) -> BaseResultWithData:
        """
        Create a listing after performing all business validations:
        - Points ≥ 1
        - At least one hotspot
        - Image size < 3 MB
        - Image extension allowed (jpg, jpeg, png, webp)
        - Price ≥ 0
        - Freebie listings must have price = 0 or null
        - Basic field validations via serializer
        """
        op = OperationLogger("ListingCommand.create_listing", data=data)
        op.start()

        # --- Convert QueryDict to mutable dict and clean empty values ---
        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = dict(data)   # ensure it's a dict

        # Remove empty image string (frontend sends '' when no file)
        if data.get('image') == '':
            data.pop('image', None)

        # --- 1. Points check ---
        current_points = UpdatePointsService.check_points(user)
        if current_points < 1:
            op.fail("Insufficient points")
            return BaseResultWithData(
                message="Insufficient points. You need at least 1 point to post.",
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
            if image.size > 3 * 1024 * 1024:
                op.fail("Image too large")
                return BaseResultWithData(
                    message="Image file size must not exceed 3 MB.",
                    status_code=400
                )
            allowed_extensions = ('.jpg', '.jpeg', '.png', '.webp')
            if not image.name.lower().endswith(allowed_extensions):
                op.fail("Invalid image format")
                return BaseResultWithData(
                    message="Only JPG, PNG, and WEBP images are allowed.",
                    status_code=400
                )

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
            op.fail("Serializer validation failed", extra={'errors': e.detail})
            return BaseResultWithData(
                message="Validation failed.",
                data={'errors': e.detail},
                status_code=400
            )

        # --- 8. Save within a transaction ---
        try:
            with transaction.atomic():
                listing = serializer.save(user=user)
                UpdatePointsService.update_points(user, points=1, action='subtract')
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