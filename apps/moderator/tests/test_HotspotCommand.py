from apps.moderator.BBL.Commands.hotspot import HotspotCommand
import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.db import IntegrityError
from django.utils.text import slugify
from apps.campus.models import CampusHotspot
from apps.moderator.models import ModeratorAction
from utils.enums import ModeratorActionTypeEnum, ContentTypeEnum

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
def request_factory():
    return RequestFactory()


@pytest.fixture
def moderator_request(request_factory, user):
    req = request_factory.get('/')
    req.user = user
    req.META = {'REMOTE_ADDR': '127.0.0.1'}
    return req


@pytest.fixture
def hotspot(db):
    return CampusHotspot.objects.create(
        name='Library',
        slug='library',
        description='Main library building',
        sort_order=10
    )


@pytest.fixture
def deleted_hotspot(db):
    return CampusHotspot.objects.create(
        name='Cafeteria',
        slug='cafeteria',
        is_deleted=True
    )


# ---------- Test class ----------
@pytest.mark.django_db
class TestHotspotCommand:

    # ---------- create_hotspot ----------
    def test_create_hotspot_success(self, moderator_request):
        data = {
            'name': 'Student Union',
            'description': 'Student activities center',
            'sort_order': 5
        }
        result = HotspotCommand.create_hotspot(moderator_request, data)
        assert result.status_code == 201
        assert result.message == "Hotspot created successfully"
        assert 'id' in result.data
        assert result.data['name'] == 'Student Union'

        hotspot = CampusHotspot.objects.get(id=result.data['id'])
        assert hotspot.name == 'Student Union'
        assert hotspot.slug == slugify('Student Union')
        assert hotspot.description == 'Student activities center'
        assert hotspot.sort_order == 5
        assert not hotspot.is_deleted

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.HOTSPOT.value,
            content_id=hotspot.id,
            action_type=ModeratorActionTypeEnum.CREATE.value
        ).first()
        assert action is not None
        assert action.moderator == moderator_request.user
        assert 'Created hotspot' in action.reason
        assert action.metadata['hotspot_name'] == 'Student Union'

    def test_create_hotspot_missing_name(self, moderator_request):
        data = {'description': 'No name'}
        result = HotspotCommand.create_hotspot(moderator_request, data)
        assert result.status_code == 400
        assert result.message == "Hotspot name is required"
        assert result.data is None
        assert CampusHotspot.objects.count() == 0

    def test_create_hotspot_duplicate_slug(self, moderator_request, hotspot):
        data = {'name': 'library'}   # case-insensitive slug conflict
        result = HotspotCommand.create_hotspot(moderator_request, data)
        assert result.status_code == 400
        assert result.message == "Hotspot with this name already exists"
        assert CampusHotspot.objects.count() == 1

    def test_create_hotspot_without_optional_fields(self, moderator_request):
        data = {'name': 'Gym'}
        result = HotspotCommand.create_hotspot(moderator_request, data)
        assert result.status_code == 201
        hotspot = CampusHotspot.objects.get(id=result.data['id'])
        assert hotspot.description == ''
        assert hotspot.sort_order == 0

    # ---------- update_hotspot ----------
    def test_update_hotspot_success(self, moderator_request, hotspot):
        data = {
            'name': 'New Library',
            'description': 'Updated description',
            'sort_order': 20
        }
        result = HotspotCommand.update_hotspot(moderator_request, hotspot.id, data)
        assert result.status_code == 200
        assert result.message == "Hotspot updated successfully"
        assert result.data['name'] == 'New Library'

        hotspot.refresh_from_db()
        assert hotspot.name == 'New Library'
        assert hotspot.slug == slugify('New Library')
        assert hotspot.description == 'Updated description'
        assert hotspot.sort_order == 20

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.HOTSPOT.value,
            content_id=hotspot.id,
            action_type=ModeratorActionTypeEnum.UPDATE.value
        ).first()
        assert action is not None
        assert action.metadata['old_name'] == 'Library'
        assert action.metadata['new_name'] == 'New Library'

    def test_update_hotspot_not_found(self, moderator_request):
        data = {'name': 'New'}
        result = HotspotCommand.update_hotspot(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "Hotspot not found"

    def test_update_hotspot_duplicate_name(self, moderator_request, hotspot):
        other = CampusHotspot.objects.create(name='Auditorium', slug='auditorium')
        data = {'name': 'Auditorium'}
        result = HotspotCommand.update_hotspot(moderator_request, hotspot.id, data)
        assert result.status_code == 400
        assert result.message == "Hotspot with this name already exists"
        hotspot.refresh_from_db()
        assert hotspot.name == 'Library'

    def test_update_hotspot_partial(self, moderator_request, hotspot):
        data = {'description': 'New desc'}
        result = HotspotCommand.update_hotspot(moderator_request, hotspot.id, data)
        assert result.status_code == 200
        hotspot.refresh_from_db()
        assert hotspot.name == 'Library'
        assert hotspot.description == 'New desc'
        assert hotspot.sort_order == 10

    def test_update_hotspot_no_changes(self, moderator_request, hotspot):
        data = {'name': hotspot.name, 'description': hotspot.description}
        result = HotspotCommand.update_hotspot(moderator_request, hotspot.id, data)
        assert result.status_code == 200
        hotspot.refresh_from_db()
        assert hotspot.name == 'Library'

    # ---------- toggle_delete_hotspot ----------
    def test_toggle_delete_hotspot_soft_delete(self, moderator_request, hotspot):
        data = {'reason': 'Under renovation'}
        result = HotspotCommand.toggle_delete_hotspot(moderator_request, hotspot.id, data)
        assert result.status_code == 200
        assert result.message == "Hotspot deleted successfully"
        assert result.data['is_deleted'] is True
        hotspot.refresh_from_db()
        assert hotspot.is_deleted is True

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.HOTSPOT.value,
            content_id=hotspot.id,
            action_type=ModeratorActionTypeEnum.DELETE.value
        ).first()
        assert action is not None
        assert action.reason == 'Under renovation'
        assert action.metadata['old_is_deleted'] is False
        assert action.metadata['new_is_deleted'] is True

    def test_toggle_delete_hotspot_restore(self, moderator_request, deleted_hotspot):
        data = {'reason': 'Reopening'}
        result = HotspotCommand.toggle_delete_hotspot(moderator_request, deleted_hotspot.id, data)
        assert result.status_code == 200
        assert result.message == "Hotspot restored successfully"
        assert result.data['is_deleted'] is False
        deleted_hotspot.refresh_from_db()
        assert deleted_hotspot.is_deleted is False

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.HOTSPOT.value,
            content_id=deleted_hotspot.id,
            action_type=ModeratorActionTypeEnum.REINSTATE.value
        ).first()
        assert action is not None

    def test_toggle_delete_hotspot_missing_reason(self, moderator_request, hotspot):
        data = {}
        result = HotspotCommand.toggle_delete_hotspot(moderator_request, hotspot.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required"
        hotspot.refresh_from_db()
        assert hotspot.is_deleted is False

    def test_toggle_delete_hotspot_not_found(self, moderator_request):
        data = {'reason': 'Something'}
        result = HotspotCommand.toggle_delete_hotspot(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "Hotspot not found"

    def test_toggle_delete_hotspot_already_deleted_toggle_again(self, moderator_request, deleted_hotspot):
        data = {'reason': 'Second toggle'}
        result = HotspotCommand.toggle_delete_hotspot(moderator_request, deleted_hotspot.id, data)
        assert result.status_code == 200
        assert result.message == "Hotspot restored successfully"
        deleted_hotspot.refresh_from_db()
        assert deleted_hotspot.is_deleted is False

        result2 = HotspotCommand.toggle_delete_hotspot(moderator_request, deleted_hotspot.id, data)
        assert result2.status_code == 200
        assert result2.message == "Hotspot deleted successfully"
        deleted_hotspot.refresh_from_db()
        assert deleted_hotspot.is_deleted is True

    # ---------- Edge Cases ----------
    def test_create_hotspot_with_very_long_name(self, moderator_request):
        # Assuming slug max_length is 100 (adjust if different)
        long_name = 'A' * 100
        data = {'name': long_name}
        result = HotspotCommand.create_hotspot(moderator_request, data)
        assert result.status_code == 201
        hotspot = CampusHotspot.objects.get(id=result.data['id'])
        assert hotspot.name == long_name
        assert hotspot.slug == slugify(long_name)
        assert len(hotspot.slug) == 100

    def test_update_hotspot_duplicate_slug_ignores_self(self, moderator_request, hotspot):
        data = {'name': 'Library'}   # same as existing
        result = HotspotCommand.update_hotspot(moderator_request, hotspot.id, data)
        assert result.status_code == 200
        # No conflict

    def test_toggle_delete_hotspot_uses_all_including_deleted_manager(self, moderator_request, deleted_hotspot):
        data = {'reason': 'Restore'}
        result = HotspotCommand.toggle_delete_hotspot(moderator_request, deleted_hotspot.id, data)
        assert result.status_code == 200
        # Should find deleted hotspot

    # ---------- Atomicity test ----------
    def test_create_hotspot_atomicity(self, moderator_request, mocker):
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'name': 'Test Atomic'}
            with pytest.raises(IntegrityError):
                HotspotCommand.create_hotspot(moderator_request, data)
            assert not CampusHotspot.objects.filter(name='Test Atomic').exists()