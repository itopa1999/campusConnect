

from utils.base_result import BaseResultWithData
from utils.cache_helper import GlobalCache
from utils.enums import CacheKeysEnum


class DashboardQuery:
    @staticmethod
    def get_dashboard(request) -> BaseResultWithData:
        user = request.user
        cache_key = CacheKeysEnum.format(CacheKeysEnum.MOD_DASHBOARD, user_id=user.id)

        def build_dashboard_data():
            return {
                'user': 'first_name',
                'first_name': 'first_name',
                'total_active': 'total_active',
                'total_marked_sold': 'total_marked_sold',
                'total_expired': 'total_expired',
                'total_pending': 'total_pending',
                'total_sold': 'user.sold_items',
            }

        data = GlobalCache.get_or_set(
            key=cache_key,
            callback=build_dashboard_data,
            timeout=3600,
            lock_timeout=30,
            max_wait=5.0,
        )

        return BaseResultWithData(
            message="Dashboard data retrieved successfully",
            data=data,
            status_code=200
        )




# | Feature | Description |
# |---------|-------------|
# | **Moderation dashboard** | Overview of pending tasks, recent activity, and key metrics |
# | **Listing statistics** | Total listings, active, pending, flagged, reported |
# | **User statistics** | Total users, new users, suspended/banned users |
# | **Review statistics** | Average rating, total reviews, flagged reviews |
# | **Report statistics** | Total reports, resolved rate, common violation types |
# | **Activity logs** | View all moderation actions taken (audit trail) |
# | **Export reports** | Export moderation data for reporting or analysis |
