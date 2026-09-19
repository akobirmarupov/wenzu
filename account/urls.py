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
    # --- auth ---
    # Ro'yxatdan o'tish VA kirish — bitta manzil. Google hisob bo'lsa
    # kiritadi, bo'lmasa yaratadi; foydalanuvchi uchun farqi yo'q.
    # ASOSIY YO'L — qayta yo'naltirish oqimi. Brauzer Google'ga
    # o'tadi va `code` bilan qaytadi; popup ishlatilmaydi.
    path("auth/google/start/", GoogleStartAPIView.as_view(), name="google-start"),
    path("auth/google/callback/", GoogleCallbackAPIView.as_view(), name="google-callback"),

    # `id_token` ni to'g'ridan-to'g'ri qabul qiladigan endpoint.
    # Veb-saytda ishlatilmaydi; kelajakdagi mobil ilova uchun
    # qoldirilgan — u Google SDK'sidan tokenni o'zi oladi.
    path("auth/google/", GoogleAuthAPIView.as_view(), name="google-auth"),

    # Parol bilan kirish — faqat ESKI hisoblar va administrator uchun.
    # Yangi ro'yxat bu yerdan o'tmaydi.
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("auth/me/", MeAPIView.as_view(), name="me"),
    path("auth/me/avatar/", AvatarAPIView.as_view(), name="me-avatar"),

    # --- admin panel ---
    path("admin/users/", AdminUserListAPIView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", AdminUserDetailAPIView.as_view(), name="admin-user-detail"),
]
