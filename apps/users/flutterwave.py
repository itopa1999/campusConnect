from django.utils import timezone
import json
import secrets
from django.conf import settings
from django.urls import reverse
import requests as req
from django.db import transaction

from apps.users.models import PointPurchase
from utils.constant_helper import ConstantHelper
from utils.enums import PointPurchaseStatusEnum, PointTransactionTypeEnum
from utils.helpers import UpdatePointsService
from utils.log_helpers import OperationLogger

# from apps.aso.models import Cart, Order, OrderItem, OrderTracking
# from utils.Tasks.process_order import process_paystack_order
# from utils.enum import PaymentGateway, PaymentStatus
# from utils.log_helpers import OperationLogger


def initiate_flutterwave(request, user, package):
    """
    Initialize Flutterwave payment
    """
    op = OperationLogger("FlutterwavePayment", user=user.id, package_id=package.id)
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
        op.fail(f"Failed to create purchase record: {str(e)}")
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
        op.fail(f"Flutterwave initialization error: {str(e)}")
        return None
    
    if response.status_code == 200 and result.get("status") == "success":
        op.success(f"Flutterwave initialized, reference: {ref}")
        return result["data"]["link"]
    
    op.fail("Flutterwave initialization failed")
    return None
            

def validate(reference):
    """
    Validate Flutterwave payment using transaction reference
    """
    op = OperationLogger("FlutterwaveValidate", reference=reference)
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
        op.fail(f"Flutterwave verification request error: {str(e)}")
        return {"success": False, "error": str(e)}
        
    # Check if verification is successful
    if response.status_code != 200 or result["status"] != "success":
        op.fail("Flutterwave verification failed")
        return {"success": False, "error": "Invalid or unsuccessful transaction."}
    
    transaction_data = result["data"]
    
    # Verify payment was successful
    if transaction_data.get("status") != "successful":
        op.fail("Transaction status is not successful")
        return {"success": False, "error": "Transaction not successful."}
    
    try:
        with transaction.atomic():
            purchase = PointPurchase.objects.select_for_update().get(
                payment_reference=reference,
                status=PointPurchaseStatusEnum.PENDING.value
            )
    except PointPurchase.DoesNotExist:
        op.fail("Purchase not found or already processed")
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
    op.success("Transaction validated and order confirmed")
    return {
        "success": True,
        "message": "Payment confirmed successfully.",
        "purchase": {
            "purchase_id": purchase.id,
            "points_awarded": purchase.points_awarded,
            "amount_paid": float(purchase.amount_paid),
            }
    }
