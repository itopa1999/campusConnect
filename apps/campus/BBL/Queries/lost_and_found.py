from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.campus.models import LostAndFound
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum


class GetLostItemsQuery:
    @staticmethod
    def get_items(request, page: int = 1, page_size: int = 10) -> BaseResultWithData:
        """
        Fetch paginated lost items (excludes answer1 and answer2).
        """
        cache_key = CacheKeysEnum.format(CacheKeysEnum.LOST_ITEMS, page=page, page_size=page_size)

        cached_data = GlobalCache.get(cache_key)
        if cached_data:
            return BaseResultWithData(
                message="Lost items retrieved from cache",
                data=cached_data,
                status_code=200
            )

        try:
            # Base queryset – only non‑deleted items, ordered newest first
            # queryset = LostAndFound.objects.filter(is_deleted=False, status=LostAndFoundStatusEnum.OPEN.value).order_by('-created_at')
            queryset = LostAndFound.objects.filter(is_deleted=False).order_by('-created_at')
            paginator = Paginator(queryset, page_size)

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
                    'created_at': item.created_at.isoformat(),
                    'modified_at': item.modified_at.isoformat(),
                    # answer1 and answer2 are intentionally omitted
                })

            response_data = {
                'items': items_data,
                'pagination': {
                    'current_page': items_page.number,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'page_size': page_size,
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