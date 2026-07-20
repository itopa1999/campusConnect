

## 🛡️ 1. CONTENT MODERATION

### 1.1 Listing Moderation
| Feature | Description |
|---------|-------------|
| **View all listings** | Access to a moderation dashboard showing all listings (active, pending, flagged) |
| **Approve/reject new listings** | Approve or reject listings before they go live (if manual approval is enabled) |
| **Delete listings** | Remove listings that violate community guidelines or are scams |
| **Hide listings** | Temporarily hide listings for review without permanently deleting them |
| **Flag listings** | Flag listings for further review or for other moderators |
| **View listing history** | See edit history, status changes, and moderation actions taken on a listing |

### 1.2 Review Moderation
| Feature | Description |
|---------|-------------|
| **View all reviews** | Access all reviews left by users |
| **Delete inappropriate reviews** | Remove spam, hateful, or fake reviews |
| **Flag reviews** | Flag suspicious reviews for investigation |



## 👤 2. USER MANAGEMENT

| Feature | Description |
|---------|-------------|
| **View all users** | Access a list of all registered users with filtering/search capabilities |
| **View user details** | See user's listings, reviews, points, trust score, and activity history |
| **Issue warnings** | Send formal warnings to users who violate rules |
| **Suspend users** | Temporarily suspend a user's account (with reason and duration) |
| **Ban users** | Permanently ban users for severe violations |
| **Unban/unsuspend** | Reinstate users after a ban or suspension |
| **View moderation history** | See all warnings, suspensions, and bans issued to a user |
| **Contact users** | Send direct messages to users (for warnings, assistance, etc.) |

---

## 🚨 3. REPORT & DISPUTE MANAGEMENT

| Feature | Description |
|---------|-------------|
| **View reports** | Access a dashboard of all reports submitted by users |
| **Filter reports** | Filter by type (listing, review, user, scam), status (pending, resolved), or date |
| **Review reported content** | Investigate reported listings, reviews, or users |
| **Resolve reports** | Mark reports as resolved with notes on actions taken |
| **Escalate reports** | Escalate serious cases to admins |
| **View dispute history** | Track all disputes and their resolutions |

---

## 📊 4. ANALYTICS & DASHBOARD

| Feature | Description |
|---------|-------------|
| **Moderation dashboard** | Overview of pending tasks, recent activity, and key metrics |
| **Listing statistics** | Total listings, active, pending, flagged, reported |
| **User statistics** | Total users, new users, suspended/banned users |
| **Review statistics** | Average rating, total reviews, flagged reviews |
| **Report statistics** | Total reports, resolved rate, common violation types |
| **Activity logs** | View all moderation actions taken (audit trail) |
| **Export reports** | Export moderation data for reporting or analysis |

---

## 🔍 5. SEARCH & FILTER CAPABILITIES

| Feature | Description |
|---------|-------------|
| **Search listings** | Search by title, user, category, status, date, or keyword |
| **Search users** | Search by name, email, ID, or department |
| **Search reports** | Search by ID, type, status, reporter, or date |
| **Advanced filtering** | Combine multiple filters to narrow down results |
| **Sorting** | Sort by date, status, severity, etc. |

---

## ⚙️ 6. COMMUNITY MANAGEMENT

| Feature | Description |
|---------|-------------|
| **Manage categories** | Add, edit, or remove listing categories |
| **Manage hotspots** | Add, edit, or remove safe meeting spots |
| **Create/send community messages** | Send broadcast messages to all users or specific user |

---

## 🔧 7. MODERATOR TOOLS

| Feature | Description |
|---------|-------------|
| **Moderation queue** | Centralized queue of items needing review (pending listings, reports, flagged content) |
| **Bulk actions** | Ability to approve, reject, or delete multiple items at once |
| **Predefined responses** | Quick responses for common moderation actions |
| **Templates** | Pre-written templates for warning, suspension, or ban messages |
| **Notes** | Add private notes to listings, users, or reports for other moderators |
| **Collaboration** | Assign tasks to other moderators or leave comments |


## 🎯 PRIORITY IMPLEMENTATION ORDER

