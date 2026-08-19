from asgiref.sync import sync_to_async
from apps.campus.models import Category, CampusHotspot, SubCategory
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import AdvertTypeEnum, CacheKeysEnum, ListingConditionEnum, ListingTypeEnum
import asyncio


class LookUpQuery:
    @staticmethod
    async def get_lookup(request, filters=None) -> BaseResultWithData:
        if filters is None:
            filters = request.GET.dict()
        else:
            filters = dict(filters)

        filter_keys = [
            'is_category',
            'is_subcategory', 
            'is_hotspot',
            'is_condition_choices',
            'is_type_choices',
            'is_advert_type'
        ]
        filter_parts = []
        for key in filter_keys:
            value = filters.get(key)
            if value is not None and value != '':
                filter_parts.append(f"{key}={value}")
        filter_parts.sort()
        filter_str = '&'.join(filter_parts)

        cache_key = CacheKeysEnum.format(CacheKeysEnum.LOOKUP_DATA, filters=filter_str)

        def is_true(value):
            if value is None:
                return False
            return str(value).lower() in ("true", "1", "yes")

        @sync_to_async
        def build_lookup_data():
            data = {}

            if is_true(filters.get("is_category")):
                categories_qs = Category.objects.filter(
                    is_deleted=False
                ).order_by("sort_order", "name")

                data["categories"] = [
                    {
                        "id": cat.id,
                        "name": cat.name,
                        "icon": cat.icon,
                        'listing_type': cat.listing_type,
                        "description": cat.description,
                    }
                    for cat in categories_qs
                ]

            if is_true(filters.get("is_subcategory")):
                subcategories_qs = SubCategory.objects.filter(
                    is_deleted=False
                ).select_related('category').order_by("category__sort_order", "sort_order", "name")

                data["subcategories"] = [
                    {
                        "id": sub.id,
                        "name": sub.name,
                        "category_id": sub.category.id,
                        "category_name": sub.category.name,
                        "description": sub.description,
                        "icon": sub.icon,
                    }
                    for sub in subcategories_qs
                ]

            if is_true(filters.get("is_hotspot")):
                hotspots_qs = CampusHotspot.objects.filter(
                    is_deleted=False
                ).order_by("sort_order", "name")

                data["hotspots"] = [
                    {
                        "id": hs.id,
                        "name": hs.name,
                        "description": hs.description,
                    }
                    for hs in hotspots_qs
                ]

            if is_true(filters.get("is_condition_choices")):
                data["condition_choices"] = [
                    {
                        "value": choice[0],
                        "label": choice[1],
                    }
                    for choice in ListingConditionEnum.choices()
                ]

            if is_true(filters.get("is_type_choices")):
                data["type_choices"] = [
                    {
                        "value": choice[0],
                        "label": choice[1],
                    }
                    for choice in ListingTypeEnum.choices()
                ]

            if is_true(filters.get("is_advert_type")):
                data["advert_type"] = AdvertTypeEnum.choices()

            return data

        try:
            data = await GlobalCache.aget_or_set(
                key=cache_key,
                callback=build_lookup_data,
                timeout=3600,
                lock_timeout=30,
                max_wait=5.0,
            )
        except asyncio.CancelledError:
            raise

        return BaseResultWithData(
            message="Lookup data retrieved successfully",
            data=data,
            status_code=200
        )