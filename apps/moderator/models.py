from django.db import models
from apps.campus.models import Listing, Review
from utils.base_model import BaseModel
from django.utils import timezone

from apps.users.models import User
from utils.enums import ContentTypeEnum, ModeratorActionTypeEnum

class ModeratorAction(BaseModel):
    """
    Tracks every moderation action taken by a moderator.
    """
    moderator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='moderator_actions'
    )
    action_type = models.CharField(
        max_length=50,
        choices=ModeratorActionTypeEnum.choices(),
        db_index=True
    )
    content_type = models.CharField(
        max_length=20,
        choices=ContentTypeEnum.choices(),
        help_text="Type of content acted upon (listing, review, user, report)"
    )
    content_id = models.PositiveIntegerField(
        help_text="ID of the content (listing_id, user_id, etc.)"
    )
    reason = models.TextField(blank=True, help_text="Reason for the action")
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra data (e.g., old status, new status, warning duration)"
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['moderator']),
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['content_type', 'content_id']),
        ]

    def __str__(self):
        return f"{self.moderator.email} - {self.action_type} on {self.content_type} ID {self.content_id}"
    

class FlaggedContent(BaseModel):
    """
    Allows moderators (and users) to flag content for review.
    """
    content_type = models.CharField(
        max_length=20,
        choices=ContentTypeEnum.choices(),
        help_text="Type of content (listing, review, user)"
    )
    content_id = models.PositiveIntegerField()
    flagged_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='flagged_items'
    )
    reason = models.TextField(help_text="Reason for flagging")
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_flags'
    )
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'content_id']),
            models.Index(fields=['is_resolved']),
        ]

    def __str__(self):
        return f"Flag on {self.content_type} {self.content_id} by {self.flagged_by.email}"
    

class UserModeration(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='moderation')
    warning_count = models.PositiveIntegerField(default=0)
    is_suspended = models.BooleanField(default=False)
    suspended_until = models.DateTimeField(blank=True, null=True)
    is_banned = models.BooleanField(default=False)
    banned_at = models.DateTimeField(blank=True, null=True)
    ban_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Private notes for moderators")

    class Meta:
        indexes = [
            models.Index(fields=['is_suspended']),
            models.Index(fields=['is_banned']),
        ]

    def __str__(self):
        return f"Moderation for {self.user.email}"


    @property
    def is_currently_suspended(self):
        """
        Returns True when the user currently has
        an active suspension.

        suspended_until = None means the suspension
        has no expiry date.
        """

        if not self.is_suspended:
            return False

        # Indefinite suspension
        if self.suspended_until is None:
            return True

        # Temporary suspension
        return self.suspended_until > timezone.now()


    @property
    def can_login(self):
        """
        Determines whether moderation status allows
        the user to log in.
        """

        if self.is_banned:
            return False

        if self.is_currently_suspended:
            return False

        return True


    def clear_expired_suspension(self):
        """
        Automatically clears a suspension when
        suspended_until has passed.
        """

        if (
            self.is_suspended
            and self.suspended_until is not None
            and self.suspended_until <= timezone.now()
        ):

            self.is_suspended = False
            self.suspended_until = None

            self.save(
                update_fields=[
                    "is_suspended",
                    "suspended_until",
                ]
            )

            return True

        return False


class ModeratorNote(BaseModel):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    content_type = models.CharField(max_length=20, choices=ContentTypeEnum.choices())
    content_id = models.PositiveIntegerField()
    note = models.TextField()
    is_private = models.BooleanField(default=True)  # only visible to moderators/admins

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'content_id']),
        ]

    def __str__(self):
        return f"Note by {self.author.email} on {self.content_type} {self.content_id}"