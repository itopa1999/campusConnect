from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin import ModelAdmin
from django.utils.safestring import mark_safe
from apps.moderator.models import ModeratorAction, FlaggedContent, UserModeration, ModeratorNote
from apps.users.models import User
from common.admin import SoftDeleteAdmin
from utils.enums import ContentTypeEnum, ModeratorActionTypeEnum, ReportStatusEnum


# ==================== MODERATOR ACTION ADMIN ====================

@admin.register(ModeratorAction)
class ModeratorActionAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'moderator_link',
        'action_type_badge',
        'content_type_badge',
        'content_id',
        'reason_preview',
        'is_deleted',
    )
    list_filter = (
        'action_type',
        'content_type',
        'created_at',
    )
    search_fields = (
        'moderator__email',
        'moderator__first_name',
        'moderator__last_name',
        'content_id',
        'reason',
    )
    readonly_fields = (
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    autocomplete_fields = ['moderator']

    fieldsets = (
        (None, {
            'fields': ('moderator', 'action_type', 'content_type', 'content_id'),
        }),
        ('Details', {
            'fields': ('reason', 'metadata', 'ip_address'),
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',),
        }),
    )

    def moderator_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.moderator.id])
        display_name = obj.moderator.get_full_name() or obj.moderator.email
        return format_html('<a href="{}">{}</a>', url, display_name)
    moderator_link.short_description = 'Moderator'
    moderator_link.admin_order_field = 'moderator__first_name'

    def action_type_badge(self, obj):
        colors = {
            'approve': '#28a745',
            'reject': '#dc3545',
            'hide': '#ffc107',
            'delete': '#dc3545',
            'flag': '#fd7e14',
            'unflag': '#6c757d',
            'warning': '#ffc107',
            'suspend': '#fd7e14',
            'ban': '#dc3545',
            'reinstate': '#28a745',
            'resolve_report': '#28a745',
            'escalate': '#dc3545',
        }
        color = colors.get(obj.action_type, '#6c757d')
        display = obj.get_action_type_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem;">{}</span>',
            color, display
        )
    action_type_badge.short_description = 'Action'
    action_type_badge.admin_order_field = 'action_type'

    def content_type_badge(self, obj):
        colors = {
            'listing': '#007bff',
            'review': '#fd7e14',
            'user': '#28a745',
            'report': '#dc3545',
        }
        color = colors.get(obj.content_type, '#6c757d')
        display = obj.get_content_type_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem;">{}</span>',
            color, display
        )
    content_type_badge.short_description = 'Content Type'
    content_type_badge.admin_order_field = 'content_type'

    def reason_preview(self, obj):
        return obj.reason[:50] + '...' if obj.reason and len(obj.reason) > 50 else obj.reason or '-'
    reason_preview.short_description = 'Reason'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('moderator')


# ==================== FLAGGED CONTENT ADMIN ====================

@admin.register(FlaggedContent)
class FlaggedContentAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'content_type_badge',
        'content_id',
        'flagged_by_link',
        'reason_preview',
        'is_resolved_badge',
        'is_deleted',
    )
    list_filter = (
        'content_type',
        'is_resolved',
        'created_at',
    )
    search_fields = (
        'content_id',
        'reason',
        'flagged_by__email',
        'flagged_by__first_name',
        'flagged_by__last_name',
        'resolution_note',
    )
    readonly_fields = (
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    autocomplete_fields = ['flagged_by', 'resolved_by']

    fieldsets = (
        (None, {
            'fields': ('content_type', 'content_id', 'flagged_by', 'reason'),
        }),
        ('Resolution', {
            'fields': ('is_resolved', 'resolved_by', 'resolved_at', 'resolution_note'),
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',),
        }),
    )

    actions = ['mark_as_resolved', 'mark_as_unresolved']

    # Use mark_safe with f-strings instead of format_html
    def content_type_badge(self, obj):
        colors = {
            'listing': '#007bff',
            'review': '#fd7e14',
            'user': '#28a745',
            'report': '#dc3545',
        }
        color = colors.get(obj.content_type, '#6c757d')
        display = obj.get_content_type_display()
        return mark_safe(
            f'<span style="background-color: {color}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem;">{display}</span>'
        )
    content_type_badge.short_description = 'Content Type'
    content_type_badge.admin_order_field = 'content_type'

    def flagged_by_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.flagged_by.id])
        display_name = obj.flagged_by.get_full_name() or obj.flagged_by.email
        return mark_safe(f'<a href="{url}">{display_name}</a>')
    flagged_by_link.short_description = 'Flagged By'
    flagged_by_link.admin_order_field = 'flagged_by__first_name'

    def reason_preview(self, obj):
        return obj.reason[:50] + '...' if obj.reason and len(obj.reason) > 50 else obj.reason or '-'
    reason_preview.short_description = 'Reason'

    def is_resolved_badge(self, obj):
        if obj.is_resolved:
            return mark_safe('<span style="color: green;">✅ Resolved</span>')
        return mark_safe('<span style="color: #ffc107;">⏳ Pending</span>')
    is_resolved_badge.short_description = 'Status'
    is_resolved_badge.admin_order_field = 'is_resolved'

    @admin.action(description='Mark selected flags as resolved')
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(
            is_resolved=True,
            resolved_by=request.user,
            resolved_at=timezone.now()
        )
        self.message_user(request, f'{updated} flag(s) marked as resolved.')

    @admin.action(description='Mark selected flags as unresolved (pending)')
    def mark_as_unresolved(self, request, queryset):
        updated = queryset.update(
            is_resolved=False,
            resolved_by=None,
            resolved_at=None
        )
        self.message_user(request, f'{updated} flag(s) marked as unresolved.')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('flagged_by', 'resolved_by')

    
