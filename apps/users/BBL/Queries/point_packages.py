from apps.users.models import PointPackage, PointPurchase, PointTransaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum


class PointPackagesQueries:

    @staticmethod
    def _format_price_per_point(price_per_point):
        """Helper to round price per point to 2 decimal places."""
        return round(price_per_point, 2)

    @staticmethod
    def get_point_packages(request=None):
        """Return serialized list of point packages."""

        cache_key = CacheKeysEnum.POINT_PACKAGES.value

        def build_point_packages_data():
            """Heavy computation callback – runs only on cache miss."""
            queryset = PointPackage.objects.filter(is_deleted=False).order_by('sort_order', 'points')
            return [
                {
                    "id": pkg.id,
                    "points": pkg.points,
                    "price": float(pkg.price),
                    "description": pkg.description,
                    "is_popular": pkg.is_popular,
                    "is_best_value": pkg.is_best_value,
                    "sort_order": pkg.sort_order,
                    "price_per_point": PointPackagesQueries._format_price_per_point(pkg.price_per_point),
                    "savings_percentage": pkg.savings_percentage,
                }
                for pkg in queryset
            ]

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_point_packages_data,
            timeout=86400,
            lock_timeout=30,
            max_wait=5.0,
        )

        return data
    
    @staticmethod
    def get_purchases(user, page=1, per_page=10)-> BaseResultWithData:
        """Retrieve paginated purchase history for a user."""

        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.PURCHASES,
            user_id=user.id,
            page=page,
            per_page=per_page
        )

        def build_purchases_data():
            """Heavy computation callback – runs only on cache miss."""
            queryset = PointPurchase.objects.filter(
                user=user
            ).select_related('package').order_by('-created_at')

            paginator = Paginator(queryset, per_page)
            try:
                page_obj = paginator.page(page)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            purchase_list = []
            for purchase in page_obj.object_list:
                pkg = purchase.package
                purchase_list.append({
                    'id': purchase.id,
                    'package': {
                        'id': pkg.id,
                        'points': pkg.points,
                        'price': float(pkg.price),
                        'description': pkg.description,
                        'is_popular': pkg.is_popular,
                        'is_best_value': pkg.is_best_value,
                        'price_per_point': PointPackagesQueries._format_price_per_point(pkg.price_per_point),
                        'savings_percentage': pkg.savings_percentage,
                    },
                    'gateway': purchase.gateway,
                    'payment_reference': purchase.payment_reference,
                    'points_awarded': purchase.points_awarded,
                    'amount_paid': float(purchase.amount_paid),
                    'status': purchase.status,
                    'created_at': purchase.created_at.isoformat(),
                })

            return {
                'items': purchase_list,
                'page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_purchases_data,
            timeout=86400,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Purchases retrieved successfully",
            data=data,
            status_code=200
        )
    

    @staticmethod
    def get_transactions(user, page=1, per_page=10)-> BaseResultWithData:
        """Retrieve paginated transaction history for a user."""

        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.TRANSACTIONS,
            user_id=user.id,
            page=page,
            per_page=per_page
        )

        def build_transactions_data():
            """Heavy computation callback – runs only on cache miss."""
            queryset = PointTransaction.objects.filter(
                user=user
            ).select_related('purchase').order_by('-created_at')

            paginator = Paginator(queryset, per_page)
            try:
                page_obj = paginator.page(page)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            transaction_list = []
            for txn in page_obj.object_list:
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
                'page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_transactions_data,
            timeout=300, 
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Transactions retrieved successfully",
            data=data,
            status_code=200
        )