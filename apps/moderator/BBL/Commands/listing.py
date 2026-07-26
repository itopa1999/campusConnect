from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.campus.models import Listing
from apps.moderator.models import FlaggedContent, ModeratorAction
from utils.base_result import BaseResultWithData
from utils.enums import ListingStatusType, ContentTypeEnum, ModeratorActionTypeEnum
from utils.log_helpers import OperationLogger

User = get_user_model()


class ListingCommand:

    # ─── Approve ──────────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def approve_listing(request, listing_id, validated_data) -> BaseResultWithData:
        """
        Approve a pending listing.
        """
        op = OperationLogger("ModeratorListingCommand.approve_listing", listing_id=listing_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for approving a listing",
                data=None,
                status_code=400
            )

        try:
            listing = Listing.objects.select_for_update().get(
                id=listing_id,
                is_deleted=False,
                status=ListingStatusType.PENDING.value
            )
        except Listing.DoesNotExist:
            op.fail("Listing not found or not pending")
            return BaseResultWithData(
                message="Listing not found or not pending or is_deleted",
                data=None,
                status_code=404
            )

        old_status = listing.status
        listing.status = ListingStatusType.ACTIVE.value
        listing.save(update_fields=['status'])

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.APPROVE.value,
            content_type=ContentTypeEnum.LISTING.value,
            content_id=listing.id,
            reason=reason,
            metadata={
                'old_status': old_status,
                'new_status': listing.status,
                'listing_title': listing.title,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # TODO implement to notify the user.

        op.success(f"Listing {listing_id} approved")
        return BaseResultWithData(
            message="Listing approved successfully",
            data={'listing_id': listing.id, 'status': listing.status},
            status_code=200
        )

    # ─── Reject ──────────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def reject_listing(request, listing_id, validated_data) -> BaseResultWithData:
        """
        Reject a pending listing
        """
        op = OperationLogger("ModeratorListingCommand.reject_listing", listing_id=listing_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for rejecting a listing",
                data=None,
                status_code=400
            )

        try:
            listing = Listing.objects.select_for_update().get(
                id=listing_id,
                is_deleted=False,
                status=ListingStatusType.PENDING.value
            )
        except Listing.DoesNotExist:
            op.fail("Listing not found or not pending")
            return BaseResultWithData(
                message="Listing not found or not pending or is_deleted",
                data=None,
                status_code=404
            )

        old_status = listing.status
        listing.status = ListingStatusType.REJECT.value
        listing.save(update_fields=['status'])

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.REJECT.value,
            content_type=ContentTypeEnum.LISTING.value,
            content_id=listing.id,
            reason=reason,
            metadata={
                'old_status': old_status,
                'new_new_status': listing.status,
                'listing_title': listing.title,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # TODO implement to notify the user.

        op.success(f"Listing {listing_id} rejected")
        return BaseResultWithData(
            message="Listing rejected",
            data={'listing_id': listing.id},
            status_code=200
        )

    # ─── Toggle Delete (soft delete / restore) ────────────────────
    @staticmethod
    @transaction.atomic
    def toggle_delete_listing(request, listing_id, validated_data) -> BaseResultWithData:
        """
        Toggle soft-delete status.
        If currently deleted → restore; otherwise → soft delete.
        """
        op = OperationLogger("ModeratorListingCommand.toggle_delete_listing", listing_id=listing_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for toggling delete status",
                data=None,
                status_code=400
            )

        try:
            listing = Listing.objects.all_including_deleted().select_for_update().get(id=listing_id)
        except Listing.DoesNotExist:
            op.fail("Listing not found")
            return BaseResultWithData(
                message="Listing not found",
                data=None,
                status_code=404
            )

        old_deleted = listing.is_deleted
        new_deleted = not old_deleted
        listing.is_deleted = new_deleted
        listing.save(update_fields=['is_deleted'])

        action_type = ModeratorActionTypeEnum.DELETE.value if new_deleted else ModeratorActionTypeEnum.REINSTATE.value
        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=action_type,
            content_type=ContentTypeEnum.LISTING.value,
            content_id=listing.id,
            reason=reason,
            metadata={
                'old_is_deleted': old_deleted,
                'new_is_deleted': new_deleted,
                'status': listing.status,
                'listing_title': listing.title,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # TODO implement to notify the user.

        op.success(f"Listing {listing_id} delete toggled to {new_deleted}")
        return BaseResultWithData(
            message=f"Listing {'deleted' if new_deleted else 'restored'} successfully",
            data={'listing_id': listing.id, 'is_deleted': listing.is_deleted},
            status_code=200
        )


    # ─── Toggle Hide (hide / unhide) ──────────────────────────────
    @staticmethod
    @transaction.atomic
    def toggle_hide_listing(request, listing_id, validated_data) -> BaseResultWithData:
        """
        Toggle hidden status.
        If currently HIDDEN → set to PENDING; otherwise → set to HIDDEN.
        """
        op = OperationLogger("ModeratorListingCommand.toggle_hide_listing", listing_id=listing_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for toggling hide status",
                data=None,
                status_code=400
            )

        try:
            listing = Listing.objects.select_for_update().get(id=listing_id, is_deleted=False)
        except Listing.DoesNotExist:
            op.fail("Listing not found or deleted")
            return BaseResultWithData(
                message="Listing not found or deleted",
                data=None,
                status_code=404
            )

        old_status = listing.status

        if listing.status == ListingStatusType.HIDDEN.value:
            listing.status = ListingStatusType.PENDING.value
            action_type = ModeratorActionTypeEnum.UNHIDE.value
            message_text = "Listing unhidden and set to PENDING"
        else:
            listing.status = ListingStatusType.HIDDEN.value
            action_type = ModeratorActionTypeEnum.HIDE.value
            message_text = "Listing hidden"

        listing.save(update_fields=['status'])

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=action_type,
            content_type=ContentTypeEnum.LISTING.value,
            content_id=listing.id,
            reason=reason,
            metadata={
                'old_status': old_status,
                'new_status': listing.status,
                'is_deleted': listing.is_deleted,
                'listing_title': listing.title,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # TODO implement to notify the user.

        op.success(f"Listing {listing_id} hide toggled to {listing.status}")
        return BaseResultWithData(
            message=message_text,
            data={'listing_id': listing.id, 'status': listing.status},
            status_code=200
        )

    # ─── Toggle Flag (flag / unflag) ──────────────────────────────
    @staticmethod
    @transaction.atomic
    def toggle_flag_listing(request, listing_id, validated_data) -> BaseResultWithData:
        """
        Toggle flag status.
        If not flagged → create flag; if flagged → resolve it.
        """
        op = OperationLogger("ModeratorListingCommand.toggle_flag_listing", listing_id=listing_id)
        op.start()

        resolution_note = validated_data.get('resolution_note')
        if not resolution_note:
            return BaseResultWithData(
                message="A resolution_note is required for flagging/unflagging a listing",
                data=None,
                status_code=400
            )

        # Check if an unresolved flag exists
        existing_flag = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=listing_id,
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
                content_type=ContentTypeEnum.LISTING.value,
                content_id=listing_id,
                reason=resolution_note,
                metadata={
                    'flag_id': existing_flag.id,
                    'resolved': True,
                    'listing_id': listing_id,
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            op.success(f"Listing {listing_id} unflagged")
            return BaseResultWithData(
                message="Flag resolved successfully",
                data={'listing_id': listing_id, 'is_flagged': False},
                status_code=200
            )
        else:
            # ─── Flag ─────────────────────────────────────────────
            flag = FlaggedContent.objects.create(
                content_type=ContentTypeEnum.LISTING.value,
                content_id=listing_id,
                flagged_by=request.user,
                reason=resolution_note,
            )

            ModeratorAction.objects.create(
                moderator=request.user,
                action_type=ModeratorActionTypeEnum.FLAG.value,
                content_type=ContentTypeEnum.LISTING.value,
                content_id=listing_id,
                reason=resolution_note,
                metadata={
                    'flag_id': flag.id,
                    'resolved': False,
                    'listing_id': listing_id,
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            # TODO implement to notify the user.

            op.success(f"Listing {listing_id} flagged")
            return BaseResultWithData(
                message="Listing flagged successfully",
                data={'listing_id': listing_id, 'is_flagged': True},
                status_code=200
            )