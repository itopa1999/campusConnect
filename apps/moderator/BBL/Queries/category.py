from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.campus.models import Category
from utils.base_result import BaseResultWithData
from utils.log_helpers import OperationLogger


class CategoryQuery:
    @staticmethod
    def get_all_categories(request, filters=None)-> BaseResultWithData:
        op = OperationLogger("ModeratorCategoryQuery.get_all_categories", user=request.user.id)
        op.start()

        if filters is None:
            filters = request.GET.dict()
        else:
            filters = dict(filters)

        page = filters.get('page', 1) if filters else request.GET.get('page', 1)
        per_page = filters.get('per_page', 20) if filters else request.GET.get('per_page', 20)
        try:
            page = int(page)
            per_page = int(per_page)
            if per_page < 1:
                per_page = 1
            if per_page > 100:
                per_page = 100
        except (ValueError, TypeError):
            page = 1
            per_page = 20

        queryset = Category.objects.filter(is_deleted=False)

        # Search
        search = filters.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        queryset = queryset.order_by('sort_order', 'name')
        paginator = Paginator(queryset, per_page)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        items = []
        for cat in page_obj:
            items.append({
                'id': cat.id,
                'name': cat.name,
                'slug': cat.slug,
                'icon': cat.icon,
                'description': cat.description,
                'sort_order': cat.sort_order,
                'is_deleted': cat.is_deleted,
                'listing_count': cat.listings.filter(is_deleted=False).count(),
            })

        op.success(f"Retrieved {len(items)} categories")
        return BaseResultWithData(
            message="Categories retrieved successfully",
            data={
                'items': items,
                'pagination': {
                    "page": page_obj.number,
                    "per_page": per_page,
                    "total_pages": paginator.num_pages,
                    "total_items": paginator.count,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                }
            },
            status_code=200
        )

    @staticmethod
    def get_category_detail(request, category_id)-> BaseResultWithData:
        op = OperationLogger("ModeratorCategoryQuery.get_category_detail", category_id=category_id)
        op.start()

        try:
            cat = Category.objects.get(id=category_id, is_deleted=False)
        except Category.DoesNotExist:
            op.fail(f"Category {category_id} not found")
            return BaseResultWithData(
                message="Category not found",
                data=None,
                status_code=404
            )
        
        listings = cat.listings.filter(is_deleted=False)
        listings_data = [
            {
                'id': listing.id,
                'title': listing.title,
                'description': listing.description,
                'price': float(listing.price) if listing.price else 0,
                'image':listing.image.url if listing.image else None,
                'listing_type': listing.listing_type,
                'status': listing.status,
                'is_ads_banner': listing.is_ads_banner,
                'is_hot_sales': listing.is_hot_sales,
                'auto_reactivate': listing.auto_reactivate, 
                'expires_at': listing.expires_at.isoformat() if listing.expires_at else None,
                'is_deleted': listing.is_deleted,
                'created_at': listing.created_at.isoformat(),
            }
            for listing in listings
        ]
        listings_count = listings.count() 


        data = {
            'id': cat.id,
            'name': cat.name,
            'slug': cat.slug,
            'icon': cat.icon,
            'description': cat.description,
            'sort_order': cat.sort_order,
            'is_deleted': cat.is_deleted,
            'listing_count': listings_count,
            'listings_data': listings_data,
            'created_at': cat.created_at.isoformat(),
        }

        op.success(f"Retrieved category {category_id}")
        return BaseResultWithData(
            message="Category details retrieved successfully",
            data=data,
            status_code=200
        )