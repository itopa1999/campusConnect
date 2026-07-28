import secrets
from django.conf import settings
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
import requests
from apps.users.models import PointPurchase
from utils.constant_helper import ConstantHelper
from utils.enums import NotificationEnum, PointPurchaseStatusEnum, PointTransactionTypeEnum
from utils.helpers import UpdatePointsService, create_notification
from utils.log_helpers import OperationLogger


def initiate_paystack(request, user, package):
    """
    Initiate Paystack payment for a point package.
    Creates a pending PointPurchase record and returns the Paystack checkout URL.
    """
    op = OperationLogger(f"PaystackInitiate.initiate_paystack for user: {user.first_name or user.email} -- amount: {package.price}", data = {"package_id": package.id})
    op.start()

    # Generate a unique reference
    ref = secrets.token_urlsafe(15)

    # Create pending purchase record
    try:
        with transaction.atomic():
            purchase = PointPurchase.objects.create(
                user=user,
                package=package,
                points_awarded=package.points,
                amount_paid=package.price,
                payment_reference=ref,
                status=PointPurchaseStatusEnum.PENDING.value,
                gateway = ConstantHelper.PAYSTACK
            )
    except Exception as e:
        op.fail(f"Failed to create purchase record for package: {package.description}: user: {user.first_name or user.email}: {str(e)}")
        return None

    # Prepare Paystack payload
    amount_in_kobo = int(float(package.price) * 100)
    callback_url = request.build_absolute_uri(
        reverse('paystack-points-confirm', kwargs={"reference": ref})
    )

    paystack_data = {
        "email": user.email,
        "amount": amount_in_kobo,
        "reference": ref,
        "metadata": {
            "purchase_id": purchase.id,
            "package_id": package.id,
            "user_id": user.id,
        },
        "callback_url": callback_url,
    }

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            settings.PAYSTACK_INITIALIZE_URL,
            headers=headers,
            json=paystack_data
        )
        result = response.json()
    except Exception as e:
        op.fail(f"Paystack request error for package: {package.description}: user: {user.first_name or user.email}: {str(e)}")
        return None

    if response.status_code != 200 or not result.get("status"):
        op.fail(f"Paystack initialization failed for package: {package.description}: user: {user.first_name or user.email}:", exc=result)
        # Update purchase status to failed
        purchase.status = PointPurchaseStatusEnum.FAILED.value
        purchase.save(update_fields=['status'])
        return None

    op.success(f"Paystack initiated, reference: {ref} for user: {user.first_name or user.email}")
    return result["data"]["authorization_url"]


def verify_paystack_payment(reference):
    """
    Verify Paystack payment and complete the purchase.
    """
    op = OperationLogger("PaystackVerify.verify_paystack_payment", reference=reference)
    op.start()

    # 1. Verify with Paystack
    url = f"{settings.PAYSTACK_VERIFY_URL}/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

    try:
        response = requests.get(url, headers=headers)
        result = response.json()
    except Exception as e:
        op.fail(f"Verification request error for reference: {reference}:: {str(e)}")
        return {"success": False, "error": str(e)}

    if response.status_code != 200 or not result.get("status"):
        op.fail(f"Verification failed for reference: {reference}:", exc=result)
        return {"success": False, "error": result.get("message", "Verification failed")}

    data = result.get("data", {})
    if data.get("status") != "success":
        op.fail(f"Transaction was not successful for reference: {reference}:", exc=data)
        return {"success": False, "error": "Transaction was not successful"}

    # 2. Update purchase record
    try:
        with transaction.atomic():
            purchase = PointPurchase.objects.select_for_update().get(
                payment_reference=reference,
                status=PointPurchaseStatusEnum.PENDING.value
            )
    except PointPurchase.DoesNotExist:
        op.fail(f"Purchase not found or already processed for reference: {reference}:")
        return {"success": False, "error": "Purchase not found or already processed"}

    # Mark as completed
    purchase.status = PointPurchaseStatusEnum.COMPLETED.value
    purchase.completed_at = timezone.now()
    purchase.save(update_fields=['status', 'completed_at'])

    # Add points to user
    points_awarded = purchase.points_awarded
    UpdatePointsService.update_points(
        user=purchase.user,
        points=points_awarded,
        action=ConstantHelper.POINT_ADDITION,
        transaction_type=PointTransactionTypeEnum.PURCHASE.value,
        description=f"Purchased {points_awarded} points via Paystack",
        reference=purchase.payment_reference,
        purchase=purchase,
    )

    create_notification(
        user=purchase.user,
        notification_type=NotificationEnum.TRANSACTION.value,
        title="Payment Update",
        message=f"Purchased {points_awarded} points via Paystack was successful",
        action_url="/student/buy-points.html"
    )

    op.success(f"Purchase completed: {purchase.id} for user: {purchase.user.first_name or purchase.user.email}")
    return {
        "success": True,
        "message": "Payment confirmed and points added successfully.",
        "purchase": {
            "purchase_id": purchase.id,
            "points_awarded": purchase.points_awarded,
            "amount_paid": float(purchase.amount_paid),
        }
    }