"""ReviewPhoto modeli uchun API'lar — sharhga biriktirilgan rasmlar."""

import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from reviews.models import Review, ReviewPhoto
from reviews.routes.serializers import ReviewPhotoSerializer

logger = logging.getLogger(__name__)

MAX_PHOTOS_PER_REVIEW = 5


class ReviewPhotoCreateAPIView(APIView):
    """
    POST /api/reviews/{review_id}/photos/ — sharhga rasm qo'shish.
    Bitta sharhga eng ko'pi bilan 5 ta rasm.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=ReviewPhotoSerializer, responses={201: ReviewPhotoSerializer})
    def post(self, request, review_id):
        try:
            review = Review.objects.get(pk=review_id)
        except Review.DoesNotExist:
            raise NotFound("Sharh topilmadi")

        if review.user_id != request.user.id:
            return Response(
                {"detail": "Bu sharhga rasm qo'sha olmaysiz."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if review.photos.count() >= MAX_PHOTOS_PER_REVIEW:
            return Response(
                {"detail": f"Bitta sharhga eng ko'pi bilan {MAX_PHOTOS_PER_REVIEW} ta rasm qo'shiladi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReviewPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            photo = serializer.save(review=review)

        logger.info(f"ReviewPhoto created: photo_id={photo.id}, review_id={review.id}")
        return Response(ReviewPhotoSerializer(photo).data, status=status.HTTP_201_CREATED)


class ReviewPhotoDeleteAPIView(APIView):
    """DELETE /api/review-photos/{pk}/ — rasmni o'chirish (faqat sharh egasi)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        try:
            photo = ReviewPhoto.objects.select_related("review").get(pk=pk)
        except ReviewPhoto.DoesNotExist:
            raise NotFound("Rasm topilmadi")

        if photo.review.user_id != request.user.id and not request.user.is_staff:
            return Response(
                {"detail": "Bu rasmni o'chira olmaysiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            photo_id = photo.id
            photo.delete()

        logger.info(f"ReviewPhoto deleted: photo_id={photo_id}, by={request.user.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)
