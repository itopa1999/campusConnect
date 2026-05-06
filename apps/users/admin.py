from django.contrib import admin
from django.utils.html import format_html
from .models import *

class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'matric_number', 'student_id_verified_badge', 'email_verified_badge', 
                    'average_rating', 'transaction_count', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'email_verified', 'student_id_verified', 'level', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'matric_number', 'phone')
    readonly_fields = ('date_joined', 'last_login', 'student_id_preview', 'profile_picture_preview', 
                       'average_rating_display')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('email', 'first_name', 'last_name', 'phone', 'email_verified')
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
            'fields': ('average_rating_display', 'transaction_count'),
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


admin.site.register(User, UserAdmin)
admin.site.register(VerificationToken, VerificationTokenAdmin)