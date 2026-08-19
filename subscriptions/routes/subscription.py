"""Subscription modeli uchun API'lar."""

import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import PlatformSettings
from common.pagination import StandardResultsPagination
from common.permissions import IsBusinessRole, IsSuperAdmin
from common.services import get_owner_business
from subscriptions.filters import SubscriptionFilter
from subscriptions.models import Subscription
from subscriptions.routes.serializers import (
    SubscriptionActivateSerializer,
    SubscriptionSerializer,
)
from subscriptions.services import activate_subscription, expire_subscription

logger = logging.getLogger(__name__)


class OwnerSubscriptionAPIView(APIView):
    """
    GET /api/owner/subscription/ — biznes egasining "Obuna" ekrani:
    holat, oylik narx, qolgan kun va admin Telegram'i.
    """

    permission_classes = [IsBusinessRole]

    @extend_schema(responses=SubscriptionSerializer)
    def get(self, request):
        business = get_owner_business(request.user)
        subscription = (
            Subscription.objects.filter(business=business)
            .select_related("business", "business__owner", "plan")
            .prefetch_related("payments")
            .first()
        )
        if subscription is None:
            return Response(
                {"has_subscription": False, "detail": "Obuna topilmadi."},
                status=status.HTTP_200_OK,
            )

        data = SubscriptionSerializer(subscription).data
        data["admin_telegram"] = f"@{PlatformSettings.get_solo().admin_telegram_username}"
        return Response(data, status=status.HTTP_200_OK)


class AdminSubscriptionListAPIView(APIView):
    """GET /api/admin/subscriptions/ — admin panelidagi "Obunalar" jadvali."""

    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SubscriptionFilter
    queryset = Subscription.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=SubscriptionSerializer(many=True))
    def get(self, request):
        queryset = (
            Subscription.objects.select_related("business", "business__owner", "plan", "approved_by")
            .prefetch_related("payments")
            .order_by("-created_at")
        )
        queryset = SubscriptionFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = SubscriptionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminSubscriptionActivateAPIView(APIView):
    """
    POST /api/admin/subscriptions/{pk}/activate/ — "To'lovni tasdiqlash".
    Obuna 30 kunga uzayadi va PaymentLog'ga yozuv tushadi.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(request=SubscriptionActivateSerializer, responses=SubscriptionSerializer)
    def post(self, request, pk):
        try:
            subscription = Subscription.objects.select_related("business", "plan").get(pk=pk)
        except Subscription.DoesNotExist:
            raise NotFound("Obuna topilmadi")

        serializer = SubscriptionActivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = activate_subscription(
            business=subscription.business,
            approved_by=request.user,
            amount=serializer.validated_data.get("amount"),
            note=serializer.validated_data.get("note", ""),
        )
        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_200_OK)


class AdminSubscriptionExpireAPIView(APIView):
    """POST /api/admin/subscriptions/{pk}/expire/ — obunani qo'lda tugatish."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(request=None, responses=SubscriptionSerializer)
    def post(self, request, pk):
        try:
            subscription = Subscription.objects.select_related("business", "plan").get(pk=pk)
        except Subscription.DoesNotExist:
            raise NotFound("Obuna topilmadi")

        subscription = expire_subscription(subscription=subscription)
        logger.info(f"Subscription expired manually: id={subscription.id}, by={request.user.id}")
        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_200_OK)
