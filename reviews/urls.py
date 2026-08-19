from django.urls import path

from reviews.routes.review import (
    BusinessReviewListAPIView,
    MyReviewListAPIView,
    OwnerReviewListAPIView,
    ReviewCreateAPIView,
    ReviewDetailAPIView,
)
from reviews.routes.review_photo import ReviewPhotoCreateAPIView, ReviewPhotoDeleteAPIView

app_name = "reviews"

urlpatterns = [
    # --- ommaviy ---
    path("businesses/<uuid:business_id>/reviews/", BusinessReviewListAPIView.as_view(), name="business-reviews"),

    # --- mijoz ---
    path("reviews/", ReviewCreateAPIView.as_view(), name="review-create"),
    path("reviews/my/", MyReviewListAPIView.as_view(), name="review-my"),
    path("reviews/<uuid:pk>/", ReviewDetailAPIView.as_view(), name="review-detail"),
    path("reviews/<uuid:review_id>/photos/", ReviewPhotoCreateAPIView.as_view(), name="review-photo-create"),
    path("review-photos/<uuid:pk>/", ReviewPhotoDeleteAPIView.as_view(), name="review-photo-delete"),

    # --- biznes egasi paneli ---
    path("owner/reviews/", OwnerReviewListAPIView.as_view(), name="owner-reviews"),
]
