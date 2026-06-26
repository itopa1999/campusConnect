from datetime import timedelta
from django.utils import timezone
from decimal import Decimal

from apps.campus.models import Listing, Review, ListingHotspot
from utils.base_result import BaseResultWithData
from utils.enums import ListingStatusType

class DashboardQuery:
    @staticmethod
    def get_dashboard(request):
        user = request.user
        now = timezone.now()

        # --- Basic counts ---
        total_active = Listing.objects.filter(
            user=user,
            status=ListingStatusType.ACTIVE.value,
            is_deleted=False,
            expires_at__gt=now
        ).count()

        total_expired = Listing.objects.filter(
            user=user,
            status=ListingStatusType.EXPIRED.value,
            is_deleted=False
        ).count()

        total_sold = Listing.objects.filter(
            user=user,
            status=ListingStatusType.SOLD.value,
            is_deleted=False
        ).count()

        # Points balance (direct field on User)
        points_balance = user.points if user.points is not None else 0

        # Trust score (average rating)
        trust_score = float(user.average_rating) if user.average_rating else 0.0

        # Profile completion calculation
        profile_fields = {
            'phone': user.phone,
            'profile_picture': user.profile_picture,
            'matric_number': user.matric_number,
            'department': user.department,
            'faculty': user.faculty,
            'level': user.level,
            'student_id_verified': user.student_id_verified,
            'hall_verified': user.hall_verified,
            'email_verified': user.email_verified,
        }
        total_fields = len(profile_fields)
        filled_fields = sum(1 for value in profile_fields.values() if value)
        profile_completion = int((filled_fields / total_fields) * 100) if total_fields else 0

        # --- Upcoming expirations (next 7 days) ---
        upcoming_expiring = Listing.objects.filter(
            user=user,
            status=ListingStatusType.ACTIVE.value,
            is_deleted=False,
            expires_at__gt=now,
            expires_at__lte=now + timedelta(days=7)
        ).order_by('expires_at')[:5]

        upcoming_expiring_listings = []
        for listing in upcoming_expiring:
            days_left = (listing.expires_at - now).days
            upcoming_expiring_listings.append({
                'title': listing.title,
                'description': listing.description or "",
                'expires_at_humanized': f"Expires in {days_left} day{'s' if days_left != 1 else ''}",
                'hostpost_names': [hs.name for hs in listing.hotspots.all()[:2]]
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
            'total_expired': total_expired,
            'total_sold': total_sold,
            'trust_score': trust_score,
            'profile_completion': profile_completion,
            'points_balance': points_balance,
            'upcoming_expiring_listings': upcoming_expiring_listings,
            'all_listings': all_listings,
            'all_reviews': all_reviews,
        }

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