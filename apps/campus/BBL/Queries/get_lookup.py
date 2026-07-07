from apps.campus.models import Category, CampusHotspot
from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import AdvertTypeEnum, BadgeListingType, CacheKeysEnum, ListingType

class LookUpQuery:
    @staticmethod
    def get_lookup(request):
        """
        Return all lookup data needed for the create‑listing page:
        - categories (id, name, icon, description)
        - campus hotspots (id, name, description)
        - badge choices (value, label)
        - Type choices (value, label)
        """
        
        cache_key = CacheKeysEnum.LOOKUP_DATA.value
        cached_data = GlobalCache.get(cache_key)
        if cached_data:
            return BaseResultWithData(
                message="Lookup data retrieved successfully",
                data=cached_data,
                status_code=200
            )
        # Fetch categories (active, not deleted) – one query, no N+1
        categories_qs = Category.objects.filter(is_deleted=False).order_by('sort_order', 'name')
        categories = [
            {
                'id': cat.id,
                'name': cat.name,
                'icon': cat.icon,
                'description': cat.description,
            }
            for cat in categories_qs
        ]

        # Fetch hotspots (active, not deleted) – one query, no N+1
        hotspots_qs = CampusHotspot.objects.filter(is_deleted=False).order_by('sort_order', 'name')
        hotspots = [
            {
                'id': hs.id,
                'name': hs.name,
                'description': hs.description,
            }
            for hs in hotspots_qs
        ]

        # Badge choices from enum – no database query
        badge_choices = [
            {'value': choice[0], 'label': choice[1]}
            for choice in BadgeListingType.choices()
        ]

        type_choices = [
            {'value': choice[0], 'label': choice[1]}
            for choice in ListingType.choices()
        ]


        data = {
            'categories': categories,
            'hotspots': hotspots,
            'badge_choices': badge_choices,
            'type_choices': type_choices,
            'advert_type': AdvertTypeEnum.choices()
        }

        GlobalCache.set(cache_key, data)

        return BaseResultWithData(
            message="Lookup data retrieved successfully",
            data=data,
            status_code=200
        )