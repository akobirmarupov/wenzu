"""Availability modeli uchun API'lar — bo'sh vaqtlar jadvali."""

import datetime
import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from businesses.models import Business, Room
from common.pagination import StandardResultsPagination
from common.permissions import HasActiveSubscription, IsBusinessRole
from common.services import get_owner_business
from reservations.filters import AvailabilityFilter
from reservations.models import Availability, Reservation
from reservations.routes.serializers import (
    AvailabilitySerializer,
    BusyRangeSerializer,
    GenerateAvailabilitySerializer,
)

logger = logging.getLogger(__name__)


class BusinessAvailabilityAPIView(APIView):
    """
    GET /api/businesses/{business_id}/availability/?date=YYYY-MM-DD

    To'yxona uchun: shu kun bo'shmi yoki bandmi.
    Restoran uchun: har bir xonaning shu kundagi ish oralig'i.
    """

    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AvailabilityFilter
    queryset = Availability.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(
        responses=AvailabilitySerializer(many=True),
        parameters=[
            OpenApiParameter("date", str, description="YYYY-MM-DD"),
            OpenApiParameter("date_from", str),
            OpenApiParameter("date_to", str),
            OpenApiParameter("room", str, description="Xona UUID (restoran uchun)"),
        ],
    )
    def get(self, request, business_id):
        if not Business.objects.filter(pk=business_id, is_visible=True).exists():
            raise NotFound("Biznes topilmadi")

        queryset = (
            Availability.objects.filter(business_id=business_id)
            .select_related("room")
            .order_by("date", "start_time")
        )
        # Sana berilmasa, o'tib ketgan kunlarni ko'rsatishning ma'nosi yo'q.
        if not request.GET.get("date") and not request.GET.get("date_from"):
            queryset = queryset.filter(date__gte=timezone.localdate())

        queryset = AvailabilityFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(AvailabilitySerializer(page, many=True).data)


class RoomBusyHoursAPIView(APIView):
    """
    GET /api/rooms/{room_id}/busy-hours/?date=YYYY-MM-DD

    Restoran bron ekranidagi soat gridini bo'yash uchun: shu xonaning shu
    kundagi ish oralig'i va allaqachon band qilingan soat oraliqlari.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        responses=None,
        parameters=[OpenApiParameter("date", str, description="YYYY-MM-DD", required=True)],
    )
    def get(self, request, room_id):
        date = request.GET.get("date")
        if not date:
            return Response(
                {"detail": "`date` parametri majburiy (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            room = Room.objects.select_related("business").get(pk=room_id)
        except Room.DoesNotExist:
            raise NotFound("Xona topilmadi")

        availability = Availability.objects.filter(room=room, date=date).first()
        busy = (
            Reservation.objects.filter(
                room=room,
                availability__date=date,
                status__in=["pending", "confirmed"],
            )
            .exclude(start_time__isnull=True)
            .values("start_time", "end_time")
            .order_by("start_time")
        )

        return Response({
            "room_id": str(room.id),
            "room_name": room.name,
            "capacity": room.capacity,
            "deposit_amount": room.deposit_amount,
            "date": date,
            "is_open": availability is not None,
            "open_time": availability.start_time if availability else None,
            "close_time": availability.end_time if availability else None,
            "busy_ranges": BusyRangeSerializer(busy, many=True).data,
        }, status=status.HTTP_200_OK)


class HallBusyDatesAPIView(APIView):
    """
    GET /api/halls/{hall_id}/busy-dates/?date_from=&date_to=

    To'yxonada bir kunda faqat bitta to'y bo'lgani uchun, mijozga kalendarda
    band kunlarni ko'rsatish kifoya.
    """

    permission_classes = [AllowAny]

    @extend_schema(responses=None)
    def get(self, request, hall_id):
        from businesses.models import Hall

        try:
            hall = Hall.objects.select_related("business").get(pk=hall_id)
        except Hall.DoesNotExist:
            raise NotFound("Zal topilmadi")

        queryset = Reservation.objects.filter(
            hall=hall, status__in=["pending", "confirmed"]
        ).select_related("availability")

        date_from = request.GET.get("date_from") or str(timezone.localdate())
        queryset = queryset.filter(availability__date__gte=date_from)
        if request.GET.get("date_to"):
            queryset = queryset.filter(availability__date__lte=request.GET["date_to"])

        busy_dates = list(
            queryset.values_list("availability__date", flat=True).order_by("availability__date")
        )

        return Response({
            "hall_id": str(hall.id),
            "hall_name": hall.name,
            "capacity": hall.people,
            "deposit_amount": hall.deposit_amount,
            "all_price": hall.all_price,
            "busy_dates": [str(d) for d in busy_dates if d],
        }, status=status.HTTP_200_OK)


class OwnerAvailabilityListAPIView(APIView):
    """GET /api/owner/availability/ — biznes egasining bo'sh vaqtlar jadvali."""

    permission_classes = [IsBusinessRole, HasActiveSubscription]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AvailabilityFilter
    queryset = Availability.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=AvailabilitySerializer(many=True))
    def get(self, request):
        business = get_owner_business(request.user)
        queryset = (
            Availability.objects.filter(business=business)
            .select_related("room")
            .order_by("date", "start_time")
        )
        queryset = AvailabilityFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(AvailabilitySerializer(page, many=True).data)


