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
        related_name='moderator_actions',
        help_text="The moderator who performed the action.",
    )
    action_type = models.CharField(
        max_length=50,
        choices=ModeratorActionTypeEnum.choices(),
        db_index=True,
        help_text="Type of moderation action (e.g., warning, suspend, delete, restore).",
    )
    content_type = models.CharField(
        max_length=20,
        choices=ContentTypeEnum.choices(),
        help_text="Type of content acted upon (listing, review, user, report).",
    )
    content_id = models.PositiveIntegerField(
        help_text="ID of the content (listing_id, user_id, review_id, etc.).",
    )
    reason = models.TextField(
        blank=True,
        help_text="Reason for the action (optional).",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra data such as old status, new status, warning duration, etc.",
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP address of the moderator at the time of action.",
    )

    class Meta:
        verbose_name = "Moderator Action"
        verbose_name_plural = "Moderator Actions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['moderator']),
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['content_type', 'content_id']),
            models.Index(fields=['moderator', 'created_at']),  # additional
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
        help_text="Type of content being flagged (listing, review, user).",
    )
    content_id = models.PositiveIntegerField(
        help_text="ID of the content being flagged.",
    )
    flagged_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='flagged_items',
        help_text="The user who flagged the content.",
    )
    reason = models.TextField(
        help_text="Reason for flagging the content.",
    )
    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether the flag has been reviewed and resolved.",
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_flags',
        help_text="Moderator who resolved the flag (if any).",
    )
    resolved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when the flag was resolved.",
    )
    resolution_note = models.TextField(
        blank=True,
        help_text="Explanation of the resolution (e.g., content removed, warning issued).",
    )

    class Meta:
        verbose_name = "Flagged Content"
        verbose_name_plural = "Flagged Content"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'content_id']),
            models.Index(fields=['is_resolved']),
        ]

    def __str__(self):
        return f"Flag on {self.content_type} {self.content_id} by {self.flagged_by.email}"


class UserModeration(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='moderation',
        help_text="The user whose moderation status is tracked.",
    )
    warning_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of active warnings issued to the user.",
    )
    is_suspended = models.BooleanField(
        default=False,
        help_text="Indicates if the user is currently suspended (temporarily blocked).",
    )
    suspended_until = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date and time when the suspension expires. If None, suspension is indefinite.",
    )
    is_banned = models.BooleanField(
        default=False,
        help_text="Indicates if the user is permanently banned from the platform.",
    )
    banned_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date and time when the user was banned.",
    )
    ban_reason = models.TextField(
        blank=True,
        help_text="Reason for the permanent ban.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Private notes for moderators (not visible to the user).",
    )

    class Meta:
        verbose_name = "User Moderation"
        verbose_name_plural = "User Moderations"
        indexes = [
            models.Index(fields=['is_suspended']),
            models.Index(fields=['is_banned']),
            models.Index(fields=['suspended_until']),
            models.Index(fields=['is_suspended', 'suspended_until']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(warning_count__gte=0),
                name="user_moderation_warning_count_non_negative"
            ),
        ]

    def __str__(self):
        return f"Moderation for {self.user.email}"

    @property
    def is_currently_suspended(self):
        """
        Returns True when the user currently has an active suspension.
        suspended_until = None means the suspension has no expiry date.
        """
        if not self.is_suspended:
            return False
        if self.suspended_until is None:
            return True
        return self.suspended_until > timezone.now()

    @property
    def can_login(self):
        """
        Determines whether moderation status allows the user to log in.
        """
        if self.is_banned:
            return False
        if self.is_currently_suspended:
            return False
        return True

    def clear_expired_suspension(self):
        """
        Automatically clears a suspension when suspended_until has passed.
        """
        if (
            self.is_suspended
            and self.suspended_until is not None
            and self.suspended_until <= timezone.now()
        ):
            self.is_suspended = False
            self.suspended_until = None
            self.save(update_fields=["is_suspended", "suspended_until"])
            return True
        return False


class ModeratorNote(BaseModel):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notes',
        help_text="The moderator who wrote the note.",
    )
    content_type = models.CharField(
        max_length=20,
        choices=ContentTypeEnum.choices(),
        help_text="Type of content the note is attached to (listing, review, user, etc.).",
    )
    content_id = models.PositiveIntegerField(
        help_text="ID of the content this note refers to.",
    )
    note = models.TextField(
        help_text="The actual note content.",
    )
    is_private = models.BooleanField(
        default=True,
        help_text="If True, only moderators/admins can see this note. If False, visible to the content owner as well.",
    )

    class Meta:
        verbose_name = "Moderator Note"
        verbose_name_plural = "Moderator Notes"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'content_id']),
        ]

    def __str__(self):
        return f"Note by {self.author.email} on {self.content_type} {self.content_id}"