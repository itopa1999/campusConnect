from apps.moderator.BBL.Queries.get_dashboard import DashboardQuery
import pytest
import datetime
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone
from django.db.models import Count, Q
from unittest.mock import Mock
from apps.campus.models import Listing, Review, Category
from apps.moderator.models import FlaggedContent, ModeratorAction, UserModeration
from apps.users.models import ContactReport
from utils.enums import (
    ContentTypeEnum,
    ListingStatusTypeEnum,
    ReportStatusEnum,
    ModeratorActionTypeEnum,
    CacheKeysEnum,
)
from utils.cache_helper import GlobalCache

User = get_user_model()


# ---------- Fixtures ----------
@pytest.fixture
def moderator(db):
    return User.objects.create_user(
        email='moderator@example.com',
        password='testpass123',
        first_name='Mod',
        last_name='erator',
        is_staff=True,
        is_deleted=False,
    )


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def request_with_user(request_factory, moderator):
    req = request_factory.get('/')
    req.user = moderator
    req.META = {'REMOTE_ADDR': '127.0.0.1'}
    return req


@pytest.fixture
def category(db):
    return Category.objects.create(name='Electronics', slug='electronics')


@pytest.fixture
def listing_for_review(db, moderator, category):
    """A single listing used for review fixtures."""
    return Listing.objects.create(
        title='Review Listing',
        description='For reviews',
        price=10,
        user=moderator,
        category=category,
        status=ListingStatusTypeEnum.ACTIVE.value,
        expires_at=timezone.now() + datetime.timedelta(days=10),
        is_deleted=False,
    )


@pytest.fixture
def listings(db, moderator, category):
    now = timezone.now()
    # Active listings (2)
    active1 = Listing.objects.create(
        title='Active 1',
        description='desc',
        price=10,
        user=moderator,
        category=category,
        status=ListingStatusTypeEnum.ACTIVE.value,
        expires_at=now + datetime.timedelta(days=10),
        is_deleted=False,
    )
    active2 = Listing.objects.create(
        title='Active 2',
        description='desc',
        price=20,
        user=moderator,
        category=category,
        status=ListingStatusTypeEnum.ACTIVE.value,
        expires_at=now + datetime.timedelta(days=20),
        is_deleted=False,
    )
    # Pending (1)
    pending = Listing.objects.create(
        title='Pending',
        description='desc',
        price=15,
        user=moderator,
        category=category,
        status=ListingStatusTypeEnum.PENDING.value,
        expires_at=now + datetime.timedelta(days=30),
        is_deleted=False,
    )
    # Expired (1)
    expired = Listing.objects.create(
        title='Expired',
        description='desc',
        price=5,
        user=moderator,
        category=category,
        status=ListingStatusTypeEnum.EXPIRED.value,
        expires_at=now - datetime.timedelta(days=1),
        is_deleted=False,
    )
    # Sold (1)
    sold = Listing.objects.create(
        title='Sold',
        description='desc',
        price=25,
        user=moderator,
        category=category,
        status=ListingStatusTypeEnum.SOLD.value,
        expires_at=now + datetime.timedelta(days=5),
        is_deleted=False,
    )
    # Soft-deleted listing (should be counted in deleted_listing_stats, not in main)
    deleted = Listing.objects.create(
        title='Deleted',
        description='desc',
        price=30,
        user=moderator,
        category=category,
        status=ListingStatusTypeEnum.ACTIVE.value,
        expires_at=now + datetime.timedelta(days=15),
        is_deleted=True,
    )
    return {
        'active': [active1, active2],
        'pending': pending,
        'expired': expired,
        'sold': sold,
        'deleted': deleted,
    }


@pytest.fixture
def flagged_listing(db, listings):
    # Flag one active listing
    listing = listings['active'][0]
    return FlaggedContent.objects.create(
        content_type=ContentTypeEnum.LISTING.value,
        content_id=listing.id,
        flagged_by=listing.user,
        reason='spam',
        is_resolved=False,
        is_deleted=False,
    )


