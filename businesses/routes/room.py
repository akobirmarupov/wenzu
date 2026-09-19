"""Room modeli uchun API'lar — ommaviy ro'yxat va restoran egasining CRUD'i."""

import logging

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from businesses.filters import RoomFilter
from businesses.models import Business, Room
from businesses.routes.serializers import RoomSerializer
from common.pagination import StandardResultsPagination
from common.permissions import HasActiveSubscription, IsOwnerOfBusinessType
from common.services import get_owner_business

logger = logging.getLogger(__name__)


class BusinessRoomListAPIView(APIView):
    """
    GET /api/businesses/{business_id}/rooms/ — ommaviy: biznesning xona/stollari.
    ?room_type=vip&min_capacity=4 bilan filtrlash mumkin.
    """

    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RoomFilter
    queryset = Room.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=RoomSerializer(many=True))
    def get(self, request, business_id):
        if not Business.objects.filter(pk=business_id, is_visible=True).exists():
            raise NotFound("Biznes topilmadi")

        queryset = (
            Room.objects.filter(business_id=business_id)
            .select_related("business")
            .order_by("capacity", "name")
        )
        queryset = RoomFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = RoomSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class OwnerRoomListCreateAPIView(APIView):
    """
    GET/POST /api/owner/rooms/ — restoran egasining "Xonalar" ekrani.
    Faqat restoran egasiga ochiq (to'yxona egasida "Zallar" bo'limi bo'ladi).
    """

    permission_classes = [IsOwnerOfBusinessType, HasActiveSubscription]
    required_business_type = Business.TYPE_RESTAURANT
    filter_backends = [DjangoFilterBackend]
    filterset_class = RoomFilter
    queryset = Room.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=RoomSerializer(many=True))
    def get(self, request):
        business = get_owner_business(request.user)
        queryset = (
            Room.objects.filter(business=business)
            .select_related("business")
            .order_by("capacity", "name")
        )
        queryset = RoomFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = RoomSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(request=RoomSerializer, responses={201: RoomSerializer})
    def post(self, request):
        business = get_owner_business(request.user)
        serializer = RoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            room = serializer.save(business=business)

        logger.info(f"Room created: room_id={room.id}, business_id={business.id}")
        return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)


class OwnerRoomDetailAPIView(APIView):
    """GET/PATCH/DELETE /api/owner/rooms/{pk}/ — bitta xonani boshqarish."""

    permission_classes = [IsOwnerOfBusinessType, HasActiveSubscription]
    required_business_type = Business.TYPE_RESTAURANT

    def get_object(self, request, pk):
        business = get_owner_business(request.user)
        try:
            return Room.objects.select_related("business").get(pk=pk, business=business)
        except Room.DoesNotExist:
            raise NotFound("Xona topilmadi yoki sizga tegishli emas")

    @extend_schema(responses=RoomSerializer)
    def get(self, request, pk):
        return Response(RoomSerializer(self.get_object(request, pk)).data)

    @extend_schema(request=RoomSerializer, responses=RoomSerializer)
    def patch(self, request, pk):
        room = self.get_object(request, pk)
        serializer = RoomSerializer(room, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

        logger.info(f"Room updated: room_id={room.id}, by={request.user.id}")
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        room = self.get_object(request, pk)

        # Kelajakdagi bronlari bor xonani o'chirib bo'lmaydi — mijozning
        # tasdiqlangan broni "yo'qolib" qolmasligi kerak.
        active = room.reservations.filter(status__in=["pending", "confirmed"]).exists()
        if active:
            return Response(
                {"detail": "Bu xonada faol bronlar bor — avval ularni yakunlang yoki bekor qiling."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            room_id = room.id
            room.delete()

        logger.info(f"Room deleted: room_id={room_id}, by={request.user.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)
