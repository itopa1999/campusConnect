from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.vote.models import PollCategory
from apps.vote.serializers import PollCategoryCreateUpdateSerializer
from utils.base_result import BaseResultWithData
from utils.log_helpers import OperationLogger


class CategoryCommand:
    @staticmethod
    def create_category(request, validated_data: dict) -> BaseResultWithData:
        """
        Create a poll category.
        - Validate name is unique
        """
        op = OperationLogger(
            f"CategoryCommand.create_category from {validated_data.get('name')}",
            data=validated_data
        )
        op.start()

        name = validated_data.get('name', '').strip()
        if PollCategory.objects.filter(
            name__iexact=name,
            is_deleted=False
        ).exists():
            op.fail(f"Category name '{name}' already exists")
            return BaseResultWithData(
                message="A category with this name already exists.",
                status_code=400
            )

        serializer = PollCategoryCreateUpdateSerializer(data=validated_data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            op.fail(f"Serializer validation failed", exc={'errors': e.detail})
            return BaseResultWithData(
                message="Validation failed.",
                data={'errors': e.detail},
                status_code=400
            )

        try:
            with transaction.atomic():
                category = serializer.save()
                op.success(f"Category created: {category.name}")
                return BaseResultWithData(
                    message="Category created successfully.",
                    data={'id': category.id, 'name': category.name},
                    status_code=201
                )

        except Exception as e:
            op.fail(f"Unexpected error during category creation", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )

    @staticmethod
    def update_category(request, category_id: int, validated_data: dict) -> BaseResultWithData:
        """
        Update a poll category.
        - Check if category exists
        - Validate name is unique (excluding self)
        """
        op = OperationLogger(
            f"CategoryCommand.update_category for ID: {category_id}",
            data=validated_data
        )
        op.start()

        try:
            category = PollCategory.objects.only(
                'id', 'name', 'is_deleted'
            ).get(id=category_id, is_deleted=False)
        except PollCategory.DoesNotExist:
            op.fail(f"Category ID {category_id} not found")
            return BaseResultWithData(
                message="Category not found.",
                status_code=404
            )

        name = validated_data.get('name', '').strip()
        if name:
            if PollCategory.objects.filter(
                name__iexact=name,
                is_deleted=False
            ).exclude(id=category_id).exists():
                op.fail(f"Category name '{name}' already exists")
                return BaseResultWithData(
                    message="A category with this name already exists.",
                    status_code=400
                )

        serializer = PollCategoryCreateUpdateSerializer(
            instance=category,
            data=validated_data,
            partial=True
        )
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            op.fail(f"Serializer validation failed", exc={'errors': e.detail})
            return BaseResultWithData(
                message="Validation failed.",
                data={'errors': e.detail},
                status_code=400
            )

        try:
            with transaction.atomic():
                category = serializer.save()
                op.success(f"Category updated: {category.name}")
                return BaseResultWithData(
                    message="Category updated successfully.",
                    data={'id': category.id, 'name': category.name},
                    status_code=200
                )

        except Exception as e:
            op.fail(f"Unexpected error during category update", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )

    @staticmethod
    def toggle_category_status(request, category_id: int) -> BaseResultWithData:
        """
        Toggle category status (soft delete if active, restore if deleted).
        - If active: soft delete (prevents deletion if has active polls)
        - If deleted: restore
        """
        op = OperationLogger(
            f"CategoryCommand.toggle_category_status for ID: {category_id}"
        )
        op.start()
        
        try:
            category = PollCategory.objects.only(
                'id', 'name', 'is_deleted'
            ).get(id=category_id)
        except PollCategory.DoesNotExist:
            op.fail(f"Category ID {category_id} not found")
            return BaseResultWithData(
                message="Category not found.",
                status_code=404
            )

        try:
            with transaction.atomic():
                if category.is_deleted:
                    category.is_deleted = False
                    category.save(update_fields=['is_deleted'])
                    
                    op.success(f"Category restored: {category.name}")
                    return BaseResultWithData(
                        message="Category restored successfully.",
                        data={'id': category.id, 'name': category.name, 'status': 'active'},
                        status_code=200
                    )
                else:
                    if category.polls.filter(is_deleted=False).exists():
                        op.fail(f"Category '{category.name}' has active polls")
                        return BaseResultWithData(
                            message="Cannot delete this category because it has active polls. "
                                    "Please delete or reassign the polls first.",
                            status_code=400
                        )
                    
                    category.is_deleted = True
                    category.save(update_fields=['is_deleted'])
                    
                    op.success(f"Category deleted: {category.name}")
                    return BaseResultWithData(
                        message="Category deleted successfully.",
                        data={'id': category.id, 'name': category.name, 'status': 'deleted'},
                        status_code=200
                    )

        except Exception as e:
            op.fail(f"Unexpected error during category toggle", exc=e)
            return BaseResultWithData(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=500
            )