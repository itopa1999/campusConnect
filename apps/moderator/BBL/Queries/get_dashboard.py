from apps.campus.models import Listing, Review
from apps.moderator.models import FlaggedContent, ModeratorAction, UserModeration
from apps.users.models import User, ContactReport
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum, ContentTypeEnum, ListingStatusTypeEnum, ReportStatusEnum
from django.utils import timezone
import datetime
from django.db.models import Count, Q, Avg


class DashboardQuery:
    @staticmethod
    def get_dashboard_stats(request) -> BaseResultWithData:
        user = request.user
        cache_key = CacheKeysEnum.format(CacheKeysEnum.MOD_DASHBOARD, user_id=user.id)

        def build_dashboard_data():
            now = timezone.now()
            today = now.date()
            start_of_today = timezone.make_aware(
                datetime.datetime.combine(today, datetime.datetime.min.time())
            )

            # ─── Listing stats ──────────────────────────────────────
            deleted_listing_counts = Listing.objects.filter(is_deleted=True).aggregate(
                total=Count('id'),
                total_active=Count('id', filter=Q(status=ListingStatusTypeEnum.ACTIVE.value, expires_at__gt=now)),
                total_expired=Count('id', filter=Q(status=ListingStatusTypeEnum.EXPIRED.value)),
                total_marked_sold=Count('id', filter=Q(status=ListingStatusTypeEnum.SOLD.value)),
                total_pending=Count('id', filter=Q(status=ListingStatusTypeEnum.PENDING.value)),
            )
            listing_counts = Listing.objects.filter(is_deleted=False).aggregate(
                total=Count('id'),
                total_active=Count('id', filter=Q(status=ListingStatusTypeEnum.ACTIVE.value, expires_at__gt=now)),
                total_expired=Count('id', filter=Q(status=ListingStatusTypeEnum.EXPIRED.value)),
                total_marked_sold=Count('id', filter=Q(status=ListingStatusTypeEnum.SOLD.value)),
                total_pending=Count('id', filter=Q(status=ListingStatusTypeEnum.PENDING.value)),
            )
            listing_stats = {
                'deleted_listing_stats':{
                    'total': deleted_listing_counts['total'],
                    'active': deleted_listing_counts['total_active'],
                    'pending': deleted_listing_counts['total_pending'],
                    'expired': deleted_listing_counts['total_expired'],
                    'sold': deleted_listing_counts['total_marked_sold'],
                    'flagged': FlaggedContent.objects.filter(
                        content_type=ContentTypeEnum.LISTING.value,
                        is_resolved=False,
                        is_deleted=True
                    ).count(),
                },
                'listing_stats':{
                    'total': listing_counts['total'],
                    'active': listing_counts['total_active'],
                    'pending': listing_counts['total_pending'],
                    'expired': listing_counts['total_expired'],
                    'sold': listing_counts['total_marked_sold'],
                    'flagged': FlaggedContent.objects.filter(
                        content_type=ContentTypeEnum.LISTING.value,
                        is_resolved=False,
                        is_deleted=False
                    ).count(),
                }
            }

            # ─── Review stats ──────────────────────────────────────
            review_aggregate = Review.objects.filter(is_deleted=False).aggregate(
                total=Count('id'),
                avg_rating=Avg('rating')
            )
            review_stats = {
                'total': review_aggregate['total'],
                'average_rating': round(review_aggregate['avg_rating'] or 0.0, 1),
                'flagged': FlaggedContent.objects.filter(
                    content_type=ContentTypeEnum.REVIEW.value,
                    is_resolved=False,
                    is_deleted=False
                ).count(),
            }

            # ─── Report stats ──────────────────────────────────────
            report_counts = ContactReport.objects.filter(is_deleted=False).aggregate(
                total=Count('id'),
                pending=Count('id', filter=Q(status=ReportStatusEnum.PENDING.value)),
                in_review=Count('id', filter=Q(status=ReportStatusEnum.IN_REVIEW.value)),
                resolved=Count('id', filter=Q(status=ReportStatusEnum.RESOLVED.value)),
                escalated=Count('id', filter=Q(status=ReportStatusEnum.ESCALATED.value)),
            )
            report_stats = {
                'total': report_counts['total'],
                'pending': report_counts['pending'],
                'in_review': report_counts['in_review'],
                'resolved': report_counts['resolved'],
                'escalated': report_counts['escalated'],
                'resolved_rate': round((report_counts['resolved'] / report_counts['total']) * 100, 1) if report_counts['total'] > 0 else 0,
            }

            # ─── User stats ────────────────────────────────────────
            user_stats = {
                'total': User.objects.filter(is_deleted=False).count(),
                'new_today': User.objects.filter(
                    is_deleted=False,
                    created_at__gte=start_of_today
                ).count(),
                'suspended': UserModeration.objects.filter(is_suspended=True).count(),
                'banned': UserModeration.objects.filter(is_banned=True).count(),
            }

            # ─── Recent activity (summary) ────────────────────────
            recent_actions = ModeratorAction.objects.filter(
                moderator = user,
                is_deleted=False
            ).select_related('moderator').order_by('-created_at')[:10]

            recent_activity = [
                {
                    'id': action.id,
                    'moderator': action.moderator.get_full_name() or action.moderator.email,
                    'action': action.get_action_type_display(),
                    'content_type': action.get_content_type_display(),
                    'content_id': action.content_id,
                    'created_at': action.created_at.isoformat(),
                    'reason': action.reason[:100] if action.reason else '',
                }
                for action in recent_actions
            ]

            data = {
                'listing_stats': listing_stats,
                'review_stats': review_stats,
                'report_stats': report_stats,
                'user_stats': user_stats,
                'recent_activity': recent_activity,
                'last_updated': now.isoformat(),
            }
            return data

        # Cache for 1 hour (3600 seconds)
        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_dashboard_data,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Dashboard data retrieved successfully",
            data=data,
            status_code=200
        )