class OwnerAvailabilityGenerateAPIView(APIView):
    """
    POST /api/owner/availability/generate/ — tanlangan oylarning BARCHA
    kunlari uchun bir vaqtda bo'sh vaqt yozuvlarini yaratadi.

    Allaqachon mavjud kunlar qayta yozilmaydi — band qilingan kun
    tasodifan bo'shatib yuborilmasligi uchun.
    """

    permission_classes = [IsBusinessRole, HasActiveSubscription]

    @extend_schema(request=GenerateAvailabilitySerializer, responses={201: None})
    def post(self, request):
        business = get_owner_business(request.user)
        serializer = GenerateAvailabilitySerializer(
            data=request.data, context={"business": business}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        room = None
        if data.get("room"):
            room = Room.objects.get(pk=data["room"], business=business)

        months = [datetime.date(data["year"], m, 1) for m in sorted(set(data["months"]))]

        try:
            with transaction.atomic():
                created, skipped = Availability.generate_for_months(
                    business=business,
                    room=room,
                    start_time=data["start_time"],
                    end_time=data["end_time"],
                    months=months,
                )
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(
            f"Availability generated: business_id={business.id}, room_id={room.id if room else None}, "
            f"created={created}, skipped={skipped}"
        )
        return Response({
            "created": created,
            "skipped": skipped,
            "detail": f"{created} ta kun uchun bo'sh vaqt yaratildi, {skipped} ta kun allaqachon mavjud edi.",
        }, status=status.HTTP_201_CREATED)


class OwnerAvailabilityDetailAPIView(APIView):
    """PATCH/DELETE /api/owner/availability/{pk}/ — bitta kunni tahrirlash/o'chirish."""

    permission_classes = [IsBusinessRole, HasActiveSubscription]

    def get_object(self, request, pk):
        business = get_owner_business(request.user)
        try:
            return Availability.objects.select_related("room").get(pk=pk, business=business)
        except Availability.DoesNotExist:
            raise NotFound("Bo'sh vaqt yozuvi topilmadi yoki sizga tegishli emas")

    @extend_schema(request=AvailabilitySerializer, responses=AvailabilitySerializer)
    def patch(self, request, pk):
        availability = self.get_object(request, pk)
        serializer = AvailabilitySerializer(availability, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        availability = self.get_object(request, pk)
        if availability.reservations.filter(status__in=["pending", "confirmed"]).exists():
            return Response(
                {"detail": "Bu kunda faol bronlar bor — o'chirib bo'lmaydi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            availability_id = availability.id
            availability.delete()

        logger.info(f"Availability deleted: id={availability_id}, by={request.user.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)
