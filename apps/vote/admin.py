from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Sum, Avg
from django.urls import reverse

from apps.vote.models import (
    PollCategory,
    Poll,
    Contestant,
    Vote,
    PollResultCache
)
from common.admin import SoftDeleteAdmin
from utils.enums import PollStatusEnum, ResultsVisibilityEnum, ContestantStatusEnum


# =============================================
# INLINES
# =============================================

class ContestantInline(admin.TabularInline):
    """
    Inline for displaying contestants directly in Poll admin.
    """
    model = Contestant
    extra = 0
    readonly_fields = (
        'vote_count',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
    )
    fields = (
        'student',
        'display_order',
        'status',
        'vote_count',
        'created_at',
    )
    can_delete = False  # Contestants cannot be deleted
    show_change_link = True
    ordering = ('display_order', '-vote_count')
    autocomplete_fields = ['student']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student')


class VoteInline(admin.TabularInline):
    """
    Inline for displaying votes directly in Poll admin.
    """
    model = Vote
    extra = 0
    readonly_fields = (
        'voter',
        'contestant',
        'voted_at',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
    )
    fields = (
        'voter',
        'contestant',
        'voted_at',
    )
    can_delete = False  # Votes cannot be deleted
    show_change_link = True
    ordering = ('-voted_at',)
    autocomplete_fields = ['voter', 'contestant']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('voter', 'contestant', 'contestant__student')


# =============================================
# POLL CATEGORY ADMIN
# =============================================

@admin.register(PollCategory)
class PollCategoryAdmin(SoftDeleteAdmin):
    list_display = (
        'name',
        'description_short',
        'color_preview',
        'icon_preview',
        'is_active_badge',
        'polls_count',
        'created_at',
        'is_deleted'
    )
    list_filter = (
        'is_active',
        'is_deleted',
        'created_at',
    )
    search_fields = ('name', 'description')
    ordering = ('name',)

    readonly_fields = (
        'color_preview',
        'icon_preview',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )

    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'description', 'color_code', 'icon', 'is_active')
        }),
        ('Preview', {
            'fields': ('color_preview', 'icon_preview'),
            'classes': ('wide',)
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_categories', 'deactivate_categories']

    # ─── Display helpers ─────────────────────────────────────────────

    def description_short(self, obj):
        if obj.description and len(obj.description) > 75:
            return obj.description[:75] + '...'
        return obj.description
    description_short.short_description = 'Description'

    def color_preview(self, obj):
        if obj.color_code:
            return format_html(
                '<span style="display: inline-block; width: 30px; height: 30px; background-color: {}; border-radius: 4px; border: 1px solid #ddd;"></span>'
                '<span style="margin-left: 8px;">{}</span>',
                obj.color_code, obj.color_code
            )
        return '—'
    color_preview.short_description = 'Color Preview'

    def icon_preview(self, obj):
        if obj.icon:
            return format_html(
                '<span style="font-size: 24px;">{}</span>',
                obj.icon
            )
        return '—'
    icon_preview.short_description = 'Icon'

    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span style="background-color: #28a745; padding: 3px 8px; border-radius: 4px; color: white;">Active</span>'
            )
        return mark_safe(
            '<span style="background-color: #dc3545; padding: 3px 8px; border-radius: 4px; color: white;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'

    def polls_count(self, obj):
        count = obj.polls.filter(is_deleted=False).count()
        url = reverse('admin:poll_poll_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    polls_count.short_description = 'Polls'
    polls_count.admin_order_field = 'polls_count'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            polls_count=Count('polls', filter=models.Q(polls__is_deleted=False))
        )
        return queryset

    # ─── Actions ─────────────────────────────────────────────────────

    @admin.action(description='Activate selected categories')
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} category(s) activated.')

    @admin.action(description='Deactivate selected categories')
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} category(s) deactivated.')


# =============================================
# POLL ADMIN
# =============================================

