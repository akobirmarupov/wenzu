from django.urls import path

from common.routes.feedback import (
    AdminFeedbackDetailAPIView,
    AdminFeedbackListAPIView,
    FeedbackCreateAPIView,
)
from common.routes.health import HealthCheckAPIView
from common.routes.platform_settings import AdminSettingsAPIView, PublicSettingsAPIView

app_name = "common"

urlpatterns = [
    path("health/", HealthCheckAPIView.as_view(), name="health"),
    path("settings/", PublicSettingsAPIView.as_view(), name="public-settings"),
    path("admin/settings/", AdminSettingsAPIView.as_view(), name="admin-settings"),

    # Takliflar: yuborish hammaga ochiq, o'qish faqat administratorga.
    path("feedback/", FeedbackCreateAPIView.as_view(), name="feedback-create"),
    path("admin/feedback/", AdminFeedbackListAPIView.as_view(), name="admin-feedback"),
    path("admin/feedback/<uuid:pk>/", AdminFeedbackDetailAPIView.as_view(), name="admin-feedback-detail"),
]
