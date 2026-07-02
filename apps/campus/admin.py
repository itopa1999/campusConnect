from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Avg

from .models import *

# ==================== INLINES ====================

class ListingHotspotInline(admin.TabularInline):
    """Show which hotspots a listing can meet at"""
    model = ListingHotspot
    extra = 1
    autocomplete_fields = ['hotspot']
    verbose_name = "Meeting Spot"
    verbose_name_plural = "Meeting Spots"


class ReviewGivenInline(admin.TabularInline):
    """Reviews this user wrote for others"""
    model = Review
    fk_name = 'from_user'
    extra = 0
    fields = ('to_user', 'listing', 'rating', 'comment', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = False
    verbose_name = "Review Given"
    verbose_name_plural = "Reviews Given"


class ReviewReceivedInline(admin.TabularInline):
    """Reviews others wrote about this user"""
    model = Review
    fk_name = 'to_user'
    extra = 0
    fields = ('from_user', 'listing', 'rating', 'comment', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = False
    verbose_name = "Review Received"
    verbose_name_plural = "Reviews Received"


class UserListingInline(admin.TabularInline):
    """Listings created by this user"""
    model = Listing
    extra = 0
    fields = ('title', 'price', 'listing_type', 'status', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = False
    show_change_link = True


# ==================== MODEL ADMINS ====================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'sort_order', 'is_deleted', 'listing_count')
    list_filter = ('is_deleted', 'sort_order')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'modified_at', 'listing_count_display')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'icon', 'description', 'sort_order')
        }),
        ('Status', {
            'fields': ('is_deleted',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'modified_at', 'created_by', 'modified_by'),
            'classes': ('collapse',)
        })
    )
    actions = ['mark_active', 'mark_deleted']

    def listing_count(self, obj):
        return obj.listings.count()
    listing_count.short_description = 'Active Listings'

    def listing_count_display(self, obj):
        url = reverse('admin:listings_listing_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} listings</a>', url, obj.listings.count())
    listing_count_display.short_description = 'Total Listings'

    def mark_active(self, request, queryset):
        queryset.update(is_deleted=False)
    mark_active.short_description = "Mark as active"

    def mark_deleted(self, request, queryset):
        queryset.update(is_deleted=True)
    mark_deleted.short_description = "Mark as deleted"


@admin.register(CampusHotspot)
class CampusHotspotAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order', 'is_deleted', 'listing_count')
    list_filter = ('is_deleted', 'sort_order')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'modified_at',)
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'sort_order')
        }),
        ('Status', {'fields': ('is_deleted',)}),
        ('Metadata', {'fields': ('created_at', 'modified_at'), 'classes': ('collapse',)})
    )
    actions = ['mark_active', 'mark_deleted']

    def listing_count(self, obj):
        return obj.listings.count()
    listing_count.short_description = 'Active Assoc. Listings'


from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Avg
from apps.campus.models import Listing



@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'user_link', 'category',
        'price', 'listing_type', 'badge',
        'status', 'expires_at', 'is_expired',
        'created_at',
        'is_hot_sales', 'is_hot_sales_expires_at',
        'is_ads_banner', 'is_ads_banner_expires_at'
    )
    list_filter = (
        'listing_type', 'status', 'category', 'is_deleted',
        'expires_at', 'is_hot_sales', 'is_ads_banner'  # new filters
    )
    search_fields = (
        'title', 'description', 'user__email', 'user__full_name',
        'is_hot_sales', 'is_ads_banner'  # optional, but can help
    )
    readonly_fields = (
        'created_at', 'modified_at', 'review_count', 'avg_rating',
        'is_hot_sales_expires_at', 'is_ads_banner_expires_at'  # auto-set, so read-only
    )
    autocomplete_fields = ['user', 'category']
    inlines = [ListingHotspotInline]
    date_hierarchy = 'created_at'
    actions = ['mark_active', 'mark_sold', 'mark_expired', 'extend_expiry']

    fieldsets = (
        (None, {
            'fields': ('user', 'category', 'title', 'description', 'price', 'listing_type', 'status', 'image')
        }),
        ('Expiry', {
            'fields': ('expires_at',)
        }),
        ('Promotions', {   # <-- new fieldset
            'fields': ('is_ads_banner', 'is_ads_banner_expires_at', 'is_hot_sales', 'is_hot_sales_expires_at'),
            'classes': ('wide',)
        }),
        ('Analytics', {
            'fields': ('review_count', 'avg_rating'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'modified_at', 'created_by', 'modified_by', 'is_deleted'),
            'classes': ('collapse',)
        })
    )

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        display_name = obj.user.get_full_name() or obj.user.email
        return format_html('<a href="{}">{}</a>', url, display_name)
    user_link.short_description = 'Student'
    user_link.admin_order_field = 'user__full_name'

    def is_expired(self, obj):
        return obj.expires_at < timezone.now()
    is_expired.boolean = True
    is_expired.short_description = 'Expired?'

    def review_count(self, obj):
        return obj.reviews.filter(is_deleted=False).count()
    review_count.short_description = 'Reviews'

    def avg_rating(self, obj):
        avg = obj.reviews.filter(is_deleted=False).aggregate(Avg('rating'))['rating__avg']
        return f"{avg:.1f}★" if avg else 'No reviews'
    avg_rating.short_description = 'Avg Rating'

    def mark_active(self, request, queryset):
        queryset.update(status='active', is_deleted=False)
    mark_active.short_description = "Set as Active"

    def mark_sold(self, request, queryset):
        queryset.update(status='sold')
    mark_sold.short_description = "Mark as Sold"

    def mark_expired(self, request, queryset):
        queryset.update(status='expired')
    mark_expired.short_description = "Mark as Expired"

    def extend_expiry(self, request, queryset):
        for listing in queryset:
            listing.expires_at = timezone.now() + timezone.timedelta(days=30)
            listing.save()
    extend_expiry.short_description = "Extend expiry +30 days"

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('user', 'category')
        queryset = queryset.prefetch_related('hotspots')
        return queryset
    

