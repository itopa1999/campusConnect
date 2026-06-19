from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.campus.models import LostAndFound
from utils.base_result import BaseResultWithData
from utils.log_helpers import OperationLogger


class GetLostItemsQuery:
    @staticmethod
    def get_items(page: int = 1, page_size: int = 10) -> BaseResultWithData:
        """
        Fetch paginated lost items (excludes answer1 and answer2).
        """
        op = OperationLogger("GetLostItemsQuery.get_items", data={'page': page, 'page_size': page_size})
        op.start()

        try:
            # Base queryset – only non‑deleted items, ordered newest first
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
                items_data.append({
                    'id': item.id,
                    'item_name': item.item_name,
                    'description': item.description,
                    'location': item.location,
                    'date_found': item.date_found.isoformat(),
                    'status': item.status,
                    'verification1': item.verification1,   # question 1 (safe)
                    'verification2': item.verification2,   # question 2 (safe)
                    'image': item.image.url if item.image else None,
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

            op.success(f"Retrieved {len(items_data)} items (page {page})")
            return BaseResultWithData(
                message="Lost items retrieved successfully.",
                data=response_data,
                status_code=200
            )

        except Exception as e:
            op.fail("Unexpected error", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )