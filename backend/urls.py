from django.contrib import admin
from django.urls import path, include
from backend.health import health_check
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

from backend.schema import BothHttpAndHttpsSchemaGenerator, swagger_protect

  
schema_view = get_schema_view(
    openapi.Info(
        title="CampusConnect Backend API",
        default_version="v1",
        description="API description for CampusConnect Backend",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=[],
    generator_class=BothHttpAndHttpsSchemaGenerator,
)

urlpatterns = [

    path("health/", health_check),
    
    path('', RedirectView.as_view(url='/backdoor/', permanent=False)),
    path('backdoor/', admin.site.urls),

    path('campus/api/', include("apps.campus.urls")),
    path('user/api/', include("apps.users.urls")),
    path('moderator/api/', include("apps.moderator.urls")),
    
    path(
        "doc/",
        include(
            [
                path(
                    "swagger/",
                    swagger_protect(schema_view.with_ui("swagger", cache_timeout=0)),
                    name="schema-swagger-ui",
                ),
                path(
                    "swagger.json",
                    swagger_protect(schema_view.without_ui(cache_timeout=0)),
                    name="schema-json",
                ),
                path(
                    "redoc/",
                    swagger_protect(schema_view.with_ui("redoc", cache_timeout=0)),
                    name="schema-redoc",
                ),
            ]
        ),
    ),
] 

# Serve static and media files based on DEBUG
if not settings.DEBUG:  # Production / DEBUG = False
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:  # Development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
