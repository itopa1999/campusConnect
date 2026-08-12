from django.utils import timezone
import secrets
from django.conf import settings
from django.urls import reverse
import requests as req
from django.db import transaction

from apps.users.models import PointPurchase
from utils.constant_helper import ConstantHelper
from utils.enums import NotificationEnum, PointPurchaseStatusEnum, PointTransactionTypeEnum
from utils.helpers import UpdatePointsService, create_notification
from utils.log_helpers import OperationLogger

# from apps.aso.models import Cart, Order, OrderItem, OrderTracking
# from utils.Tasks.process_order import process_paystack_order
# from utils.enum import PaymentGateway, PaymentStatus
# from utils.log_helpers import OperationLogger


def initiate_flutterwave(request, user, package):
    """
    Initialize Flutterwave payment
    """
    op = OperationLogger(f"FlutterwavePayment.initiate_flutterwave for user: {user.first_name or user.email} -- amount: {package.price}", data = {"package_id": package.id})
    op.start()

    ref = secrets.token_urlsafe(15)
    
    try:
        with transaction.atomic():
            purchase = PointPurchase.objects.create(
                user=user,
                package=package,
                points_awarded=package.points,
                amount_paid=package.price,
                payment_reference=ref,
                status=PointPurchaseStatusEnum.PENDING.value,
                gateway = ConstantHelper.FLUTTERWAVE
            )
    except Exception as e:
        op.fail(f"Failed to create purchase record for package: {package.description}: user: {user.first_name or user.email}: {str(e)}")
        return None

    
    amount = float(package.price)
    
    redirect_url = request.build_absolute_uri(
        reverse('flutterwave-points-confirm', kwargs={"reference": ref})
    )
        
    flutterwave_data = {
        "tx_ref": ref,
        "amount": amount,
        "currency": "NGN",
        "customer": {
            "email": user.email,
            "phonenumber": user.phone if user.phone else "",
            "name": f"{user.first_name if user.first_name else ''} {user.last_name if user.last_name else ''}"
        },
        "customizations": {
            "title": "Point Purchase Payment",
            "description": f"Payment for order {ref}",
            "logo": ""
        },
        "meta": {
            "purchase_id": purchase.id,
            "package_id": package.id,
            "user_id": user.id,
        },
        "redirect_url": redirect_url,
    }
    
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    flutterwave_url = f"{settings.FLUTTERWAVE_INITIALIZE_URL}"

    try:
        response = req.post(flutterwave_url, headers=headers, json=flutterwave_data)
        result = response.json()
    except Exception as e:
        op.fail(f"Flutterwave initialization error for package: {package.description}: user: {user.first_name or user.email}: {str(e)}")
        return None
    
    if response.status_code == 200 and result.get("status") == "success":
        op.success(f"Flutterwave initialized, reference: {ref} for user: {user.first_name or user.email}")
        return result["data"]["link"]
    
    op.fail(f"Flutterwave initialization failed for package: {package.description}: user: {user.first_name or user.email}:")
    return None
            

def validate(reference):
    """
    Validate Flutterwave payment using transaction reference
    """
    op = OperationLogger("FlutterwaveValidate.validate", reference=reference)
    op.start()
    
    # Get the transaction details from Flutterwave
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"
    }
    
    try:
        # Flutterwave requires querying by tx_ref or transaction ID
        url = f"{settings.FLUTTERWAVE_VERIFY_URL}?tx_ref={reference}"
        response = req.get(url, headers=headers)
        result = response.json()
    except Exception as e:
        op.fail(f"Flutterwave verification request error for reference: {reference}: {str(e)}")
        return {"success": False, "error": str(e)}
        
    # Check if verification is successful
    if response.status_code != 200 or result["status"] != "success":
        op.fail(f"Flutterwave verification failed for reference: {reference}:")
        return {"success": False, "error": "Invalid or unsuccessful transaction."}
    
    transaction_data = result["data"]
    
    # Verify payment was successful
    if transaction_data.get("status") != "successful":
        op.fail(f"Transaction status is not successful for reference: {reference}:")
        return {"success": False, "error": "Transaction not successful."}
    
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
        description=f"Purchased {points_awarded} points via flutterwave",
        reference=purchase.payment_reference,
        purchase=purchase,
    )

    create_notification(
        user=purchase.user,
        notification_type=NotificationEnum.TRANSACTION.value,
        title="Payment Update",
        message=f"Purchased {points_awarded} points via flutterwave was successful",
        action_url="/student/buy-point.html"
    )

    
    op.success(f"Transaction validated and order confirmed for user: {purchase.user.first_name or purchase.user.email}")
    return {
        "success": True,
        "message": "Payment confirmed successfully.",
        "purchase": {
            "purchase_id": purchase.id,
            "points_awarded": purchase.points_awarded,
            "amount_paid": float(purchase.amount_paid),
            'notification': True
            }
    }
