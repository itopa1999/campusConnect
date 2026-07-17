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

        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.NOTIFICATIONS,
            user_id=user.id,
            page=page,
            per_page=per_page
        )

        def build_notifications_data():
            """Heavy computation callback – runs only on cache miss."""
            queryset = Notification.objects.filter(
                user=user,
                is_deleted=False
            ).select_related('user').order_by('-created_at')

            unread_messages_counts = queryset.filter(is_read=False).count()

            # Pagination logic
            paginator = Paginator(queryset, per_page)
            try:
                page_obj = paginator.page(page)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            notifications_list = []
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

            return {
                "notifications": notifications_list,
                "unread_messages_counts": unread_messages_counts,
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous()
            }

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_notifications_data,
            timeout=300,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Notifications retrieved successfully",
            data=data,
            status_code=200
        )
    
    @staticmethod
    def get_notifications_header(request, user) -> BaseResultWithData:
        """Retrieve the latest notifications for the header display."""

        cache_key = CacheKeysEnum.format(
            CacheKeysEnum.NOTIFICATION_HEADER,
            user_id=user.id
        )

        def build_header_notifications_data():
            """Heavy computation callback – runs only on cache miss."""
            qs = Notification.objects.filter(
                user=user,
                is_deleted=False
            ).select_related('user')

            unread_messages_counts = qs.filter(is_read=False).count()
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

            return {
                "notifications": notifications_list,
                "unread_messages_counts": unread_messages_counts
            }

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_header_notifications_data,
            timeout=120,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Header notifications retrieved successfully",
            data=data,
            status_code=200
        )