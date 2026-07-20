from apps.moderator.BBL.Commands.review import ReviewCommand
import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.db import IntegrityError
from django.utils import timezone
from apps.campus.models import Review, Listing, Category
from apps.moderator.models import FlaggedContent, ModeratorAction
from utils.enums import ContentTypeEnum, ModeratorActionTypeEnum, ListingStatusType

User = get_user_model()


# ---------- Fixtures ----------
@pytest.fixture
def moderator(db):
    return User.objects.create_user(
        email='moderator@example.com',
        password='testpass123',
        first_name='Mod',
        last_name='erator',
        is_staff=True
    )


@pytest.fixture
def another_user(db):
    return User.objects.create_user(
        email='another_user@example.com',
        password='testpass123',
        first_name='another_user',
        last_name='erator',
        is_staff=True
    )


@pytest.fixture
def category(db):
    return Category.objects.create(
        name='Electronics',
        slug='electronics',
        description='All things electronic'
    )


@pytest.fixture
def listing(db, moderator, category):
    return Listing.objects.create(
        title='Test Listing',
        description='Test desc',
        price=10.00,
        user=moderator,
        category=category,
        status=ListingStatusType.ACTIVE.value,
        is_deleted=False
    )


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def moderator_request(request_factory, moderator):
    req = request_factory.get('/')
    req.user = moderator
    req.META = {'REMOTE_ADDR': '127.0.0.1'}
    return req


@pytest.fixture
def review(db, moderator, another_user, listing):
    # Create a review (not deleted, not flagged)
    return Review.objects.create(
        listing=listing,          # use the listing fixture
        from_user=moderator,
        to_user=another_user,
        rating=5,
        comment='Great product!',
        is_deleted=False
    )


@pytest.fixture
def deleted_review(db, moderator, another_user, listing):
    return Review.objects.create(
        listing=listing,
        from_user=moderator,
        to_user=another_user,
        rating=3,
        comment='Average',
        is_deleted=True
    )


@pytest.fixture
def flagged_review(db, moderator, review):
    # Create an unresolved flag for the review
    flag = FlaggedContent.objects.create(
        content_type=ContentTypeEnum.REVIEW.value,
        content_id=review.id,
        flagged_by=moderator,
        reason='Inappropriate comment',
        is_resolved=False,
        is_deleted=False
    )
    return review, flag


@pytest.fixture
def resolved_flag_review(db, moderator, review):
    # Create a resolved flag (will not be picked up as unresolved)
    FlaggedContent.objects.create(
        content_type=ContentTypeEnum.REVIEW.value,
        content_id=review.id,
        flagged_by=moderator,
        reason='Old issue',
        is_resolved=True,
        resolved_by=moderator,
        resolved_at=timezone.now(),
        resolution_note='Fixed',
        is_deleted=False
    )
    return review


