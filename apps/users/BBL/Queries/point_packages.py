from apps.users.models import PointPackage, PointPurchase, PointTransaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum
from utils.helpers import format_naira
from asgiref.sync import sync_to_async
import asyncio


class PointPackagesQueries:

    @staticmethod
    def _format_price_per_point(price_per_point) -> BaseResultWithData:
        """Helper to round price per point to 2 decimal places."""
        return round(price_per_point, 2)

    @staticmethod
    async def get_point_packages():
        """Return serialized list of point packages."""

        cache_key = CacheKeysEnum.POINT_PACKAGES.value

        @sync_to_async(thread_sensitive=False)
        def build_point_packages_data():
            """Heavy computation callback – runs only on cache miss."""
            queryset = PointPackage.objects.filter(is_deleted=False).order_by('sort_order', 'points')
            return [
                {
                    "id": pkg.id,
                    "points": pkg.points,
                    "price": format_naira(pkg.price),
                    "package_price": float(pkg.price),
                    "description": pkg.description,
                    "is_popular": pkg.is_popular,
                    "is_best_value": pkg.is_best_value,
                    "sort_order": pkg.sort_order,
                    "price_per_point": format_naira(pkg.price_per_point),
                    "savings_percentage": pkg.savings_percentage,
                }
                for pkg in queryset
            ]

        try:
            data = await GlobalCache.aget_or_set(
                key=cache_key,
                callback=build_point_packages_data,
                timeout=86400,
                lock_timeout=30,
                max_wait=5.0,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return BaseResultWithData(
                message=f"An error occurred: {str(e)}",
                status_code=500
            )

        return BaseResultWithData(
            message="point packages retrieved successfully",
            data=data,
            status_code=200
        )
    
    @staticmethod
    async def get_purchases(request, filters=None)-> BaseResultWithData:
        """Retrieve paginated purchase history for a user."""
        user = request.user
        if filters is None:
            filters = request.GET.dict()
        else:
            filters = dict(filters)
        
        page = filters.get('page', 1)
        per_page = filters.get('per_page', 10)
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
        try:
            per_page = int(per_page)
        except (ValueError, TypeError):
            per_page = 10
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        filter_keys = ['reference', 'status', 'gateway', 'points_awarded', 'date_from', 'date_to']
        filter_parts = []
        for key in filter_keys:
            value = filters.get(key)
            if value is not None and value != '':
                filter_parts.append(f"{key}={value}")
        filter_parts.sort()
        filter_str = '&'.join(filter_parts)

        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.PURCHASES,
            user_id=user.id,
            page=page,
            per_page=per_page,
            filters = filter_str
        )

        @sync_to_async(thread_sensitive=False)
        def build_purchases_data():
            """Heavy computation callback – runs only on cache miss."""
            queryset = PointPurchase.objects.filter(
                user=user
            ).select_related('package').order_by('-created_at')

            reference = filters.get("reference")
            if reference:
                queryset = queryset.filter(
                    payment_reference__icontains=reference
                )
            
            status = filters.get("status")
            if status:
                queryset = queryset.filter(
                    status__iexact=status
                )

            gateway = filters.get("gateway")
            if gateway:
                queryset = queryset.filter(
                    gateway__iexact=gateway
                )

            points_awarded = filters.get("points_awarded")
            if points_awarded:
                queryset = queryset.filter(
                    points_awarded=points_awarded
                )

            date_from = filters.get("date_from")
            if date_from:
                queryset = queryset.filter(
                    created_at__date__gte=date_from
                )

            date_to = filters.get("date_to")
            if date_to:
                queryset = queryset.filter(
                    created_at__date__lte=date_to
                )

            paginator = Paginator(queryset, per_page)
            try:
                page_obj = paginator.page(page)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            purchase_list = []
            for purchase in page_obj:
                purchase_list.append({
                    'id': purchase.id,
                    'gateway': purchase.gateway,
                    'payment_reference': purchase.payment_reference,
                    'points_awarded': purchase.points_awarded,
                    'amount_paid': format_naira(purchase.amount_paid),
                    'status': purchase.status,
                    'created_at': purchase.created_at.isoformat(),
                })

            return {
                'items': purchase_list,
                'pagination': {
                    "page": page_obj.number,
                    "per_page": per_page,
                    "total_pages": paginator.num_pages,
                    "total_items": paginator.count,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                }
            }
        try:
            data = await GlobalCache.aget_or_set(
                key=cache_key,
                callback=build_purchases_data,
                timeout=86400,
                lock_timeout=30,
                max_wait=5.0,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return BaseResultWithData(
                message=f"An error occurred: {str(e)}",
                status_code=500
            )

        return BaseResultWithData(
            message="Purchases retrieved successfully",
            data=data,
            status_code=200
        )
    

    @staticmethod
    async def get_transactions(request, filters=None)-> BaseResultWithData:
        """Retrieve paginated transaction history for a user."""
        user = request.user
        if filters is None:
            filters = request.GET.dict()
        else:
            filters = dict(filters)

        page = filters.get('page', 1)
        per_page = filters.get('per_page', 10)
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
        try:
            per_page = int(per_page)
        except (ValueError, TypeError):
            per_page = 10
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        filter_keys = ['transaction_type', 'reference', 'date_from', 'date_to']
        filter_parts = []
        for key in filter_keys:
            value = filters.get(key)
            if value is not None and value != '':
                filter_parts.append(f"{key}={value}")
        filter_parts.sort()
        filter_str = '&'.join(filter_parts)
        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.TRANSACTIONS,
            user_id=user.id,
            page=page,
            per_page=per_page,
            filters = filter_str
        )

        @sync_to_async(thread_sensitive=False)
        def build_transactions_data():
            """Heavy computation callback – runs only on cache miss."""
            queryset = PointTransaction.objects.filter(
                user=user
            ).select_related('purchase').order_by('-created_at')

            transaction_type = filters.get("transaction_type")
            if transaction_type:
                queryset = queryset.filter(
                    transaction_type__iexact=transaction_type
                )

            reference = filters.get("reference")
            if reference:
                queryset = queryset.filter(
                    reference__icontains=reference
                )

            date_from = filters.get("date_from")
            if date_from:
                queryset = queryset.filter(
                    created_at__date__gte=date_from
                )

            date_to = filters.get("date_to")
            if date_to:
                queryset = queryset.filter(
                    created_at__date__lte=date_to
                )

            paginator = Paginator(queryset, per_page)
            try:
                page_obj = paginator.page(page)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            transaction_list = []
            for txn in page_obj:
                transaction_list.append({
                    'id': txn.id,
                    'amount': txn.amount,
                    'balance_after': txn.balance_after,
                    'transaction_type': txn.transaction_type,
                    'transaction_type_display': txn.get_transaction_type_display(),
                    'description': txn.description,
                    'reference': txn.reference,
                    'purchase_id': txn.purchase.id if txn.purchase else None,
                    'created_at': txn.created_at.isoformat(),
                })

            return {
                'items': transaction_list,
                'pagination': {
                    "page": page_obj.number,
                    "per_page": per_page,
                    "total_pages": paginator.num_pages,
                    "total_items": paginator.count,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                }
            }

        try:
            data = await GlobalCache.aget_or_set(
                key=cache_key,
                callback=build_transactions_data,
                timeout=300, 
                lock_timeout=30,
                max_wait=5.0,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return BaseResultWithData(
                message=f"An error occurred: {str(e)}",
                status_code=500
            )

        return BaseResultWithData(
            message="Transactions retrieved successfully",
            data=data,
            status_code=200
        )