from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.users.models import User
from utils.base_model import BaseModel
from utils.enums import BaseChoiceEnum, ContestantStatusEnum, PollStatusEnum, ResultsVisibilityEnum


# =============================================
# MODELS
# =============================================

class PollCategory(BaseModel):
    """
    Represents a category for organizing polls (e.g., Student Elections, Awards).
    """
    name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Name of the category (e.g., Student Elections, Awards, Competitions).",
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of what this category represents.",
    )
    color_code = models.CharField(
        max_length=7,
        blank=True,
        help_text="Hex color code for UI styling (e.g., #FF5733).",
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon name for UI display (e.g., 'vote', 'award', 'trophy').",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this category is active and visible.",
    )

    class Meta:
        verbose_name = "Poll Category"
        verbose_name_plural = "Poll Categories"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name', 'is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.color_code and not self.color_code.startswith('#'):
            raise ValidationError("Color code must start with '#'.")
        if self.color_code and len(self.color_code) not in [4, 7]:
            raise ValidationError("Color code must be a valid hex code (e.g., #FFF or #FFFFFF).")


class Poll(BaseModel):
    """
    Represents a voting poll/election created by a moderator.
    """
    # Core fields
    title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Title of the poll (e.g., 'Class President Election 2026').",
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the poll, its purpose, and rules.",
    )
    
    # Relationships
    category = models.ForeignKey(
        PollCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='polls',
        help_text="Category this poll belongs to (optional).",
    )
    
    # Date/Time fields
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When voting begins. If null, voting starts immediately upon publishing.",
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When voting ends. If null, the poll never expires.",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When the poll was published (made active/visible).",
    )
    
    # Voting settings
    max_votes_per_voter = models.PositiveIntegerField(
        default=1,
        help_text="Maximum votes each student can cast in this poll. Default is 1.",
    )
    allow_self_voting = models.BooleanField(
        default=True,
        help_text="If True, contestants can vote for themselves.",
    )
    is_anonymous = models.BooleanField(
        default=True,
        help_text="If True, no one can see who voted for whom.",
    )
    
    # Visibility & status
    results_visibility = models.CharField(
        max_length=50,
        choices=ResultsVisibilityEnum.choices(),
        default=ResultsVisibilityEnum.LIVE.value,
        db_index=True,
        help_text="When and who can see results.",
    )
    status = models.CharField(
        max_length=20,
        choices=PollStatusEnum.choices(),
        default=PollStatusEnum.DRAFT.value,
        db_index=True,
        help_text="Current status of the poll.",
    )
    
    # QR Code
    qr_code_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL/path to the generated QR code image for this poll.",
    )
    
    # Statistics (denormalized for faster queries)
    total_votes_cast = models.PositiveIntegerField(
        default=0,
        help_text="Running total of all votes cast in this poll (cached for performance).",
    )
    total_contestants = models.PositiveIntegerField(
        default=0,
        help_text="Total number of contestants in this poll (cached for performance).",
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra data such as poll settings, configuration flags, etc.",
    )

    class Meta:
        verbose_name = "Poll"
        verbose_name_plural = "Polls"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status', 'start_date', 'end_date']),
            models.Index(fields=['published_at', 'status']),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        # Validate dates
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("Start date must be before end date.")
        
        # Validate max_votes_per_voter
        if self.max_votes_per_voter < 1:
            raise ValidationError("Max votes per voter must be at least 1.")

    def save(self, *args, **kwargs):
        # Auto-calculate status based on dates
        if self.status == PollStatusEnum.DRAFT.value:
            pass  # Draft status is manual
        else:
            now = timezone.now()
            if self.published_at and self.published_at > now:
                self.status = PollStatusEnum.UPCOMING.value
            elif self.start_date and self.start_date > now:
                self.status = PollStatusEnum.UPCOMING.value
            elif self.end_date and self.end_date < now:
                self.status = PollStatusEnum.ENDED.value
            elif self.published_at and self.published_at <= now:
                self.status = PollStatusEnum.ACTIVE.value
            elif self.start_date and self.start_date <= now:
                self.status = PollStatusEnum.ACTIVE.value
            elif not self.start_date and not self.end_date:
                self.status = PollStatusEnum.ACTIVE.value
        
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        """Check if poll is currently active for voting."""
        return self.status == PollStatusEnum.ACTIVE.value

    @property
    def is_upcoming(self):
        """Check if poll is upcoming."""
        return self.status == PollStatusEnum.UPCOMING.value

    @property
    def is_ended(self):
        """Check if poll has ended."""
        return self.status == PollStatusEnum.ENDED.value
    
    @property
    def is_draft(self):
        """Check if poll is in draft state."""
        return self.status == PollStatusEnum.DRAFT.value
    
    @property
    def time_remaining(self):
        """Time remaining until poll ends (for active polls)."""
        if self.end_date and self.is_active:
            remaining = self.end_date - timezone.now()
            return max(remaining, timezone.timedelta(0))
        return None
    
    @property
    def time_until_start(self):
        """Time until poll starts (for upcoming polls)."""
        start = self.start_date or self.published_at
        if start and self.is_upcoming:
            remaining = start - timezone.now()
            return max(remaining, timezone.timedelta(0))
        return None


