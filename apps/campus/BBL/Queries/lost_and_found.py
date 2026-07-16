from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.campus.models import LostAndFound
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum, LostAndFoundStatusEnum


class GetLostItemsQuery:
    @staticmethod
    def get_items(request) -> BaseResultWithData:
        """
        Fetch paginated lost items (excludes answer1 and answer2).
        """

        page = request.GET.get('page', 1)
        per_page = request.GET.get('per_page', 10)
        
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

        cache_key = CacheKeysEnum.format(CacheKeysEnum.LOST_ITEMS, page=page, per_page=per_page)

        cached_data = GlobalCache.get(cache_key)
        if cached_data:
            return BaseResultWithData(
                message="Lost items retrieved from cache",
                data=cached_data,
                status_code=200
            )

        try:
            # Base queryset – only non‑deleted items, ordered newest first
            queryset = LostAndFound.objects.filter(is_deleted=False, status=LostAndFoundStatusEnum.OPEN.value).order_by('-created_at')
            # queryset = LostAndFound.objects.filter(is_deleted=False).order_by('-created_at')
            paginator = Paginator(queryset, per_page)

            try:
                items_page = paginator.page(page)
            except PageNotAnInteger:
                items_page = paginator.page(1)
            except EmptyPage:
                items_page = paginator.page(paginator.num_pages)

            # Build safe data list (exclude answers)
            items_data = []
            for item in items_page:
                image_url = None
                if item.image:
                    image_url = request.build_absolute_uri(item.image.url)
                items_data.append({
                    'id': item.id,
                    'item_name': item.item_name,
                    'description': item.description,
                    'location': item.location,
                    'date_found': item.date_found.isoformat(),
                    'status': item.status,
                    'verification1': item.verification1,   # question 1 (safe)
                    'verification2': item.verification2,   # question 2 (safe)
                    'image': image_url,
                })

            response_data = {
                'items': items_data,
                'pagination': {
                    'current_page': items_page.number,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'per_page': per_page,
                    'has_next': items_page.has_next(),
                    'has_previous': items_page.has_previous(),
                    'next_page_number': items_page.next_page_number() if items_page.has_next() else None,
                    'previous_page_number': items_page.previous_page_number() if items_page.has_previous() else None,
                }
            }

            GlobalCache.set(cache_key, response_data)  

            return BaseResultWithData(
                message="Lost items retrieved successfully.",
                data=response_data,
                status_code=200
            )

        except Exception as e:
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )