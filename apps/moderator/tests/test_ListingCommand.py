from apps.moderator.BBL.Commands.listing import ListingCommand
import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.db import IntegrityError
from django.utils import timezone
from apps.campus.models import Listing, Category
from apps.moderator.models import FlaggedContent, ModeratorAction
from utils.enums import ListingStatusTypeEnum, ContentTypeEnum, ModeratorActionTypeEnum

User = get_user_model()


# ---------- Fixtures ----------
@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='moderator@example.com',
        password='testpass123',
        first_name='Mod',
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
def request_factory():
    return RequestFactory()


@pytest.fixture
def moderator_request(request_factory, user):
    req = request_factory.get('/')
    req.user = user
    req.META = {'REMOTE_ADDR': '127.0.0.1'}
    return req


@pytest.fixture
def pending_listing(db, user, category):
    return Listing.objects.create(
        title='Test Listing',
        description='Test desc',
        price=10.00,
        user=user,
        category=category,
        status=ListingStatusTypeEnum.PENDING.value,
        is_deleted=False,
    )


@pytest.fixture
def active_listing(db, user, category):
    return Listing.objects.create(
        title='Active Listing',
        description='Active desc',
        price=20.00,
        user=user,
        category=category,
        status=ListingStatusTypeEnum.ACTIVE.value,
        is_deleted=False,
    )


@pytest.fixture
def deleted_listing(db, user, category):
    return Listing.objects.create(
        title='Deleted Listing',
        description='Deleted desc',
        price=0,
        user=user,
        category=category,
        status=ListingStatusTypeEnum.PENDING.value,
        is_deleted=True,
    )


@pytest.fixture
def hidden_listing(db, user, category):
    return Listing.objects.create(
        title='Hidden Listing',
        description='Hidden desc',
        price=5.00,
        user=user,
        category=category,
        status=ListingStatusTypeEnum.HIDDEN.value,
        is_deleted=False,
    )


@pytest.fixture
def flagged_listing(db, user, category, pending_listing):
    # Create a flag for pending_listing
    flag = FlaggedContent.objects.create(
        content_type=ContentTypeEnum.LISTING.value,
        content_id=pending_listing.id,
        flagged_by=user,
        reason='Inappropriate content',
        is_resolved=False,
    )
    return pending_listing, flag


