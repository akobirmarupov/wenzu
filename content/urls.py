from django.urls import path

from content.routes.banner import (
    AdminBannerDetailAPIView,
    AdminBannerListCreateAPIView,
    BannerListAPIView,
)
from content.routes.news import (
    AdminNewsDetailAPIView,
    AdminNewsListCreateAPIView,
    NewsDetailAPIView,
    NewsListAPIView,
)

app_name = "content"

urlpatterns = [
    # --- ommaviy ---
    path("banners/", BannerListAPIView.as_view(), name="banner-list"),
    path("news/", NewsListAPIView.as_view(), name="news-list"),
    path("news/<uuid:pk>/", NewsDetailAPIView.as_view(), name="news-detail"),

    # --- admin ---
    path("admin/banners/", AdminBannerListCreateAPIView.as_view(), name="admin-banner-list"),
    path("admin/banners/<uuid:pk>/", AdminBannerDetailAPIView.as_view(), name="admin-banner-detail"),
    path("admin/news/", AdminNewsListCreateAPIView.as_view(), name="admin-news-list"),
    path("admin/news/<uuid:pk>/", AdminNewsDetailAPIView.as_view(), name="admin-news-detail"),
]
