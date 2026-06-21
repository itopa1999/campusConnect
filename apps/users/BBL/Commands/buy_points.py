from decimal import Decimal
from apps.users.models import PointPackage, PointPurchase
from utils.base_result import BaseResultWithData
from utils.constant_helper import ConstantHelper
from utils.enums import PointPurchaseStatusEnum
from utils.log_helpers import OperationLogger
from apps.users.paystack import initiate_paystack, verify_paystack_payment
from apps.users.flutterwave import initiate_flutterwave


class BuyPointsCommand:
    @staticmethod
    def execute(request, user, data: dict) -> BaseResultWithData:
        op = OperationLogger("BuyPointsCommand.execute", data=data)
        op.start()

        package_id = data.get('package_id')
        points = data.get('points')
        amount = data.get('amount')
        gateway = data.get('gateway')

        # Basic validation
        if not all([package_id, points, amount, gateway]):
            missing = []
            if not package_id: missing.append('package_id')
            if not points: missing.append('points')
            if not amount: missing.append('amount')
            if not gateway: missing.append('gateway')
            op.fail("Missing required fields", extra={'missing': missing})
            return BaseResultWithData(
                message=f"Missing required fields: {', '.join(missing)}",
                status_code=400
            )

        # Fetch package
        try:
            package = PointPackage.objects.get(id=package_id, is_deleted=False)
        except PointPackage.DoesNotExist:
            op.fail("Package not found")
            return BaseResultWithData(
                message="Point package not found.",
                status_code=404
            )

        # Validate points and amount
        try:
            points = int(points)
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            op.fail("Invalid points or amount format")
            return BaseResultWithData(
                message="Invalid points or amount format.",
                status_code=400
            )

        if points != package.points:
            op.fail("Points mismatch")
            return BaseResultWithData(
                message="Points mismatch.",
                status_code=400
            )

        if amount != package.price:
            op.fail("Amount mismatch")
            return BaseResultWithData(
                message="Amount mismatch.",
                status_code=400
            )

        # Route to payment gateway
        checkout_url = None
        if gateway == ConstantHelper.PAYSTACK:
            checkout_url = initiate_paystack(request, user, package)
        elif gateway == ConstantHelper.FLUTTERWAVE:
            checkout_url = initiate_flutterwave(request, user, package)
        elif gateway == ConstantHelper.MONNIFY:
            # TODO: Implement Flutterwave integration
            op.fail("Monnify not implemented yet")
            return BaseResultWithData(
                message="Monnify is currently not available.",
                status_code=400
            )
        else:
            op.fail(f"Unknown gateway: {gateway}")
            return BaseResultWithData(
                message=f"Unknown gateway: {gateway}",
                status_code=400
            )

        if not checkout_url:
            op.fail("Payment initialization failed.")
            return BaseResultWithData(
                message="Payment initialization failed.",
                status_code=500
            )

        op.success("Payment initialized successfully.")
        return BaseResultWithData(
            data={"checkout_url": checkout_url},
            status_code=200,
            message="Payment initialized successfully."
        )
    
    @staticmethod
    def payment_retry(request, user, data: dict) -> BaseResultWithData:
        """
        Retry a failed payment or verify a pending payment.
        """
        op = OperationLogger("BuyPointsCommand.payment_retry", data=data)
        op.start()

        reference = data.get('reference_id')
        if not reference:
            op.fail("Reference ID missing")
            return BaseResultWithData(
                message="Reference ID is required.",
                status_code=400
            )

        # Find the purchase
        purchase = PointPurchase.objects.filter(
            payment_reference=reference,
            user=user
        ).first()

        if not purchase:
            op.fail("Purchase not found")
            return BaseResultWithData(
                message="Purchase not found.",
                status_code=404
            )

        # If already completed, return success
        if purchase.status == PointPurchaseStatusEnum.COMPLETED.value:
            op.success("Purchase already completed")
            return BaseResultWithData(
                message="Purchase already completed.",
                status_code=200
            )

        if purchase.status in {
            PointPurchaseStatusEnum.PENDING.value,
            PointPurchaseStatusEnum.FAILED.value
        }:
            if purchase.gateway == ConstantHelper.PAYSTACK:
                result = verify_paystack_payment(reference)
            elif purchase.gateway == ConstantHelper.FLUTTERWAVE:
                result = verify_paystack_payment(reference)
            elif purchase.gateway == ConstantHelper.MONNIFY:
                result = verify_paystack_payment(reference)
            else:
                return BaseResultWithData(
                    message="Gateway not provided.",
                    status_code=400
                )
            if result.get("success"):
                op.success("Payment verified successfully")
                return BaseResultWithData(
                    message=result.get("message", "Payment verified."),
                    data=result.get("purchase"),
                    status_code=200
                )
            else:
                # Verification failed – could be network or the user didn't pay
                # We'll return the error and let the user decide to retry
                op.fail("Verification failed", extra=result)
                return BaseResultWithData(
                    message=result.get("error", "Verification failed."),
                    status_code=400
                )

        # If failed, return error
        return Response({
            "is_success": False,
            "message": "Purchase has failed. Please try again.",
        }, status=400)