@pytest.fixture
def reviews(db, moderator, listing_for_review):
    # Create 3 reviews with different users to avoid unique constraint
    # We'll create two additional users
    user2 = User.objects.create_user(email='user2@example.com', password='pass', is_deleted=False)
    user3 = User.objects.create_user(email='user3@example.com', password='pass', is_deleted=False)

    review1 = Review.objects.create(
        listing=listing_for_review,
        from_user=moderator,
        to_user=user2,
        rating=4,
        comment='Good',
        is_deleted=False,
    )
    review2 = Review.objects.create(
        listing=listing_for_review,
        from_user=user2,
        to_user=moderator,
        rating=5,
        comment='Great',
        is_deleted=False,
    )
    review3 = Review.objects.create(
        listing=listing_for_review,
        from_user=user3,
        to_user=moderator,
        rating=3,
        comment='Ok',
        is_deleted=False,
    )
    # Soft-deleted review (excluded from stats)
    Review.objects.create(
        listing=listing_for_review,
        from_user=moderator,
        to_user=user3,
        rating=1,
        comment='Bad',
        is_deleted=True,
    )
    return [review1, review2, review3]


@pytest.fixture
def flagged_review(db, reviews):
    review = reviews[0]
    return FlaggedContent.objects.create(
        content_type=ContentTypeEnum.REVIEW.value,
        content_id=review.id,
        flagged_by=review.from_user,
        reason='offensive',
        is_resolved=False,
        is_deleted=False,
    )


@pytest.fixture
def reports(db, moderator):
    now = timezone.now()
    # Ensure field names match the ContactReport model.
    # Common fields: reporter_email, issue_type, details (or description), status, etc.
    # I'll assume 'details' is used; adjust if needed.
    report1 = ContactReport.objects.create(
        reporter_email='user1@example.com',
        issue_type='spam',
        message='Spam report',
        status=ReportStatusEnum.PENDING.value,
        is_deleted=False,
    )
    report2 = ContactReport.objects.create(
        reporter_email='user2@example.com',
        issue_type='harassment',
        message='Harassment',
        status=ReportStatusEnum.IN_REVIEW.value,
        is_deleted=False,
    )
    report3 = ContactReport.objects.create(
        reporter_email='user3@example.com',
        issue_type='other',
        message='Resolved',
        status=ReportStatusEnum.RESOLVED.value,
        is_deleted=False,
        resolved_by=moderator,
        resolved_at=now,
        resolution_notes='ok',
    )
    report4 = ContactReport.objects.create(
        reporter_email='user4@example.com',
        issue_type='fraud',
        message='Escalated',
        status=ReportStatusEnum.ESCALATED.value,
        is_deleted=False,
        escalated_to_admin=True,
        escalated_at=now,
        escalated_note='escalated',
    )
    # Soft-deleted report (excluded)
    ContactReport.objects.create(
        reporter_email='deleted@example.com',
        issue_type='spam',
        message='Deleted report',
        status=ReportStatusEnum.PENDING.value,
        is_deleted=True,
    )
    return [report1, report2, report3, report4]


@pytest.fixture
def users_and_moderation(db):
    # Create normal users
    user1 = User.objects.create_user(email='u1@example.com', password='pass', is_deleted=False)
    user2 = User.objects.create_user(email='u2@example.com', password='pass', is_deleted=False)
    # One user created today
    today = timezone.now().date()
    start_of_today = timezone.make_aware(
        datetime.datetime.combine(today, datetime.datetime.min.time())
    )
    user3 = User.objects.create_user(
        email='u3@example.com',
        password='pass',
        is_deleted=False,
        created_at=start_of_today + datetime.timedelta(hours=1),
    )
    # Suspended user
    suspended_user = User.objects.create_user(email='suspended@example.com', password='pass', is_deleted=False)
    UserModeration.objects.create(user=suspended_user, is_suspended=True)
    # Banned user
    banned_user = User.objects.create_user(email='banned@example.com', password='pass', is_deleted=False)
    UserModeration.objects.create(user=banned_user, is_banned=True)
    # Soft-deleted user (excluded from total)
    User.objects.create_user(email='deleted@example.com', password='pass', is_deleted=True)
    return {'users': [user1, user2, user3]}


@pytest.fixture
def moderator_actions(db, moderator):
    # Create 12 actions for recent activity test
    actions = []
    for i in range(12):
        action = ModeratorAction.objects.create(
            moderator=moderator,
            action_type=ModeratorActionTypeEnum.APPROVE.value,
            content_type=ContentTypeEnum.LISTING.value,
            content_id=i,
            reason=f'Reason {i}',
            is_deleted=False,
        )
        actions.append(action)
    return actions


