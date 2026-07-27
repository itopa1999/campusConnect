from apps.campus.models import Category, CampusHotspot
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import AdvertTypeEnum, BadgeListingTypeEnum, CacheKeysEnum, ListingTypeEnum


class LookUpQuery:
    @staticmethod
    def get_lookup(request, filters=None) -> BaseResultWithData:
        """
        Return all lookup data needed for the create‑listing page:
        - categories (id, name, icon, description)
        - campus hotspots (id, name, description)
        - badge choices (value, label)
        - Type choices (value, label)
        """
        if filters is None:
            filters = request.GET.dict()
        else:
            filters = dict(filters)

        filter_keys = ['is_category', 'is_hotspot', 'is_badge_choices', 'is_type_choices', 'is_advert_type']
        filter_parts = []
        for key in filter_keys:
            value = filters.get(key)
            if value is not None and value != '':
                filter_parts.append(f"{key}={value}")
        filter_parts.sort()
        filter_str = '&'.join(filter_parts)

        cache_key = CacheKeysEnum.format(CacheKeysEnum.LOOKUP_DATA, filters = filter_str)
        def is_true(value):
            if value is None:
                return False

            return str(value).lower() in ("true", "1", "yes")
        
        def build_lookup_data():
            data = {}

            # Categories
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

            # Hotspots
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

            # Badge choices
            if is_true(filters.get("is_badge_choices")):
                data["badge_choices"] = [
                    {
                        "value": choice[0],
                        "label": choice[1],
                    }
                    for choice in BadgeListingTypeEnum.choices()
                ]

            # Listing type choices
            if is_true(filters.get("is_type_choices")):
                data["type_choices"] = [
                    {
                        "value": choice[0],
                        "label": choice[1],
                    }
                    for choice in ListingTypeEnum.choices()
                ]

            # Advert type choices
            if is_true(filters.get("is_advert_type")):
                data["advert_type"] = AdvertTypeEnum.choices()

            return data

        # ── Atomic cache get-or-set with stampede protection ──
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