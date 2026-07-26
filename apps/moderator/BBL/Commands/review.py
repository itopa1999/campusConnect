from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.campus.models import Review
from apps.moderator.models import FlaggedContent, ModeratorAction
from utils.base_result import BaseResultWithData
from utils.enums import ContentTypeEnum, ModeratorActionTypeEnum
from utils.log_helpers import OperationLogger

User = get_user_model()


class ReviewCommand:

    # ─── Toggle Delete (soft delete / restore) ────────────────────
    @staticmethod
    @transaction.atomic
    def toggle_delete_review(request, review_id, validated_data)-> BaseResultWithData:
        """
        Toggle soft-delete status of a review.
        If currently deleted → restore; otherwise → soft delete.
        """
        op = OperationLogger("ModeratorReviewCommand.toggle_delete_review", review_id=review_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for toggling delete status",
                data=None,
                status_code=400
            )

        try:
            review = Review.objects.all_including_deleted().select_for_update().get(id=review_id)
        except Review.DoesNotExist:
            op.fail("Review not found")
            return BaseResultWithData(
                message="Review not found",
                data=None,
                status_code=404
            )

        old_deleted = review.is_deleted
        new_deleted = not old_deleted
        review.is_deleted = new_deleted
        review.save(update_fields=['is_deleted'])

        action_type = ModeratorActionTypeEnum.DELETE.value if new_deleted else ModeratorActionTypeEnum.REINSTATE.value
        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=action_type,
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=review.id,
            reason=reason,
            metadata={
                'old_is_deleted': old_deleted,
                'new_is_deleted': new_deleted,
                'review_rating': review.rating,
                'review_comment': review.comment[:100],
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # TODO implement to notify the user.

        op.success(f"Review {review_id} delete toggled to {new_deleted}")
        return BaseResultWithData(
            message=f"Review {'deleted' if new_deleted else 'restored'} successfully",
            data={'review_id': review.id, 'is_deleted': review.is_deleted},
            status_code=200
        )

    # ─── Toggle Flag (flag / unflag) ──────────────────────────────
    @staticmethod
    @transaction.atomic
    def toggle_flag_review(request, review_id, validated_data) -> BaseResultWithData:
        """
        Toggle flag status of a review.
        If not flagged → create flag; if flagged → resolve it.
        """
        op = OperationLogger("ModeratorReviewCommand.toggle_flag_review", review_id=review_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required for flagging/unflagging a review",
                data=None,
                status_code=400
            )

        # Check if an unresolved flag exists
        existing_flag = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=review_id,
            is_resolved=False,
            is_deleted=False
        ).select_for_update().first()

        if existing_flag:
            # ─── Unflag (resolve) ─────────────────────────────────
            existing_flag.is_resolved = True
            existing_flag.resolved_by = request.user
            existing_flag.resolved_at = timezone.now()
            existing_flag.resolution_note = reason
            existing_flag.save()

            ModeratorAction.objects.create(
                moderator=request.user,
                action_type=ModeratorActionTypeEnum.UNFLAG.value,
                content_type=ContentTypeEnum.REVIEW.value,
                content_id=review_id,
                reason=reason,
                metadata={
                    'flag_id': existing_flag.id,
                    'resolved': True,
                    'review_id': review_id,
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            op.success(f"Review {review_id} unflagged")
            return BaseResultWithData(
                message="Flag resolved successfully",
                data={'review_id': review_id, 'is_flagged': False},
                status_code=200
            )
        else:
            # ─── Flag ─────────────────────────────────────────────
            flag = FlaggedContent.objects.create(
                content_type=ContentTypeEnum.REVIEW.value,
                content_id=review_id,
                flagged_by=request.user,
                reason=reason,
            )

            ModeratorAction.objects.create(
                moderator=request.user,
                action_type=ModeratorActionTypeEnum.FLAG.value,
                content_type=ContentTypeEnum.REVIEW.value,
                content_id=review_id,
                reason=reason,
                metadata={
                    'flag_id': flag.id,
                    'resolved': False,
                    'review_id': review_id,
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            # TODO implement to notify the user.

            op.success(f"Review {review_id} flagged")
            return BaseResultWithData(
                message="Review flagged successfully",
                data={'review_id': review_id, 'is_flagged': True},
                status_code=200
            )