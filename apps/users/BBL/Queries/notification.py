


from apps.users.models import Notification
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


class NotificationQueries:
    @staticmethod
    def get_notification(request, user, page=1, per_page=10) -> BaseResultWithData:
        """Retrieve paginated notifications for a user."""
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
                "created_at": notification.created_at.isoformat(),
            })

        result_data = {
            "notifications": notifications_list,
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

        queryset = Notification.objects.filter(
            user=user,
            is_deleted=False
        ).select_related('user').order_by('-created_at')[:5]

        notifications_list = []
        for notification in queryset:
            notifications_list.append({
                "id": notification.id,
                "notification_type": notification.notification_type,
                "title": notification.title,
                "message": notification.message,
                "is_read": notification.is_read,
                "action_url": notification.action_url,
                "created_at": notification.created_at.isoformat(),
            })

        result_data = {
            "notifications": notifications_list
        }

        GlobalCache.set(cache_key, result_data)

        return BaseResultWithData(
            message="Header notifications retrieved successfully",
            data=result_data,
            status_code=200
        )


    