class Contestant(BaseModel):
    """
    Represents a student who is contesting/running in a poll.
    Contestants CANNOT be removed once added (per project requirements).
    """
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name='contestants',
        help_text="The poll this student is contesting in.",
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='contestant_entries',
        help_text="The registered student who is a contestant.",
    )
    
    # Display settings
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which contestants appear in the poll (0 = first).",
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=ContestantStatusEnum.choices(),
        default=ContestantStatusEnum.ACTIVE.value,
        db_index=True,
        help_text="Status of the contestant (Active or Withdrawn).",
    )
    
    # Statistics (denormalized for performance)
    vote_count = models.PositiveIntegerField(
        default=0,
        help_text="Total votes this contestant has received (cached for performance).",
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra data such as campaign promises, tags, etc.",
    )

    class Meta:
        verbose_name = "Contestant"
        verbose_name_plural = "Contestants"
        ordering = ['display_order', '-vote_count']
        indexes = [
            models.Index(fields=['poll', 'student']),
            models.Index(fields=['poll', 'display_order']),
            models.Index(fields=['poll', '-vote_count']),
            models.Index(fields=['student', 'created_at']),
            models.Index(fields=['poll', 'status']),
        ]
        # Ensure a student can only be added once per poll
        unique_together = [
            ('poll', 'student'),
        ]

    def __str__(self):
        student_name = self.student.get_full_name() or self.student.email
        return f"{student_name} - {self.poll.title}"

    def clean(self):
        # Validate that poll is in a state where contestants can be added
        if self.poll.status == PollStatusEnum.ENDED.value:
            raise ValidationError("Cannot add contestants to an ended poll.")
        
        # Validate that student is actually a student (not admin)
        if self.student.is_staff:
            raise ValidationError("Staff members cannot be contestants.")
        
        # Validate that the student is not already a contestant in this poll
        if self.pk is None:  # New contestant
            if Contestant.objects.filter(poll=self.poll, student=self.student).exists():
                raise ValidationError("This student is already a contestant in this poll.")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Update total_contestants count on poll
            self.poll.total_contestants = Contestant.objects.filter(poll=self.poll).count()
            self.poll.save(update_fields=['total_contestants'])

    def delete(self, *args, **kwargs):
        """
        Override delete to PREVENT deletion of contestants.
        """
        raise ValidationError("Contestants cannot be removed once added.")

    def hard_delete(self, *args, **kwargs):
        """
        Emergency hard delete (super admin only).
        """
        super().delete(*args, **kwargs)

    def update_vote_count(self):
        """
        Recalculate and update vote count from votes table.
        """
        from apps.poll.models import Vote
        self.vote_count = Vote.objects.filter(contestant=self).count()
        self.save(update_fields=['vote_count', 'modified_at'])


