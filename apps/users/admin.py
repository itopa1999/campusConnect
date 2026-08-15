from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Avg
from django.utils import timezone
from apps.users.models import (BackupCode, Badge, ContactReport, FeatureFlag, Notification, PointPackage, PointPurchase, PointTransaction, TwoFactorMethod, User, VerificationToken)
from common.admin import SoftDeleteAdmin

from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from utils.enums import ReportStatusEnum


@admin.register(User)
class UserAdmin(SoftDeleteAdmin):
    list_display = (
        'email',
        'full_name',
        'matric_number',
        'student_id_verified_badge',
        'email_verified_badge',
        'badges_display',
        'average_rating',
        'sold_items',
        'is_active',
        'date_joined',
        'is_deleted'
    )
    list_filter = (
        'is_active',
        'is_staff',
        'email_verified',
        'student_id_verified',
        'hall_verified',
        'level',
        'created_at'
    )
    search_fields = ('email', 'first_name', 'last_name', 'matric_number', 'phone')
    
    # ─── All audit fields as readonly ───
    readonly_fields = (
        'date_joined',
        'last_login',
        'student_id_preview',
        'profile_picture_preview',
        'average_rating_display',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by'
    )
    
    fieldsets = (
        ('Account Information', {
            'fields': ('email', 'first_name', 'last_name', 'phone', 'email_verified', 'points',
                       'notification', 'visibility', 'two_factor_enabled')
        }),
        ('Student Verification', {
            'fields': ('matric_number', 'student_id_photo', 'student_id_preview', 'student_id_verified','student_id_verified_status')
        }),
        ('Student Hall Verification', {
            'fields': ('hall_number', 'hall_residence','hall_verified', 'hall_verified_status')
        }),
        ('Academic Info', {
            'fields': ('department', 'faculty', 'level'),
            'classes': ('collapse',)
        }),
        ('Profile', {
            'fields': ('profile_picture', 'profile_picture_preview'),
            'classes': ('collapse',)
        }),
        ('Trust Metrics', {
            'fields': ('average_rating_display', 'user_badges'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login'),
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
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = "Full Name"
    full_name.admin_order_field = 'first_name'
    
    def email_verified_badge(self, obj):
        if obj.email_verified:
            return mark_safe('<span style="background-color: #28a745; padding: 3px 8px; border-radius: 4px; color: white;">✓ Email</span>')
        return mark_safe('<span style="background-color: #ffc107; padding: 3px 8px; border-radius: 4px; color: black;">⏳ Email</span>')
    email_verified_badge.short_description = "Email"

    def badges_display(self, obj):
        badges = obj.user_badges.all()
        if not badges:
            return "No badges"
        return ", ".join(badge.name for badge in badges)
    badges_display.short_description = "Badges"
    
    def student_id_verified_badge(self, obj):
        if obj.student_id_verified:
            return mark_safe('<span style="background-color: #28a745; padding: 3px 8px; border-radius: 4px; color: white;">✓ ID Verified</span>')
        return mark_safe('<span style="background-color: #dc3545; padding: 3px 8px; border-radius: 4px; color: white;">✗ ID Pending</span>')
    student_id_verified_badge.short_description = "ID Status"
    
    def average_rating_display(self, obj):
        avg = obj.reviews_received.aggregate(avg=Avg('rating'))['avg'] or 0.0
        return f"{avg:.1f} ★"
    average_rating_display.short_description = "Average Rating"
    
    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="80" height="80" style="border-radius: 50%; object-fit: cover;"/>', 
                              obj.profile_picture.url)
        return "No picture"
    profile_picture_preview.short_description = "Profile Preview"
    
    def student_id_preview(self, obj):
        if obj.student_id_photo:
            return format_html('<a href="{}" target="_blank"><img src="{}" width="150" style="border: 1px solid #ccc;"/></a>', 
                              obj.student_id_photo.url, obj.student_id_photo.url)
        return "No ID uploaded"
    student_id_preview.short_description = "Student ID Image"
    
    actions = ['verify_student_ids', 'deactivate_users']
    
    def verify_student_ids(self, request, queryset):
        queryset.update(student_id_verified=True)
        self.message_user(request, f"{queryset.count()} student(s) marked as ID verified.")
    verify_student_ids.short_description = "Mark selected as ID Verified"
    
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} user(s) deactivated.")
    deactivate_users.short_description = "Deactivate selected users"
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('user_badges', 'groups', 'user_permissions')
        return queryset


@admin.register(VerificationToken)
class VerificationTokenAdmin(SoftDeleteAdmin):
    list_display = ('user_email', 'token_type', 'status_badge', 'created_at', 'is_deleted')
    list_filter = ('token_type', 'is_used', 'created_at')
    search_fields = ('user__email', 'token')
    
    readonly_fields = (
        'token',
        'created_at', 'created_by',
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    
    fieldsets = (
        ('Token Information', {
            'fields': ('user', 'token', 'token_type')
        }),
        ('Status', {
            'fields': ('is_used',)
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
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User Email"
    
    def status_badge(self, obj):
        if obj.is_used:
            return mark_safe('<span style="background-color: #808080; padding: 5px 10px; border-radius: 5px; color: white;">Used</span>')
        else:
            return mark_safe('<span style="background-color: #28a745; padding: 5px 10px; border-radius: 5px; color: white;">Valid</span>')
    status_badge.short_description = "Status"
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('user')
        return queryset


@admin.register(Badge)
class BadgeAdmin(SoftDeleteAdmin):
    list_display = ('name', 'description_short', 'icon_preview', 'is_deleted')
    search_fields = ('name', 'description')
    
    readonly_fields = (
        'icon_preview',
        'created_at', 'created_by',
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'icon')
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
    
    def description_short(self, obj):
        return (obj.description[:75] + '...') if obj.description and len(obj.description) > 75 else obj.description
    description_short.short_description = "Description"
    
    def icon_preview(self, obj):
        if obj.icon:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;"/>', 
                              obj.icon.url)
        return "No icon"
    icon_preview.short_description = "Icon Preview"


@admin.register(ContactReport)
class ContactReportAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'issue_type_badge',
        'reporter_name',
        'reporter_email',
        'status_badge',
        'assigned_to',
        'created_at',
        'is_deleted',
    )
    list_filter = (
        'issue_type',
        'status',
        'assigned_to',
        'escalated_to_admin',
        'created_at',
        'is_deleted',
    )
    search_fields = (
        'reporter_name',
        'reporter_email',
        'reported_user_email',
        'listing_identifier',
        'message',
        'admin_notes',
        'resolution_notes',
        'escalated_note',
    )
    readonly_fields = (
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'deleted_at',
        'deleted_by',
    )
    list_per_page = 25
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    autocomplete_fields = ['assigned_to', 'resolved_by']

    fieldsets = (
        ('Reporter Information', {
            'fields': ('reporter_name', 'reporter_email'),
        }),
        ('Issue Details', {
            'fields': ('issue_type', 'message', 'listing_identifier', 'reported_user_email'),
        }),
        ('Moderation Workflow', {
            'fields': ('status', 'assigned_to', 'resolved_by', 'resolved_at', 'resolution_notes'),
        }),
        ('Escalation', {
            'fields': ('escalated_to_admin', 'escalated_at', 'escalated_note', 'escalated_by'),
        }),
        ('Admin Handling (legacy)', {
            'fields': ('is_reviewed', 'admin_notes'),
            'classes': ('collapse',),
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'created_by', 'modified_at', 'modified_by', 'is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',),
        }),
    )

    actions = ['mark_as_resolved', 'assign_to_me', 'escalate_to_admin']

    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'in_review': '#17a2b8',
            'resolved': '#28a745',
            'escalated': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        display = obj.get_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem;">{}</span>',
            color, display
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def issue_type_badge(self, obj):
        colors = {
            'report_listing': '#dc3545',
            'report_user': '#fd7e14',
            'bug': '#ffc107',
            'question': '#28a745',
            'other': '#6c757d',
        }
        display = obj.get_issue_type_display()
        color = colors.get(obj.issue_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.75rem;">{}</span>',
            color, display
        )
    issue_type_badge.short_description = 'Issue Type'
    issue_type_badge.admin_order_field = 'issue_type'

    @admin.action(description='Mark selected reports as resolved')
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(status=ReportStatusEnum.RESOLVED.value, resolved_by=request.user, resolved_at=timezone.now())
        self.message_user(request, f'{updated} report(s) marked as resolved.')

    @admin.action(description='Assign selected reports to me')
    def assign_to_me(self, request, queryset):
        updated = queryset.update(assigned_to=request.user, status=ReportStatusEnum.IN_REVIEW.value)
        self.message_user(request, f'{updated} report(s) assigned to you.')

    @admin.action(description='Escalate selected reports to admin')
    def escalate_to_admin(self, request, queryset):
        updated = queryset.update(escalated_to_admin=True, escalated_at=timezone.now(), escalated_by=request.user, status=ReportStatusEnum.ESCALATED.value)
        self.message_user(request, f'{updated} report(s) escalated to admin.')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user.username
        obj.modified_by = request.user.username
        super().save_model(request, obj, form, change)

# ========== PointTransaction Inline ==========
class PointTransactionInline(admin.TabularInline):
    model = PointTransaction
    extra = 0
    readonly_fields = (
        'amount', 'balance_after', 'transaction_type', 
        'description', 'reference', 'created_at'
    )
    fields = ('amount', 'balance_after', 'transaction_type', 'description', 'reference', 'created_at')
    can_delete = False
    show_change_link = True
    ordering = ('-created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# ========== PointPackage Admin ==========
@admin.register(PointPackage)
class PointPackageAdmin(SoftDeleteAdmin):
    list_display = ('points', 'price', 'price_per_point_display', 'savings_percentage_display', 'is_popular', 'is_best_value', 'sort_order', 'is_deleted')
    list_filter = ('is_popular', 'is_best_value', 'sort_order')
    search_fields = ('description',)
    ordering = ('sort_order', 'points')
    
    readonly_fields = (
        'created_at', 'created_by',
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    
    fieldsets = (
        (None, {
            'fields': ('points', 'price', 'description', 'sort_order')
        }),
        ('Highlighting', {
            'fields': ('is_popular', 'is_best_value'),
            'classes': ('wide',)
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_popular', 'unmark_popular', 'mark_best_value', 'unmark_best_value']

    def price_per_point_display(self, obj):
        return f"₦{obj.price_per_point:.2f}"
    price_per_point_display.short_description = 'Price/Point'

    def savings_percentage_display(self, obj):
        savings = obj.savings_percentage
        if savings:
            return f"{savings}%"
        return "-"
    savings_percentage_display.short_description = 'Savings'

    def mark_popular(self, request, queryset):
        queryset.update(is_popular=True)
    mark_popular.short_description = "Mark as Popular"

    def unmark_popular(self, request, queryset):
        queryset.update(is_popular=False)
    unmark_popular.short_description = "Unmark Popular"

    def mark_best_value(self, request, queryset):
        queryset.update(is_best_value=True)
    mark_best_value.short_description = "Mark as Best Value"

    def unmark_best_value(self, request, queryset):
        queryset.update(is_best_value=False)
    unmark_best_value.short_description = "Unmark Best Value"


# ========== PointPurchase Admin ==========
@admin.register(PointPurchase)
class PointPurchaseAdmin(SoftDeleteAdmin):
    list_display = ('user_link', 'package_link', 'points_awarded', 'gateway', 'amount_paid', 'status', 'completed_at', 'created_at', 'is_deleted')
    list_filter = ('status', 'completed_at', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'package__description', 'payment_reference')
    raw_id_fields = ('user', 'package')
    
    readonly_fields = (
        'created_at', 'created_by',
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
        'points_awarded', 'amount_paid'
    )
    
    fieldsets = (
        (None, {
            'fields': ('user', 'package', 'points_awarded', 'amount_paid', 'status', 'payment_reference', 'completed_at')
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [PointTransactionInline]
    actions = ['mark_completed', 'mark_failed', 'mark_pending']

    def user_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:users_user_change', args=[obj.user.id])
        display_name = obj.user.get_full_name() or obj.user.email
        return format_html('<a href="{}">{}</a>', url, display_name)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'

    def package_link(self, obj):
        from django.urls import reverse
        app_label = obj.package._meta.app_label
        model_name = obj.package._meta.model_name
        url = reverse(f'admin:{app_label}_{model_name}_change', args=[obj.package.id])
        return format_html('<a href="{}">{} pts – ₦{}</a>', url, obj.package.points, obj.package.price)
    package_link.short_description = 'Package'
    package_link.admin_order_field = 'package__points'

    def mark_completed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='completed', completed_at=timezone.now())
    mark_completed.short_description = "Mark as Completed"

    def mark_failed(self, request, queryset):
        queryset.update(status='failed')
    mark_failed.short_description = "Mark as Failed"

    def mark_pending(self, request, queryset):
        queryset.update(status='pending', completed_at=None)
    mark_pending.short_description = "Mark as Pending"


# ========== PointTransaction Admin ==========
@admin.register(PointTransaction)
class PointTransactionAdmin(SoftDeleteAdmin):
    list_display = ('id', 'user_link', 'amount', 'balance_after', 'transaction_type_display', 'description', 'created_at', 'is_deleted')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'description', 'reference')
    
    readonly_fields = (
        'user', 'amount', 'balance_after', 'transaction_type', 
        'description', 'reference', 'purchase', 'created_at',
        'created_by', 'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    
    fieldsets = (
        (None, {
            'fields': ('user', 'amount', 'balance_after', 'transaction_type', 'description', 'reference', 'purchase')
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by',
            ),
            'classes': ('collapse',)
        })
    )
    
    # Disable add/delete to preserve audit integrity
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def user_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:users_user_change', args=[obj.user.id])
        display_name = obj.user.get_full_name() or obj.user.email
        return format_html('<a href="{}">{}</a>', url, display_name)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'

    def transaction_type_display(self, obj):
        return obj.get_transaction_type_display()
    transaction_type_display.short_description = 'Type'
    transaction_type_display.admin_order_field = 'transaction_type'


@admin.register(FeatureFlag)
class FeatureFlagAdmin(SoftDeleteAdmin):
    list_display = (
        'name',
        'is_active',
        'users_count',
        'created_at',
        'modified_at',
        'is_deleted'
    )
    list_filter = (
        'is_active',
        'is_deleted',   
    )
    search_fields = ('name', 'description')
    filter_horizontal = ('users',)
    
    readonly_fields = (
        'created_at', 'created_by',
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active', 'users')
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

    actions = ['activate_features', 'deactivate_features']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_deleted=False)

    def users_count(self, obj):
        return obj.users.count()
    users_count.short_description = _('Users')
    users_count.admin_order_field = 'users__count'

    @admin.action(description=_('Activate selected features'))
    def activate_features(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, _('{0} features activated.').format(updated))

    @admin.action(description=_('Deactivate selected features'))
    def deactivate_features(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, _('{0} features deactivated.').format(updated))


@admin.register(Notification)
class NotificationAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'user_email',
        'title',
        'notification_type',
        'is_read',
        'is_deleted',
        'created_at'
    )
    list_filter = (
        'notification_type',
        'is_read',
        'is_deleted',
        'created_at',
        'modified_at'
    )
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'title',
        'message'
    )
    
    readonly_fields = (
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'deleted_at',
        'deleted_by'
    )
    
    fieldsets = (
        (None, {
            'fields': ('user', 'notification_type', 'title', 'message', 'is_read', 'action_url')
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    @admin.action(description='Mark selected notifications as read')
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notification(s) marked as read.')

    @admin.action(description='Mark selected notifications as unread')
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} notification(s) marked as unread.')


@admin.register(TwoFactorMethod)
class TwoFactorMethodAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'user_email',
        'method',
        'is_enabled_badge',
        'secret_masked',
        'created_at',
        'is_deleted'
    )
    list_filter = ('method', 'is_enabled', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    
    readonly_fields = (
        'user',
        'method',
        'secret',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by'
    )
    
    fieldsets = (
        ('2FA Method Details', {
            'fields': ('user', 'method', 'is_enabled', 'secret')
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['enable_methods', 'disable_methods']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def is_enabled_badge(self, obj):
        if obj.is_enabled:
            return mark_safe(
                '<span style="background-color: #28a745; padding: 3px 8px; border-radius: 4px; color: white;">Enabled</span>'
            )
        return mark_safe(
            '<span style="background-color: #dc3545; padding: 3px 8px; border-radius: 4px; color: white;">Disabled</span>'
        )
    is_enabled_badge.short_description = 'Status'

    def secret_masked(self, obj):
        if obj.secret:
            # Show only first and last 4 characters for security
            return f"{obj.secret[:4]}...{obj.secret[-4:]}" if len(obj.secret) > 8 else "****"
        return "No secret"
    secret_masked.short_description = 'Secret (masked)'

    @admin.action(description='Enable selected 2FA methods')
    def enable_methods(self, request, queryset):
        updated = queryset.update(is_enabled=True)
        self.message_user(request, f"{updated} method(s) enabled.")

    @admin.action(description='Disable selected 2FA methods')
    def disable_methods(self, request, queryset):
        updated = queryset.update(is_enabled=False)
        self.message_user(request, f"{updated} method(s) disabled.")

@admin.register(BackupCode)
class BackupCodeAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'user_email',
        'code_hash_preview',
        'is_used_badge',
        'created_at',
        'is_deleted'
    )
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'code_hash')
    
    readonly_fields = (
        'user',
        'code_hash',
        'is_used',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'is_deleted',
        'deleted_at',
        'deleted_by'
    )
    
    fieldsets = (
        ('Backup Code', {
            'fields': ('user', 'code_hash', 'is_used')
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_used', 'mark_unused']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def code_hash_preview(self, obj):
        # Show only a short preview of the hashed code
        return obj.code_hash[:12] + '...' if obj.code_hash else ''
    code_hash_preview.short_description = 'Hash (preview)'

    def is_used_badge(self, obj):
        if obj.is_used:
            return mark_safe(
                '<span style="background-color: #dc3545; padding: 3px 8px; border-radius: 4px; color: white;">Used</span>'
            )
        return mark_safe(
            '<span style="background-color: #28a745; padding: 3px 8px; border-radius: 4px; color: white;">Available</span>'
        )
    is_used_badge.short_description = 'Status'

    @admin.action(description='Mark selected backup codes as used')
    def mark_used(self, request, queryset):
        updated = queryset.update(is_used=True)
        self.message_user(request, f"{updated} code(s) marked as used.")

    @admin.action(description='Mark selected backup codes as unused')
    def mark_unused(self, request, queryset):
        updated = queryset.update(is_used=False)
        self.message_user(request, f"{updated} code(s) marked as unused.")