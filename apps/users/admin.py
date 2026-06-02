from django.contrib import admin
from django.utils.html import format_html
from .models import *
from django.db.models import Avg


class UserAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'full_name',
        'matric_number',
        'student_id_verified_badge',
        'email_verified_badge',
        'badges_display',
        'average_rating',
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
            'fields': ('email', 'first_name', 'last_name', 'phone', 'email_verified', 'hall_verified')
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
            return format_html('<span style="background-color: #28a745; padding: 3px 8px; border-radius: 4px; color: white;">✓ Email</span>')
        return format_html('<span style="background-color: #ffc107; padding: 3px 8px; border-radius: 4px; color: black;">⏳ Email</span>')
    email_verified_badge.short_description = "Email"

    def badges_display(self, obj):
        badges = obj.user_badges.all()
        if not badges:
            return "No badges"
        return ", ".join(badge.name for badge in badges)
    badges_display.short_description = "Badges"
    
    def student_id_verified_badge(self, obj):
        if obj.student_id_verified:
            return format_html('<span style="background-color: #28a745; padding: 3px 8px; border-radius: 4px; color: white;">✓ ID Verified</span>')
        return format_html('<span style="background-color: #dc3545; padding: 3px 8px; border-radius: 4px; color: white;">✗ ID Pending</span>')
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
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User Email"
    
    def status_badge(self, obj):
        if obj.is_used:
            return format_html('<span style="background-color: #808080; padding: 5px 10px; border-radius: 5px; color: white;">Used</span>')
        else:
            return format_html('<span style="background-color: #28a745; padding: 5px 10px; border-radius: 5px; color: white;">Valid</span>')
    status_badge.short_description = "Status"

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
    
class PointAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'amount')
    search_fields = ('user__email',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User Email"

admin.site.register(ContactReport, ContactReportAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(VerificationToken, VerificationTokenAdmin)
admin.site.register(Badge, BadgeAdmin)
admin.site.register(Point, PointAdmin)