class Vote(BaseModel):
    """
    Represents a vote cast by a student for a contestant in a poll.
    """
    # Relationships
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name='votes',
        help_text="The poll in which this vote was cast.",
    )
    contestant = models.ForeignKey(
        Contestant,
        on_delete=models.CASCADE,
        related_name='votes',
        help_text="The contestant who received this vote.",
    )
    voter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cast_votes',
        help_text="The student who cast this vote.",
    )
    
    # Timestamp
    voted_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the vote was cast.",
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra data such as device info, tracking, etc.",
    )

    class Meta:
        verbose_name = "Vote"
        verbose_name_plural = "Votes"
        ordering = ['-voted_at']
        indexes = [
            models.Index(fields=['poll', 'voter']),
            models.Index(fields=['poll', 'contestant']),
            models.Index(fields=['voter', 'voted_at']),
            models.Index(fields=['poll', 'voter', 'voted_at']),
            models.Index(fields=['contestant', '-voted_at']),
        ]
        # Ensure a voter can only vote once per poll
        unique_together = [
            ('poll', 'voter'),
        ]

    def __str__(self):
        voter_name = self.voter.get_full_name() or self.voter.email
        contestant_name = self.contestant.student.get_full_name() or self.contestant.student.email
        return f"{voter_name} → {contestant_name} ({self.poll.title})"

    def clean(self):
        # 1. Validate poll is active
        if self.poll.status != PollStatusEnum.ACTIVE.value:
            raise ValidationError("Voting is not active for this poll.")
        
        # 2. Validate poll start date
        if self.poll.start_date and self.poll.start_date > timezone.now():
            raise ValidationError("Voting has not started yet.")
        
        # 3. Validate poll end date
        if self.poll.end_date and self.poll.end_date < timezone.now():
            raise ValidationError("Voting has ended for this poll.")
        
        # 4. Validate max votes per voter
        existing_votes = Vote.objects.filter(poll=self.poll, voter=self.voter).count()
        if existing_votes >= self.poll.max_votes_per_voter:
            raise ValidationError(
                f"You have already cast your maximum of {self.poll.max_votes_per_voter} vote(s) in this poll."
            )
        
        # 5. Validate self-voting
        if not self.poll.allow_self_voting:
            if self.voter.id == self.contestant.student.id:
                raise ValidationError("Self-voting is not allowed in this poll.")
        
        # 6. Validate voter is not a staff member
        if self.voter.is_staff:
            raise ValidationError("Staff members cannot vote.")
        
        # 7. Validate contestant belongs to this poll
        if self.contestant.poll_id != self.poll.id:
            raise ValidationError("Contestant does not belong to this poll.")
        
        # 8. Validate contestant is active (not withdrawn)
        if self.contestant.status == ContestantStatusEnum.WITHDRAWN.value:
            raise ValidationError("This contestant has withdrawn from the poll.")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Update vote count on contestant
            self.contestant.update_vote_count()
            # Update total_votes_cast on poll
            self.poll.total_votes_cast = Vote.objects.filter(poll=self.poll).count()
            self.poll.save(update_fields=['total_votes_cast', 'modified_at'])

    def delete(self, *args, **kwargs):
        """
        Override delete to prevent deletion of votes (maintain integrity).
        """
        raise ValidationError("Votes cannot be deleted once cast.")

    def hard_delete(self, *args, **kwargs):
        """
        Emergency hard delete (super admin only).
        """
        super().delete(*args, **kwargs)
        # Update counts after deletion
        self.contestant.update_vote_count()
        self.poll.total_votes_cast = Vote.objects.filter(poll=self.poll).count()
        self.poll.save(update_fields=['total_votes_cast', 'modified_at'])


class PollResultCache(BaseModel):
    """
    Cached results for a poll to improve performance on result pages.
    """
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name='cached_results',
        help_text="The poll these results belong to.",
    )
    contestant = models.ForeignKey(
        Contestant,
        on_delete=models.CASCADE,
        related_name='cached_results',
        help_text="The contestant these results belong to.",
    )
    vote_count = models.PositiveIntegerField(
        default=0,
        help_text="Total votes received by this contestant at the time of caching.",
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Percentage of total votes (e.g., 45.67%).",
    )
    rank = models.PositiveIntegerField(
        default=0,
        help_text="Rank/position of this contestant (1st, 2nd, etc.).",
    )
    
    class Meta:
        verbose_name = "Poll Result Cache"
        verbose_name_plural = "Poll Result Caches"
        ordering = ['rank', '-vote_count']
        indexes = [
            models.Index(fields=['poll', 'rank']),
            models.Index(fields=['poll', '-vote_count']),
            models.Index(fields=['contestant']),
        ]
        unique_together = [
            ('poll', 'contestant'),
        ]

    def __str__(self):
        student_name = self.contestant.student.get_full_name() or self.contestant.student.email
        return f"{self.poll.title} - {student_name} - {self.vote_count} votes"

    @classmethod
    def refresh_for_poll(cls, poll_id):
        """
        Refresh cached results for a specific poll.
        """
        from django.db import connection
        from decimal import Decimal

        # Clear existing cache
        cls.objects.filter(poll_id=poll_id).delete()

        # Get all votes for this poll
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    contestant_id,
                    COUNT(*) as vote_count
                FROM poll_vote
                WHERE poll_id = %s
                GROUP BY contestant_id
                ORDER BY vote_count DESC
            """, [poll_id])

            results = cursor.fetchall()

        total_votes = sum(r[1] for r in results)
        cached_objects = []

        for idx, (contestant_id, vote_count) in enumerate(results, start=1):
            percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
            cached_objects.append(
                cls(
                    poll_id=poll_id,
                    contestant_id=contestant_id,
                    vote_count=vote_count,
                    percentage=round(Decimal(percentage), 2),
                    rank=idx,
                )
            )

        if cached_objects:
            cls.objects.bulk_create(cached_objects)