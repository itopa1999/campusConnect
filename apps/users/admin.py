from django.contrib import admin
from django.utils.html import format_html
from .models import *


class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'phone', 'profile_picture_display', 'email_verified_badge', 'date_joined', 'is_active')
    list_filter = ('is_active', 'is_staff', 'email_verified', 'date_joined', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    readonly_fields = ('date_joined', 'last_login', 'profile_picture_preview')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('email', 'first_name', 'last_name', 'phone', 'email_verified')
        }),
        ('Profile Details', {
            'fields': ('profile_picture', 'profile_picture_preview', 'meeting_point_description'),
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
    
    def email_verified_badge(self, obj):
        if obj.email_verified:
            return format_html('<span style="background-color: #28a745; padding: 5px 10px; border-radius: 5px; color: white;">Verified</span>')
        return format_html('<span style="background-color: #ffc107; padding: 5px 10px; border-radius: 5px; color: white;">Pending</span>')
    email_verified_badge.short_description = "Email Status"
    
    def profile_picture_display(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="30" height="30" style="border-radius: 50%;"/>',
                obj.profile_picture.url
            )
        return "No picture"
    profile_picture_display.short_description = "Profile Picture"
    
    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="200" height="200" style="border-radius: 10px; object-fit: cover;"/>',
                obj.profile_picture.url
            )
        return "No profile picture uploaded"
    profile_picture_preview.short_description = "Profile Picture Preview"


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