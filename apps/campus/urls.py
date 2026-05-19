from django.urls import path, include
from .views import *




urlpatterns = [
    path(
        "campus/",
        include(
            [
                path("dashboard", GetDashboardView.as_view(), name="campus-dashboard"),
            ]
        )
    )
]