@admin.register(ListingHotspot)
class ListingHotspotAdmin(admin.ModelAdmin):
    list_display = ('listing_link', 'hotspot_link', 'created_at')
    list_filter = ('hotspot',)
    autocomplete_fields = ['listing', 'hotspot']
    search_fields = ('listing__title', 'hotspot__name')

    def listing_link(self, obj):
        url = reverse('admin:campus_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)
    listing_link.short_description = 'Listing'

    def hotspot_link(self, obj):
        url = reverse('admin:campus_campushotspot_change', args=[obj.hotspot.id])
        return format_html('<a href="{}">{}</a>', url, obj.hotspot.name)
    hotspot_link.short_description = 'Hotspot'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('from_user_link', 'to_user_link', 'listing_link', 'rating', 'comment_preview', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('from_user__email', 'to_user__email', 'listing__title', 'comment')
    readonly_fields = ('created_at', 'modified_at')
    raw_id_fields = ('from_user', 'to_user', 'listing')
    actions = ['delete_selected']

    def from_user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.from_user.id])
        display_name = obj.from_user.get_full_name() or obj.from_user.email
        return format_html('<a href="{}">{}</a>', url, display_name)
    from_user_link.short_description = 'From'
    from_user_link.admin_order_field = 'from_user__first_name'

    def to_user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.to_user.id])
        display_name = obj.to_user.get_full_name() or obj.to_user.email
        return format_html('<a href="{}">{}</a>', url, display_name)
    to_user_link.short_description = 'To'
    to_user_link.admin_order_field = 'to_user__first_name'

    def listing_link(self, obj):
        if obj.listing:
            url = reverse('admin:campus_listing_change', args=[obj.listing.id])
            return format_html('<a href="{}">{}</a>', url, obj.listing.title)
        return '-'
    listing_link.short_description = 'Listing'

    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if obj.comment and len(obj.comment) > 50 else obj.comment or ''
    comment_preview.short_description = 'Comment'


# ==================== LOST AND FOUND ADMIN ====================

@admin.register(LostAndFound)
class LostAndFoundAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'location', 'date_found', 'status', 'full_name', 'email', 'claimed_by', 'created_at')
    list_filter = ('status', 'date_found', 'department', 'created_at')
    search_fields = ('item_name', 'description', 'location', 'full_name', 'email', 'department')
    readonly_fields = ('created_at', 'modified_at', 'is_deleted')
    fieldsets = (
        (None, {
            'fields': ('item_name', 'description', 'location', 'date_found', 'image')
        }),
        ('Verification Questions', {
            'fields': ('verification1', 'answer1', 'verification2', 'answer2'),
            'classes': ('wide',)
        }),
        ('Finder Contact', {
            'fields': ('full_name', 'email', 'department')
        }),
        ('Status', {
            'fields': ('status', 'is_deleted'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        })
    )
    actions = ['mark_open', 'mark_claimed', 'mark_expired', 'mark_deleted']

    def mark_open(self, request, queryset):
        queryset.update(status='open', is_deleted=False)
    mark_open.short_description = "Set status to Open"

    def mark_claimed(self, request, queryset):
        queryset.update(status='claimed')
    mark_claimed.short_description = "Set status to Claimed"

    def mark_expired(self, request, queryset):
        queryset.update(status='expired')
    mark_expired.short_description = "Set status to Expired"

    def mark_deleted(self, request, queryset):
        queryset.update(is_deleted=True)
    mark_deleted.short_description = "Soft delete selected items"


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('lost_item_link', 'full_name', 'email', 'phone', 'answers_match', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('lost_item__item_name', 'full_name', 'email', 'phone')
    readonly_fields = ('created_at', 'modified_at', 'is_deleted')
    raw_id_fields = ('lost_item',)
    fieldsets = (
        (None, {
            'fields': ('lost_item', 'full_name', 'email', 'phone')
        }),
        ('Verification Answers', {
            'fields': ('answer1', 'answer2')
        }),
        ('Status', {
            'fields': ('is_deleted',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        })
    )
    actions = ['mark_deleted', 'mark_active']

    def lost_item_link(self, obj):
        app_label = obj.lost_item._meta.app_label
        url = reverse(f'admin:{app_label}_lostandfound_change', args=[obj.lost_item.id])
        return format_html('<a href="{}">{}</a>', url, obj.lost_item.item_name)
    lost_item_link.short_description = 'Lost Item'
    lost_item_link.admin_order_field = 'lost_item__item_name'

    def answers_match(self, obj):
        match1 = (obj.answer1 == obj.lost_item.answer1)
        match2 = (obj.answer2 == obj.lost_item.answer2)
        if match1 and match2:
            return format_html('<span style="color: green; font-weight: bold;">✓ Both match</span>')
        elif match1 or match2:
            return format_html('<span style="color: orange;">⚠️ Partial match</span>')
        else:
            return format_html('<span style="color: red;">✗ No match</span>')
    answers_match.short_description = 'Answers Match'

    def mark_active(self, request, queryset):
        queryset.update(is_deleted=False)
    mark_active.short_description = "Mark as active"

    def mark_deleted(self, request, queryset):
        queryset.update(is_deleted=True)
    mark_deleted.short_description = "Soft delete selected claims"