# ---------- Tests ----------
@pytest.mark.django_db
class TestDashboardQuery:

    def test_get_dashboard_stats_cache_miss(
        self,
        request_with_user,
        moderator,
        listings,
        flagged_listing,
        reviews,
        flagged_review,
        reports,
        users_and_moderation,
        moderator_actions,
        mocker,
    ):
        """Test cache miss: data is built from scratch and cached."""
        cache_mock = mocker.patch.object(GlobalCache, 'get_or_set')
        cache_mock.side_effect = lambda key, callback, timeout, lock_timeout, max_wait: callback()

        result = DashboardQuery.get_dashboard_stats(request_with_user)
        assert result.status_code == 200
        data = result.data

        cache_mock.assert_called_once()
        call_kwargs = cache_mock.call_args[1]
        assert call_kwargs['timeout'] == 3600
        assert call_kwargs['lock_timeout'] == 30
        assert call_kwargs['max_wait'] == 5.0

        # Listing stats
        listing_stats = data['listing_stats']
        assert listing_stats['listing_stats']['total'] == 6
        assert listing_stats['listing_stats']['active'] == 3
        assert listing_stats['listing_stats']['pending'] == 1
        assert listing_stats['listing_stats']['expired'] == 1
        assert listing_stats['listing_stats']['sold'] == 1
        assert listing_stats['listing_stats']['flagged'] == 1

        assert listing_stats['deleted_listing_stats']['total'] == 0
        assert listing_stats['deleted_listing_stats']['active'] == 0
        assert listing_stats['deleted_listing_stats']['pending'] == 0
        assert listing_stats['deleted_listing_stats']['expired'] == 0
        assert listing_stats['deleted_listing_stats']['sold'] == 0
        assert listing_stats['deleted_listing_stats']['flagged'] == 0

        # Review stats
        review_stats = data['review_stats']
        assert review_stats['total'] == 3
        assert review_stats['average_rating'] == 4.0
        assert review_stats['flagged'] == 1

        # Report stats
        report_stats = data['report_stats']
        assert report_stats['total'] == 4
        assert report_stats['pending'] == 1
        assert report_stats['in_review'] == 1
        assert report_stats['resolved'] == 1
        assert report_stats['escalated'] == 1
        assert report_stats['resolved_rate'] == 25.0

        # User stats
        user_stats = data['user_stats']
        assert user_stats['total'] == 8
        assert user_stats['new_today'] == 8
        assert user_stats['suspended'] == 1
        assert user_stats['banned'] == 1

        # Recent activity
        recent_activity = data['recent_activity']
        assert len(recent_activity) == 10
        for act in recent_activity:
            assert 'id' in act
            assert 'moderator' in act
            assert 'action' in act
            assert 'content_type' in act
            assert 'content_id' in act
            assert 'created_at' in act
            assert 'reason' in act

        assert 'last_updated' in data
        assert data['last_updated'] is not None

    def test_get_dashboard_stats_cache_hit(self, request_with_user, mocker):
        cached_data = {'test': 'data', 'last_updated': timezone.now().isoformat()}
        cache_mock = mocker.patch.object(GlobalCache, 'get_or_set')
        cache_mock.return_value = cached_data

        result = DashboardQuery.get_dashboard_stats(request_with_user)
        assert result.status_code == 200
        assert result.data == cached_data
        cache_mock.assert_called_once()

    def test_get_dashboard_stats_no_data(self, request_with_user, mocker):
        # Clear all data except the request user (moderator)
        # We already have the moderator user in the DB, and that is the only user.
        # Ensure no other data.
        cache_mock = mocker.patch.object(GlobalCache, 'get_or_set')
        cache_mock.side_effect = lambda key, callback, timeout, lock_timeout, max_wait: callback()

        result = DashboardQuery.get_dashboard_stats(request_with_user)
        assert result.status_code == 200
        data = result.data

        listing_stats = data['listing_stats']
        assert listing_stats['listing_stats']['total'] == 0
        assert listing_stats['listing_stats']['active'] == 0
        assert listing_stats['listing_stats']['pending'] == 0
        assert listing_stats['listing_stats']['expired'] == 0
        assert listing_stats['listing_stats']['sold'] == 0
        assert listing_stats['listing_stats']['flagged'] == 0
        assert listing_stats['deleted_listing_stats']['total'] == 0
        assert listing_stats['deleted_listing_stats']['flagged'] == 0

        review_stats = data['review_stats']
        assert review_stats['total'] == 0
        assert review_stats['average_rating'] == 0.0
        assert review_stats['flagged'] == 0

        report_stats = data['report_stats']
        assert report_stats['total'] == 0
        assert report_stats['pending'] == 0
        assert report_stats['in_review'] == 0
        assert report_stats['resolved'] == 0
        assert report_stats['escalated'] == 0
        assert report_stats['resolved_rate'] == 0

        user_stats = data['user_stats']
        # Only the moderator user exists
        assert user_stats['total'] == 1
        assert user_stats['new_today'] == 1
        assert user_stats['suspended'] == 0
        assert user_stats['banned'] == 0

        assert data['recent_activity'] == []

    def test_get_dashboard_stats_flagged_counts_separate(
        self,
        request_with_user,
        listings,
        flagged_listing,
        reviews,
        flagged_review,
        mocker,
    ):
        cache_mock = mocker.patch.object(GlobalCache, 'get_or_set')
        cache_mock.side_effect = lambda key, callback, timeout, lock_timeout, max_wait: callback()

        result = DashboardQuery.get_dashboard_stats(request_with_user)
        data = result.data

        assert data['listing_stats']['listing_stats']['flagged'] == 1
        assert data['listing_stats']['deleted_listing_stats']['flagged'] == 0
        assert data['review_stats']['flagged'] == 1

    def test_get_dashboard_stats_recent_activity_limit(
        self,
        request_with_user,
        moderator_actions,
        mocker,
    ):
        cache_mock = mocker.patch.object(GlobalCache, 'get_or_set')
        cache_mock.side_effect = lambda key, callback, timeout, lock_timeout, max_wait: callback()

        result = DashboardQuery.get_dashboard_stats(request_with_user)
        data = result.data
        recent = data['recent_activity']
        assert len(recent) == 10
        created_at_list = [act['created_at'] for act in recent]
        sorted_dates = sorted(created_at_list, reverse=True)
        assert created_at_list == sorted_dates

    def test_get_dashboard_stats_soft_deleted_reports(
        self,
        request_with_user,
        reports,
        mocker,
    ):
        cache_mock = mocker.patch.object(GlobalCache, 'get_or_set')
        cache_mock.side_effect = lambda key, callback, timeout, lock_timeout, max_wait: callback()

        result = DashboardQuery.get_dashboard_stats(request_with_user)
        data = result.data
        report_stats = data['report_stats']
        assert report_stats['total'] == 4
        assert report_stats['pending'] == 1
        assert report_stats['resolved_rate'] == 25.0

    def test_get_dashboard_stats_deleted_listings_count(
        self,
        request_with_user,
        listings,
        mocker,
    ):
        cache_mock = mocker.patch.object(GlobalCache, 'get_or_set')
        cache_mock.side_effect = lambda key, callback, timeout, lock_timeout, max_wait: callback()

        result = DashboardQuery.get_dashboard_stats(request_with_user)
        data = result.data
        assert data['listing_stats']['listing_stats']['total'] == 5
        assert data['listing_stats']['deleted_listing_stats']['total'] == 0
        assert data['listing_stats']['deleted_listing_stats']['active'] == 0
        assert data['listing_stats']['deleted_listing_stats']['expired'] == 0

    def test_get_dashboard_stats_recent_activity_includes_full_name(
        self,
        request_with_user,
        moderator,
        mocker,
    ):
        ModeratorAction.objects.create(
            moderator=moderator,
            action_type=ModeratorActionTypeEnum.APPROVE.value,
            content_type=ContentTypeEnum.LISTING.value,
            content_id=1,
            reason='test',
            is_deleted=False,
        )
        cache_mock = mocker.patch.object(GlobalCache, 'get_or_set')
        cache_mock.side_effect = lambda key, callback, timeout, lock_timeout, max_wait: callback()

        result = DashboardQuery.get_dashboard_stats(request_with_user)
        data = result.data
        recent = data['recent_activity']
        assert len(recent) == 1
        assert recent[0]['moderator'] == 'Mod Erator'

    def test_get_dashboard_stats_average_rating_rounded(
        self,
        request_with_user,
        reviews,
        listing_for_review,
        mocker,
    ):
        cache_mock = mocker.patch.object(GlobalCache, 'get_or_set')
        cache_mock.side_effect = lambda key, callback, timeout, lock_timeout, max_wait: callback()

        result = DashboardQuery.get_dashboard_stats(request_with_user)
        data = result.data
        assert data['review_stats']['average_rating'] == 4.0

        # Add another review
        # Use a different user to avoid unique constraint
        new_user = User.objects.create_user(email='new@example.com', password='pass', is_deleted=False)
        Review.objects.create(
            listing=listing_for_review,
            from_user=new_user,
            to_user=request_with_user.user,
            rating=2,
            comment='another',
            is_deleted=False,
        )
        # Force cache miss
        cache_mock.side_effect = lambda key, callback, timeout, lock_timeout, max_wait: callback()
        result2 = DashboardQuery.get_dashboard_stats(request_with_user)
        data2 = result2.data
        assert data2['review_stats']['average_rating'] == 3.5