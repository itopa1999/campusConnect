from apps.moderator.BBL.Commands.category import CategoryCommand
import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.db import IntegrityError
from django.utils.text import slugify
from apps.campus.models import Category
from apps.moderator.models import ModeratorAction
from utils.enums import ModeratorActionTypeEnum, ContentTypeEnum

User = get_user_model()


# ---------- Fixtures (defined inside the test file) ----------
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
def category(db):
    return Category.objects.create(
        name='Electronics',
        slug='electronics',
        description='All things electronic',
        sort_order=10
    )


@pytest.fixture
def deleted_category(db):
    return Category.objects.create(
        name='Deleted',
        slug='deleted',
        is_deleted=True
    )


# ---------- Test class ----------
@pytest.mark.django_db
class TestCategoryCommand:

    # ---------- create_category ----------
    def test_create_category_success(self, moderator_request):
        data = {
            'name': 'Books',
            'description': 'All kinds of books',
            'icon': '📚',
            'sort_order': 5
        }
        result = CategoryCommand.create_category(moderator_request, data)
        assert result.status_code == 201
        assert result.message == "Category created successfully"
        assert 'id' in result.data
        assert result.data['name'] == 'Books'

        category = Category.objects.get(id=result.data['id'])
        assert category.name == 'Books'
        assert category.slug == slugify('Books')
        assert category.description == 'All kinds of books'
        assert category.icon == '📚'
        assert category.sort_order == 5
        assert not category.is_deleted

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.CATEGORY.value,
            content_id=category.id,
            action_type=ModeratorActionTypeEnum.CREATE.value
        ).first()
        assert action is not None
        assert action.moderator == moderator_request.user
        assert 'Created category' in action.reason
        assert action.metadata['category_name'] == 'Books'

    def test_create_category_missing_name(self, moderator_request):
        data = {'description': 'No name'}
        result = CategoryCommand.create_category(moderator_request, data)
        assert result.status_code == 400
        assert result.message == "Category name is required"
        assert result.data is None
        assert Category.objects.count() == 0

    def test_create_category_duplicate_slug(self, moderator_request, category):
        data = {'name': 'electronics'}
        result = CategoryCommand.create_category(moderator_request, data)
        assert result.status_code == 400
        assert result.message == "Category with this name already exists"
        assert Category.objects.count() == 1

    def test_create_category_without_optional_fields(self, moderator_request):
        data = {'name': 'Toys'}
        result = CategoryCommand.create_category(moderator_request, data)
        assert result.status_code == 201
        category = Category.objects.get(id=result.data['id'])
        assert category.description == ''
        assert category.icon == ''
        assert category.sort_order == 0

    # ---------- update_category ----------
    def test_update_category_success(self, moderator_request, category):
        data = {
            'name': 'Gadgets',
            'description': 'Updated description',
            'icon': '💡',
            'sort_order': 20
        }
        result = CategoryCommand.update_category(moderator_request, category.id, data)
        assert result.status_code == 200
        assert result.message == "Category updated successfully"
        assert result.data['name'] == 'Gadgets'

        category.refresh_from_db()
        assert category.name == 'Gadgets'
        assert category.slug == slugify('Gadgets')
        assert category.description == 'Updated description'
        assert category.icon == '💡'
        assert category.sort_order == 20

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.CATEGORY.value,
            content_id=category.id,
            action_type=ModeratorActionTypeEnum.UPDATE.value
        ).first()
        assert action is not None
        assert action.metadata['old_name'] == 'Electronics'
        assert action.metadata['new_name'] == 'Gadgets'

    def test_update_category_not_found(self, moderator_request):
        data = {'name': 'New'}
        result = CategoryCommand.update_category(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "Category not found"

    def test_update_category_duplicate_name(self, moderator_request, category):
        other = Category.objects.create(name='Furniture', slug='furniture')
        data = {'name': 'Furniture'}
        result = CategoryCommand.update_category(moderator_request, category.id, data)
        assert result.status_code == 400
        assert result.message == "Category with this name already exists"
        category.refresh_from_db()
        assert category.name == 'Electronics'

    def test_update_category_partial(self, moderator_request, category):
        data = {'description': 'New desc'}
        result = CategoryCommand.update_category(moderator_request, category.id, data)
        assert result.status_code == 200
        category.refresh_from_db()
        assert category.name == 'Electronics'
        assert category.description == 'New desc'
        assert category.sort_order == 10

    def test_update_category_no_changes(self, moderator_request, category):
        data = {'name': category.name, 'description': category.description}
        result = CategoryCommand.update_category(moderator_request, category.id, data)
        assert result.status_code == 200
        category.refresh_from_db()
        assert category.name == 'Electronics'

    # ---------- toggle_delete_category ----------
    def test_toggle_delete_category_soft_delete(self, moderator_request, category):
        data = {'reason': 'Obsolete category'}
        result = CategoryCommand.toggle_delete_category(moderator_request, category.id, data)
        assert result.status_code == 200
        assert result.message == "Category deleted successfully"
        assert result.data['is_deleted'] is True
        category.refresh_from_db()
        assert category.is_deleted is True

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.CATEGORY.value,
            content_id=category.id,
            action_type=ModeratorActionTypeEnum.DELETE.value
        ).first()
        assert action is not None
        assert action.reason == 'Obsolete category'
        assert action.metadata['old_is_deleted'] is False
        assert action.metadata['new_is_deleted'] is True

    def test_toggle_delete_category_restore(self, moderator_request, deleted_category):
        data = {'reason': 'Restoring accidentally deleted'}
        result = CategoryCommand.toggle_delete_category(moderator_request, deleted_category.id, data)
        assert result.status_code == 200
        assert result.message == "Category restored successfully"
        assert result.data['is_deleted'] is False
        deleted_category.refresh_from_db()
        assert deleted_category.is_deleted is False

        action = ModeratorAction.objects.filter(
            content_type=ContentTypeEnum.CATEGORY.value,
            content_id=deleted_category.id,
            action_type=ModeratorActionTypeEnum.REINSTATE.value
        ).first()
        assert action is not None

    def test_toggle_delete_category_missing_reason(self, moderator_request, category):
        data = {}
        result = CategoryCommand.toggle_delete_category(moderator_request, category.id, data)
        assert result.status_code == 400
        assert result.message == "A reason is required"
        category.refresh_from_db()
        assert category.is_deleted is False

    def test_toggle_delete_category_not_found(self, moderator_request):
        data = {'reason': 'Something'}
        result = CategoryCommand.toggle_delete_category(moderator_request, 999, data)
        assert result.status_code == 404
        assert result.message == "Category not found"

    def test_toggle_delete_category_already_deleted_toggle_again(self, moderator_request, deleted_category):
        data = {'reason': 'Second toggle'}
        result = CategoryCommand.toggle_delete_category(moderator_request, deleted_category.id, data)
        assert result.status_code == 200
        assert result.message == "Category restored successfully"
        deleted_category.refresh_from_db()
        assert deleted_category.is_deleted is False

        result2 = CategoryCommand.toggle_delete_category(moderator_request, deleted_category.id, data)
        assert result2.status_code == 200
        assert result2.message == "Category deleted successfully"
        deleted_category.refresh_from_db()
        assert deleted_category.is_deleted is True

    # ---------- Edge Cases ----------
    def test_create_category_with_very_long_name(self, moderator_request):
        long_name = 'A' * 100  # 100 characters → slug length = 100
        data = {'name': long_name}
        result = CategoryCommand.create_category(moderator_request, data)
        assert result.status_code == 201
        category = Category.objects.get(id=result.data['id'])
        assert category.name == long_name
        assert category.slug == slugify(long_name)  # 'a' * 100
        assert len(category.slug) == 100

    def test_update_category_duplicate_slug_ignores_self(self, moderator_request, category):
        data = {'name': 'Electronics'}   # same as existing
        result = CategoryCommand.update_category(moderator_request, category.id, data)
        assert result.status_code == 200
        # No conflict

    def test_toggle_delete_category_uses_all_including_deleted_manager(self, moderator_request, deleted_category):
        data = {'reason': 'Restore'}
        result = CategoryCommand.toggle_delete_category(moderator_request, deleted_category.id, data)
        assert result.status_code == 200
        # Should find deleted category

    # ---------- Atomicity test ----------
    def test_create_category_atomicity(self, moderator_request, mocker):
        # Mock ModeratorAction.objects.create to raise an exception
        with mocker.patch(
            'apps.moderator.models.ModeratorAction.objects.create',
            side_effect=IntegrityError("DB error")
        ):
            data = {'name': 'Test Atomic'}
            with pytest.raises(IntegrityError):
                CategoryCommand.create_category(moderator_request, data)
            # Ensure no category was created
            assert not Category.objects.filter(name='Test Atomic').exists()