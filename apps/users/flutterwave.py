from django.utils import timezone
import json
import secrets
from django.conf import settings
from django.urls import reverse
import requests as req
from django.db import transaction

from utils.log_helpers import OperationLogger

# from apps.aso.models import Cart, Order, OrderItem, OrderTracking
# from utils.Tasks.process_order import process_paystack_order
# from utils.enum import PaymentGateway, PaymentStatus
# from utils.log_helpers import OperationLogger


def initiate_flutterwave(request, user, cart_id, data, order_id=None):
    """
    Initialize Flutterwave payment
    """
    op = OperationLogger(
        "FlutterwaveInitiate",
        user=user.id if user else "Anonymous",
        cart_id=cart_id,
        order_id=order_id,
        data=data
    )
    op.start()
    
    with transaction.atomic():    
        ref = secrets.token_urlsafe(15)
        
        # If order_id is provided (retry), fetch existing order
        if order_id:
            try:
                order = Order.objects.get(id=order_id, is_deleted=False)
                amount = float(order.total)
            except Order.DoesNotExist:
                op.fail("Order not found for retry")
                return None
        else:
            # New order flow
            amount = float(data["total"])
        
        redirect_url = request.build_absolute_uri(
            reverse('flutterwave-confirm', kwargs={"reference": ref})
        )
            
        flutterwave_data = {
            "tx_ref": ref,
            "amount": amount,
            "currency": "NGN",
            "customer": {
                "email": user.email,
                "phonenumber": data.get("phone", "") if data else "",
                "name": f"{data.get('first_name', '') if data else ''} {data.get('last_name', '') if data else ''}"
            },
            "customizations": {
                "title": "Esther's Fabrics Order Payment",
                "description": f"Payment for order {ref}",
                "logo": ""
            },
            "meta": {
                "cart_id": cart_id,
            },
            "redirect_url": redirect_url,
        }
        
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        flutterwave_url = f"{settings.FLUTTERWAVE_INITIALIZE_URL}"
        response = req.post(flutterwave_url, headers=headers, json=flutterwave_data)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "success":
                
                # If retry (order_id provided), just update reference and return URL
                if order_id:
                    order.payment_reference = ref
                    order.payment_status = PaymentStatus.PENDING.name.lower()
                    order.save(update_fields=['payment_reference', 'payment_status'])
                    op.success(f"Flutterwave retry initialized for order {order.order_number}")
                    return response_data["data"]["link"]
                
                # New order flow
                 # Fetch cart and create order + order items immediately
                cart = Cart.objects.get(id=cart_id, is_deleted=False)
                
                order = Order.objects.create(
                    user=user,
                    subtotal=cart.subtotal(),
                    shipping_fee=cart.shipping_cost(),
                    discount=cart.discount(),
                    total=cart.total(),
                    other_info=data.get("otherInfo"),
                    payment_status=PaymentStatus.PENDING.name.lower(),
                    payment_reference=ref,
                    payment_method=PaymentGateway.FLUTTERWAVE.value,
                )
                
                # Create order items from cart items
                for cart_item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.current_price,
                        desc=cart_item.desc
                    )
                    
                try:
                    shipping_data = data
                    
                    process_paystack_order(order.id, ref, shipping_data)
                    
                    # Delete Cart and Items
                    cart.items.all().delete()
                    cart.delete()
            
                    op.success(f"Flutterwave initialization successful, order {order.order_number} created and processing")
                except Exception as e:
                    order.payment_status = PaymentStatus.FAILED.name.lower()
                    order.save(update_fields=['payment_status'])
                    op.fail(f"Order processing failed: {str(e)}")
                    return None
                
                return response_data["data"]["link"]
        
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
        
        print("Flutterwave validation response:", result)
        
        # Check if verification is successful
        if response.status_code != 200 or result["status"] != "success":
            op.fail("Flutterwave verification failed")
            return {"success": False, "error": "Invalid or unsuccessful transaction."}
        
        transaction_data = result["data"]
        
        # Verify payment was successful
        if transaction_data.get("status") != "successful":
            op.fail("Transaction status is not successful")
            return {"success": False, "error": "Transaction not successful."}
        
        meta = transaction_data.get("meta", {})

                
        with transaction.atomic():
            # Find existing order by payment reference
            order = Order.objects.filter(
                payment_reference=reference,
                payment_method=PaymentGateway.FLUTTERWAVE.value
            ).first()
            
            if not order:
                op.fail("Order not found for this payment reference")
                return {"success": False, "error": "Order not found for this payment reference."}
            
            # If order already confirmed, return it
            if order.payment_status == PaymentStatus.CONFIRMED.name.lower():
                op.success("Order already confirmed for this reference (retry)")
                return {
                    "success": True,
                    "message": "Payment already confirmed.",
                    "order": {
                        "id": order.id,
                        "order_number": order.order_number,
                        "amount": float(order.total),
                        "created_at": order.created_at
                    }
                }
            
            # Update order status to confirmed and process
            try:
                OrderTracking.objects.create(
                    order = order,
                    date = timezone.now(),
                    description = "Order has been placed and ready for processing."
                )
                order.payment_status = PaymentStatus.CONFIRMED.name.lower()
                order.save(update_fields=['payment_status'])
                op.success("Order confirmed")
            except Exception as e:
                order.payment_status = PaymentStatus.FAILED.name.lower()
                order.save(update_fields=['payment_status'])
                op.fail(f"Status update failed: {str(e)}")
                return {"success": False, "error": f"Order status update failed: {str(e)}"}
            
        op.success("Transaction validated and order confirmed")
        return {
            "success": True,
            "message": "Payment confirmed successfully.",
            "order": {
                "id": order.id,
                "order_number": order.order_number,
                "amount": float(order.total),
                "created_at": order.created_at
            }
        }
        
    except Exception as e:
        op.fail(f"Flutterwave validation error: {str(e)}")
        return {"success": False, "error": str(e)}
