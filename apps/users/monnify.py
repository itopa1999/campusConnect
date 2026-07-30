import base64
import secrets

import requests

from django.conf import settings
from django.db import transaction

from apps.users.models import PointPackage, PointPurchase, User
from utils.constant_helper import ConstantHelper
from utils.enums import PointPurchaseStatusEnum
from utils.log_helpers import OperationLogger


def authenticate():
    api_key = settings.MONNIFY_API_KEY
    secret_key = settings.MONNIFY_SECRET_KEY
    base_url = settings.MONNIFY_BASE_URL

    credentials = f"{api_key}:{secret_key}"

    encoded = base64.b64encode(
        credentials.encode()
    ).decode()

    headers = {
        "Authorization": f"Basic {encoded}"
    }

    response = requests.post(
        f"{base_url}/api/v1/auth/login",
        headers=headers
    )

    response.raise_for_status()

    data = response.json()

    return data["responseBody"]["accessToken"]


def initiate_monnify(request, user: User, package: PointPackage):

    op = OperationLogger(
        f"MonnifyInitiate.initiate_monnify for user:"
        f" {user.first_name or user.email}"
        f" -- amount: {package.price}",
        data={"package_id": package.id},
    )

    op.start()

    ref = secrets.token_urlsafe(15)

    # Create pending purchase
    try:
        with transaction.atomic():

            purchase = PointPurchase.objects.create(
                user=user,
                package=package,
                points_awarded=package.points,
                amount_paid=package.price,
                payment_reference=ref,
                status=PointPurchaseStatusEnum.PENDING.value,
                gateway=ConstantHelper.MONNIFY,
            )

    except Exception as e:

        op.fail(
            f"Failed to create purchase record."
            f" {str(e)}"
        )

        return None

    payload = {
        "amount": float(package.price),
        "customerName": user.get_full_name(),
        "customerEmail": user.email,
        "paymentReference": ref,
        "paymentDescription": package.description,
        "currencyCode": "NGN",
        "contractCode": settings.MONNIFY_CONTRACT_CODE,
        "redirectUrl": settings.MONNIFY_REDIRECT_URL,
        "paymentMethods": [
            "CARD",
            "ACCOUNT_TRANSFER",
        ],
    }

    try:

        token = authenticate()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            f"{settings.MONNIFY_BASE_URL}"
            "/api/v1/merchant/transactions/init-transaction",
            headers=headers,
            json=payload,
        )

        result = response.json()

    except Exception as e:

        op.fail(
            f"Monnify request failed."
            f" {str(e)}"
        )

        purchase.status = PointPurchaseStatusEnum.FAILED.value
        purchase.save(update_fields=["status"])

        return None

    # Monnify returns request successfully but payment
    # initialization failed.
    if (
        response.status_code != 200
        or not result.get("requestSuccessful")
    ):

        op.fail(
            f"Monnify initialization failed.",
            exc=result,
        )

        purchase.status = PointPurchaseStatusEnum.FAILED.value
        purchase.save(update_fields=["status"])

        return None

    body = result["responseBody"]

    # Optional
    purchase.transaction_reference = body.get(
        "transactionReference"
    )

    purchase.save(
        update_fields=["transaction_reference"]
    )

    op.success(
        f"Monnify initiated successfully."
        f" Reference: {ref}"
    )

    return body["checkoutUrl"]