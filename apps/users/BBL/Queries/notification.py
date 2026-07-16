


from apps.users.models import Notification
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from utils.helpers import humanize_date


class NotificationQueries:
    @staticmethod
    def get_notification(request, user) -> BaseResultWithData:
        """Retrieve paginated notifications for a user."""
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
            
        cache_key = CacheKeysEnum.format(CacheKeysEnum.NOTIFICATIONS, user_id=user.id, page=page)

        cached_data = GlobalCache.get(cache_key)
        if cached_data:
            return BaseResultWithData(
                message="Header notifications retrieved successfully",
                data=cached_data,
                status_code=200
            )
        
        queryset = Notification.objects.filter(
            user=user,
            is_deleted=False
        ).select_related('user').order_by('-created_at')

        unread_messages_counts = queryset.filter(is_read = False).count()

        # Pagination logic
        paginator = Paginator(queryset, per_page)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        notifications_list= []
        for notification in page_obj.object_list:
            notifications_list.append({
                "id": notification.id,
                "notification_type": notification.notification_type,
                "title": notification.title,
                "message": notification.message,
                "is_read": notification.is_read,
                "action_url": notification.action_url,
                "created_at": humanize_date(notification.created_at),
            })

        result_data = {
            "notifications": notifications_list,
            "unread_messages_counts": unread_messages_counts,
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous()
        }

        GlobalCache.set(cache_key, result_data)

        return BaseResultWithData(
            message="Notifications retrieved successfully",
            data=result_data,
            status_code=200
        )
    

    @staticmethod
    def get_notifications_header(request, user) -> BaseResultWithData:
        """Retrieve the latest notifications for the header display."""

        cache_key = CacheKeysEnum.format(CacheKeysEnum.NOTIFICATION_HEADER, user_id=user.id)
        cached_data = GlobalCache.get(cache_key)
        if cached_data:
            return BaseResultWithData(
                message="Notifications retrieved successfully",
                data=cached_data,
                status_code=200
            )

        qs = Notification.objects.filter(
            user=user,
            is_deleted=False
        ).select_related('user')

        unread_messages_counts = qs.filter(is_read = False).count()
        queryset = qs.order_by('-created_at')[:5]
        
        notifications_list = []
        for notification in queryset:
            notifications_list.append({
                "id": notification.id,
                "notification_type": notification.notification_type,
                "title": notification.title,
                "message": notification.message,
                "is_read": notification.is_read,
                "action_url": notification.action_url,
                "created_at": humanize_date(notification.created_at),
            })

        result_data = {
            "notifications": notifications_list,
            "unread_messages_counts":unread_messages_counts
        }

        GlobalCache.set(cache_key, result_data)

        return BaseResultWithData(
            message="Header notifications retrieved successfully",
            data=result_data,
            status_code=200
        )


    