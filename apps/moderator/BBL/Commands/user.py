from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.moderator.models import UserModeration, ModeratorAction
from utils.base_result import BaseResultWithData
from utils.enums import ContentTypeEnum, ModeratorActionTypeEnum
from utils.log_helpers import OperationLogger

User = get_user_model()


class UserCommand:
    @staticmethod
    def _ensure_moderation(user):
        """Ensure UserModeration exists for the user."""
        moderation, created = UserModeration.objects.get_or_create(user=user)
        return moderation

    # ─── Issue Warning ──────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def issue_warning(request, user_id, validated_data):
        """
        Issue a formal warning to a user.
        Increments warning_count.
        """
        op = OperationLogger("ModeratorUserCommand.issue_warning", user_id=user_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for issuing a warning",
                data=None,
                status_code=400
            )

        try:
            user = User.objects.all_including_deleted().get(id=user_id)
        except User.DoesNotExist:
            op.fail("User not found")
            return BaseResultWithData(
                message="User not found",
                data=None,
                status_code=404
            )

        moderation = UserCommand._ensure_moderation(user)
        moderation.warning_count += 1
        moderation.save(update_fields=['warning_count'])

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.WARNING.value,
            content_type=ContentTypeEnum.USER.value,
            content_id=user.id,
            reason=reason,
            metadata={
                'warning_count': moderation.warning_count,
                'user_email': user.email,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"Warning issued to user {user_id}")
        return BaseResultWithData(
            message="Warning issued successfully",
            data={'user_id': user.id, 'warning_count': moderation.warning_count},
            status_code=200
        )

    # ─── Toggle Suspend ─────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def toggle_suspend_user(request, user_id, validated_data):
        """
        Suspend or unsuspend a user.
        If suspended, set is_active=False and store suspension details.
        If unsuspended, set is_active=True and clear suspension fields.
        """
        op = OperationLogger("ModeratorUserCommand.toggle_suspend_user", user_id=user_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for suspending/unsuspending",
                data=None,
                status_code=400
            )

        duration_hours = validated_data.get('duration_hours', 24)  # default 24h

        try:
            user = User.objects.all_including_deleted().get(id=user_id)
        except User.DoesNotExist:
            op.fail("User not found")
            return BaseResultWithData(
                message="User not found",
                data=None,
                status_code=404
            )

        moderation = UserCommand._ensure_moderation(user)

        if moderation.is_suspended:
            # ─── Unsuspend ─────────────────────────────────────────
            moderation.is_suspended = False
            moderation.suspended_until = None
            moderation.save(update_fields=['is_suspended', 'suspended_until'])
            user.is_active = True
            user.save(update_fields=['is_active'])

            action_type = ModeratorActionTypeEnum.REINSTATE.value
            message_text = "User unsuspended"

            ModeratorAction.objects.create(
                moderator=request.user,
                action_type=action_type,
                content_type=ContentTypeEnum.USER.value,
                content_id=user.id,
                reason=reason,
                metadata={
                    'user_email': user.email,
                    'was_suspended': True,
                    'action': 'unsuspend'
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            op.success(f"User {user_id} unsuspended")
            return BaseResultWithData(
                message=message_text,
                data={'user_id': user.id, 'is_suspended': False},
                status_code=200
            )
        else:
            # ─── Suspend ───────────────────────────────────────────
            try:
                duration_hours = int(duration_hours)
            except (ValueError, TypeError):
                duration_hours = 24

            suspended_until = timezone.now() + timezone.timedelta(hours=duration_hours)

            moderation.is_suspended = True
            moderation.suspended_until = suspended_until
            moderation.save(update_fields=['is_suspended', 'suspended_until'])
            user.is_active = False
            user.save(update_fields=['is_active'])

            ModeratorAction.objects.create(
                moderator=request.user,
                action_type=ModeratorActionTypeEnum.SUSPEND.value,
                content_type=ContentTypeEnum.USER.value,
                content_id=user.id,
                reason=reason,
                metadata={
                    'user_email': user.email,
                    'suspended_until': suspended_until.isoformat(),
                    'duration_hours': duration_hours,
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            op.success(f"User {user_id} suspended until {suspended_until}")
            return BaseResultWithData(
                message=f"User suspended until {suspended_until.strftime('%Y-%m-%d %H:%M')}",
                data={'user_id': user.id, 'is_suspended': True, 'suspended_until': suspended_until.isoformat()},
                status_code=200
            )

    # ─── Toggle Ban ──────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def toggle_ban_user(request, user_id, validated_data):
        """
        Ban or unban a user.
        If banned, set is_active=False and store ban details.
        If unbanned, set is_active=True and clear ban fields.
        """
        op = OperationLogger("ModeratorUserCommand.toggle_ban_user", user_id=user_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for banning/unbanning",
                data=None,
                status_code=400
            )

        try:
            user = User.objects.all_including_deleted().get(id=user_id)
        except User.DoesNotExist:
            op.fail("User not found")
            return BaseResultWithData(
                message="User not found",
                data=None,
                status_code=404
            )

        moderation = UserCommand._ensure_moderation(user)

        if moderation.is_banned:
            # ─── Unban ─────────────────────────────────────────────
            moderation.is_banned = False
            moderation.banned_at = None
            moderation.ban_reason = reason
            moderation.save(update_fields=['is_banned', 'banned_at', 'ban_reason'])
            user.is_active = True
            user.save(update_fields=['is_active'])

            ModeratorAction.objects.create(
                moderator=request.user,
                action_type=ModeratorActionTypeEnum.REINSTATE.value,
                content_type=ContentTypeEnum.USER.value,
                content_id=user.id,
                reason=reason,
                metadata={
                    'user_email': user.email,
                    'was_banned': True,
                    'action': 'unban'
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            op.success(f"User {user_id} unbanned")
            return BaseResultWithData(
                message="User unbanned",
                data={'user_id': user.id, 'is_banned': False},
                status_code=200
            )
        else:
            # ─── Ban ───────────────────────────────────────────────
            moderation.is_banned = True
            moderation.banned_at = timezone.now()
            moderation.ban_reason = reason
            moderation.save(update_fields=['is_banned', 'banned_at', 'ban_reason'])
            user.is_active = False
            user.save(update_fields=['is_active'])

            ModeratorAction.objects.create(
                moderator=request.user,
                action_type=ModeratorActionTypeEnum.BAN.value,
                content_type=ContentTypeEnum.USER.value,
                content_id=user.id,
                reason=reason,
                metadata={
                    'user_email': user.email,
                    'banned_at': moderation.banned_at.isoformat(),
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            op.success(f"User {user_id} banned")
            return BaseResultWithData(
                message="User banned permanently",
                data={'user_id': user.id, 'is_banned': True, 'banned_at': moderation.banned_at.isoformat()},
                status_code=200
            )

    # ─── Toggle Soft Delete ────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def toggle_delete_user(request, user_id, validated_data):
        """
        Soft delete or restore a user.
        """
        op = OperationLogger("ModeratorUserCommand.toggle_delete_user", user_id=user_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for toggling delete status",
                data=None,
                status_code=400
            )

        try:
            user = User.objects.all_including_deleted().get(id=user_id)
        except User.DoesNotExist:
            op.fail("User not found")
            return BaseResultWithData(
                message="User not found",
                data=None,
                status_code=404
            )

        old_deleted = user.is_deleted
        new_deleted = not old_deleted
        user.is_deleted = new_deleted
        user.save(update_fields=['is_deleted'])

        action_type = ModeratorActionTypeEnum.DELETE.value if new_deleted else ModeratorActionTypeEnum.REINSTATE.value
        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=action_type,
            content_type=ContentTypeEnum.USER.value,
            content_id=user.id,
            reason=reason,
            metadata={
                'old_is_deleted': old_deleted,
                'new_is_deleted': new_deleted,
                'user_email': user.email,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"User {user_id} delete toggled to {new_deleted}")
        return BaseResultWithData(
            message=f"User {'deleted' if new_deleted else 'restored'} successfully",
            data={'user_id': user.id, 'is_deleted': user.is_deleted},
            status_code=200
        )