from decimal import Decimal
from apps.users.models import PointPackage
from utils.base_result import BaseResultWithData
from utils.constant_helper import ConstantHelper
from utils.log_helpers import OperationLogger
from apps.users.paystack import initiate_paystack
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