# ---------- Test class ----------
@pytest.mark.django_db
class TestModeratorListingCommand:

    # ---------- approve_listing ----------
    def test_approve_listing_success(self, moderator_request, pending_listing):
        data = {'reason': 'Looks good'}
        result = ListingCommand.approve_listing(moderator_request, pending_listing.id, data)
        assert result.status_code == 200
        assert result.message == "Listing approved successfully"
        assert result.data['status'] == ListingStatusTypeEnum.ACTIVE.value

        pending_listing.refresh_from_db()
        assert pending_listing.status == ListingStatusTypeEnum.ACTIVE.value

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=pending_listing.id,
            action_type=ModeratorActionTypeEnum.APPROVE.value
        ).first()
        assert action is not None
        assert action.reason == 'Looks good'
        assert action.metadata['old_status'] == ListingStatusTypeEnum.PENDING.value
        assert action.metadata['new_status'] == ListingStatusTypeEnum.ACTIVE.value

    def test_approve_listing_missing_reason(self, moderator_request, pending_listing):
        data = {}
        result = ListingCommand.approve_listing(moderator_request, pending_listing.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required for approving a listing"
        pending_listing.refresh_from_db()
        assert pending_listing.status == ListingStatusTypeEnum.PENDING.value

    def test_approve_listing_not_found(self, moderator_request):
        data = {'reason': 'test'}
        result = ListingCommand.approve_listing(moderator_request, 999, data)
        assert result.status_code == 404
        assert "not found or not pending" in result.message

    def test_approve_listing_not_pending(self, moderator_request, active_listing):
        data = {'reason': 'test'}
        result = ListingCommand.approve_listing(moderator_request, active_listing.id, data)
        assert result.status_code == 404
        assert "not found or not pending" in result.message

    def test_approve_listing_already_deleted(self, moderator_request, deleted_listing):
        data = {'reason': 'test'}
        result = ListingCommand.approve_listing(moderator_request, deleted_listing.id, data)
        assert result.status_code == 404
        assert "not found or not pending" in result.message

    # ---------- reject_listing ----------
    def test_reject_listing_success(self, moderator_request, pending_listing):
        data = {'reason': 'Violates policy'}
        result = ListingCommand.reject_listing(moderator_request, pending_listing.id, data)
        assert result.status_code == 200
        assert result.message == "Listing rejected and deleted"
        pending_listing.refresh_from_db()
        assert pending_listing.is_deleted is True

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=pending_listing.id,
            action_type=ModeratorActionTypeEnum.REJECT.value
        ).first()
        assert action is not None
        assert action.reason == 'Violates policy'
        assert action.metadata['old_is_deleted'] is False
        assert action.metadata['new_is_deleted'] is True

    def test_reject_listing_missing_reason(self, moderator_request, pending_listing):
        data = {}
        result = ListingCommand.reject_listing(moderator_request, pending_listing.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required for rejecting a listing"
        pending_listing.refresh_from_db()
        assert pending_listing.is_deleted is False

    def test_reject_listing_not_found(self, moderator_request):
        data = {'reason': 'test'}
        result = ListingCommand.reject_listing(moderator_request, 999, data)
        assert result.status_code == 404
        assert "not found or not pending" in result.message

    def test_reject_listing_not_pending(self, moderator_request, active_listing):
        data = {'reason': 'test'}
        result = ListingCommand.reject_listing(moderator_request, active_listing.id, data)
        assert result.status_code == 404
        assert "not found or not pending" in result.message

    # ---------- toggle_delete_listing ----------
    def test_toggle_delete_listing_soft_delete(self, moderator_request, pending_listing):
        data = {'reason': 'Remove from marketplace'}
        result = ListingCommand.toggle_delete_listing(moderator_request, pending_listing.id, data)
        assert result.status_code == 200
        assert result.message == "Listing deleted successfully"
        assert result.data['is_deleted'] is True
        pending_listing.refresh_from_db()
        assert pending_listing.is_deleted is True

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=pending_listing.id,
            action_type=ModeratorActionTypeEnum.DELETE.value
        ).first()
        assert action is not None
        assert action.reason == 'Remove from marketplace'

    def test_toggle_delete_listing_restore(self, moderator_request, deleted_listing):
        data = {'reason': 'Restore by mistake'}
        result = ListingCommand.toggle_delete_listing(moderator_request, deleted_listing.id, data)
        assert result.status_code == 200
        assert result.message == "Listing restored successfully"
        assert result.data['is_deleted'] is False
        deleted_listing.refresh_from_db()
        assert deleted_listing.is_deleted is False

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=deleted_listing.id,
            action_type=ModeratorActionTypeEnum.REINSTATE.value
        ).first()
        assert action is not None

    def test_toggle_delete_listing_missing_reason(self, moderator_request, pending_listing):
        data = {}
        result = ListingCommand.toggle_delete_listing(moderator_request, pending_listing.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required for toggling delete status"
        pending_listing.refresh_from_db()
        assert pending_listing.is_deleted is False

    def test_toggle_delete_listing_not_found(self, moderator_request):
        data = {'reason': 'test'}
        result = ListingCommand.toggle_delete_listing(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "Listing not found"

    # ---------- toggle_hide_listing ----------
    def test_toggle_hide_listing_hide(self, moderator_request, active_listing):
        data = {'reason': 'Inappropriate content'}
        result = ListingCommand.toggle_hide_listing(moderator_request, active_listing.id, data)
        assert result.status_code == 200
        assert result.message == "Listing hidden"
        assert result.data['status'] == ListingStatusTypeEnum.HIDDEN.value
        active_listing.refresh_from_db()
        assert active_listing.status == ListingStatusTypeEnum.HIDDEN.value

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=active_listing.id,
            action_type=ModeratorActionTypeEnum.HIDE.value
        ).first()
        assert action is not None
        assert action.reason == 'Inappropriate content'
        assert action.metadata['old_status'] == ListingStatusTypeEnum.ACTIVE.value
        assert action.metadata['new_status'] == ListingStatusTypeEnum.HIDDEN.value

    def test_toggle_hide_listing_unhide(self, moderator_request, hidden_listing):
        data = {'reason': 'Content was valid'}
        result = ListingCommand.toggle_hide_listing(moderator_request, hidden_listing.id, data)
        assert result.status_code == 200
        assert result.message == "Listing unhidden and set to PENDING"
        assert result.data['status'] == ListingStatusTypeEnum.PENDING.value
        hidden_listing.refresh_from_db()
        assert hidden_listing.status == ListingStatusTypeEnum.PENDING.value

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=hidden_listing.id,
            action_type=ModeratorActionTypeEnum.UNHIDE.value
        ).first()
        assert action is not None

    def test_toggle_hide_listing_missing_reason(self, moderator_request, active_listing):
        data = {}
        result = ListingCommand.toggle_hide_listing(moderator_request, active_listing.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required for toggling hide status"
        active_listing.refresh_from_db()
        assert active_listing.status == ListingStatusTypeEnum.ACTIVE.value

    def test_toggle_hide_listing_not_found(self, moderator_request):
        data = {'reason': 'test'}
        result = ListingCommand.toggle_hide_listing(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "Listing not found or deleted"

    def test_toggle_hide_listing_deleted(self, moderator_request, deleted_listing):
        data = {'reason': 'test'}
        result = ListingCommand.toggle_hide_listing(moderator_request, deleted_listing.id, data)
        assert result.status_code == 404
        assert result.message == "Listing not found or deleted"

    # ---------- toggle_flag_listing ----------
    def test_toggle_flag_listing_flag_creation(self, moderator_request, pending_listing):
        data = {'resolution_note': 'Spam content'}
        result = ListingCommand.toggle_flag_listing(moderator_request, pending_listing.id, data)
        assert result.status_code == 200
        assert result.message == "Listing flagged successfully"
        assert result.data['is_flagged'] is True

        flag = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=pending_listing.id,
            is_resolved=False,
        ).first()
        assert flag is not None
        assert flag.flagged_by == moderator_request.user
        assert flag.reason == 'Spam content'

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=pending_listing.id,
            action_type=ModeratorActionTypeEnum.FLAG.value
        ).first()
        assert action is not None
        assert action.reason == 'Spam content'

    def test_toggle_flag_listing_flag_resolution(self, moderator_request, flagged_listing):
        listing, flag = flagged_listing
        data = {'resolution_note': 'Issue resolved'}
        result = ListingCommand.toggle_flag_listing(moderator_request, listing.id, data)
        assert result.status_code == 200
        assert result.message == "Flag resolved successfully"
        assert result.data['is_flagged'] is False

        flag.refresh_from_db()
        assert flag.is_resolved is True
        assert flag.resolved_by == moderator_request.user
        assert flag.resolved_at is not None
        assert flag.resolution_note == 'Issue resolved'

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=listing.id,
            action_type=ModeratorActionTypeEnum.UNFLAG.value
        ).first()
        assert action is not None

    def test_toggle_flag_listing_missing_resolution_note(self, moderator_request, pending_listing):
        data = {}
        result = ListingCommand.toggle_flag_listing(moderator_request, pending_listing.id, data)
        assert result.status_code == 400
        assert result.message == "A resolution_note is required for flagging/unflagging a listing"

    def test_toggle_flag_listing_with_existing_resolved_flag(self, moderator_request, pending_listing):
        # Create a resolved flag
        resolved_flag = FlaggedContent.objects.create(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=pending_listing.id,
            flagged_by=moderator_request.user,
            reason='Old issue',
            is_resolved=True,
            resolved_by=moderator_request.user,
            resolved_at=timezone.now(),
            resolution_note='Fixed'
        )
        data = {'resolution_note': 'New flag'}
        result = ListingCommand.toggle_flag_listing(moderator_request, pending_listing.id, data)
        # Since there is no unresolved flag, it should create a new flag
        assert result.status_code == 200
        assert result.message == "Listing flagged successfully"
        new_flag = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=pending_listing.id,
            is_resolved=False,
        ).first()
        assert new_flag is not None
        assert new_flag.reason == 'New flag'
        # The resolved flag should remain untouched
        resolved_flag.refresh_from_db()
        assert resolved_flag.is_resolved is True

    # ---------- Edge Cases / Potential Bug ----------
    def test_toggle_flag_listing_listing_does_not_exist(self, moderator_request):
        """
        BUG: The command does NOT check if the listing exists before flagging.
        This test reveals that flagging a non-existent listing succeeds,
        which is problematic because it creates a flag with no valid listing.
        We'll test that and note the bug.
        """
        data = {'resolution_note': 'Flag non-existent'}
        result = ListingCommand.toggle_flag_listing(moderator_request, 999, data)
        # Currently, it will create a flag because no unresolved flag exists
        assert result.status_code == 200
        assert result.message == "Listing flagged successfully"
        flag = FlaggedContent.objects.filter(
            content_type=ContentTypeEnum.LISTING.value,
            content_id=999,
            is_resolved=False,
        ).first()
        assert flag is not None
        # This is a bug: we should validate that the listing exists before flagging.
        # After fixing the code, this test should expect a 404.

    # ---------- Atomicity Tests ----------
    def test_approve_listing_atomicity(self, moderator_request, pending_listing, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test'}
            with pytest.raises(IntegrityError):
                ListingCommand.approve_listing(moderator_request, pending_listing.id, data)
            pending_listing.refresh_from_db()
            assert pending_listing.status == ListingStatusTypeEnum.PENDING.value

    def test_reject_listing_atomicity(self, moderator_request, pending_listing, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test'}
            with pytest.raises(IntegrityError):
                ListingCommand.reject_listing(moderator_request, pending_listing.id, data)
            pending_listing.refresh_from_db()
            assert pending_listing.is_deleted is False

    def test_toggle_delete_listing_atomicity(self, moderator_request, pending_listing, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test'}
            with pytest.raises(IntegrityError):
                ListingCommand.toggle_delete_listing(moderator_request, pending_listing.id, data)
            pending_listing.refresh_from_db()
            assert pending_listing.is_deleted is False

    def test_toggle_hide_listing_atomicity(self, moderator_request, active_listing, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'reason': 'test'}
            with pytest.raises(IntegrityError):
                ListingCommand.toggle_hide_listing(moderator_request, active_listing.id, data)
            active_listing.refresh_from_db()
            assert active_listing.status == ListingStatusTypeEnum.ACTIVE.value

    def test_toggle_flag_listing_atomicity_flag_creation(self, moderator_request, pending_listing, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'resolution_note': 'test'}
            with pytest.raises(IntegrityError):
                ListingCommand.toggle_flag_listing(moderator_request, pending_listing.id, data)
            # No flag should be created
            flag = FlaggedContent.objects.filter(
                content_type=ContentTypeEnum.LISTING.value,
                content_id=pending_listing.id,
            ).first()
            assert flag is None

    def test_toggle_flag_listing_atomicity_flag_resolution(self, moderator_request, flagged_listing, mocker):
        listing, flag = flagged_listing
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'resolution_note': 'test'}
            with pytest.raises(IntegrityError):
                ListingCommand.toggle_flag_listing(moderator_request, listing.id, data)
            # Flag should remain unresolved
            flag.refresh_from_db()
            assert flag.is_resolved is False