# ==================== USER MODERATION ADMIN ====================

from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone

@admin.register(UserModeration)
class UserModerationAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'user_link',
        'warning_count',
        'is_suspended_badge',
        'suspended_until',
        'is_banned_badge',
        'banned_at',
        'modified_at',
        'is_deleted'
    )
    list_filter = (
        'is_suspended',
        'is_banned',
        'created_at',
        'is_deleted',
    )
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'notes',
        'ban_reason',
    )
    readonly_fields = (
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )
    ordering = ['-user__email']
    autocomplete_fields = ['user']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('user',),
        }),
        ('Moderation Status', {
            'fields': ('warning_count', 'is_suspended', 'suspended_until', 'is_banned', 'banned_at', 'ban_reason'),
        }),
        ('Notes', {
            'fields': ('notes',),
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',),
        }),
    )

    actions = ['increment_warning', 'reset_warnings', 'suspend_user', 'unsuspend_user', 'ban_user', 'unban_user']

    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.id])
            display_name = obj.user.get_full_name() or obj.user.email
            return mark_safe(f'<a href="{url}">{display_name}</a>')
        return "—"
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__first_name'

    def is_suspended_badge(self, obj):
        if obj.is_suspended:
            return mark_safe('<span style="color: #fd7e14;">⏳ Suspended</span>')
        return mark_safe('<span style="color: green;">✅ Active</span>')
    is_suspended_badge.short_description = 'Suspended?'
    is_suspended_badge.admin_order_field = 'is_suspended'

    def is_banned_badge(self, obj):
        if obj.is_banned:
            return mark_safe('<span style="color: #dc3545;">🚫 Banned</span>')
        return mark_safe('<span style="color: green;">✅ Active</span>')
    is_banned_badge.short_description = 'Banned?'
    is_banned_badge.admin_order_field = 'is_banned'

    @admin.action(description='Increment warning count for selected users')
    def increment_warning(self, request, queryset):
        for obj in queryset:
            obj.warning_count += 1
            obj.save()
        self.message_user(request, f'Warning count incremented for {queryset.count()} user(s).')

    @admin.action(description='Reset warning count to 0')
    def reset_warnings(self, request, queryset):
        queryset.update(warning_count=0)
        self.message_user(request, f'Warning count reset for {queryset.count()} user(s).')

    @admin.action(description='Suspend selected users until tomorrow')
    def suspend_user(self, request, queryset):
        until = timezone.now() + timezone.timedelta(days=1)
        updated = queryset.update(is_suspended=True, suspended_until=until)
        self.message_user(request, f'{updated} user(s) suspended until {until.strftime("%Y-%m-%d %H:%M")}.')

    @admin.action(description='Unsuspend selected users')
    def unsuspend_user(self, request, queryset):
        updated = queryset.update(is_suspended=False, suspended_until=None)
        self.message_user(request, f'{updated} user(s) unsuspended.')

    @admin.action(description='Ban selected users permanently')
    def ban_user(self, request, queryset):
        updated = queryset.update(is_banned=True, banned_at=timezone.now())
        self.message_user(request, f'{updated} user(s) banned permanently.')

    @admin.action(description='Unban selected users')
    def unban_user(self, request, queryset):
        updated = queryset.update(is_banned=False, banned_at=None, ban_reason='')
        self.message_user(request, f'{updated} user(s) unbanned.')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

# ==================== MODERATOR NOTE ADMIN ====================


@admin.register(ModeratorNote)
class ModeratorNoteAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'author_link',
        'content_type_badge',
        'content_id',
        'note_preview',
        'is_private_badge',
        'created_at',
        'is_deleted'
    )
    list_filter = (
        'content_type',
        'is_private',
        'created_at',
    )
    search_fields = (
        'author__email',
        'author__first_name',
        'author__last_name',
        'content_id',
        'note',
    )
    readonly_fields = (
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )
    ordering = ['-created_at']
    autocomplete_fields = ['author']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('author', 'content_type', 'content_id', 'note', 'is_private'),
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',),
        }),
    )

    def author_link(self, obj):
        if obj.author:
            url = reverse('admin:users_user_change', args=[obj.author.id])
            display_name = obj.author.get_full_name() or obj.author.email
            return mark_safe(f'<a href="{url}">{display_name}</a>')
        return "—"
    author_link.short_description = 'Author'
    author_link.admin_order_field = 'author__first_name'

    def content_type_badge(self, obj):
        colors = {
            'listing': '#007bff',
            'review': '#fd7e14',
            'user': '#28a745',
            'report': '#dc3545',
        }
        color = colors.get(obj.content_type, '#6c757d')
        display = obj.get_content_type_display()
        return mark_safe(
            f'<span style="background-color: {color}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem;">{display}</span>'
        )
    content_type_badge.short_description = 'Content Type'
    content_type_badge.admin_order_field = 'content_type'

    def note_preview(self, obj):
        return obj.note[:50] + '...' if obj.note and len(obj.note) > 50 else obj.note or '-'
    note_preview.short_description = 'Note'

    def is_private_badge(self, obj):
        if obj.is_private:
            return mark_safe('<span style="color: #6c757d;">🔒 Private</span>')
        return mark_safe('<span style="color: #28a745;">🌐 Public</span>')
    is_private_badge.short_description = 'Privacy'
    is_private_badge.admin_order_field = 'is_private'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author')