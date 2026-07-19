from django.db import OperationalError, transaction
from rest_framework import serializers
from apps.campus.models import Claim, LostAndFound
from apps.campus.serializers import ClaimSerializer, LostAndFoundSerializer  # you'll need this
from utils.Tasks.backgroundTask import background_task_send_founder_details_to_claimer_email, background_task_send_lost_item_claim_email
from utils.base_result import BaseResultWithData
from utils.constant_helper import ConstantHelper
from utils.enums import LostAndFoundStatusEnum
from utils.log_helpers import OperationLogger


class LostandFoundCommand:
    @staticmethod
    def create_item(data: dict) -> BaseResultWithData:
        """
        Create a lost item report after performing validations:
        - All required fields present
        - Image size < 2 MB
        - Image extension allowed (jpg, jpeg, png, webp)
        - Phone number optional (validated by model)
        """
        op = OperationLogger(f"LostandFoundCommand.create_item from {data.get('full_name') or data.get('email')}", data=data)
        op.start()

        # Convert QueryDict to mutable dict if needed
        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = dict(data)

        # Remove empty image string (frontend sends '' when no file)
        if data.get('image') == '':
            data.pop('image', None)

        # --- Required fields validation ---
        required_fields = [
            'item_name', 'description', 'location', 'date_found',
            'verification1', 'answer1', 'verification2', 'answer2',
            'full_name', 'email', 'department'
        ]
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            op.fail(f"Missing required fields for creating item {data.get('item_name')}", exc={'missing': missing})
            return BaseResultWithData(
                message=f"Missing required fields: {', '.join(missing)}",
                status_code=400
            )

        # --- Image validation (if provided) ---
        image = data.get('image')
        if image:
            if image.size > ConstantHelper.IMAGE_SIZE:
                op.fail(f"Image too large for creating item {data.get('item_name')}")
                return BaseResultWithData(
                    message=f"Image file size must not exceed {ConstantHelper.IMAGE_SIZE} MB.",
                    status_code=400
                )
            # Extension check
            allowed_extensions = ('.jpg', '.jpeg', '.png', '.webp')
            if not image.name.lower().endswith(allowed_extensions):
                op.fail(f"Invalid image format for creating item {data.get('item_name')}")
                return BaseResultWithData(
                    message="Only JPG, PNG, and WEBP images are allowed.",
                    status_code=400
                )

        # --- Serializer validation ---
        serializer = LostAndFoundSerializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            op.fail(f"Serializer validation failed for creating item {data.get('item_name')}", exc={'errors': e.detail})
            return BaseResultWithData(
                message="Validation failed.",
                data={'errors': e.detail},
                status_code=400
            )

        # --- Save ---
        try:
            with transaction.atomic():
                item = serializer.save()
                op.success(f"Lost item reported: {item.item_name}")
                return BaseResultWithData(
                    message="Item reported successfully.",
                    data={'id': item.id},
                    status_code=201
                )
            # Todo: Consider sending a confirmation email to the user here if needed.
        except Exception as e:
            op.fail(f"Unexpected error during creation: item {data.get('item_name')}", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        
    
    @staticmethod
    def create_claim(request, data: dict) -> BaseResultWithData:
        """
        Submit a claim for a lost item.
        - Verify the item exists and is still open.
        - Compare the provided answers with the stored answers.
        - If correct, create the claim and return the finder's contact details.
        """
        op = OperationLogger(f"ClaimCommand.create_claim for item_id: {data.get('lost_item_id')}", data=data)
        op.start()

        # ---- 1. Extract and validate required fields ----
        lost_item_id = data.get('lost_item_id')
        answer1 = data.get('answer1')
        answer2 = data.get('answer2')
        full_name = data.get('full_name')
        email = data.get('email')
        phone = data.get('phone', '')

        if not all([lost_item_id, answer1, answer2, full_name, email]):
            missing = []
            if not lost_item_id: missing.append('lost_item_id')
            if not answer1: missing.append('answer1')
            if not answer2: missing.append('answer2')
            if not full_name: missing.append('full_name')
            if not email: missing.append('email')
            op.fail(f"Missing required fields while creating claim for lost_item ID {data.get('lost_item_id')}", exc={'missing': missing})
            return BaseResultWithData(
                message=f"Missing required fields: {', '.join(missing)}",
                status_code=400
            )

        # ---- 2. Fetch the lost item ----
        try:
            item = LostAndFound.objects.get(id=lost_item_id, is_deleted=False)
        except LostAndFound.DoesNotExist:
            op.fail(f"Item ID {lost_item_id} not found")
            return BaseResultWithData(
                message="The lost item does not exist.",
                status_code=404
            )

        # ---- 3. Check status ----
        if item.status.lower() != LostAndFoundStatusEnum.OPEN.value.lower():
            op.fail(f"Item not claimable for item {item.item_name}")
            return BaseResultWithData(
                message="This item has already been claimed or resolved.",
                status_code=400
            )

        existing_claims_count = Claim.objects.filter(lost_item=item, email=email).count()
        if existing_claims_count >= 2:
            op.fail(f"Max claims limit reached for Email: {email}")
            return BaseResultWithData(
                message="You have already submitted the maximum number of claims (2) for this item.",
                status_code=400
            )    

        # ---- 5. All good – create the claim ----
        claim_data = {
            'lost_item': item.id,
            'answer1': answer1,
            'answer2': answer2,
            'full_name': full_name,
            'email': email,
            'phone': phone or None,
        }
        serializer = ClaimSerializer(data=claim_data)

        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            op.fail(f"Serializer validation failed while creating claim for lost_item ID {data.get('lost_item_id')} ", exc={'errors': e.detail})
            return BaseResultWithData(
                message="Validation failed.",
                data={'errors': e.detail},
                status_code=400
            )

        try:
            with transaction.atomic():
                claim = serializer.save()
        except Exception as e:
            op.fail(f"Unexpected error during claim creation for lost_item_id {data.get('lost_item_id')}", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        

        approval_link = request.build_absolute_uri(
            f"/campus/api/campus/approve-claim?claim_id={claim.id}&email={claim.email}"
        )
        try:
            background_task_send_lost_item_claim_email.delay(
                item.item_name,
                item.email, 
                item.full_name, 
                approval_link,
                claim.full_name,
                claim.answer1,
                claim.answer2
                )
        except OperationalError:
            op.success("Successfully, but failed to queue lost item claim email")

        op.success(f"Successfully, verification email queued for lost email item: {item.item_name}")
        return BaseResultWithData(
            message="If your answer is right we will forward you the founder details. ",
            status_code=200
        )
    

    @staticmethod
    def approve_claim(request) -> BaseResultWithData:
        claim_id = request.GET.get('claim_id')
        email = request.GET.get('email')
        op = OperationLogger(f"ClaimCommand.approve_claim for claim_id: {claim_id}",  data={'claim_id': claim_id, 'email': email})
        op.start()
                
        if not claim_id or not email:
            op.fail("claim_id or email is required")
            return BaseResultWithData(
                message="Invalid request: missing claim_id or email.",
                status_code=400
            )
        
        claim = Claim.objects.filter(id=claim_id, email=email).first()
        if not claim:
            op.fail(f"claim not found for claim ID {claim_id}")
            return BaseResultWithData(
                message="Claim not found",
                status_code=400
            )
        
        lost_item = claim.lost_item

        if lost_item.status.lower() != LostAndFoundStatusEnum.OPEN.value.lower():
            op.fail(f"Item not claimable for lost_item {lost_item.item_name}")
            return BaseResultWithData(
                message="This item has already been claimed or resolved.",
                status_code=400
            )
        
        lost_item.status = LostAndFoundStatusEnum.CLAIMED.value
        lost_item.claimed_by = claim.full_name
        lost_item.save()

        try:
            background_task_send_founder_details_to_claimer_email.delay(
                lost_item.item_name,
                lost_item.email, 
                lost_item.full_name, 
                lost_item.phone,
                claim.full_name,
                claim.email
                )
        except OperationalError:
            op.success("Successfully, but failed to queue email")
        
        op.success(f"Successfully, email queued for sent founder details, item: {lost_item.item_name}")
        return BaseResultWithData (
            message="Details has been forwarded.",
            status_code=200
        )