### Phase 1 – Essential (MVP)
1. View all listings (with status filtering)
2. Approve/reject pending listings
3. Edit/update listings (correct info)
4. Delete/hide inappropriate listings
5. View user profiles and basic history
6. Issue warnings to users
7. Suspension/ban users
8. View and resolve reports
9. Moderation activity log (audit trail)
10. Basic search and filtering

### Phase 2 – Enhanced Moderation
1. Review moderation (delete/edit reviews)
2. Content flagging system
3. Escalation to admins
4. Bulk actions (approve, delete)
5. Predefined responses and templates
6. Private notes on listings/users/reports
7. Advanced filtering and sorting
8. Moderation dashboard with metrics

### Phase 3 – Community Management
2. Manage categories and hotspots

### Phase 4 – Advanced Features
1. Advanced analytics and reports 
---

## 🛠️ Backend Endpoints Required

### Listing Moderation
- `GET /api/moderator/listings/` – List all listings (with filters)
- `PATCH /api/moderator/listings/{id}/approve/` – Approve listing
- `PATCH /api/moderator/listings/{id}/reject/` – Reject listing (with reason)
- `PATCH /api/moderator/listings/{id}/hide/` – Hide listing
- `PATCH /api/moderator/listings/{id}/flag/` – Flag listing
- `GET /api/moderator/listings/{id}/history/` – View listing history

### User Management
- `GET /api/moderator/users/` – List all users
- `GET /api/moderator/users/{id}/` – View user details
- `POST /api/moderator/users/{id}/warning/` – Issue warning
- `POST /api/moderator/users/{id}/suspend/` – Suspend user
- `POST /api/moderator/users/{id}/ban/` – Ban user
- `POST /api/moderator/users/{id}/reinstate/` – Reinstate user
- `GET /api/moderator/users/{id}/history/` – View user moderation history

### Report Management
- `GET /api/moderator/reports/` – List all reports
- `GET /api/moderator/reports/{id}/` – View report details
- `PATCH /api/moderator/reports/{id}/resolve/` – Resolve report
- `PATCH /api/moderator/reports/{id}/escalate/` – Escalate to admin

### Review Moderation
- `GET /api/moderator/reviews/` – List all reviews
- `DELETE /api/moderator/reviews/{id}/` – Delete review
- `PATCH /api/moderator/reviews/{id}/flag/` – Flag review

### Analytics
- `GET /api/moderator/dashboard/stats/` – Moderation statistics
- `GET /api/moderator/dashboard/recent/` – Recent activity
- `GET /api/moderator/audit-log/` – View moderation audit trail

---




from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.campus.models import Listing, Review
from apps.users.models import User
from apps.moderator.models import ModeratorAction, FlaggedContent, UserModeration
from apps.users.models import ContactReport  # assuming ContactReport is in users app
from utils.permissions import ConstantPermission
from utils.enums import GroupNames, ReportStatusEnum, ContentTypeEnum
from utils.pagination import CustomPagination


