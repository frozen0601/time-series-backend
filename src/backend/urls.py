from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from rest_framework import routers
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView


from subway.views import get_status, get_uptime

router = routers.DefaultRouter()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/subway/status/", get_status, name="subway-status"),
    path("api/subway/uptime/", get_uptime, name="subway-uptime"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("", include(router.urls)),
]


if settings.DEBUG:  # pragma: no cover
    # Django debug toolbar
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
