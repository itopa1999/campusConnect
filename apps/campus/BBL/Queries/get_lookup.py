from apps.campus.models import Category, CampusHotspot, SubCategory
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import AdvertTypeEnum, CacheKeysEnum, ListingConditionEnum, ListingTypeEnum


class LookUpQuery:
    @staticmethod
    def get_lookup(request, filters=None) -> BaseResultWithData:
        """
        Return all lookup data needed for the create‑listing page:
        - categories (id, name, icon, description)
        - subcategories (id, name, category_id, category_name)
        - campus hotspots (id, name, description)
        - badge choices (value, label)
        - type choices (value, label)
        - advert type choices
        """
        if filters is None:
            filters = request.GET.dict()
        else:
            filters = dict(filters)

        # Include the new filter key 'is_subcategory'
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

        def build_lookup_data():
            data = {}

            # ─── Categories ───
            if is_true(filters.get("is_category")):
                categories_qs = Category.objects.filter(
                    is_deleted=False
                ).order_by("sort_order", "name")

                data["categories"] = [
                    {
                        "id": cat.id,
                        "name": cat.name,
                        "icon": cat.icon,
                        "description": cat.description,
                    }
                    for cat in categories_qs
                ]

            # ─── Subcategories (new) ───
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
                        # optional: include description, icon, sort_order if needed
                        # "description": sub.description,
                        # "icon": sub.icon,
                        # "sort_order": sub.sort_order,
                    }
                    for sub in subcategories_qs
                ]

            # ─── Hotspots ───
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

            # ─── Badge choices ───
            if is_true(filters.get("is_condition_choices")):
                data["condition_choices"] = [
                    {
                        "value": choice[0],
                        "label": choice[1],
                    }
                    for choice in ListingConditionEnum.choices()
                ]

            # ─── Listing type choices ───
            if is_true(filters.get("is_type_choices")):
                data["type_choices"] = [
                    {
                        "value": choice[0],
                        "label": choice[1],
                    }
                    for choice in ListingTypeEnum.choices()
                ]

            # ─── Advert type choices ───
            if is_true(filters.get("is_advert_type")):
                data["advert_type"] = AdvertTypeEnum.choices()

            return data

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_lookup_data,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Lookup data retrieved successfully",
            data=data,
            status_code=200
        )