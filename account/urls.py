from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from account.routes.user import (
    AdminUserDetailAPIView,
    AdminUserListAPIView,
    AvatarAPIView,
    LoginAPIView,
    LogoutAPIView,
    MeAPIView,
    RegisterAPIView,
    SendCodeAPIView,
    VerifyPhoneAPIView,
)

app_name = "account"

urlpatterns = [
    # --- auth ---
    path("auth/register/", RegisterAPIView.as_view(), name="register"),
    path("auth/send-code/", SendCodeAPIView.as_view(), name="send-code"),
    path("auth/verify-phone/", VerifyPhoneAPIView.as_view(), name="verify-phone"),
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("auth/me/", MeAPIView.as_view(), name="me"),
    path("auth/me/avatar/", AvatarAPIView.as_view(), name="me-avatar"),

    # --- admin panel ---
    path("admin/users/", AdminUserListAPIView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", AdminUserDetailAPIView.as_view(), name="admin-user-detail"),
]
