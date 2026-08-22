"""BusinessPhoto modeli uchun API'lar — biznes rasm galereyasi."""

import logging

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from businesses.models import Business, BusinessPhoto
from businesses.routes.serializers import BusinessPhotoSerializer
from common.cache import invalidate_business_cache
from common.permissions import HasActiveSubscription, IsBusinessRole
from common.services import get_owner_business

logger = logging.getLogger("businesses")

# Galereya chegarasi. "Xohlagancha" desa ham mutlaqo cheksiz qoldirib
# bo'lmaydi: bitta akkaunt disk va trafikni cheksiz yeb qo'yishi mumkin.
# 40 ta surat — restoranning tashqarisi, yo'lagi, zallari, stollari va
# taomlari uchun mo'l-ko'l.
MAX_PHOTOS_PER_BUSINESS = 40


class BusinessPhotoListAPIView(APIView):
    """GET /api/businesses/{business_id}/photos/ — ommaviy galereya."""

    permission_classes = [AllowAny]

    @extend_schema(responses=BusinessPhotoSerializer(many=True))
    def get(self, request, business_id):
        if not Business.objects.filter(pk=business_id, is_visible=True).exists():
            raise NotFound("Biznes topilmadi")

        photos = BusinessPhoto.objects.filter(business_id=business_id)
        return Response(
            BusinessPhotoSerializer(photos, many=True, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class ShowcasePhotoListAPIView(APIView):
    """
    GET /api/showcase/photos/ — bosh sahifadagi rasm lentasi uchun.

    Butun platformadagi ko'rinadigan joylarning suratlari: muqova rasmi
    va galereyasi birga. Ro'yxat endpointiga galereyani qo'shish o'rniga
    alohida yengil endpoint: katalog sahifalari har safar ortiqcha
    surat ro'yxatini tortib yurmasin.
    """

    permission_classes = [AllowAny]

    @extend_schema(responses={200: None})
    def get(self, request):
        limit = min(int(request.GET.get("limit", 60) or 60), 120)

        photos = []
        covers = (
            Business.objects.filter(is_visible=True)
            .exclude(cover_photo="")
            .values("id", "name", "cover_photo")[:limit]
        )
        for row in covers:
            photos.append({
                "business": str(row["id"]),
                "business_name": row["name"],
                "image": request.build_absolute_uri(
                    f"{settings.MEDIA_URL}{row['cover_photo']}"
                ),
            })

        gallery = (
            BusinessPhoto.objects.filter(business__is_visible=True)
            .select_related("business")
            .values("business_id", "business__name", "image")[:limit]
        )
        for row in gallery:
            photos.append({
                "business": str(row["business_id"]),
                "business_name": row["business__name"],
                "image": request.build_absolute_uri(
                    f"{settings.MEDIA_URL}{row['image']}"
                ),
            })

        return Response(photos[:limit], status=status.HTTP_200_OK)


class OwnerBusinessPhotoListCreateAPIView(APIView):
    """
    GET/POST /api/owner/photos/ — egasining galereyasi.
    Bitta biznesga eng ko'pi bilan 10 ta rasm.
    """

    permission_classes = [IsBusinessRole, HasActiveSubscription]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(responses=BusinessPhotoSerializer(many=True))
    def get(self, request):
        business = get_owner_business(request.user)
        photos = BusinessPhoto.objects.filter(business=business)
        return Response(
            BusinessPhotoSerializer(photos, many=True, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=BusinessPhotoSerializer, responses={201: BusinessPhotoSerializer})
    def post(self, request):
        business = get_owner_business(request.user)

        if BusinessPhoto.objects.filter(business=business).count() >= MAX_PHOTOS_PER_BUSINESS:
            return Response(
                {"detail": f"Galereyaga eng ko'pi bilan {MAX_PHOTOS_PER_BUSINESS} ta rasm qo'shiladi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BusinessPhotoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            photo = serializer.save(business=business)

        invalidate_business_cache()
        logger.info(f"BusinessPhoto created: photo_id={photo.id}, business_id={business.id}")
        return Response(
            BusinessPhotoSerializer(photo, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class OwnerBusinessPhotoDetailAPIView(APIView):
    """PATCH/DELETE /api/owner/photos/{pk}/ — tartibni o'zgartirish yoki o'chirish."""

    permission_classes = [IsBusinessRole, HasActiveSubscription]

    def get_object(self, request, pk):
        business = get_owner_business(request.user)
        try:
            return BusinessPhoto.objects.get(pk=pk, business=business)
        except BusinessPhoto.DoesNotExist:
            raise NotFound("Rasm topilmadi yoki sizga tegishli emas")

    @extend_schema(request=BusinessPhotoSerializer, responses=BusinessPhotoSerializer)
    def patch(self, request, pk):
        photo = self.get_object(request, pk)
        serializer = BusinessPhotoSerializer(
            photo, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

        invalidate_business_cache()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        photo = self.get_object(request, pk)
        with transaction.atomic():
            photo_id = photo.id
            photo.delete()

        invalidate_business_cache()
        logger.info(f"BusinessPhoto deleted: photo_id={photo_id}, by={request.user.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)
