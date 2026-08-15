from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import Avg
from django.utils.safestring import mark_safe
from django.urls import reverse

from apps.campus.models import (
    CampusHotspot, Category, Claim, Favourite, Listing,
    ListingHotspot, LostAndFound, Review, SubCategory,
    SellListing, ServiceListing, AccommodationListing  # <-- added new models
)
from common.admin import SoftDeleteAdmin


# ==================== INLINES ====================

class FavouriteInline(admin.TabularInline):
    model = Favourite
    extra = 0
    fields = ('user_link', 'created_at')
    readonly_fields = ('user_link', 'created_at')
    can_delete = True
    verbose_name = "Favourited by"
    verbose_name_plural = "Favourited by"

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        display_name = obj.user.get_full_name() or obj.user.email
        return format_html('<a href="{}">{}</a>', url, display_name)
    user_link.short_description = 'User'


class ListingHotspotInline(admin.TabularInline):
    model = ListingHotspot
    extra = 1
    autocomplete_fields = ['hotspot']
    verbose_name = "Meeting Spot"
    verbose_name_plural = "Meeting Spots"


class SellListingInline(admin.StackedInline):
    """Inline for SellListing details"""
    model = SellListing
    extra = 1
    fields = ('category', 'subcategory', 'price', 'negotiation', 'condition',
              'brand', 'model', 'quantity', 'warranty')
    verbose_name = "Sell Details"
    verbose_name_plural = "Sell Details"
    can_delete = True


class ServiceListingInline(admin.StackedInline):
    """Inline for ServiceListing details"""
    model = ServiceListing
    extra = 1
    fields = ('category', 'subcategory', 'price', 'negotiation',
              'delivery_time', 'service_duration', 'experience',
              'portfolio', 'online_available')
    verbose_name = "Service Details"
    verbose_name_plural = "Service Details"
    can_delete = True


class AccommodationListingInline(admin.StackedInline):
    """Inline for AccommodationListing details"""
    model = AccommodationListing
    extra = 1
    fields = ('purpose', 'property_type', 'bedrooms', 'bathrooms', 'furnished',
              'rent_price', 'available_from', 'lease_duration',
              'electricity', 'water', 'security', 'parking',
              'distance_to_campus', 'preferred_gender', 'preferred_student_type',
              'max_occupants', 'roommate_notes')
    verbose_name = "Accommodation Details"
    verbose_name_plural = "Accommodation Details"
    can_delete = True


