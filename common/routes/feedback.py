"""
Platforma haqidagi takliflar — foydalanuvchidan administratorga.

Sinov davrida bu eng qimmat kanal: nima ishlamayotganini faqat undan
foydalanayotgan odam biladi. Shuning uchun forma imkon qadar past
to'siqli: kirish talab qilinmaydi, majburiy maydon bittagina.
"""

import logging

from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import Feedback
from common.pagination import StandardResultsPagination
from common.permissions import IsSuperAdmin
from common.routes.serializers import FeedbackCreateSerializer, FeedbackSerializer
from common.throttles import FeedbackThrottle

logger = logging.getLogger("common")


class FeedbackCreateAPIView(APIView):
    """
    POST /api/feedback/ — taklif yoki muammo haqida xabar.

    Kirish TALAB QILINMAYDI. Sabab modelda batafsil yozilgan: eng
    foydali fikr ko'pincha ro'yxatdan o'tmagan, ya'ni saytni tashlab
    ketayotgan odamdan keladi.

    Spam `FeedbackThrottle` bilan ushlanadi — kirgan foydalanuvchi
    hisobiga, mehmon esa IP'siga qarab cheklanadi.
    """

    permission_classes = [AllowAny]
    throttle_classes = [FeedbackThrottle]

    @extend_schema(request=FeedbackCreateSerializer, responses={201: None})
    def post(self, request):
        serializer = FeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        feedback = Feedback.objects.create(
            **serializer.validated_data,
            user=request.user if request.user.is_authenticated else None,
            # Manzil MIJOZDAN keladi (`Referer` emas): u brauzer
            # sozlamasiga qarab yuborilmasligi mumkin, JS esa aniq
            # qaysi ekranda turganini biladi.
            page=str(request.data.get("page", ""))[:200],
        )

        # Administratorlarga darhol xabar.
        #
        # Vazifa navbatga QO'YILMAYDI: yozuv yengil (bitta INSERT) va
        # sinov davrida taklif kuniga o'nlab bo'ladi, ming emas.
        # Xatolik esa foydalanuvchining fikrini yo'qotmasligi kerak —
        # shuning uchun butun blok himoyalangan.
        try:
            from notifications.models import Notification
            from notifications.services import notify_many

            staff = get_user_model().objects.filter(is_staff=True, is_active=True)
            notify_many(
                list(staff),
                kind=Notification.KIND_SYSTEM,
                title=f"Yangi taklif: {feedback.get_kind_display().lower()}",
                body=feedback.short,
                link_url="/admin/common/feedback/",
            )
        except Exception as exc:
            logger.warning(f"Taklif haqida xabar yuborilmadi: {exc}")

        logger.info(
            f"Feedback created: id={feedback.id}, kind={feedback.kind}, "
            f"user_id={feedback.user_id}, page={feedback.page}"
        )
        return Response(
            {"detail": "Rahmat! Fikringiz administratorga yuborildi."},
            status=status.HTTP_201_CREATED,
        )


class AdminFeedbackListAPIView(APIView):
    """GET /api/admin/feedback/ — administrator uchun takliflar ro'yxati."""

    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "kind"]
    queryset = Feedback.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=FeedbackSerializer(many=True))
    def get(self, request):
        queryset = Feedback.objects.select_related("user").order_by("-created_at")

        # Filtrni qo'lda qo'llaymiz: bu `APIView`, `GenericAPIView` emas —
        # loyihadagi qolgan ro'yxatlar ham shu uslubda.
        for field in ("status", "kind"):
            value = request.GET.get(field)
            if value:
                queryset = queryset.filter(**{field: value})

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        data = paginator.get_paginated_response(
            FeedbackSerializer(page, many=True).data
        ).data
        # Ro'yxat tepasida "nechta o'qilmagan" — administrator qaysi
        # biriga qarash kerakligini darhol ko'rsin.
        data["unread"] = Feedback.objects.filter(status=Feedback.STATUS_NEW).count()
        return Response(data, status=status.HTTP_200_OK)


class AdminFeedbackDetailAPIView(APIView):
    """PATCH /api/admin/feedback/{pk}/ — holatni va ichki izohni yangilash."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(request=FeedbackSerializer, responses=FeedbackSerializer)
    def patch(self, request, pk):
        try:
            feedback = Feedback.objects.select_related("user").get(pk=pk)
        except Feedback.DoesNotExist:
            raise NotFound("Taklif topilmadi")

        serializer = FeedbackSerializer(feedback, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