class ModeratorDashboardStatsView(APIView):
    """
    Get aggregated statistics for the moderator dashboard.
    """
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.MODERATOR.value)]

    def get(self, request):
        now = timezone.now()
        today = now.date()
        start_of_today = timezone.make_aware(
            datetime.combine(today, datetime.min.time())
        )

        # ─── Listing stats ──────────────────────────────────────
        listing_stats = {
            'total': Listing.objects.filter(is_deleted=False).count(),
            'active': Listing.objects.filter(is_deleted=False, status='active').count(),
            'pending': Listing.objects.filter(is_deleted=False, status='pending').count(),
            'expired': Listing.objects.filter(is_deleted=False, status='expired').count(),
            'sold': Listing.objects.filter(is_deleted=False, status='sold').count(),
            'flagged': FlaggedContent.objects.filter(
                content_type=ContentTypeEnum.LISTING.value,
                is_resolved=False,
                is_deleted=False
            ).count(),
        }

        # ─── Review stats ──────────────────────────────────────
        review_stats = {
            'total': Review.objects.filter(is_deleted=False).count(),
            'flagged': FlaggedContent.objects.filter(
                content_type=ContentTypeEnum.REVIEW.value,
                is_resolved=False,
                is_deleted=False
            ).count(),
        }

        # ─── Report stats ──────────────────────────────────────
        report_stats = {
            'total': ContactReport.objects.filter(is_deleted=False).count(),
            'pending': ContactReport.objects.filter(
                status=ReportStatusEnum.PENDING.value,
                is_deleted=False
            ).count(),
            'in_review': ContactReport.objects.filter(
                status=ReportStatusEnum.IN_REVIEW.value,
                is_deleted=False
            ).count(),
            'resolved': ContactReport.objects.filter(
                status=ReportStatusEnum.RESOLVED.value,
                is_deleted=False
            ).count(),
            'escalated': ContactReport.objects.filter(
                status=ReportStatusEnum.ESCALATED.value,
                is_deleted=False
            ).count(),
            # resolved rate
            'resolved_rate': 0,
        }
        if report_stats['total'] > 0:
            report_stats['resolved_rate'] = round(
                (report_stats['resolved'] / report_stats['total']) * 100, 1
            )

        # ─── User stats ────────────────────────────────────────
        user_stats = {
            'total': User.objects.filter(is_deleted=False).count(),
            'new_today': User.objects.filter(
                is_deleted=False,
                created_at__gte=start_of_today
            ).count(),
            'suspended': UserModeration.objects.filter(
                is_suspended=True
            ).count(),
            'banned': UserModeration.objects.filter(
                is_banned=True
            ).count(),
        }

        # ─── Recent activity (summary) ────────────────────────
        recent_actions = ModeratorAction.objects.filter(
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

        return Response({
            'is_success': True,
            'message': 'Moderation dashboard stats retrieved successfully',
            'data': data,
        })


class ModeratorRecentActivityView(APIView):
    """
    Get paginated recent moderation actions with detailed content info.
    """
    permission_classes = [IsAuthenticated, ConstantPermission(GroupNames.MODERATOR.value)]

    def get(self, request):
        paginator = CustomPagination()
        page = request.GET.get('page', 1)
        per_page = request.GET.get('per_page', 20)

        queryset = ModeratorAction.objects.filter(
            is_deleted=False
        ).select_related('moderator').order_by('-created_at')

        paginated = paginator.paginate_queryset(queryset, request, page, per_page)

        results = []
        for action in paginated:
            # Fetch related content title/name
            content_display = self._get_content_display(action.content_type, action.content_id)
            results.append({
                'id': action.id,
                'moderator': action.moderator.get_full_name() or action.moderator.email,
                'action': action.get_action_type_display(),
                'content_type': action.get_content_type_display(),
                'content_id': action.content_id,
                'content_display': content_display,
                'reason': action.reason,
                'metadata': action.metadata,
                'ip_address': action.ip_address,
                'created_at': action.created_at.isoformat(),
            })

        return Response({
            'is_success': True,
            'message': 'Recent activity retrieved successfully',
            'data': {
                'items': results,
                'page': paginator.page,
                'per_page': paginator.per_page,
                'total_pages': paginator.total_pages,
                'total_items': paginator.total_items,
            }
        })

    def _get_content_display(self, content_type, content_id):
        """
        Helper to fetch a human-readable representation of the content.
        """
        try:
            if content_type == ContentTypeEnum.LISTING.value:
                listing = Listing.objects.only('title').get(id=content_id, is_deleted=False)
                return listing.title
            elif content_type == ContentTypeEnum.USER.value:
                user = User.objects.only('first_name', 'last_name', 'email').get(id=content_id, is_deleted=False)
                return user.get_full_name() or user.email
            elif content_type == ContentTypeEnum.REVIEW.value:
                review = Review.objects.select_related('from_user', 'to_user').get(id=content_id, is_deleted=False)
                return f"Review by {review.from_user.email} → {review.to_user.email}"
            elif content_type == ContentTypeEnum.REPORT.value:
                report = ContactReport.objects.get(id=content_id, is_deleted=False)
                return f"Report #{report.id} - {report.get_issue_type_display()}"
        except Exception:
            return f"ID {content_id} (deleted or not found)"
        return f"ID {content_id}"





# | Feature | Description |
# |---------|-------------|
# | **Listing statistics** | Total listings, active, pending, flagged, reported |
# | **User statistics** | Total users, new users, suspended/banned users |
# | **Review statistics** | Average rating, total reviews, flagged reviews |
# | **Report statistics** | Total reports, resolved rate, common violation types |
# | **Activity logs** | View all moderation actions taken (audit trail) |