class ReviewGivenInline(admin.TabularInline):
    model = Review
    fk_name = 'from_user'
    extra = 0
    fields = ('to_user', 'listing', 'rating', 'comment', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = False
    verbose_name = "Review Given"
    verbose_name_plural = "Reviews Given"


class ReviewReceivedInline(admin.TabularInline):
    model = Review
    fk_name = 'to_user'
    extra = 0
    fields = ('from_user', 'listing', 'rating', 'comment', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = False
    verbose_name = "Review Received"
    verbose_name_plural = "Reviews Received"


class UserListingInline(admin.TabularInline):
    model = Listing
    extra = 0
    fields = ('title', 'listing_type', 'status', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = False
    show_change_link = True


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1
    fields = ('name', 'slug', 'icon', 'description', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    verbose_name = "Subcategory"
    verbose_name_plural = "Subcategories"
    ordering = ('sort_order', 'name')


# ==================== MODEL ADMINS ====================

@admin.register(Category)
class CategoryAdmin(SoftDeleteAdmin):
    list_display = ('name', 'slug', 'icon', 'sort_order', 'listing_type', 'is_deleted', 'listing_count')
    list_filter = ('is_deleted', 'sort_order')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    readonly_fields = (
        'created_at', 'created_by', 
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
        'listing_count_display',
    )

    inlines = [SubCategoryInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'icon', 'description', 'listing_type', 'sort_order')
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
    actions = ['mark_active']

    def listing_count(self, obj):
        sell_count = obj.sell_listings.filter(is_deleted=False).count()
        service_count = obj.service_listings.filter(is_deleted=False).count()
        return sell_count + service_count
    listing_count.short_description = 'Active Listings'

    def listing_count_display(self, obj):
        sell_count = obj.sell_listings.filter(is_deleted=False).count()
        service_count = obj.service_listings.filter(is_deleted=False).count()
        total = sell_count + service_count
        return format_html('{} listings', total)
    listing_count_display.short_description = 'Total Listings'

    def mark_active(self, request, queryset):
        queryset.update(is_deleted=False)
    mark_active.short_description = "Mark as active"


@admin.register(SubCategory)
class SubCategoryAdmin(SoftDeleteAdmin):
    list_display = (
        'id', 'name', 'category_link', 'slug', 'icon',
        'sort_order', 'is_deleted', 'listing_count'
    )
    list_filter = ('category', 'is_deleted', 'sort_order')
    search_fields = ('name', 'slug', 'description', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['category']
    actions = ['mark_active']

    readonly_fields = (
        'created_at', 'created_by',
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
        'listing_count_display',
    )

    fieldsets = (
        (None, {
            'fields': ('category', 'name', 'slug', 'icon', 'description', 'sort_order')
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

    def category_link(self, obj):
        url = reverse('admin:campus_category_change', args=[obj.category.id])
        return format_html('<a href="{}">{}</a>', url, obj.category.name)
    category_link.short_description = 'Category'
    category_link.admin_order_field = 'category__name'

    def listing_count(self, obj):
        sell_count = obj.sell_listings.filter(is_deleted=False).count()
        service_count = obj.service_listings.filter(is_deleted=False).count()
        return sell_count + service_count
    listing_count.short_description = 'Listings'

    def listing_count_display(self, obj):
        sell_count = obj.sell_listings.filter(is_deleted=False).count()
        service_count = obj.service_listings.filter(is_deleted=False).count()
        total = sell_count + service_count
        return format_html('{} listings', total)
    listing_count_display.short_description = 'Total Listings'

    def mark_active(self, request, queryset):
        queryset.update(is_deleted=False)
    mark_active.short_description = "Mark as active"

    ordering = ('category__name', 'sort_order', 'name')


@admin.register(CampusHotspot)
class CampusHotspotAdmin(SoftDeleteAdmin):
    list_display = ('name', 'sort_order', 'is_deleted', 'listing_count')
    list_filter = ('is_deleted', 'sort_order')
    search_fields = ('name', 'description')
    
    readonly_fields = (
        'created_at', 'created_by',
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'sort_order')
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
    actions = ['mark_active']

    def listing_count(self, obj):
        return obj.listings.filter(is_deleted=False).count()
    listing_count.short_description = 'Active Assoc. Listings'


@admin.register(Listing)
class ListingAdmin(SoftDeleteAdmin):
    list_display = (
        'title', 'user_link', 'listing_type',
        'status', 'expires_at', 'is_expired',
        'created_at', 'favourite_count',
        'is_hot_sales', 'is_ads_banner', 'auto_reactivate', 'is_deleted'
    )
    list_filter = (
        'listing_type', 'status', 'is_deleted',
        'expires_at', 'is_hot_sales', 'is_ads_banner'
    )
    search_fields = (
        'title', 'description', 'user__email', 'user__first_name', 'user__last_name'
    )
    
    readonly_fields = (
        'created_at', 'created_by',
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
        'review_count', 'avg_rating',
        'is_hot_sales_expires_at', 'is_ads_banner_expires_at',
        'sell_price', 'service_price', 'accommodation_price', 'listing_category'
    )
    
    autocomplete_fields = ['user']
    inlines = [
        SellListingInline,
        ServiceListingInline,
        AccommodationListingInline,
        ListingHotspotInline,
        FavouriteInline,
    ]
    date_hierarchy = 'created_at'
    actions = ['mark_active', 'mark_sold', 'mark_expired', 'extend_expiry']

    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'description', 'listing_type', 'status', 'image', 'auto_reactivate')
        }),
        ('Pricing', {
            'fields': ('sell_price', 'service_price', 'accommodation_price'),
            'classes': ('wide',)
        }),
        ('Category', {
            'fields': ('listing_category',),
        }),
        ('Expiry', {
            'fields': ('expires_at',)
        }),
        ('Promotions', {
            'fields': ('is_ads_banner', 'is_ads_banner_expires_at', 'is_hot_sales', 'is_hot_sales_expires_at'),
            'classes': ('wide',)
        }),
        ('Analytics', {
            'fields': ('review_count', 'avg_rating'),
            'classes': ('collapse',)
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

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        display_name = obj.user.get_full_name() or obj.user.email
        return format_html('<a href="{}">{}</a>', url, display_name)
    user_link.short_description = 'Student'
    user_link.admin_order_field = 'user__first_name'

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

    def sell_price(self, obj):
        try:
            return f"₦{obj.sell_details.price:.2f}" if hasattr(obj, 'sell_details') else '-'
        except:
            return '-'
    sell_price.short_description = 'Sell Price'
    sell_price.admin_order_field = 'sell_details__price'

    def service_price(self, obj):
        try:
            return f"₦{obj.service_details.price:.2f}" if hasattr(obj, 'service_details') and obj.service_details.price else '-'
        except:
            return '-'
    service_price.short_description = 'Service Price'

    def accommodation_price(self, obj):
        try:
            return f"₦{obj.accommodation_details.rent_price:.2f}" if hasattr(obj, 'accommodation_details') else '-'
        except:
            return '-'
    accommodation_price.short_description = 'Accommodation Rent'

    def listing_category(self, obj):
        if hasattr(obj, 'sell_details'):
            return obj.sell_details.category.name
        elif hasattr(obj, 'service_details'):
            return obj.service_details.category.name
        else:
            return '-'
    listing_category.short_description = 'Category'

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

    def favourite_count(self, obj):
        return obj.favourited_by.count()
    favourite_count.short_description = '❤️ Favs'
    favourite_count.admin_order_field = 'favourited_by__count'

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('user')
        queryset = queryset.prefetch_related(
            'hotspots',
            'sell_details',
            'service_details',
            'accommodation_details',
            'favourited_by'
        )
        return queryset


# ==================== DETAIL MODEL ADMINS ====================

@admin.register(SellListing)
class SellListingAdmin(SoftDeleteAdmin):
    list_display = ('id', 'listing_link', 'category', 'price', 'negotiation', 'condition', 'quantity')
    list_filter = ('category', 'negotiation', 'condition')
    search_fields = ('listing__title', 'brand', 'model', 'warranty')
    autocomplete_fields = ['listing', 'category', 'subcategory']
    raw_id_fields = ('listing',)

    fieldsets = (
        (None, {
            'fields': ('listing', 'category', 'subcategory', 'price', 'negotiation',
                       'condition', 'brand', 'model', 'quantity', 'warranty')
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

    def listing_link(self, obj):
        url = reverse('admin:campus_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)
    listing_link.short_description = 'Listing'


@admin.register(ServiceListing)
class ServiceListingAdmin(SoftDeleteAdmin):
    list_display = ('id', 'listing_link', 'category', 'price', 'negotiation', 'delivery_time', 'online_available')
    list_filter = ('category', 'negotiation', 'online_available')
    search_fields = ('listing__title', 'delivery_time', 'service_duration')
    autocomplete_fields = ['listing', 'category', 'subcategory']
    raw_id_fields = ('listing',)

    fieldsets = (
        (None, {
            'fields': ('listing', 'category', 'subcategory', 'price', 'negotiation',
                       'delivery_time', 'service_duration', 'experience',
                       'portfolio', 'online_available')
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

    def listing_link(self, obj):
        url = reverse('admin:campus_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)
    listing_link.short_description = 'Listing'


@admin.register(AccommodationListing)
class AccommodationListingAdmin(SoftDeleteAdmin):
    list_display = ('id', 'listing_link', 'purpose', 'property_type', 'rent_price', 'bedrooms', 'furnished')
    list_filter = ('purpose', 'property_type', 'furnished', 'electricity', 'water', 'security', 'parking')
    search_fields = ('listing__title', 'property_type', 'distance_to_campus')
    autocomplete_fields = ['listing']
    raw_id_fields = ('listing',)

    fieldsets = (
        (None, {
            'fields': ('listing', 'purpose', 'property_type', 'bedrooms', 'bathrooms',
                       'furnished', 'rent_price', 'available_from', 'lease_duration',
                       'electricity', 'water', 'security', 'parking',
                       'distance_to_campus', 'preferred_gender',
                       'preferred_student_type', 'max_occupants', 'roommate_notes')
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

    def listing_link(self, obj):
        url = reverse('admin:campus_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)
    listing_link.short_description = 'Listing'


# ==================== LOST AND FOUND ADMIN ====================

@admin.register(LostAndFound)
class LostAndFoundAdmin(SoftDeleteAdmin):
    list_display = ('item_name', 'location', 'date_found', 'status', 'full_name', 'email', 'claimed_by', 'is_deleted')
    list_filter = ('status', 'date_found', 'department', 'created_at')
    search_fields = ('item_name', 'description', 'location', 'full_name', 'email', 'department')
    
    readonly_fields = (
        'created_at', 'created_by',
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    
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
            'fields': ('status', 'claimed_by'),
            'classes': ('collapse',)
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
    actions = ['mark_open', 'mark_claimed', 'mark_expired']

    def mark_open(self, request, queryset):
        queryset.update(status='open', is_deleted=False)
    mark_open.short_description = "Set status to Open"

    def mark_claimed(self, request, queryset):
        queryset.update(status='claimed')
    mark_claimed.short_description = "Set status to Claimed"

    def mark_expired(self, request, queryset):
        queryset.update(status='expired')
    mark_expired.short_description = "Set status to Expired"


@admin.register(Claim)
class ClaimAdmin(SoftDeleteAdmin):
    list_display = ('id', 'lost_item_link', 'full_name', 'email', 'phone', 'answers_match', 'is_deleted')
    list_filter = ('created_at',)
    search_fields = ('lost_item__item_name', 'full_name', 'email', 'phone')
    raw_id_fields = ('lost_item',)
    
    readonly_fields = (
        'created_at', 'created_by',
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    
    fieldsets = (
        (None, {
            'fields': ('lost_item', 'full_name', 'email', 'phone')
        }),
        ('Verification Answers', {
            'fields': ('answer1', 'answer2')
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
    actions = ['mark_active']

    def lost_item_link(self, obj):
        if obj.lost_item:
            app_label = obj.lost_item._meta.app_label
            url = reverse(f'admin:{app_label}_lostandfound_change', args=[obj.lost_item.id])
            return mark_safe(f'<a href="{url}">{obj.lost_item.item_name}</a>')
        return "—"
    lost_item_link.short_description = 'Lost Item'
    lost_item_link.admin_order_field = 'lost_item__item_name'

    def answers_match(self, obj):
        if not obj.lost_item:
            return mark_safe('<span style="color: red;">✗ No item</span>')
        
        match1 = (obj.answer1 == obj.lost_item.answer1)
        match2 = (obj.answer2 == obj.lost_item.answer2)
        
        if match1 and match2:
            return mark_safe('<span style="color: green; font-weight: bold;">✓ Both match</span>')
        elif match1 or match2:
            return mark_safe('<span style="color: orange;">⚠️ Partial match</span>')
        else:
            return mark_safe('<span style="color: red;">✗ No match</span>')
    answers_match.short_description = 'Answers Match'

    def mark_active(self, request, queryset):
        queryset.update(is_deleted=False)
    mark_active.short_description = "Mark as active"


@admin.register(Favourite)
class FavouriteAdmin(SoftDeleteAdmin):
    list_display = ('id','user_link', 'listing_link', 'created_at', 'is_deleted')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'listing__title')
    raw_id_fields = ('user', 'listing')
    readonly_fields = (
        'created_at', 'created_by',
        'modified_at', 'modified_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )

    fieldsets = (
        (None, {
            'fields': ('user', 'listing')
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

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        display_name = obj.user.get_full_name() or obj.user.email
        return format_html('<a href="{}">{}</a>', url, display_name)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__first_name'

    def listing_link(self, obj):
        url = reverse('admin:campus_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)
    listing_link.short_description = 'Listing'
    listing_link.admin_order_field = 'listing__title'


@admin.register(Review)
class ReviewAdmin(SoftDeleteAdmin):
    list_display = (
        'id',
        'from_user_link',
        'to_user_link',
        'listing_link',
        'rating_stars',
        'comment_preview',
        'created_at',
        'is_deleted',
    )
    list_filter = (
        'rating',
        'created_at',
        'is_deleted',
    )
    search_fields = (
        'from_user__email',
        'from_user__first_name',
        'from_user__last_name',
        'to_user__email',
        'to_user__first_name',
        'to_user__last_name',
        'listing__title',
        'comment',
    )
    raw_id_fields = ('from_user', 'to_user', 'listing')
    autocomplete_fields = ['from_user', 'to_user', 'listing']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    # ─── Read‑only audit fields ──────────────────────────────────────
    readonly_fields = (
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'deleted_at',
        'deleted_by',
    )

    fieldsets = (
        (None, {
            'fields': ('from_user', 'to_user', 'listing', 'rating', 'comment')
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

    # ─── Custom list display methods ────────────────────────────────

    def from_user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.from_user.id])
        display = obj.from_user.get_full_name() or obj.from_user.email
        return format_html('<a href="{}">{}</a>', url, display)
    from_user_link.short_description = 'From'
    from_user_link.admin_order_field = 'from_user__first_name'

    def to_user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.to_user.id])
        display = obj.to_user.get_full_name() or obj.to_user.email
        return format_html('<a href="{}">{}</a>', url, display)
    to_user_link.short_description = 'To'
    to_user_link.admin_order_field = 'to_user__first_name'

    def listing_link(self, obj):
        if obj.listing:
            url = reverse('admin:campus_listing_change', args=[obj.listing.id])
            return format_html('<a href="{}">{}</a>', url, obj.listing.title)
        return '-'
    listing_link.short_description = 'Listing'
    listing_link.admin_order_field = 'listing__title'

    def rating_stars(self, obj):
        full = '★' * obj.rating
        empty = '☆' * (5 - obj.rating)
        return mark_safe(f'<span style="color: var(--star, #f5b342);">{full}{empty}</span>')
    rating_stars.short_description = 'Rating'
    rating_stars.admin_order_field = 'rating'

    def comment_preview(self, obj):
        if obj.comment:
            return obj.comment[:50] + '…' if len(obj.comment) > 50 else obj.comment
        return '-'
    comment_preview.short_description = 'Comment'

    # ─── Actions ──────────────────────────────────────────────────────

    actions = ['mark_as_deleted', 'restore_selected']

    def mark_as_deleted(self, request, queryset):
        queryset.update(is_deleted=True)
        self.message_user(request, f'{queryset.count()} review(s) marked as deleted.')
    mark_as_deleted.short_description = 'Soft‑delete selected reviews'

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(request, f'{queryset.count()} review(s) restored.')
    restore_selected.short_description = 'Restore selected reviews'

    # ─── Optimize queryset ──────────────────────────────────────────

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'from_user', 'to_user', 'listing'
        )