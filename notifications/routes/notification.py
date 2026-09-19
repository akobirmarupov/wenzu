"""Notification modeli uchun API'lar."""

import logging

from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardResultsPagination
from notifications.filters import NotificationFilter
from notifications.models import Notification
from notifications.routes.serializers import NotificationSerializer, UnreadCountSerializer

logger = logging.getLogger("notifications")


class NotificationListAPIView(APIView):
    """
    GET /api/notifications/ — o'z bildirishnomalarim.

    Filtrlar: `?is_read=false`, `?kind=reservation`.
    Faqat o'z yozuvlari ko'rinadi — queryset boshidanoq `request.user`
    bo'yicha cheklangan, ID taxmin qilib boshqanikini ochib bo'lmaydi.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = NotificationFilter
    queryset = Notification.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=NotificationSerializer(many=True))
    def get(self, request):
        queryset = Notification.objects.for_user(request.user)
        queryset = NotificationFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = NotificationSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class NotificationUnreadCountAPIView(APIView):
    """
    GET /api/notifications/unread-count/ — qo'ng'iroqcha ustidagi raqam.

    Alohida endpoint: to'liq ro'yxatni tortmasdan faqat sonni olish
    uchun. Har sahifa yuklanganda chaqiriladi, shuning uchun yengil
    bo'lishi shart — bu bitta COUNT so'rovi, indeksdan o'qiladi.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UnreadCountSerializer)
    def get(self, request):
        unread = Notification.objects.for_user(request.user).unread().count()
        return Response({"unread": unread}, status=status.HTTP_200_OK)


class NotificationReadAPIView(APIView):
    """PATCH /api/notifications/{pk}/read/ — bittasini o'qilgan deb belgilash."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=NotificationSerializer)
    def patch(self, request, pk):
        try:
            notification = Notification.objects.for_user(request.user).get(pk=pk)
        except Notification.DoesNotExist:
            raise NotFound("Bildirishnoma topilmadi")

        with transaction.atomic():
            notification.mark_read()

        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)


class NotificationReadAllAPIView(APIView):
    """
    POST /api/notifications/read-all/ — hammasini o'qilgan deb belgilash.

    Bitta UPDATE bilan: yuzta yozuvni bittalab saqlash o'rniga.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=UnreadCountSerializer)
    def post(self, request):
        with transaction.atomic():
            updated = (
                Notification.objects.for_user(request.user)
                .unread()
                .update(is_read=True, read_at=timezone.now())
            )
        logger.info(f"Notifications marked read: user_id={request.user.pk}, count={updated}")
        return Response({"unread": 0}, status=status.HTTP_200_OK)
