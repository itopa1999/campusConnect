from django.urls import path, include
from .views import *




urlpatterns = [
    path(
        "campus/",
        include(
            [
                path("dashboard", GetDashboardView.as_view(), name="campus-dashboard"),
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
            ]
        )
    )
]