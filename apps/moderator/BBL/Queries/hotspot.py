from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.campus.models import CampusHotspot
from utils.base_result import BaseResultWithData
from utils.log_helpers import OperationLogger
from django.db.models import Count, Q 

class HotspotQuery:
    @staticmethod
    def get_all_hotspots(request, filters=None):
        op = OperationLogger("ModeratorHotspotQuery.get_all_hotspots", user=request.user.id)
        op.start()

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

        queryset = CampusHotspot.objects.filter(is_deleted=False).annotate(
            listing_count=Count('listings', filter=Q(listings__is_deleted=False))
        )

        # Search
        search = filters.get('search') if filters else None
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
        for hot in page_obj:
            items.append({
                'id': hot.id,
                'name': hot.name,
                'description': hot.description,
                'sort_order': hot.sort_order,
                'is_deleted': hot.is_deleted,
                'listing_count': hot.listing_count
            })

        op.success(f"Retrieved {len(items)} hostpots")
        return BaseResultWithData(
            message="hotspots retrieved successfully",
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
    def get_hotspot_id_detail(request, hotspot_id):
        op = OperationLogger("ModeratorHotspotQuery.get_hotspot_id_detail", hotspot_id=hotspot_id)
        op.start()

        try:
            hot = CampusHotspot.objects.get(id=hotspot_id, is_deleted=False)
        except CampusHotspot.DoesNotExist:
            op.fail(f"Hotspot {hotspot_id} not found")
            return BaseResultWithData(
                message="Hotspot not found",
                data=None,
                status_code=404
            )
        
        listings = hot.listings.filter(is_deleted=False)
        listings_data = [
            {
                'id': listing.id,
                'title': listing.title,
                'description': listing.description,
                'price': float(listing.price) if listing.price else 0,
                'image':request.build_absolute_uri(listing.image.url) if listing.image else None,
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
        listings_count = len(listings_data) 


        data = {
            'id': hot.id,
            'name': hot.name,
            'description': hot.description,
            'sort_order': hot.sort_order,
            'is_deleted': hot.is_deleted,
            'listings_count': listings_count,
            'listings_data': listings_data,
            'created_at': hot.created_at.isoformat(),
        }

        op.success(f"Retrieved hotspot {hotspot_id}")
        return BaseResultWithData(
            message="Hotspot details retrieved successfully",
            data=data,
            status_code=200
        )