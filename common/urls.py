from django.urls import path

from common.routes.health import HealthCheckAPIView
from common.routes.platform_settings import AdminSettingsAPIView, PublicSettingsAPIView

app_name = "common"

urlpatterns = [
    path("health/", HealthCheckAPIView.as_view(), name="health"),
    path("settings/", PublicSettingsAPIView.as_view(), name="public-settings"),
    path("admin/settings/", AdminSettingsAPIView.as_view(), name="admin-settings"),
]
