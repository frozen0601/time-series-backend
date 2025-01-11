from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from rest_framework import routers
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView

from metrics.views import MetricTypeViewSet, SessionViewSet, TimeSeriesDataViewSet

router = routers.DefaultRouter()
router.register(r"metrictypes", MetricTypeViewSet, basename="metrictypes")
router.register(r"timeseries", TimeSeriesDataViewSet, basename="timeseries")
router.register(r"sessions", SessionViewSet, basename="sessions")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    # path("api/sessions/", SessionViewSet.as_view({"post": "create"}), name="sessions"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]


if settings.DEBUG:  # pragma: no cover
    # Django debug toolbar
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
