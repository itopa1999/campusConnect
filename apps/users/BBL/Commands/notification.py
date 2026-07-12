

from apps.users.models import Notification
from utils.base_result import BaseResultWithData
from utils.log_helpers import OperationLogger


class NotificationCommand:
    @staticmethod
    def mark_as_read(user, notification_id) -> BaseResultWithData:
        """Mark a specific notification as read for the user."""
        op = OperationLogger(f"NotificationCommand.mark_as_read for user: {user.first_name or user.email}", data={"notification_id": notification_id})
        op.start()
        try:
            notification = Notification.objects.get(id=notification_id, user=user, is_deleted=False)
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            op.success(f"Notification: {notification_id} mark_as_read successfully for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Notification marked as read successfully",
                status_code=200
            )

        except Notification.DoesNotExist:
            op.fail(f"Notification ID {notification_id} not found for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Notification not found",
                status_code=404
            )

    @staticmethod
    def mark_all_as_read(user) -> BaseResultWithData:
        """Mark all notifications as read for the user."""
        op = OperationLogger(f"NotificationCommand.mark_all_as_read for user: {user.first_name or user.email}", data={"user": user.first_name or user.email})
        op.start()
        updated_count = Notification.objects.filter(user=user, is_read=False, is_deleted=False).update(is_read=True)
        op.success(f"Notification mark_all_as_read successfully for user: {user.first_name or user.email}")
        return BaseResultWithData(
            message=f"{updated_count} notifications marked as read successfully",
            status_code=200
        )
    
    @staticmethod
    def delete_notification(user, notification_id) -> BaseResultWithData:
        """Mark as deleted"""
        op = OperationLogger(f"NotificationCommand.delete_notification for user: {user.first_name or user.email}", data={"notification_id": notification_id})
        op.start()
        try:
            notification = Notification.objects.get(id=notification_id, user=user, is_deleted=False)
            notification.is_deleted = True
            notification.save(update_fields=['is_deleted'])
            op.success(f"Notification: {notification_id} delete_notification successfully for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Notification deleted successfully",
                status_code=200
            )
        except Notification.DoesNotExist:
            op.fail(f"Notification ID {notification_id} not found for user: {user.first_name or user.email}")
            return BaseResultWithData(
                message="Notification not found",
                status_code=404
            )

    @staticmethod
    def delete_all_notifications(user) -> BaseResultWithData:
        """delete all notifications for the user."""
        op = OperationLogger(f"NotificationCommand.delete_all_notifications for for user: {user.first_name or user.email}", data={"user": user.first_name or user.email})
        op.start()
        updated_count = Notification.objects.filter(user=user, is_read=False, is_deleted=False).update(is_deleted=True)
        op.success(f"Notification delete_all_notifications successfully for user: {user.first_name or user.email}")
        return BaseResultWithData(
            message=f"{updated_count} notifications deleted successfully",
            status_code=200
        )