@admin.register(Poll)
class PollAdmin(SoftDeleteAdmin):
    list_display = (
        'title',
        'category_display',
        'status_badge',
        'is_active_badge',
        'total_contestants',
        'total_votes_cast',
        'start_date_display',
        'end_date_display',
        'created_at',
        'is_deleted'
    )
    list_filter = (
        'status',
        'category',
        'results_visibility',
        'allow_self_voting',
        'is_anonymous',
        'created_at',
        'is_deleted',
    )
    search_fields = ('title', 'description')
    readonly_fields = (
        'qr_code_url',
        'total_votes_cast',
        'total_contestants',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )
    autocomplete_fields = ('category',)

    # Inlines
    inlines = [ContestantInline, VoteInline]

    fieldsets = (
        ('Poll Information', {
            'fields': ('title', 'description', 'category')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'published_at')
        }),
        ('Voting Settings', {
            'fields': ('max_votes_per_voter', 'allow_self_voting', 'is_anonymous')
        }),
        ('Visibility & Status', {
            'fields': ('status', 'results_visibility')
        }),
        ('QR Code', {
            'fields': ('qr_code_url',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_votes_cast', 'total_contestants'),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',)
        }),
    )

    actions = [
        'publish_polls',
        'end_polls',
        'reset_to_draft',
        'refresh_results_cache'
    ]

    # ─── Display helpers ─────────────────────────────────────────────

    @admin.display(description='Category', ordering='category__name')
    def category_display(self, obj):
        if obj.category:
            url = reverse('admin:poll_pollcategory_change', args=[obj.category.id])
            return format_html('<a href="{}">{}</a>', url, obj.category.name)
        return '—'

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            PollStatusEnum.DRAFT.value: '#6c757d',      # Gray
            PollStatusEnum.UPCOMING.value: '#17a2b8',   # Cyan
            PollStatusEnum.ACTIVE.value: '#28a745',     # Green
            PollStatusEnum.ENDED.value: '#dc3545',      # Red
        }
        color = colors.get(obj.status, '#6c757d')
        display = obj.get_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;">{}</span>',
            color, display
        )

    @admin.display(description='Active', boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @admin.display(description='Start Date')
    def start_date_display(self, obj):
        if obj.start_date:
            return obj.start_date.strftime('%b %d, %Y %H:%M')
        return 'Immediate'

    @admin.display(description='End Date')
    def end_date_display(self, obj):
        if obj.end_date:
            return obj.end_date.strftime('%b %d, %Y %H:%M')
        return 'Never'

    # ─── Actions ─────────────────────────────────────────────────────

    @admin.action(description='Publish selected polls')
    def publish_polls(self, request, queryset):
        now = timezone.now()
        updated = 0
        for poll in queryset:
            if poll.status == PollStatusEnum.DRAFT.value:
                poll.published_at = now
                poll.status = PollStatusEnum.UPCOMING.value
                poll.save()
                updated += 1
        self.message_user(request, f'{updated} poll(s) published.')

    @admin.action(description='End selected polls')
    def end_polls(self, request, queryset):
        updated = queryset.update(
            status=PollStatusEnum.ENDED.value,
            end_date=timezone.now()
        )
        self.message_user(request, f'{updated} poll(s) ended.')

    @admin.action(description='Reset selected polls to draft')
    def reset_to_draft(self, request, queryset):
        updated = queryset.update(
            status=PollStatusEnum.DRAFT.value,
            published_at=None
        )
        self.message_user(request, f'{updated} poll(s) reset to draft.')

    @admin.action(description='Refresh results cache for selected polls')
    def refresh_results_cache(self, request, queryset):
        updated = 0
        for poll in queryset:
            PollResultCache.refresh_for_poll(poll.id)
            updated += 1
        self.message_user(request, f'Results cache refreshed for {updated} poll(s).')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('category')
        return queryset


# =============================================
# CONTESTANT ADMIN
# =============================================

@admin.register(Contestant)
class ContestantAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'student_link',
        'poll_link',
        'status_badge',
        'vote_count',
        'display_order',
        'created_at',
        'is_deleted'
    )
    list_filter = (
        'status',
        'poll__category',
        'created_at',
        'is_deleted',
    )
    search_fields = (
        'student__email',
        'student__first_name',
        'student__last_name',
        'student__matric_number',
        'poll__title',
    )
    readonly_fields = (
        'vote_count',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )
    autocomplete_fields = ('poll', 'student')

    fieldsets = (
        ('Contestant Information', {
            'fields': ('poll', 'student', 'display_order', 'status')
        }),
        ('Statistics', {
            'fields': ('vote_count',),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',)
        }),
    )

    actions = [
        'mark_active',
        'mark_withdrawn',
        'refresh_vote_counts'
    ]

    # ─── Display helpers ─────────────────────────────────────────────

    def student_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.student.id])
        display_name = obj.student.get_full_name() or obj.student.email
        return format_html('<a href="{}">{}</a>', url, display_name)
    student_link.short_description = 'Student'
    student_link.admin_order_field = 'student__first_name'

    def poll_link(self, obj):
        url = reverse('admin:poll_poll_change', args=[obj.poll.id])
        return format_html('<a href="{}">{}</a>', url, obj.poll.title)
    poll_link.short_description = 'Poll'
    poll_link.admin_order_field = 'poll__title'

    def status_badge(self, obj):
        colors = {
            ContestantStatusEnum.ACTIVE.value: '#28a745',
            ContestantStatusEnum.WITHDRAWN.value: '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        display = obj.get_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;">{}</span>',
            color, display
        )
    status_badge.short_description = 'Status'

    # ─── Actions ─────────────────────────────────────────────────────

    @admin.action(description='Mark selected contestants as Active')
    def mark_active(self, request, queryset):
        updated = queryset.update(status=ContestantStatusEnum.ACTIVE.value)
        self.message_user(request, f'{updated} contestant(s) marked as active.')

    @admin.action(description='Mark selected contestants as Withdrawn')
    def mark_withdrawn(self, request, queryset):
        updated = queryset.update(status=ContestantStatusEnum.WITHDRAWN.value)
        self.message_user(request, f'{updated} contestant(s) marked as withdrawn.')

    @admin.action(description='Refresh vote counts for selected contestants')
    def refresh_vote_counts(self, request, queryset):
        updated = 0
        for contestant in queryset:
            contestant.update_vote_count()
            updated += 1
        self.message_user(request, f'Vote counts refreshed for {updated} contestant(s).')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('poll', 'student')
        return queryset

    # Disable deletion
    def has_delete_permission(self, request, obj=None):
        return False