# ---------- Test class ----------
@pytest.mark.django_db
class TestReviewCommand:

    # ---------- toggle_delete_review ----------
    def test_toggle_delete_review_soft_delete(self, moderator_request, review):
        data = {'reason': 'Inappropriate content'}
        result = ReviewCommand.toggle_delete_review(moderator_request, review.id, data)
        assert result.status_code == 200
        assert result.message == "Review deleted successfully"
        assert result.data['is_deleted'] is True

        review.refresh_from_db()
        assert review.is_deleted is True

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=review.id,
            action_type=ModeratorActionTypeEnum.DELETE.value
        ).first()
        assert action is not None
        assert action.reason == 'Inappropriate content'
        assert action.metadata['old_is_deleted'] is False
        assert action.metadata['new_is_deleted'] is True

    def test_toggle_delete_review_restore(self, moderator_request, deleted_review):
        data = {'reason': 'Restore by mistake'}
        result = ReviewCommand.toggle_delete_review(moderator_request, deleted_review.id, data)
        assert result.status_code == 200
        assert result.message == "Review restored successfully"
        assert result.data['is_deleted'] is False

        deleted_review.refresh_from_db()
        assert deleted_review.is_deleted is False

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=deleted_review.id,
            action_type=ModeratorActionTypeEnum.REINSTATE.value
        ).first()
        assert action is not None
        assert action.reason == 'Restore by mistake'

    def test_toggle_delete_review_missing_reason(self, moderator_request, review):
        data = {}
        result = ReviewCommand.toggle_delete_review(moderator_request, review.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required for toggling delete status"
        review.refresh_from_db()
        assert review.is_deleted is False

    def test_toggle_delete_review_not_found(self, moderator_request):
        data = {'reason': 'test'}
        result = ReviewCommand.toggle_delete_review(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "Review not found"

    def test_toggle_delete_review_already_deleted_toggle_again(self, moderator_request, deleted_review):
        # Toggling again on a deleted review should restore it (since we toggle)
        data = {'reason': 'Second toggle'}
        result = ReviewCommand.toggle_delete_review(moderator_request, deleted_review.id, data)
        assert result.status_code == 200
        assert result.message == "Review restored successfully"
        deleted_review.refresh_from_db()
        assert deleted_review.is_deleted is False

        # Now delete again
        result2 = ReviewCommand.toggle_delete_review(moderator_request, deleted_review.id, data)
        assert result2.status_code == 200
        assert result2.message == "Review deleted successfully"
        deleted_review.refresh_from_db()
        assert deleted_review.is_deleted is True

    # ---------- toggle_flag_review ----------
    def test_toggle_flag_review_flag_creation(self, moderator_request, review):
        data = {'reason': 'Spam review'}
        result = ReviewCommand.toggle_flag_review(moderator_request, review.id, data)
        assert result.status_code == 200
        assert result.message == "Review flagged successfully"
        assert result.data['is_flagged'] is True

        flag = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=review.id,
            is_resolved=False,
            is_deleted=False
        ).first()
        assert flag is not None
        assert flag.flagged_by == moderator_request.user
        assert flag.reason == 'Spam review'

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=review.id,
            action_type=ModeratorActionTypeEnum.FLAG.value
        ).first()
        assert action is not None
        assert action.reason == 'Spam review'
        assert action.metadata['resolved'] is False

    def test_toggle_flag_review_flag_resolution(self, moderator_request, flagged_review):
        review, flag = flagged_review
        data = {'reason': 'Issue resolved'}
        result = ReviewCommand.toggle_flag_review(moderator_request, review.id, data)
        assert result.status_code == 200
        assert result.message == "Flag resolved successfully"
        assert result.data['is_flagged'] is False

        flag.refresh_from_db()
        assert flag.is_resolved is True
        assert flag.resolved_by == moderator_request.user
        assert flag.resolved_at is not None
        assert flag.resolution_note == 'Issue resolved'

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=review.id,
            action_type=ModeratorActionTypeEnum.UNFLAG.value
        ).first()
        assert action is not None
        assert action.reason == 'Issue resolved'
        assert action.metadata['resolved'] is True

    def test_toggle_flag_review_missing_reason(self, moderator_request, review):
        data = {}
        result = ReviewCommand.toggle_flag_review(moderator_request, review.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required for flagging/unflagging a review"
        # No flag should be created
        assert not FlaggedContent.objects.filter(content_id=review.id).exists()

    def test_toggle_flag_review_with_existing_resolved_flag(self, moderator_request, resolved_flag_review):
        # There is a resolved flag, but no unresolved one → should create a new flag
        data = {'reason': 'New issue'}
        result = ReviewCommand.toggle_flag_review(moderator_request, resolved_flag_review.id, data)
        assert result.status_code == 200
        assert result.message == "Review flagged successfully"

        # New unresolved flag should exist
        new_flag = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=resolved_flag_review.id,
            is_resolved=False,
            is_deleted=False
        ).first()
        assert new_flag is not None
        assert new_flag.reason == 'New issue'

        # The old resolved flag should remain untouched
        old_flag = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=resolved_flag_review.id,
            is_resolved=True
        ).first()
        assert old_flag is not None
        assert old_flag.resolution_note == 'Fixed'

    def test_toggle_flag_review_review_does_not_exist(self, moderator_request):
        """
        BUG: The command does NOT check if the review exists before flagging.
        This test reveals that flagging a non-existent review succeeds,
        creating an orphaned flag.
        """
        data = {'reason': 'Flag non-existent'}
        result = ReviewCommand.toggle_flag_review(moderator_request, 999, data)
        # Currently, it will create a flag because no unresolved flag exists
        assert result.status_code == 200
        assert result.message == "Review flagged successfully"
        flag = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.REVIEW.value,
            content_id=999,
            is_resolved=False,
            is_deleted=False
        ).first()
        assert flag is not None
        # This is a bug: we should validate that the review exists before flagging.
        # After fixing the code, this test should expect a 404.

    # ---------- Atomicity Tests ----------
    def test_toggle_delete_review_atomicity(self, moderator_request, review, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test'}
            with pytest.raises(IntegrityError):
                ReviewCommand.toggle_delete_review(moderator_request, review.id, data)
            review.refresh_from_db()
            assert review.is_deleted is False

    def test_toggle_flag_review_atomicity_flag_creation(self, moderator_request, review, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test'}
            with pytest.raises(IntegrityError):
                ReviewCommand.toggle_flag_review(moderator_request, review.id, data)
            # No flag should be created
            flag = FlaggedContent.objects.filter(
                content_type=ContentTypeEnum.REVIEW.value,
                content_id=review.id
            ).first()
            assert flag is None

    def test_toggle_flag_review_atomicity_flag_resolution(self, moderator_request, flagged_review, mocker):
        review, flag = flagged_review
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test'}
            with pytest.raises(IntegrityError):
                ReviewCommand.toggle_flag_review(moderator_request, review.id, data)
            flag.refresh_from_db()
            assert flag.is_resolved is False
            assert flag.resolved_by is None