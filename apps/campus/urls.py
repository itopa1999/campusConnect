from django.urls import path, include
from .views import *




urlpatterns = [
    path(
        "campus/",
        include(
            [
                path("dashboard", GetDashboardView.as_view(), name="campus-dashboard"),
                path("index_products", GetIndexDefaultLisitingView.as_view(), name="get-index-products"),
                path("get_lookup", GetLookUpView.as_view(), name="get-lookup"),

                path("create_listing", ListingView.as_view(), name="create-lisiting"),
                path("mark-sold/<int:listing_id>", MarkAsSoldView.as_view(), name="mark-sold"),
                path('listing/<int:listing_id>', ListingDetailView.as_view(), name='listing-detail'),
            ]
        )
    )
]