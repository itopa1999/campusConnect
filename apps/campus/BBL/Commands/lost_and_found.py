from django.db import OperationalError, transaction
from rest_framework import serializers
from apps.campus.models import LostAndFound
from apps.campus.serializers import ClaimSerializer, LostAndFoundSerializer  # you'll need this
from utils.Tasks.emailService import background_task_send_lost_item_claim_email
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
        op = OperationLogger("LostandFoundCommand.create_item", data=data)
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
            op.fail("Missing required fields", exc={'missing': missing})
            return BaseResultWithData(
                message=f"Missing required fields: {', '.join(missing)}",
                status_code=400
            )

        # --- Image validation (if provided) ---
        image = data.get('image')
        if image:
            if image.size > ConstantHelper.IMAGE_SIZE:
                op.fail("Image too large")
                return BaseResultWithData(
                    message=f"Image file size must not exceed {ConstantHelper.IMAGE_SIZE} MB.",
                    status_code=400
                )
            # Extension check
            allowed_extensions = ('.jpg', '.jpeg', '.png', '.webp')
            if not image.name.lower().endswith(allowed_extensions):
                op.fail("Invalid image format")
                return BaseResultWithData(
                    message="Only JPG, PNG, and WEBP images are allowed.",
                    status_code=400
                )

        # --- Serializer validation ---
        serializer = LostAndFoundSerializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            op.fail("Serializer validation failed", exc={'errors': e.detail})
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
        except Exception as e:
            op.fail("Unexpected error during creation", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )
        
    
    @staticmethod
    def create_claim(data: dict) -> BaseResultWithData:
        """
        Submit a claim for a lost item.
        - Verify the item exists and is still open.
        - Compare the provided answers with the stored answers.
        - If correct, create the claim and return the finder's contact details.
        """
        op = OperationLogger("ClaimCommand.create_claim", data=data)
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
            op.fail("Missing required fields", exc={'missing': missing})
            return BaseResultWithData(
                message=f"Missing required fields: {', '.join(missing)}",
                status_code=400
            )

        # ---- 2. Fetch the lost item ----
        try:
            item = LostAndFound.objects.get(id=lost_item_id, is_deleted=False)
        except LostAndFound.DoesNotExist:
            op.fail("Item not found")
            return BaseResultWithData(
                message="The lost item does not exist.",
                status_code=404
            )

        # ---- 3. Check status ----
        if item.status.lower() != LostAndFoundStatusEnum.OPEN.value.lower():
            op.fail("Item not claimable")
            return BaseResultWithData(
                message="This item has already been claimed or resolved.",
                status_code=400
            )

        # send email to the founder with a link please.
        try:
            background_task_send_lost_item_claim_email.delay(item.email, item.full_name)
        except OperationalError as e:
            op.success("Account created successfully, but failed to queue verification email")
        else:
            op.success("Account created successfully, verification email queued")

            

        # # ---- 5. All good – create the claim ----
        # claim_data = {
        #     'lost_item': item.id,
        #     'answer1': answer1,
        #     'answer2': answer2,
        #     'full_name': full_name,
        #     'email': email,
        #     'phone': phone or None,
        # }
        # serializer = ClaimSerializer(data=claim_data)

        # try:
        #     serializer.is_valid(raise_exception=True)
        # except serializers.ValidationError as e:
        #     op.fail("Serializer validation failed", exc={'errors': e.detail})
        #     return BaseResultWithData(
        #         message="Validation failed.",
        #         data={'errors': e.detail},
        #         status_code=400
        #     )

        # try:
        #     with transaction.atomic():
        #         claim = serializer.save()
        #         # Optionally mark the lost item as 'claimed'
        #         # item.status = 'claimed'
        #         # item.save(update_fields=['status'])
        # except Exception as e:
        #     op.fail("Unexpected error during claim creation", exc=e)
        #     return BaseResultWithData(
        #         message=f"An unexpected error occurred: {str(e)}",
        #         status_code=500
        #     )

        return BaseResultWithData(
            message="If your answer is right we will forward you the founder details. ",
            status_code=200
        )