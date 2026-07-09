from datetime import timedelta
from django.utils import timezone

from apps.campus.models import Listing, Review
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum, ListingStatusType
from utils.helpers import calculate_profile_completion
from django.db.models import Count, Q

class DashboardQuery:
    @staticmethod
    def get_dashboard(request):
        user = request.user
        cache_key = CacheKeysEnum.format(CacheKeysEnum.DASHBOARD, user_id=user.id)
        cached_data = GlobalCache.get(cache_key)
        if cached_data:
            return BaseResultWithData(
                message="Dashboard data retrieved successfully",
                data=cached_data,
                status_code=200
            )
            
        now = timezone.now()

        # --- Basic counts (combined aggregate to avoid multiple DB hits) ---
        counts = Listing.objects.filter(user=user, is_deleted=False).aggregate(
            total_active=Count('id', filter=Q(status=ListingStatusType.ACTIVE.value, expires_at__gt=now)),
            total_expired=Count('id', filter=Q(status=ListingStatusType.EXPIRED.value)),
            total_marked_sold=Count('id', filter=Q(status=ListingStatusType.SOLD.value))
        )
        total_active = counts.get('total_active') or 0
        total_expired = counts.get('total_expired') or 0
        total_marked_sold = counts.get('total_marked_sold') or 0

        # Trust score (average rating)
        trust_score = round((float(user.average_rating) / 5.0) * 100, 1) if user.average_rating else 0.0

        # Profile completion calculation
        profile_completion = calculate_profile_completion(user)

        # --- Upcoming expirations (next 7 days) ---
        upcoming_expiring = Listing.objects.filter(
            user=user,
            status=ListingStatusType.ACTIVE.value,
            is_deleted=False,
            expires_at__gt=now,
            expires_at__lte=now + timedelta(days=7)
        ).select_related('category').prefetch_related('hotspots').order_by('expires_at')[:5]

        upcoming_expiring_listings = []
        for listing in upcoming_expiring:
            days_left = (listing.expires_at - now).days
            upcoming_expiring_listings.append({
                'title': listing.title,
                'description': listing.description or "",
                'expires_at_humanized': f"Expires in {days_left} day{'s' if days_left != 1 else ''}",
                'hostpost_names': [hs.name for hs in listing.hotspots.all()[:2]],
                'auto_reactivate': listing.auto_reactivate,
            })

        # --- All listings (full details) ---
        all_listings_qs = Listing.objects.filter(
            user=user,
            is_deleted=False
        ).select_related('category').prefetch_related('hotspots').order_by('-created_at')

        all_listings = []
        for listing in all_listings_qs:
            location = [hs.name for hs in listing.hotspots.all()] or ["Campus"]
            image_url = None
            if listing.image:
                image_url = request.build_absolute_uri(listing.image.url)
            all_listings.append({
                'id': listing.id,
                'title': listing.title,
                'description': listing.description or "",
                'price': float(listing.price) if listing.price else 0,
                'category': listing.category.name,
                'badge': listing.badge,
                'is_hot_sale': listing.is_hot_sales,
                'is_ads_banner': listing.is_ads_banner,
                'lisiting_type': listing.listing_type,
                'auto_reactivate': listing.auto_reactivate,
                'location': location,
                'status': listing.status,
                'image': image_url,
                'created_at_humanized': DashboardQuery._humanize_date(listing.created_at),
            })

        # --- All reviews received by this user ---
        reviews_qs = Review.objects.filter(
            to_user=user,
            is_deleted=False
        ).select_related('from_user', 'listing').order_by('-created_at')

        all_reviews = []
        for review in reviews_qs:
            all_reviews.append({
                'from': review.from_user.get_full_name() or review.from_user.email,
                'rating': review.rating,
                'comment': review.comment or "",
                'date': review.created_at.date().isoformat(),
            })

        first_name = user.first_name or user.email.split('@')[0]

        data = {
            'user': first_name,
            'first_name': first_name,
            'total_active': total_active,
            'total_marked_sold': total_marked_sold,
            'total_expired': total_expired,
            'total_sold': user.sold_items,
            'trust_score': trust_score,
            'profile_completion': profile_completion,
            'upcoming_expiring_listings': upcoming_expiring_listings,
            'all_listings': all_listings,
            'all_reviews': all_reviews,
        }

        GlobalCache.set(cache_key, data)

        return BaseResultWithData(
            message="Dashboard data retrieved successfully",
            data=data,
            status_code=200
        )
        

    @staticmethod
    def _humanize_date(date):
        """Return a human-friendly relative time string."""
        now = timezone.now()
        diff = now - date
        if diff.days == 0:
            if diff.seconds < 60:
                return "just now"
            elif diff.seconds < 3600:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        else:
            return date.strftime("%b %d, %Y")