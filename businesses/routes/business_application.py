"""BusinessApplication modeli uchun API'lar — "Restoran/To'yxona ochish" oqimi."""

import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from businesses.filters import BusinessApplicationFilter
from businesses.models import BusinessApplication
from businesses.routes.serializers import (
    BusinessApplicationCreateSerializer,
    BusinessApplicationSerializer,
)
from businesses.services import approve_application, reject_application, submit_application
from common.models import PlatformSettings
from common.pagination import StandardResultsPagination
from common.permissions import IsPhoneVerified, IsSuperAdmin
from common.throttles import BusinessApplicationThrottle

logger = logging.getLogger(__name__)


class BusinessApplicationCreateAPIView(APIView):
    """
    POST /api/business-applications/ — ariza yuborish.

    Yuborilgan zahoti (TZ 4.1, 3-qadam):
      • User.role → 'business'
      • Business obyekti yaratiladi
      • Subscription 'trial' holatida, trial_ends_at = bugun + 7 kun

    Javobda foydalanuvchiga ko'rsatiladigan matn va admin Telegram'i qaytadi.
    """

    permission_classes = [IsAuthenticated, IsPhoneVerified]
    throttle_classes = [BusinessApplicationThrottle]

    @extend_schema(
        request=BusinessApplicationCreateSerializer,
        responses={201: BusinessApplicationSerializer},
    )
    def post(self, request):
        serializer = BusinessApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pending = BusinessApplication.objects.filter(
            applicant=request.user, status="pending_payment"
        ).exists()
        if pending:
            return Response(
                {"detail": "Sizda ko'rib chiqilayotgan ariza allaqachon bor."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application, business, subscription = submit_application(
            applicant=request.user,
            business_type=serializer.validated_data["business_type"],
            business_name=serializer.validated_data["business_name"],
        )

        admin_telegram = PlatformSettings.get_solo().admin_telegram_username
        return Response({
            "application": BusinessApplicationSerializer(application).data,
            "business_id": str(business.id),
            "trial_ends_at": subscription.trial_ends_at,
            "message": (
                "Arizangiz qabul qilindi! Sizga 7 kunlik BEPUL Pro versiya ochib berildi — "
                "shu muddat ichida platformaning barcha imkoniyatlaridan foydalanishingiz "
                f"mumkin. Obunani davom ettirish uchun Telegram orqali administrator bilan "
                f"bog'laning: @{admin_telegram}"
            ),
            "admin_telegram": f"@{admin_telegram}",
        }, status=status.HTTP_201_CREATED)


class MyBusinessApplicationAPIView(APIView):
    """GET /api/business-applications/my/ — foydalanuvchining o'z arizalari."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=BusinessApplicationSerializer(many=True))
    def get(self, request):
        queryset = (
            BusinessApplication.objects.filter(applicant=request.user)
            .select_related("applicant", "business")
            .order_by("-created_at")
        )
        serializer = BusinessApplicationSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminApplicationListAPIView(APIView):
    """GET /api/admin/applications/ — admin panelidagi "Arizalar" ro'yxati."""

    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BusinessApplicationFilter
    queryset = BusinessApplication.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=BusinessApplicationSerializer(many=True))
    def get(self, request):
        queryset = (
            BusinessApplication.objects.select_related("applicant", "approved_by", "business")
            .order_by("-created_at")
        )
        queryset = BusinessApplicationFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = BusinessApplicationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminApplicationApproveAPIView(APIView):
    """
    POST /api/admin/applications/{pk}/approve/ — "To'lovni tasdiqlash".

    Natijasi (TZ 4.1, 5-qadam): ariza 'approved', obuna 'active',
    subscription_ends_at = bugun + 30 kun, profil ommaviy ko'rinadi.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(request=None, responses=BusinessApplicationSerializer)
    def post(self, request, pk):
        try:
            application = BusinessApplication.objects.select_related(
                "applicant", "business"
            ).get(pk=pk)
        except BusinessApplication.DoesNotExist:
            raise NotFound("Ariza topilmadi")

        if application.status == "approved":
            return Response(
                {"detail": "Bu ariza allaqachon tasdiqlangan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application = approve_application(application=application, approved_by=request.user)
        return Response(BusinessApplicationSerializer(application).data, status=status.HTTP_200_OK)


class AdminApplicationRejectAPIView(APIView):
    """POST /api/admin/applications/{pk}/reject/ — arizani rad etish."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(request=None, responses=BusinessApplicationSerializer)
    def post(self, request, pk):
        try:
            application = BusinessApplication.objects.select_related(
                "applicant", "business"
            ).get(pk=pk)
        except BusinessApplication.DoesNotExist:
            raise NotFound("Ariza topilmadi")

        application = reject_application(application=application, rejected_by=request.user)
        return Response(BusinessApplicationSerializer(application).data, status=status.HTTP_200_OK)
