from django.db import transaction
from django.utils.text import slugify
from apps.campus.models import Category
from apps.moderator.models import ModeratorAction
from utils.base_result import BaseResultWithData
from utils.enums import ContentTypeEnum, ModeratorActionTypeEnum
from utils.log_helpers import OperationLogger


class CategoryCommand:
    @staticmethod
    @transaction.atomic
    def create_category(request, validated_data) -> BaseResultWithData:
        op = OperationLogger("ModeratorCategoryCommand.create_category", user=request.user.id)
        op.start()

        name = validated_data.get('name')
        description = validated_data.get('description', '')
        icon = validated_data.get('icon', '')
        sort_order = validated_data.get('sort_order', 0)

        if not name:
            return BaseResultWithData(
                message="Category name is required",
                data=None,
                status_code=400
            )

        slug = slugify(name)
        if Category.objects.filter(slug=slug, is_deleted=False).exists():
            return BaseResultWithData(
                message="Category with this name already exists",
                data=None,
                status_code=400
            )

        category = Category.objects.create(
            name=name,
            slug=slug,
            description=description,
            icon=icon,
            sort_order=sort_order,
        )

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.CREATE.value,
            content_type=ContentTypeEnum.CATEGORY.value,
            content_id=category.id,
            reason=f"Created category '{name}'",
            metadata={
                'category_name': name,
                'slug': slug,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"Category {category.id} created")
        return BaseResultWithData(
            message="Category created successfully",
            data={'id': category.id, 'name': category.name},
            status_code=201
        )

    @staticmethod
    @transaction.atomic
    def update_category(request, category_id, validated_data) -> BaseResultWithData:
        op = OperationLogger("ModeratorCategoryCommand.update_category", category_id=category_id)
        op.start()

        try:
            category = Category.objects.get(id=category_id, is_deleted=False)
        except Category.DoesNotExist:
            op.fail("Category not found")
            return BaseResultWithData(
                message="Category not found",
                data=None,
                status_code=404
            )

        name = validated_data.get('name')
        description = validated_data.get('description')
        icon = validated_data.get('icon')
        sort_order = validated_data.get('sort_order')

        old_name = category.name
        old_sort = category.sort_order

        if name and name != category.name:
            slug = slugify(name)
            if Category.objects.filter(slug=slug, is_deleted=False).exclude(id=category_id).exists():
                return BaseResultWithData(
                    message="Category with this name already exists",
                    data=None,
                    status_code=400
                )
            category.name = name
            category.slug = slug

        if description is not None:
            category.description = description
        if icon is not None:
            category.icon = icon
        if sort_order is not None:
            category.sort_order = sort_order

        category.save()

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.UPDATE.value,
            content_type=ContentTypeEnum.CATEGORY.value,
            content_id=category.id,
            reason=f"Updated category '{category.name}'",
            metadata={
                'old_name': old_name,
                'new_name': category.name,
                'old_sort_order': old_sort,
                'new_sort_order': category.sort_order,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"Category {category_id} updated")
        return BaseResultWithData(
            message="Category updated successfully",
            data={'id': category.id, 'name': category.name},
            status_code=200
        )

    @staticmethod
    @transaction.atomic
    def toggle_delete_category(request, category_id, validated_data) -> BaseResultWithData:
        op = OperationLogger("ModeratorCategoryCommand.toggle_delete_category", category_id=category_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required",
                data=None,
                status_code=400
            )

        try:
            category = Category.objects.all_including_deleted().get(id=category_id)
        except Category.DoesNotExist:
            op.fail("Category not found")
            return BaseResultWithData(
                message="Category not found",
                data=None,
                status_code=404
            )

        old_deleted = category.is_deleted
        new_deleted = not old_deleted
        category.is_deleted = new_deleted
        category.save(update_fields=['is_deleted'])

        action_type = ModeratorActionTypeEnum.DELETE.value if new_deleted else ModeratorActionTypeEnum.REINSTATE.value
        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=action_type,
            content_type=ContentTypeEnum.CATEGORY.value,
            content_id=category.id,
            reason=reason,
            metadata={
                'old_is_deleted': old_deleted,
                'new_is_deleted': new_deleted,
                'category_name': category.name,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"Category {category_id} delete toggled to {new_deleted}")
        return BaseResultWithData(
            message=f"Category {'deleted' if new_deleted else 'restored'} successfully",
            data={'category_id': category.id, 'is_deleted': category.is_deleted},
            status_code=200
        )