"""
SubscriptionRequest modeli uchun API'lar — obunani uzaytirish oqimi.

Oqim biznes ochish bilan ATAYLAB bir xil, chunki egasi unga o'rgangan:

    egasi rejani tanlaydi  →  ariza yuboradi  →  Telegram orqali to'laydi
    →  admin arizani tasdiqlaydi  →  obuna reja muddatiga uzayadi

To'lov platformada emas, Telegram orqali qo'lda amalga oshadi — shuning
uchun bu yerda pul emas, ARIZA aylanadi.
"""

import logging

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardResultsPagination
from common.permissions import HasContactPhone, IsBusinessRole, IsSuperAdmin
from common.services import get_owner_business
from subscriptions.models import SubscriptionPlan, SubscriptionRequest
from subscriptions.routes.serializers import (
    SubscriptionRequestCreateSerializer,
    SubscriptionRequestSerializer,
)
from subscriptions.services import approve_renewal, reject_renewal, request_renewal

logger = logging.getLogger("subscriptions")


class OwnerSubscriptionRequestAPIView(APIView):
    """
    GET/POST /api/owner/subscription/requests/ — o'z obuna arizalarim.

    GET  — tarix: qachon, qaysi muddatga, qanday holatda.
    POST — yangi ariza. Ochiq ariza allaqachon bo'lsa YANGISI
           yaratilmaydi, mavjudi qaytariladi (200) — egasi tugmani ikki
           marta bossa adminga ikkita bir xil ariza ketmasin.

    `HasActiveSubscription` ATAYLAB QO'YILMAGAN: obunasi tugagan egasi
    ham ariza yubora olishi shart, aks holda uzaytirishning iloji
    bo'lmasdi.
    """

    # Raqamsiz obuna so'rovi yuborilmaydi: administrator to'lovni
    # tasdiqlash uchun egasi bilan bog'lanadi.
    permission_classes = [IsBusinessRole, HasContactPhone]
    phone_message = (
        "Obuna so'rovi uchun aloqa raqamingizni kiriting — "
        "administrator to'lovni siz bilan kelishadi."
    )
    pagination_class = StandardResultsPagination

    @extend_schema(responses=SubscriptionRequestSerializer(many=True))
    def get(self, request):
        business = get_owner_business(request.user)
        queryset = (
            SubscriptionRequest.objects.filter(business=business)
            .select_related("business", "business__owner", "plan")
            .order_by("-created_at")
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = SubscriptionRequestSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=SubscriptionRequestCreateSerializer,
        responses={201: SubscriptionRequestSerializer, 200: SubscriptionRequestSerializer},
    )
    def post(self, request):
        business = get_owner_business(request.user)

        serializer = SubscriptionRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            plan = SubscriptionPlan.objects.get(pk=serializer.validated_data["plan"])
        except SubscriptionPlan.DoesNotExist:
            raise ValidationError({"plan": "Bunday tarif rejasi topilmadi."})

        try:
            renewal, created = request_renewal(
                business=business, plan=plan, note=serializer.validated_data.get("note", "")
            )
        except ValueError as error:
            raise ValidationError({"plan": str(error)})

        return Response(
            SubscriptionRequestSerializer(renewal).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AdminSubscriptionRequestListAPIView(APIView):
    """
    GET /api/admin/subscription-requests/ — kelgan obuna arizalari.

    Standart ko'rinish — kutilayotganlar, chunki admin bu ekranga aynan
    shular uchun kiradi. Butun tarix kerak bo'lsa `?status=` bo'sh
    qoldiriladi yoki boshqa holat beriladi.
    """

    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    queryset = SubscriptionRequest.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(
        responses=SubscriptionRequestSerializer(many=True),
        parameters=[
            OpenApiParameter("status", str, description="pending_payment | approved | rejected"),
            OpenApiParameter("business", str, description="Biznes ID'si"),
        ],
    )
    def get(self, request):
        queryset = SubscriptionRequest.objects.select_related(
            "business", "business__owner", "plan"
        ).order_by("-created_at")

        state = request.GET.get("status")
        if state:
            queryset = queryset.filter(status=state)
        business = request.GET.get("business")
        if business:
            queryset = queryset.filter(business_id=business)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = SubscriptionRequestSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class AdminSubscriptionRequestApproveAPIView(APIView):
    """
    POST /api/admin/subscription-requests/{pk}/approve/ — to'lovni tasdiqlash.

    Obuna reja muddatiga uzayadi va to'lov `PaymentLog`ga yoziladi.
    Muddat mavjud tugash sanasidan boshlab qo'shiladi — erta to'lagan
    odam kunini yo'qotmaydi.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(request=None, responses=SubscriptionRequestSerializer)
    def post(self, request, pk):
        renewal = _get_request(pk)

        try:
            with transaction.atomic():
                approve_renewal(
                    request=renewal,
                    approved_by=request.user,
                    amount=request.data.get("amount"),
                    note=request.data.get("note", ""),
                )
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SubscriptionRequestSerializer(renewal).data, status=status.HTTP_200_OK)


class AdminSubscriptionRequestRejectAPIView(APIView):
    """POST /api/admin/subscription-requests/{pk}/reject/ — arizani rad etish."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(request=None, responses=SubscriptionRequestSerializer)
    def post(self, request, pk):
        renewal = _get_request(pk)

        try:
            with transaction.atomic():
                reject_renewal(
                    request=renewal,
                    rejected_by=request.user,
                    note=request.data.get("note", ""),
                )
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SubscriptionRequestSerializer(renewal).data, status=status.HTTP_200_OK)


def _get_request(pk):
    try:
        return SubscriptionRequest.objects.select_related(
            "business", "business__owner", "plan"
        ).get(pk=pk)
    except SubscriptionRequest.DoesNotExist:
        raise NotFound("Obuna arizasi topilmadi")
