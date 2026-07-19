from django.urls import path, include

from apps.moderator.views import GetDashboardView


urlpatterns = [
    path(
        "moderator/",
        include(
            [
                path("dashboard", GetDashboardView.as_view(), name="moderator-dashboard"),
            ]
        )
    )

]