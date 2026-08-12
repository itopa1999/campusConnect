from django.contrib import admin
from django.urls import path, include
from backend.health import health_check
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

from backend.schema import (
    BothHttpAndHttpsSchemaGenerator,
    swagger_protect,
)


# ============================================================
# API V1 URLS
# ============================================================

v1_urlpatterns = [
    path(
        "campus/api/",
        include("apps.campus.urls"),
    ),
    path(
        "user/api/",
        include("apps.users.urls"),
    ),
    path(
        "moderator/api/",
        include("apps.moderator.urls"),
    ),
]


# ============================================================
# API V2 URLS
# ============================================================

v2_urlpatterns = [
    path(
        "campus/api/",
        include("apps.campus.v2_urls"),
    ),
    # path(
    #     "user/api/",
    #     include("apps.users.v2_urls"),
    # ),
    # path(
    #     "moderator/api/",
    #     include("apps.moderator.v2_urls"),
    # ),
]


# ============================================================
# SWAGGER V1
# ============================================================

schema_view = get_schema_view(
    openapi.Info(
        title="CampusConnect Backend API",
        default_version="v1",
        description="API description for CampusConnect Backend",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(
            email="contact@snippets.local"
        ),
        license=openapi.License(
            name="BSD License"
        ),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=[],
    generator_class=BothHttpAndHttpsSchemaGenerator,

    # IMPORTANT:
    # Include the /v1/ prefix in the generated Swagger schema.
    patterns=[
        path(
            "v1/",
            include(v1_urlpatterns),
        ),
    ],
)


# ============================================================
# SWAGGER V2
# ============================================================

v2_schema_view = get_schema_view(
    openapi.Info(
        title="CampusConnect Backend API",
        default_version="v2",
        description="API description for CampusConnect Backend - V2",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(
            email="contact@snippets.local"
        ),
        license=openapi.License(
            name="BSD License"
        ),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=[],
    generator_class=BothHttpAndHttpsSchemaGenerator,

    # IMPORTANT:
    # Include the /v2/ prefix in the generated Swagger schema.
    patterns=[
        path(
            "v2/",
            include(v2_urlpatterns),
        ),
    ],
)


# ============================================================
# MAIN URL CONFIGURATION
# ============================================================

urlpatterns = [

    # --------------------------------------------------------
    # Health Check
    # --------------------------------------------------------

    path(
        "health/",
        health_check,
    ),

    # --------------------------------------------------------
    # Admin
    # --------------------------------------------------------

    path(
        "",
        RedirectView.as_view(
            url="/backdoor/",
            permanent=False,
        ),
    ),

    path(
        "backdoor/",
        admin.site.urls,
    ),

    # --------------------------------------------------------
    # API V1
    # --------------------------------------------------------

    path(
        "v1/",
        include(v1_urlpatterns),
    ),

    # --------------------------------------------------------
    # API V2
    # --------------------------------------------------------

    path(
        "v2/",
        include(v2_urlpatterns),
    ),

    # --------------------------------------------------------
    # API DOCUMENTATION
    # --------------------------------------------------------

    path(
        "doc/",
        include(
            [

                # ====================================================
                # V1 SWAGGER UI
                # ====================================================

                path(
                    "swagger/",
                    swagger_protect(
                        schema_view.with_ui(
                            "swagger",
                            cache_timeout=0,
                        )
                    ),
                    name="schema-swagger-ui",
                ),

                # ====================================================
                # V1 SWAGGER JSON
                # ====================================================

                path(
                    "swagger.json",
                    swagger_protect(
                        schema_view.without_ui(
                            cache_timeout=0,
                        )
                    ),
                    name="schema-json",
                ),

                # ====================================================
                # V1 REDOC
                # ====================================================

                path(
                    "redoc/",
                    swagger_protect(
                        schema_view.with_ui(
                            "redoc",
                            cache_timeout=0,
                        )
                    ),
                    name="schema-redoc",
                ),

                # ====================================================
                # V2 SWAGGER UI
                # ====================================================

                path(
                    "swagger/v2/",
                    swagger_protect(
                        v2_schema_view.with_ui(
                            "swagger",
                            cache_timeout=0,
                        )
                    ),
                    name="schema-swagger-v2-ui",
                ),

                # ====================================================
                # V2 SWAGGER JSON
                # ====================================================

                path(
                    "swagger/v2.json",
                    swagger_protect(
                        v2_schema_view.without_ui(
                            cache_timeout=0,
                        )
                    ),
                    name="schema-swagger-v2-json",
                ),

                # ====================================================
                # V2 REDOC
                # ====================================================

                path(
                    "redoc/v2/",
                    swagger_protect(
                        v2_schema_view.with_ui(
                            "redoc",
                            cache_timeout=0,
                        )
                    ),
                    name="schema-redoc-v2",
                ),
            ]
        ),
    ),
]


# ============================================================
# STATIC / MEDIA
# ============================================================

if not settings.DEBUG:

    # Production
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT,
    )

else:

    # Development
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )