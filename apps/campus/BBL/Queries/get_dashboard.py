from datetime import datetime
from django.db.models import Sum, Q
from django.utils import timezone

from apps.campus.models import Listing
from utils.base_result import BaseResultWithData
from utils.enums import ListingStatusType

class DashboardQuery:
    @staticmethod
    def get_dashboard(request):
        user = request.user
        now = timezone.now()

        # Query active listings once and reuse results
        active_listings_queryset = Listing.objects.filter(
            user=user,
            status=ListingStatusType.ACTIVE.value,
            is_deleted=False,
            expires_at__gt=now
        ).select_related('category').order_by('-created_at')
        
        active_listings_count = active_listings_queryset.count()

        trust_score = float(user.average_rating or 0.0)

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

        # Get first 10 items from already queried results
        active_listings = list(active_listings_queryset[:10])


        listings_data = [
            {
                'id': listing.id,
                'title': listing.title,
                'price': str(listing.price),
                'category': listing.category.name,
                'created_at': listing.created_at.isoformat(),
                'expires_at': listing.expires_at.isoformat(),
            }
            for listing in active_listings
        ]


        return BaseResultWithData(
            message="Dashboard data retrieved successfully",
            data={
                'active_listings_count': active_listings_count,
                'trust_score': trust_score,
                'profile_completion': profile_completion,
                'listings': listings_data
            },
            status_code=200
        )


