from http import HTTPStatus
from apps.users.paystack import verify_paystack_payment
from utils.base_result import BaseResultWithData

class PaystackConfirmQuery:
    @staticmethod
    def execute(reference) -> BaseResultWithData:
        if not reference:
            return BaseResultWithData(
                data=None,
                status_code=HTTPStatus.BAD_REQUEST,
                message="No reference provided"
            )

        result = verify_paystack_payment(reference)
        if result.get("success"):
            purchase = result.get("purchase")

            return BaseResultWithData(
                message=result.get("message"),
                data={
                    "reference": reference,
                    "purchase_id": {purchase['purchase_id']},
                    "points_awarded": {purchase['points_awarded']},
                    "amount_paid": {purchase['amount_paid']},
                },
                status_code=200
            )
        else:
            return BaseResultWithData(
                message=result.get("error"),
                data={
                    "reference": reference
                },
                status_code=400
            )