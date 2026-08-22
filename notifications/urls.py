from django.urls import path

from notifications.routes.notification import (
    NotificationListAPIView,
    NotificationReadAllAPIView,
    NotificationReadAPIView,
    NotificationUnreadCountAPIView,
)

app_name = "notifications"

urlpatterns = [
    path("notifications/", NotificationListAPIView.as_view(), name="list"),
    path("notifications/unread-count/", NotificationUnreadCountAPIView.as_view(), name="unread-count"),
    path("notifications/read-all/", NotificationReadAllAPIView.as_view(), name="read-all"),
    path("notifications/<uuid:pk>/read/", NotificationReadAPIView.as_view(), name="read"),
]
