from django.db import transaction
from apps.campus.models import LostAndFound
from apps.moderator.models import FlaggedContent, ModeratorAction
from utils.base_result import BaseResultWithData
from utils.enums import ContentTypeEnum, LostAndFoundStatusEnum, ModeratorActionTypeEnum
from utils.log_helpers import OperationLogger
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class LostAndFoundCommand:
    @staticmethod
    @transaction.atomic
    def approve_lost_item(request, item_id, validated_data) -> BaseResultWithData:
        """
        Approve a pending lost_and_found_item.
        """
        op = OperationLogger("ModeratorLostAndFoundCommand.approve_lost_item", item_id=item_id)
        op.start()

        reason = validated_data.get('reason')

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for approving a lost_item",
                data=None,
                status_code=400
            )

        try:
            lost_item = LostAndFound.objects.select_for_update().get(
                id=item_id,
                is_deleted=False,
                status=LostAndFoundStatusEnum.PENDING.value
            )
        except LostAndFound.DoesNotExist:
            op.fail("lost_item not found or not pending")
            return BaseResultWithData(
                message="lost_item not found or not pending or is_deleted",
                data=None,
                status_code=404
            )

        old_status = lost_item.status
        lost_item.status = LostAndFoundStatusEnum.OPEN.value
        lost_item.save(update_fields=['status'])

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.APPROVE.value,
            content_type=ContentTypeEnum.LOST_ITEM.value,
            content_id=lost_item.id,
            reason=reason,
            metadata={
                'old_status': old_status,
                'new_status': lost_item.status,
                'lost_item_name': lost_item.item_name,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # TODO implement to notify the user.

        op.success(f"Lost Item {item_id} approved")
        return BaseResultWithData(
            message="Lost item approved successfully",
            data={'lost_item_id': lost_item.id, 'status': lost_item.status},
            status_code=200
        )

    # ─── Reject ──────────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def reject_lost_item(request, item_id, validated_data) -> BaseResultWithData:
        """
        Reject a pending lost item .
        """
        op = OperationLogger("ModeratorLostAndFoundCommand.reject_lost_item", item_id=item_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for rejecting a lost item",
                data=None,
                status_code=400
            )

        try:
            lost_item = LostAndFound.objects.select_for_update().get(
                id=item_id,
                is_deleted=False,
                status=LostAndFoundStatusEnum.PENDING.value
            )
        except LostAndFound.DoesNotExist:
            op.fail("Lost item not found or not pending")
            return BaseResultWithData(
                message="Lost item not found or not pending or is_deleted",
                data=None,
                status_code=404
            )

        old_status = lost_item.status
        lost_item.status = LostAndFoundStatusEnum.REJECT.value
        lost_item.save(update_fields=['status'])

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.REJECT.value,
            content_type=ContentTypeEnum.LOST_ITEM.value,
            content_id=lost_item.id,
            reason=reason,
            metadata={
                'old_status': old_status,
                'new_status': lost_item.status,
                'lost_item_name': lost_item.item_name,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # TODO implement to notify the user.

        op.success(f"Lost item {item_id} rejected")
        return BaseResultWithData(
            message="Lost item rejected",
            data={'lost_item_id': lost_item.id},
            status_code=200
        )

    # ─── Toggle Delete (soft delete / restore) ────────────────────
    @staticmethod
    @transaction.atomic
    def toggle_delete_lost_item(request, item_id, validated_data) -> BaseResultWithData:
        """
        Toggle soft-delete status.
        If currently deleted → restore; otherwise → soft delete.
        """
        op = OperationLogger("ModeratorLostAndFoundCommand.toggle_delete_lost_item", item_id=item_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for toggling delete status",
                data=None,
                status_code=400
            )

        try:
            lost_item = LostAndFound.objects.all_including_deleted().select_for_update().get(id=item_id)
        except LostAndFound.DoesNotExist:
            op.fail("Lost item not found")
            return BaseResultWithData(
                message="Lost item not found",
                data=None,
                status_code=404
            )

        old_deleted = lost_item.is_deleted
        new_deleted = not old_deleted
        lost_item.is_deleted = new_deleted
        lost_item.save(update_fields=['is_deleted'])

        action_type = ModeratorActionTypeEnum.DELETE.value if new_deleted else ModeratorActionTypeEnum.REINSTATE.value
        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=action_type,
            content_type=ContentTypeEnum.LOST_ITEM.value,
            content_id=lost_item.id,
            reason=reason,
            metadata={
                'old_is_deleted': old_deleted,
                'new_is_deleted': new_deleted,
                'status': lost_item.status,
                'lost_item_name': lost_item.item_name,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # TODO implement to notify the user.

        op.success(f"Lost item {item_id} delete toggled to {new_deleted}")
        return BaseResultWithData(
            message=f"Lost item {'deleted' if new_deleted else 'restored'} successfully",
            data={'item_id': lost_item.id, 'is_deleted': lost_item.is_deleted},
            status_code=200
        )

    # ─── Toggle Hide (hide / unhide) ──────────────────────────────
    @staticmethod
    @transaction.atomic
    def toggle_hide_lost_item(request, item_id, validated_data) -> BaseResultWithData:
        """
        Toggle hidden status.
        If currently HIDDEN → set to PENDING; otherwise → set to HIDDEN.
        """
        op = OperationLogger("ModeratorLostAndFoundCommand.toggle_hide_lost_item", item_id=item_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for toggling hide status",
                data=None,
                status_code=400
            )

        try:
            lost_item = LostAndFound.objects.select_for_update().get(id=item_id, is_deleted=False)
        except LostAndFound.DoesNotExist:
            op.fail("Lost item not found or deleted")
            return BaseResultWithData(
                message="Lost item not found or deleted",
                data=None,
                status_code=404
            )

        old_status = lost_item.status

        if lost_item.status == LostAndFoundStatusEnum.HIDDEN.value:
            lost_item.status = LostAndFoundStatusEnum.PENDING.value
            action_type = ModeratorActionTypeEnum.UNHIDE.value
            message_text = "Lost Item unhidden and set to PENDING"
        else:
            lost_item.status = LostAndFoundStatusEnum.HIDDEN.value
            action_type = ModeratorActionTypeEnum.HIDE.value
            message_text = "Lost item hidden"

        lost_item.save(update_fields=['status'])

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=action_type,
            content_type=ContentTypeEnum.LOST_ITEM.value,
            content_id=lost_item.id,
            reason=reason,
            metadata={
                'old_status': old_status,
                'new_status': lost_item.status,
                'is_deleted': lost_item.is_deleted,
                'lost_item_name': lost_item.item_name,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # TODO implement to notify the user.

        op.success(f"Lost item {item_id} hide toggled to {lost_item.status}")
        return BaseResultWithData(
            message=message_text,
            data={'lost_item_id': lost_item.id, 'status': lost_item.status},
            status_code=200
        )

    # ─── Toggle Flag (flag / unflag) ──────────────────────────────
    @staticmethod
    @transaction.atomic
    def toggle_flag_lost_item(request, lost_item_id, validated_data) -> BaseResultWithData:
        """
        Toggle flag status.
        If not flagged → create flag; if flagged → resolve it.
        """
        op = OperationLogger("ModeratorLostAndFoundCommand.toggle_flag_lost_item", lost_item_id=lost_item_id)
        op.start()

        resolution_note = validated_data.get('resolution_note')
        if not resolution_note:
            return BaseResultWithData(
                message="A resolution_note is required for flagging/unflagging a lost_item",
                data=None,
                status_code=400
            )

        # Check if an unresolved flag exists
        existing_flag = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.LOST_ITEM.value,
            content_id=lost_item_id,
            is_resolved=False,
            is_deleted=False
        ).select_for_update().first()

        if existing_flag:
            # ─── Unflag (resolve) ─────────────────────────────────
            existing_flag.is_resolved = True
            existing_flag.resolved_by = request.user
            existing_flag.resolved_at = timezone.now()
            existing_flag.resolution_note = resolution_note
            existing_flag.save()

            ModeratorAction.objects.create(
                moderator=request.user,
                action_type=ModeratorActionTypeEnum.UNFLAG.value,
                content_type=ContentTypeEnum.LOST_ITEM.value,
                content_id=lost_item_id,
                reason=resolution_note,
                metadata={
                    'flag_id': existing_flag.id,
                    'resolved': True,
                    'lost_item_id': lost_item_id,
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            op.success(f"lost_item {lost_item_id} unflagged")
            return BaseResultWithData(
                message="Flag resolved successfully",
                data={'lost_item_id': lost_item_id, 'is_flagged': False},
                status_code=200
            )
        else:
            # ─── Flag ─────────────────────────────────────────────
            flag = FlaggedContent.objects.create(
                content_type=ContentTypeEnum.LOST_ITEM.value,
                content_id=lost_item_id,
                flagged_by=request.user,
                reason=resolution_note,
            )

            ModeratorAction.objects.create(
                moderator=request.user,
                action_type=ModeratorActionTypeEnum.FLAG.value,
                content_type=ContentTypeEnum.LOST_ITEM.value,
                content_id=lost_item_id,
                reason=resolution_note,
                metadata={
                    'flag_id': flag.id,
                    'resolved': False,
                    'lost_item_id': lost_item_id,
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            # TODO implement to notify the user.

            op.success(f"lost_item {lost_item_id} flagged")
            return BaseResultWithData(
                message="lost_item flagged successfully",
                data={'lost_item_id': lost_item_id, 'is_flagged': True},
                status_code=200
            )