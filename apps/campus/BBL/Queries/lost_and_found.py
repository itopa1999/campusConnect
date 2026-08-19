from asgiref.sync import sync_to_async
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.campus.models import LostAndFound
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum, LostAndFoundStatusEnum
from django.db.models import Q
import asyncio


class GetLostItemsQuery:
    @staticmethod
    async def get_items(request, filters=None) -> BaseResultWithData:
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

        filter_keys = ['search']
        filter_values = []
        for key in filter_keys:
            value = filters.get(key)
            if value is not None:
                filter_values.append((key, value.strip() if isinstance(value, str) else value))
        filter_values.sort(key=lambda x: x[0])
        filter_str = '&'.join(f"{k}={v}" for k, v in filter_values)

        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.LOST_ITEMS,
            page=page,
            per_page=per_page,
            filters=filter_str
        )

        @sync_to_async
        def build_lost_items_data():
            queryset = LostAndFound.objects.filter(
                is_deleted=False,
                status=LostAndFoundStatusEnum.OPEN.value
            )

            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    Q(item_name__icontains=search) |
                    Q(description__icontains=search) |
                    Q(location__icontains=search)
                )

            queryset = queryset.order_by('-created_at')

            paginator = Paginator(queryset, per_page)
            try:
                items_page = paginator.page(page)
            except PageNotAnInteger:
                items_page = paginator.page(1)
            except EmptyPage:
                items_page = paginator.page(paginator.num_pages)

            items_data = []
            for item in items_page:
                image_url = item.image.url if item.image else None
                items_data.append({
                    'id': item.id,
                    'item_name': item.item_name,
                    'description': item.description,
                    'location': item.location,
                    'date_found': item.date_found.isoformat(),
                    'status': item.status,
                    'verification1': item.verification1,
                    'verification2': item.verification2,
                    'image': image_url,
                })

            return {
                'items': items_data,
                'pagination': {
                    "page": items_page.number,
                    "per_page": per_page,
                    "total_pages": paginator.num_pages,
                    "total_items": paginator.count,
                    "has_next": items_page.has_next(),
                    "has_previous": items_page.has_previous(),
                }
            }

        try:
            data = await GlobalCache.aget_or_set(
                key=cache_key,
                callback=build_lost_items_data,
                timeout=3600,
                lock_timeout=30,
                max_wait=5.0,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )

        return BaseResultWithData(
            message="Lost items retrieved successfully.",
            data=data,
            status_code=200
        )