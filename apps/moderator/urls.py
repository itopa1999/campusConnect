from django.urls import path, include

from apps.moderator.views import (
    ModeratorCategoriesListView,
    ModeratorCategoryDetailView,
    ModeratorCategoryToggleDeleteView,
    ModeratorCreateCategoryView,
    ModeratorCreateHotspotView,
    ModeratorDashboardStatsView,
    ModeratorHotspotDetailView,
    ModeratorHotspotListView,
    ModeratorHotspotToggleDeleteView,
    ModeratorListingListView,
    ModeratorListingDetailView,
    ModeratorListingApproveView,
    ModeratorListingRejectView,
    ModeratorListingToggleDeleteView,
    ModeratorListingToggleHideView,
    ModeratorListingToggleFlagView,
    ModeratorLostItemApproveView,
    ModeratorLostItemDetailView,
    ModeratorLostItemListView,
    ModeratorLostItemRejectView,
    ModeratorLostItemToggleDeleteView,
    ModeratorLostItemToggleFlagView,
    ModeratorLostItemToggleHideView,
    ModeratorReportAssignView,
    ModeratorReportDetailView,
    ModeratorReportEscalateView,
    ModeratorReportListView,
    ModeratorReportReopenView,
    ModeratorReportResolveView,
    ModeratorReviewDetailView,
    ModeratorReviewListView,
    ModeratorReviewToggleDeleteView,
    ModeratorReviewToggleFlagView,
    ModeratorUpdateCategoryView,
    ModeratorUpdateHotspotView,
    ModeratorUserDetailView,
    ModeratorUserListView,
    ModeratorUserToggleBanView,
    ModeratorUserToggleDeleteView,
    ModeratorUserToggleSuspendView,
    ModeratorUserWarningView,
)


urlpatterns = [
    path(
        "moderator/",
        include(
            [
                path("dashboard", ModeratorDashboardStatsView.as_view(), name="moderator-dashboard"),
                
                # LISTING MANAGEMENT
                path('listings', ModeratorListingListView.as_view(), name='moderator-listings'),
                path('listings/<int:listing_id>', ModeratorListingDetailView.as_view(), name='moderator-listing-detail'),
                path('listings/<int:listing_id>/approve', ModeratorListingApproveView.as_view(), name='moderator-listing-approve'),
                path('listings/<int:listing_id>/reject', ModeratorListingRejectView.as_view(), name='moderator-listing-reject'),
                path('listings/<int:listing_id>/toggle-delete', ModeratorListingToggleDeleteView.as_view(), name='moderator-listing-delete'),
                path('listings/<int:listing_id>/toggle-hide', ModeratorListingToggleHideView.as_view(), name='moderator-listing-hide'),
                path('listings/<int:listing_id>/toggle-flag', ModeratorListingToggleFlagView.as_view(), name='moderator-listing-flag'),

                # REVIEWS MANAGEMENT
                path('reviews/', ModeratorReviewListView.as_view(), name='moderator-reviews'),
                path('reviews/<int:review_id>/', ModeratorReviewDetailView.as_view(), name='moderator-review-detail'),
                path('reviews/<int:review_id>/toggle-delete/', ModeratorReviewToggleDeleteView.as_view(), name='moderator-review-toggle-delete'),
                path('reviews/<int:review_id>/toggle-flag/', ModeratorReviewToggleFlagView.as_view(), name='moderator-review-toggle-flag'),


                # USER MANAGEMENT
                path('users/', ModeratorUserListView.as_view(), name='moderator-users'),
                path('users/<int:user_id>/', ModeratorUserDetailView.as_view(), name='moderator-user-detail'),
                path('users/<int:user_id>/warning/', ModeratorUserWarningView.as_view(), name='moderator-user-warning'),
                path('users/<int:user_id>/toggle-suspend/', ModeratorUserToggleSuspendView.as_view(), name='moderator-user-toggle-suspend'),
                path('users/<int:user_id>/toggle-ban/', ModeratorUserToggleBanView.as_view(), name='moderator-user-toggle-ban'),
                path('users/<int:user_id>/toggle-delete/', ModeratorUserToggleDeleteView.as_view(), name='moderator-user-toggle-delete'),
            
                # REPORT MANAGEMENT
                path('reports/', ModeratorReportListView.as_view(), name='moderator-reports'),
                path('reports/<int:report_id>/', ModeratorReportDetailView.as_view(), name='moderator-report-detail'),
                path('reports/<int:report_id>/resolve/', ModeratorReportResolveView.as_view(), name='moderator-report-resolve'),
                path('reports/<int:report_id>/escalate/', ModeratorReportEscalateView.as_view(), name='moderator-report-escalate'),
                path('reports/<int:report_id>/assign/', ModeratorReportAssignView.as_view(), name='moderator-report-assign'),
                path('reports/<int:report_id>/reopen/', ModeratorReportReopenView.as_view(), name='moderator-report-reopen'),

                # CATEGORY MANAGEMENT
                path('categories', ModeratorCategoriesListView.as_view(), name='moderator-categories'),
                path('categories/<int:category_id>', ModeratorCategoryDetailView.as_view(), name='moderator-categories-detail'),
                path('categories/create', ModeratorCreateCategoryView.as_view(), name='moderator-categories-create'),
                path('categories/<int:category_id>/update', ModeratorUpdateCategoryView.as_view(), name='moderator-categories-update'),
                path('users/<int:category_id>/toggle-delete/', ModeratorCategoryToggleDeleteView.as_view(), name='moderator-categories-toggle-delete'),


                # HOTSPOT MANAGEMENT
                path('hotspots', ModeratorHotspotListView.as_view(), name='moderator-hotspots'),
                path('hotspots/<int:hotspot_id>', ModeratorHotspotDetailView.as_view(), name='moderator-hotspots-detail'),
                path('hotspots/create', ModeratorCreateHotspotView.as_view(), name='moderator-hotspots-create'),
                path('hotspots/<int:hotspot_id>/update', ModeratorUpdateHotspotView.as_view(), name='moderator-hotspots-update'),
                path('hotspots/<int:hotspot_id>/toggle-delete/', ModeratorHotspotToggleDeleteView.as_view(), name='moderator-hotspots-toggle-delete'),
            
                # LOSTANDFOUND MANAGEMENT
                path('lost-items', ModeratorLostItemListView.as_view(), name='moderator-lost-items'),
                path('lost-items/<int:lost_item_id>', ModeratorLostItemDetailView.as_view(), name='moderator-lost-item-detail'),
                path('lost-items/<int:lost_item_id>/approve', ModeratorLostItemApproveView.as_view(), name='moderator-lost-item-approve'),
                path('lost-items/<int:lost_item_id>/reject', ModeratorLostItemRejectView.as_view(), name='moderator-lost-item-reject'),
                path('lost-items/<int:lost_item_id>/toggle-delete', ModeratorLostItemToggleDeleteView.as_view(), name='moderator-lost-item-delete'),
                path('lost-items/<int:lost_item_id>/toggle-hide', ModeratorLostItemToggleHideView.as_view(), name='moderator-lost-item-hide'),
                path('lost-items/<int:lost_item_id>/toggle-flag', ModeratorLostItemToggleFlagView.as_view(), name='moderator-lost-item-flag'),

            ]
        )
    )

]