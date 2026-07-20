from django.db import transaction
from django.utils.text import slugify
from apps.campus.models import CampusHotspot
from apps.moderator.models import ModeratorAction
from utils.base_result import BaseResultWithData
from utils.enums import ContentTypeEnum, ModeratorActionTypeEnum
from utils.log_helpers import OperationLogger


class HotspotCommand:
    @staticmethod
    @transaction.atomic
    def create_hotspot(request, validated_data):
        op = OperationLogger("ModeratorHotspotCommand.create_hotspot", user=request.user.id)
        op.start()

        name = validated_data.get('name')
        description = validated_data.get('description', '')
        sort_order = validated_data.get('sort_order', 0)

        if not name:
            return BaseResultWithData(
                message="Hotspot name is required",
                data=None,
                status_code=400
            )
        
        slug = slugify(name)
        if CampusHotspot.objects.filter(slug=slug, is_deleted=False).exists():
            return BaseResultWithData(
                message="Hotspot with this name already exists",
                data=None,
                status_code=400
            )

        hotspot = CampusHotspot.objects.create(
            name=name,
            slug=slug,
            description=description,
            sort_order=sort_order,
        )

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.CREATE.value,
            content_type=ContentTypeEnum.HOTSPOT.value,
            content_id=hotspot.id,
            reason=f"Created hotspot '{name}'",
            metadata={
                'hotspot_name': name,
                'slug': slug,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"Hotspot {hotspot.id} created")
        return BaseResultWithData(
            message="Hotspot created successfully",
            data={'id': hotspot.id, 'name': hotspot.name},
            status_code=201
        )

    @staticmethod
    @transaction.atomic
    def update_hotspot(request, hotspot_id, validated_data):
        op = OperationLogger("ModeratorHotspotCommand.update_hotspot", hotspot_id=hotspot_id)
        op.start()

        try:
            hotspot = CampusHotspot.objects.get(id=hotspot_id, is_deleted=False)
        except CampusHotspot.DoesNotExist:
            op.fail("Hotspot not found")
            return BaseResultWithData(
                message="Hotspot not found",
                data=None,
                status_code=404
            )

        name = validated_data.get('name')
        description = validated_data.get('description')
        sort_order = validated_data.get('sort_order')

        old_name = hotspot.name
        old_sort = hotspot.sort_order

        if name and name != hotspot.name:
            slug = slugify(name)
            if CampusHotspot.objects.filter(slug=slug, is_deleted=False).exclude(id=hotspot_id).exists():
                return BaseResultWithData(
                    message="Hotspot with this name already exists",
                    data=None,
                    status_code=400
                )
            hotspot.name = name
            hotspot.slug = slug

        if description is not None:
            hotspot.description = description
        if sort_order is not None:
            hotspot.sort_order = sort_order
        hotspot.save()

        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=ModeratorActionTypeEnum.UPDATE.value,
            content_type=ContentTypeEnum.HOTSPOT.value,
            content_id=hotspot.id,
            reason=f"Updated hotspot '{hotspot.name}'",
            metadata={
                'old_name': old_name,
                'new_name': hotspot.name,
                'old_sort_order': old_sort,
                'new_sort_order': hotspot.sort_order,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"Hotspot {hotspot_id} updated")
        return BaseResultWithData(
            message="Hotspot updated successfully",
            data={'id': hotspot.id, 'name': hotspot.name},
            status_code=200
        )

    @staticmethod
    @transaction.atomic
    def toggle_delete_hotspot(request, hotspot_id, validated_data):
        op = OperationLogger("ModeratorHotspotCommand.toggle_delete_hotspot", hotspot_id=hotspot_id)
        op.start()

        reason = validated_data.get('reason')
        if not reason:
            return BaseResultWithData(
                message="A reason is required",
                data=None,
                status_code=400
            )

        try:
            hotspot = CampusHotspot.objects.all_including_deleted().get(id=hotspot_id)
        except CampusHotspot.DoesNotExist:
            op.fail("Hotspot not found")
            return BaseResultWithData(
                message="Hotspot not found",
                data=None,
                status_code=404
            )

        old_deleted = hotspot.is_deleted
        new_deleted = not old_deleted
        hotspot.is_deleted = new_deleted
        hotspot.save(update_fields=['is_deleted'])

        action_type = ModeratorActionTypeEnum.DELETE.value if new_deleted else ModeratorActionTypeEnum.REINSTATE.value
        ModeratorAction.objects.create(
            moderator=request.user,
            action_type=action_type,
            content_type=ContentTypeEnum.HOTSPOT.value,
            content_id=hotspot.id,
            reason=reason,
            metadata={
                'old_is_deleted': old_deleted,
                'new_is_deleted': new_deleted,
                'hotspot_name': hotspot.name,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        op.success(f"Hotspot {hotspot_id} delete toggled to {new_deleted}")
        return BaseResultWithData(
            message=f"Hotspot {'deleted' if new_deleted else 'restored'} successfully",
            data={'hotspot_id': hotspot.id, 'is_deleted': hotspot.is_deleted},
            status_code=200
        )