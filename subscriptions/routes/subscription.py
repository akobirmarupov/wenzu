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
        from subscriptions.models import SubscriptionPlan, SubscriptionRequest
        from subscriptions.routes.serializers import (
            SubscriptionPlanSerializer,
            SubscriptionRequestSerializer,
        )

        # Barcha tariflar — egasi o'z turini ham, ikkala muddatni ham
        # BITTA ekranda ko'radi. Alohida so'rov qilishning ma'nosi yo'q:
        # bu ro'yxatda to'rtta qator bor, xolos.
        plans = SubscriptionPlanSerializer(
            SubscriptionPlan.objects.all().order_by("business_type", "duration_months"),
            many=True,
        ).data
        telegram = f"@{PlatformSettings.get_solo().admin_telegram_username}"

        # Ochiq ariza — "tugma bosilganmi?" degan savolga javob. Bo'lsa,
        # ekranda tarif kartochkalari o'rniga "ariza ko'rib chiqilmoqda"
        # holati chiqadi.
        pending = (
            SubscriptionRequest.objects.filter(
                business=business, status=SubscriptionRequest.STATUS_PENDING
            )
            .select_related("business", "business__owner", "plan")
            .first()
        )
        pending_data = SubscriptionRequestSerializer(pending).data if pending else None

        if subscription is None:
            # Obuna yo'q = ariza hali tasdiqlanmagan. Bu XATO EMAS, oddiy
            # holat — shuning uchun 200 qaytadi va ekran nima kutilayotganini
            # tushuntiradi.
            return Response({
                "has_subscription": False,
                "status": "awaiting_approval",
                "detail": "Arizangiz administrator tekshiruvida. "
                          "Tasdiqlangach 7 kunlik bepul sinov boshlanadi.",
                "business_type": business.business_type,
                "admin_telegram": telegram,
                "plans": plans,
                "pending_request": pending_data,
            }, status=status.HTTP_200_OK)

        data = SubscriptionSerializer(subscription).data
        data["has_subscription"] = True
        data["admin_telegram"] = telegram
        data["plans"] = plans
        data["pending_request"] = pending_data

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
