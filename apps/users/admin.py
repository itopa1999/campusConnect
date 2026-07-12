from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Avg, Prefetch
from .models import *
from django.utils.safestring import mark_safe

class UserAdmin(admin.ModelAdmin):
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
        'date_joined'
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
    readonly_fields = (
        'date_joined',
        'last_login',
        'student_id_preview',
        'profile_picture_preview',
        'average_rating_display',
        'created_at',
        'modified_at',
        'deleted_at',
        'deleted_by'
    )
    
    fieldsets = (
        ('Account Information', {
            'fields': ('email', 'first_name', 'last_name', 'phone', 'email_verified', 'hall_verified', 'points',
                       'notification', 'visibility')
        }),
        ('Student Verification (Trust Core)', {
            'fields': ('matric_number', 'student_id_photo', 'student_id_preview', 'student_id_verified')
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
        ('Audit Trail', {
            'fields': (
                'created_at',
                'created_by',
                'modified_at',
                'modified_by',
                'is_deleted',
                'deleted_at',
                'deleted_by',
            ),
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
    

class VerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'token_type', 'status_badge', 'created_at')
    list_filter = ('token_type', 'is_used', 'created_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('token', 'created_at', 'modified_at')
    
    fieldsets = (
        ('Token Information', {
            'fields': ('user', 'token', 'token_type')
        }),
        ('Status', {
            'fields': ('is_used',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at'),
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

class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_short', 'icon_preview')
    search_fields = ('name', 'description')
    readonly_fields = ('icon_preview',)
    
    def description_short(self, obj):
        return (obj.description[:75] + '...') if obj.description and len(obj.description) > 75 else obj.description
    description_short.short_description = "Description"
    
    def icon_preview(self, obj):
        if obj.icon:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;"/>', 
                              obj.icon.url)
        return "No icon"
    icon_preview.short_description = "Icon Preview"


class ContactReportAdmin(admin.ModelAdmin):
    # ========== LIST VIEW ==========
    list_display = (
        'id', 
        'issue_type_badge', 
        'reporter_name', 
        'reporter_email',
        'created_at', 
        'is_reviewed', 
        'is_deleted'
    )
    
    list_filter = (
        'issue_type',
        'is_reviewed',
        'is_deleted',
        'created_at',
    )
    
    search_fields = (
        'reporter_name',
        'reporter_email',
        'reported_user_email',
        'listing_identifier',
        'message',
        'admin_notes'
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
    
    # ========== FIELD SETS (detail view) ==========
    fieldsets = (
        ('Reporter Information', {
            'fields': ('reporter_name', 'reporter_email'),
            'classes': ('wide',),
        }),
        ('Issue Details', {
            'fields': ('issue_type', 'message'),
            'classes': ('wide',),
        }),
        ('Context (if applicable)', {
            'fields': ('listing_identifier', 'reported_user_email'),
            'classes': ('collapse', 'wide'),
        }),
        ('Admin Handling', {
            'fields': ('is_reviewed', 'admin_notes'),
            'classes': ('wide',),
        }),
        ('Audit Trail (BaseModel fields)', {
            'fields': (
                'created_at', 'created_by',
                'modified_at', 'modified_by',
                'is_deleted', 'deleted_at', 'deleted_by'
            ),
            'classes': ('collapse',),
        }),
    )
    
    # ========== ACTIONS ==========
    actions = ['mark_as_reviewed', 'mark_as_unreviewed', 'soft_delete_selected']
    
    @admin.action(description='Mark selected reports as reviewed')
    def mark_as_reviewed(self, request, queryset):
        updated = queryset.update(is_reviewed=True)
        self.message_user(request, f'{updated} report(s) marked as reviewed.')
    
    @admin.action(description='Mark selected reports as not reviewed')
    def mark_as_unreviewed(self, request, queryset):
        updated = queryset.update(is_reviewed=False)
        self.message_user(request, f'{updated} report(s) marked as not reviewed.')
    
    @admin.action(description='Soft delete selected reports')
    def soft_delete_selected(self, request, queryset):
        from django.utils.timezone import now
        updated = queryset.update(
            is_deleted=True,
            deleted_at=now(),
            deleted_by=request.user.username
        )
        self.message_user(request, f'{updated} report(s) soft-deleted.')
    
    # ========== CUSTOM METHODS FOR LIST DISPLAY ==========
    def issue_type_badge(self, obj):
        """Display issue type with a colored badge."""
        colors = {
            'report_listing': '#dc3545',   # red
            'report_user': '#fd7e14',      # orange
            'bug': '#ffc107',              # yellow
            'question': '#28a745',         # green
            'other': '#6c757d',            # gray
        }
        display = obj.get_issue_type_display()
        color = colors.get(obj.issue_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.75rem;">{}</span>',
            color, display
        )
    issue_type_badge.short_description = 'Issue Type'
    issue_type_badge.admin_order_field = 'issue_type'
    
    # ========== SAVE METHOD (optional) ==========
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user.username
        obj.modified_by = request.user.username
        super().save_model(request, obj, form, change)

admin.site.register(ContactReport, ContactReportAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(VerificationToken, VerificationTokenAdmin)
admin.site.register(Badge, BadgeAdmin)


# ========== PointTransaction Inline ==========
class PointTransactionInline(admin.TabularInline):
    model = PointTransaction
    extra = 0
    readonly_fields = ('amount', 'balance_after', 'transaction_type', 'description', 'reference', 'created_at')
    fields = ('amount', 'balance_after', 'transaction_type', 'description', 'reference', 'created_at')
    can_delete = False
    show_change_link = True
    ordering = ('-created_at',)

    def get_queryset(self, request):
        # Optimize with select_related for user
        return super().get_queryset(request).select_related('user')


# ========== PointPackage Admin ==========
@admin.register(PointPackage)
class PointPackageAdmin(admin.ModelAdmin):
    list_display = ('points', 'price', 'price_per_point_display', 'savings_percentage_display', 'is_popular', 'is_best_value', 'sort_order')
    list_filter = ('is_popular', 'is_best_value', 'sort_order')
    search_fields = ('description',)
    ordering = ('sort_order', 'points')
    fieldsets = (
        (None, {
            'fields': ('points', 'price', 'description', 'sort_order')
        }),
        ('Highlighting', {
            'fields': ('is_popular', 'is_best_value'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('is_deleted', 'created_at', 'modified_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('created_at', 'modified_at')
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
class PointPurchaseAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'package_link', 'points_awarded', 'gateway', 'amount_paid', 'status', 'completed_at', 'created_at')
    list_filter = ('status', 'completed_at', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'package__description', 'payment_reference')
    readonly_fields = ('created_at', 'modified_at', 'points_awarded', 'amount_paid')
    raw_id_fields = ('user', 'package')
    fieldsets = (
        (None, {
            'fields': ('user', 'package', 'points_awarded', 'amount_paid', 'status', 'payment_reference', 'completed_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'modified_at', 'is_deleted'),
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
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_link', 'amount', 'balance_after', 'transaction_type_display', 'description', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'description', 'reference')
    readonly_fields = ('user', 'amount', 'balance_after', 'transaction_type', 'description', 'reference', 'purchase', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'amount', 'balance_after', 'transaction_type', 'description', 'reference', 'purchase')
        }),
        ('Metadata', {
            'fields': ('created_at',),
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


from django.utils.translation import gettext_lazy as _

@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    """
    Admin interface for FeatureFlag.
    """
    list_display = (
        'name',
        'is_active',
        'users_count',
        'created_at',
        'modified_at',
    )
    list_filter = (
        'is_active',
        'is_deleted',   
    )
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'modified_at')
    filter_horizontal = ('users',) 

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active', 'users')
        }),
        (_('System Fields'), {
            'fields': ('created_at', 'modified_at', 'is_deleted'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_features', 'deactivate_features']

    def get_queryset(self, request):
        """Exclude soft‑deleted records by default."""
        qs = super().get_queryset(request)
        return qs.filter(is_deleted=False)

    def users_count(self, obj):
        """Return the number of users assigned to this flag."""
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


admin.site.register(Notification)