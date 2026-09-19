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
from businesses.services import (
    BusinessLimitReached,
    TrialNotAvailable,
    approve_application,
    reject_application,
    submit_application,
)
from common.models import PlatformSettings
from common.pagination import StandardResultsPagination
from common.permissions import HasContactPhone, IsSuperAdmin
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

    # ALOQA RAQAMI SHART.
    #
    # Hisob Google orqali ochiladi va unda raqam bo'lmaydi. Ariza
    # esa administrator BOG'LANADIGAN hujjat: u joyni tekshiradi,
    # savol beradi, to'lovni kelishadi. Raqamsiz ariza — javobsiz
    # ariza.
    #
    # Bu joyning o'z aloqa raqamidan boshqa narsa
    # (`Business.phone_number` — uni mijozlar ko'radi). Bu yerdagisi
    # EGASINING raqami va faqat administratorga ko'rinadi.
    permission_classes = [IsAuthenticated, HasContactPhone]
    phone_message = (
        "Ariza yuborish uchun aloqa raqamingizni kiriting — "
        "administrator siz bilan bog'lanadi."
    )
    throttle_classes = [BusinessApplicationThrottle]

    @extend_schema(
        request=BusinessApplicationCreateSerializer,
        responses={201: BusinessApplicationSerializer},
    )
    def post(self, request):
        serializer = BusinessApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Ochiq ariza — lekin faqat BIZNESI HALI BOR bo'lgani.
        #
        # Biznes o'chirilgan bo'lsa (masalan adminkadan), ariza yetim
        # qolib ketadi. Ilgari o'sha yetim ariza yangi ariza berishni
        # MANGU to'sib qo'yardi: odam "ko'rib chiqilayotgan arizangiz
        # bor" degan xabarni ko'rardi, lekin hech qanday joyi yo'q edi
        # va bu holatdan chiqib ketolmasdi.
        pending = any(
            hasattr(application, "business")
            for application in BusinessApplication.objects.filter(
                applicant=request.user, status="pending_payment"
            )
        )
        if pending:
            return Response(
                {"detail": "Sizda ko'rib chiqilayotgan ariza allaqachon bor."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan = serializer.validated_data.get("plan")

        try:
            application, business, _ = submit_application(
                applicant=request.user,
                business_type=serializer.validated_data["business_type"],
                business_name=serializer.validated_data["business_name"],
                plan=plan,
            )
        except BusinessLimitReached as error:
            return Response(
                {"detail": str(error), "code": "business_limit"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TrialNotAvailable as error:
            # Sinov ikkinchi marta so'ralgan — sabab aniq aytiladi va
            # frontend "pullik tarif tanlang" ekraniga o'tkazadi.
            return Response(
                {"detail": str(error), "code": "trial_used"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        settings_obj = PlatformSettings.get_solo()
        admin_telegram = settings_obj.admin_telegram_username

        # `trial_ends_at` ATAYLAB yo'q: bu bosqichda sinov hali
        # boshlanmagan. Ilgari ariza yuborilishi bilan 7 kunlik bepul
        # muddat ochilardi — ya'ni istalgan odam bir daqiqada "restoran"
        # ochib, hech kim tekshirmagan holda platformani bir hafta bepul
        # ishlatib ketishi mumkin edi. Endi sinov admin tasdig'idan
        # keyin boshlanadi.
        # Xabar tarifga qarab boshqacha: bepul sinovda "7 kun bepul",
        # pullik tarifda esa to'lov va muddat haqida. Ilgari ikkalasida
        # ham "7 kun bepul" yozilardi va pul to'laydigan odam ham bepul
        # kun kutardi.
        if plan is None:
            message = (
                "Arizangiz qabul qilindi! Administrator uni tekshiradi va "
                f"tasdiqlagach sizga {settings_obj.trial_days} kunlik BEPUL sinov "
                "ochiladi — shu muddat ichida platformaning barcha imkoniyatlaridan "
                "foydalanasiz. Tasdiqni tezlashtirish uchun Telegram orqali "
                f"administrator bilan bog'laning: @{admin_telegram}"
            )
        else:
            message = (
                f"Arizangiz qabul qilindi! Tanlangan tarif — {plan.duration_label}, "
                f"{plan.price:,.0f} so'm. To'lovni Telegram orqali amalga oshiring: "
                f"@{admin_telegram}. Administrator tasdiqlagach obunangiz o'sha "
                f"kundan boshlab {plan.duration_label}ga faollashadi."
            ).replace(",", " ")

        return Response({
            "application": BusinessApplicationSerializer(application).data,
            "business_id": str(business.id),
            "is_trial": plan is None,
            "trial_days": settings_obj.trial_days if plan is None else None,
            "message": message,
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