# =============================================
# VOTE ADMIN
# =============================================

@admin.register(Vote)
class VoteAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'voter_link',
        'contestant_link',
        'poll_link',
        'voted_at',
        'created_at',
        'is_deleted'
    )
    list_filter = (
        'poll__category',
        'voted_at',
        'created_at',
        'is_deleted',
    )
    search_fields = (
        'voter__email',
        'voter__first_name',
        'voter__last_name',
        'voter__matric_number',
        'contestant__student__email',
        'contestant__student__first_name',
        'contestant__student__last_name',
        'poll__title',
    )
    readonly_fields = (
        'voted_at',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )
    autocomplete_fields = ('poll', 'contestant', 'voter')

    fieldsets = (
        ('Vote Information', {
            'fields': ('poll', 'contestant', 'voter')
        }),
        ('Timestamp', {
            'fields': ('voted_at',),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',)
        }),
    )

    # ─── Display helpers ─────────────────────────────────────────────

    def voter_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.voter.id])
        display_name = obj.voter.get_full_name() or obj.voter.email
        return format_html('<a href="{}">{}</a>', url, display_name)
    voter_link.short_description = 'Voter'
    voter_link.admin_order_field = 'voter__first_name'

    def contestant_link(self, obj):
        url = reverse('admin:poll_contestant_change', args=[obj.contestant.id])
        student_name = obj.contestant.student.get_full_name() or obj.contestant.student.email
        return format_html('<a href="{}">{}</a>', url, student_name)
    contestant_link.short_description = 'Contestant'
    contestant_link.admin_order_field = 'contestant__student__first_name'

    def poll_link(self, obj):
        url = reverse('admin:poll_poll_change', args=[obj.poll.id])
        return format_html('<a href="{}">{}</a>', url, obj.poll.title)
    poll_link.short_description = 'Poll'
    poll_link.admin_order_field = 'poll__title'

    # Disable add/delete
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('poll', 'contestant', 'contestant__student', 'voter')
        return queryset


# =============================================
# POLL RESULT CACHE ADMIN
# =============================================

@admin.register(PollResultCache)
class PollResultCacheAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'poll_link',
        'contestant_link',
        'vote_count',
        'percentage_display',
        'rank_badge',
        'last_updated',
        'is_deleted'
    )
    list_filter = (
        'poll__category',
        'rank',
        'is_deleted',
    )
    search_fields = (
        'poll__title',
        'contestant__student__email',
        'contestant__student__first_name',
        'contestant__student__last_name',
    )
    readonly_fields = (
        'poll',
        'contestant',
        'vote_count',
        'percentage',
        'rank',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )

    fieldsets = (
        ('Result Information', {
            'fields': ('poll', 'contestant', 'vote_count', 'percentage', 'rank')
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',)
        }),
    )

    # ─── Display helpers ─────────────────────────────────────────────

    def poll_link(self, obj):
        url = reverse('admin:poll_poll_change', args=[obj.poll.id])
        return format_html('<a href="{}">{}</a>', url, obj.poll.title)
    poll_link.short_description = 'Poll'
    poll_link.admin_order_field = 'poll__title'

    def contestant_link(self, obj):
        url = reverse('admin:poll_contestant_change', args=[obj.contestant.id])
        student_name = obj.contestant.student.get_full_name() or obj.contestant.student.email
        return format_html('<a href="{}">{}</a>', url, student_name)
    contestant_link.short_description = 'Contestant'
    contestant_link.admin_order_field = 'contestant__student__first_name'

    def percentage_display(self, obj):
        return f"{obj.percentage}%"
    percentage_display.short_description = 'Percentage'
    percentage_display.admin_order_field = 'percentage'

    def rank_badge(self, obj):
        rank = obj.rank
        colors = {
            1: '#FFD700',  # Gold
            2: '#C0C0C0',  # Silver
            3: '#CD7F32',  # Bronze
        }
        color = colors.get(rank, '#6c757d')
        prefix = {1: '🥇', 2: '🥈', 3: '🥉'}.get(rank, f'#{rank}')
        return format_html(
            '<span style="background-color: {}; color: #000; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;">{}</span>',
            color, prefix
        )
    rank_badge.short_description = 'Rank'
    rank_badge.admin_order_field = 'rank'

    def last_updated(self, obj):
        return obj.modified_at or obj.created_at
    last_updated.short_description = 'Updated'
    last_updated.admin_order_field = 'modified_at'

    # Disable add/delete
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('poll', 'contestant', 'contestant__student')
        return queryset