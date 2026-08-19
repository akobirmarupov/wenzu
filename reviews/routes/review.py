"""Review modeli uchun API'lar."""

import logging

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from businesses.models import Business
from common.pagination import ReviewsPagination, StandardResultsPagination
from common.permissions import IsBusinessRole
from common.services import get_owner_business
from common.throttles import ReviewCreateThrottle
from reviews.filters import ReviewFilter
from reviews.models import Review
from reviews.routes.serializers import ReviewCreateSerializer, ReviewSerializer

logger = logging.getLogger(__name__)


class BusinessReviewListAPIView(APIView):
    """GET /api/businesses/{business_id}/reviews/ — ommaviy sharhlar ro'yxati."""

    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReviewFilter
    queryset = Review.objects.none()
    pagination_class = ReviewsPagination

    @extend_schema(responses=ReviewSerializer(many=True))
    def get(self, request, business_id):
        if not Business.objects.filter(pk=business_id, is_visible=True).exists():
            raise NotFound("Biznes topilmadi")

        queryset = (
            Review.objects.filter(business_id=business_id)
            .select_related("user", "business")
            .prefetch_related("photos")
            .order_by("-created_at")
        )
        queryset = ReviewFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ReviewSerializer(page, many=True).data)


class ReviewCreateAPIView(APIView):
    """POST /api/reviews/ — sharh qoldirish (faqat yakunlangan bron uchun)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ReviewCreateThrottle]

    @extend_schema(request=ReviewCreateSerializer, responses={201: ReviewSerializer})
    def post(self, request):
        serializer = ReviewCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        reservation = serializer.validated_data["reservation"]

        with transaction.atomic():
            review = serializer.save(user=request.user, business=reservation.business)

        logger.info(
            f"Review created: review_id={review.id}, user_id={request.user.id}, "
            f"business_id={review.business_id}, rating={review.rating}"
        )
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class MyReviewListAPIView(APIView):
    """GET /api/reviews/my/ — foydalanuvchining o'z sharhlari."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination
    queryset = Review.objects.none()

    @extend_schema(responses=ReviewSerializer(many=True))
    def get(self, request):
        queryset = (
            Review.objects.filter(user=request.user)
            .select_related("user", "business")
            .prefetch_related("photos")
            .order_by("-created_at")
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ReviewSerializer(page, many=True).data)


class ReviewDetailAPIView(APIView):
    """GET/PATCH/DELETE /api/reviews/{pk}/ — faqat sharh egasi tahrirlay/o'chira oladi."""

    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Review.objects.select_related("user", "business").prefetch_related("photos").get(pk=pk)
        except Review.DoesNotExist:
            raise NotFound("Sharh topilmadi")

    @extend_schema(responses=ReviewSerializer)
    def get(self, request, pk):
        return Response(ReviewSerializer(self.get_object(pk)).data)

    @extend_schema(request=ReviewCreateSerializer, responses=ReviewSerializer)
    def patch(self, request, pk):
        review = self.get_object(pk)
        if review.user_id != request.user.id:
            return Response(
                {"detail": "Bu sharhni tahrirlay olmaysiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        allowed = {k: v for k, v in request.data.items() if k in {"rating", "comment"}}
        with transaction.atomic():
            for field, value in allowed.items():
                setattr(review, field, value)
            if allowed:
                review.full_clean(exclude=["user", "business", "reservation"])
                review.save(update_fields=list(allowed.keys()))

        logger.info(f"Review updated: review_id={review.id}, by={request.user.id}")
        return Response(ReviewSerializer(review).data, status=status.HTTP_200_OK)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        review = self.get_object(pk)
        if review.user_id != request.user.id and not request.user.is_staff:
            return Response(
                {"detail": "Bu sharhni o'chira olmaysiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            review_id = review.id
            review.delete()

        logger.info(f"Review deleted: review_id={review_id}, by={request.user.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)


class OwnerReviewListAPIView(APIView):
    """GET /api/owner/reviews/ — biznes egasining "Sharhlar" ekrani."""

    permission_classes = [IsBusinessRole]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReviewFilter
    queryset = Review.objects.none()
    pagination_class = ReviewsPagination

    @extend_schema(responses=ReviewSerializer(many=True))
    def get(self, request):
        business = get_owner_business(request.user)
        queryset = (
            Review.objects.filter(business=business)
            .select_related("user", "business")
            .prefetch_related("photos")
            .order_by("-created_at")
        )
        queryset = ReviewFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ReviewSerializer(page, many=True).data)
