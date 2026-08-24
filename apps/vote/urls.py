from django.urls import path, include

from apps.vote.views import CategoryCreateView, CategoryToggleView, CategoryUpdateView


urlpatterns = [
    path("categories/", include([
        path("create", CategoryCreateView.as_view(), name="create_category"),
        path('update/<int:category_id>', CategoryUpdateView.as_view(), name='category-update'),
        path('toggle/<int:category_id>', CategoryToggleView.as_view(), name='category-toggle'),

    ])),
]