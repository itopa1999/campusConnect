from django.urls import path, include

from apps.campus.views import (ToggleFavouriteListingView, 
        ApproveClaimView, CategorizedListingsView, 
        GetDashboardLisitingView, GetDashboardReviewsView, GetDashboardUpCommingExpirationLisitingView, 
        GetDashboardView, GetIndexDefaultLisitingView, GetLookUpView, 
        ListFavouriteListingView, ListingAutoActivation, ListingDetailView, 
        ListingDetailsView, ListingView, LostAndFoundClaimView, LostAndFoundListView, 
        LostAndFoundView, MarkAsSoldView, UpdateAdsView, UploadImageView)




urlpatterns = [
    path(
        "campus/",
        include(
            [
                path("dashboard", GetDashboardView.as_view(), name="campus-dashboard"),
                path("dashboard-upcoming-listing", GetDashboardUpCommingExpirationLisitingView.as_view(), name="campus-dashboard-upcoming-listing"),
                path("dashboard-listing", GetDashboardLisitingView.as_view(), name="campus-dashboard-listing"),
                path("dashboard-reviews", GetDashboardReviewsView.as_view(), name="campus-dashboard-reviews"),

                path("index-products", GetIndexDefaultLisitingView.as_view(), name="get_index_products"),
                path("get-lookup", GetLookUpView.as_view(), name="get_lookup"),

                path("create-listing", ListingView.as_view(), name="create_lisiting"),
                path("mark-sold/<int:listing_id>", MarkAsSoldView.as_view(), name="mark_sold"),
                path('listing/<int:listing_id>', ListingDetailView.as_view(), name='listing_detail'),
                path('listing-upload-image/<int:listing_id>', UploadImageView.as_view(), name='listing_upload_image'),
                path('listing-update-ads/<int:listing_id>', UpdateAdsView.as_view(), name='listing_update_ads'),
                path('listing-auto-reactivate/<int:listing_id>', ListingAutoActivation.as_view(), name='listing_auto_reactivate'),
                path('listings/categorized', CategorizedListingsView.as_view(), name='categorized_listings'),
                path('listing-details/<int:listing_id>', ListingDetailsView.as_view(), name='listing_details'),

                path("report-lost-item", LostAndFoundView.as_view(), name="report_lost_item"),
                path('lost-and-found/reports', LostAndFoundListView.as_view(), name='lost_and_found_report'),
                path('lost-and-found/claim', LostAndFoundClaimView.as_view(), name='lost-and-found-claim'),
                path('approve-claim', ApproveClaimView.as_view(), name='approve_claim'),

                path("toggle-favourite/<int:listing_id>", ToggleFavouriteListingView.as_view(), name="toggle_favourite"),
                path('list-favourites', ListFavouriteListingView.as_view(), name='list_favourites'),
            ]
        )
    )
]