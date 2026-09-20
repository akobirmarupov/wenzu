from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from account.routes.user import (
    AdminUserDetailAPIView,
    AdminUserListAPIView,
    AvatarAPIView,
    GoogleAuthAPIView,
    GoogleCallbackAPIView,
    GoogleStartAPIView,
    LoginAPIView,
    LogoutAPIView,
    MeAPIView,
)

app_name = "account"

urlpatterns = [
    path("auth/google/start/", GoogleStartAPIView.as_view(), name="google-start"),
    path("auth/google/callback/", GoogleCallbackAPIView.as_view(), name="google-callback"),

    path("auth/google/", GoogleAuthAPIView.as_view(), name="google-auth"),

    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("auth/me/", MeAPIView.as_view(), name="me"),
    path("auth/me/avatar/", AvatarAPIView.as_view(), name="me-avatar"),

    # --- admin panel ---
    path("admin/users/", AdminUserListAPIView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", AdminUserDetailAPIView.as_view(), name="admin-user-detail"),
]
