"""Reservation modeli uchun API'lar — bron yaratish, ko'rish, bekor qilish."""

import datetime
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

from account.trust import TRUST_CANCEL_PENALTY
from common.models import PlatformSettings
from common.pagination import StandardResultsPagination
from common.permissions import HasContactPhone, IsBusinessRole, IsCustomer, IsSuperAdmin
from common.services import get_owner_business
from common.throttles import ReservationCreateThrottle
from reservations.filters import ReservationFilter
from reservations.models import Availability, Reservation
from reservations.routes.serializers import (
    ReservationSerializer,
    ReservationStatusSerializer,
    RestaurantReservationCreateSerializer,
    VenueReservationCreateSerializer,
)

logger = logging.getLogger(__name__)


def _overlaps(qs, start_time, end_time):
    """Berilgan oraliq mavjud bronlardan biri bilan kesishadimi."""
    return qs.filter(start_time__lt=end_time, end_time__gt=start_time).exists()


class ReservationCreateAPIView(APIView):
    """
    POST /api/reservations/ — yangi bron.

    Restoran uchun:  {"room": uuid, "date": "2026-09-01", "start_time": "19:00",
                      "end_time": "21:00", "guests_count": 4}
    To'yxona uchun:  {"hall": uuid, "date": "2026-09-14", "guests_count": 250}
                     — `dish_count` va `menu_items` IXTIYORIY. Zal bir
                     kunga ijaraga olinadi (`Hall.all_price`), ovqatni
                     esa to'y egasi xohlasa to'yxonadan buyurtma qiladi,
                     xohlasa o'zi tashkil qiladi. Taom soni tanlangan
                     bo'lsa, menyudan aynan shuncha xil taom
                     ko'rsatilishi shart.

    Ikki mijoz bir vaqtni bir vaqtda band qilib qo'ymasligi uchun bandlik
    tekshiruvi `select_for_update()` bilan qulflangan tranzaksiya ichida
    bajariladi (TZ 9-bo'lim talabi).
    """

    permission_classes = [IsAuthenticated, HasContactPhone, IsCustomer]
    phone_message = (
        "Bron qilish uchun aloqa raqamingizni kiriting — "
        "joy egasi bronni tasdiqlash uchun sizga qo'ng'iroq qiladi."
    )
    throttle_classes = [ReservationCreateThrottle]

    @extend_schema(
        request=RestaurantReservationCreateSerializer,
        responses={201: ReservationSerializer},
    )
    def post(self, request):
        is_venue = "hall" in request.data

        if is_venue:
            serializer = VenueReservationCreateSerializer(data=request.data)
        else:
            serializer = RestaurantReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                if is_venue:
                    reservation = self._create_venue_reservation(request.user, data)
                else:
                    reservation = self._create_restaurant_reservation(request.user, data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        admin_telegram = reservation.business.telegram_username or (
            PlatformSettings.get_solo().admin_telegram_username
        )
        payload = ReservationSerializer(reservation, context={"request": request}).data
        payload["message"] = (
            f"So'rovingiz qabul qilindi va hozircha \"kutilmoqda\" holatida. "
            f"Bronni yakuniy tasdiqlash uchun @{admin_telegram} administratoriga "
            f"Telegram orqali murojaat qiling va oldindan {reservation.deposit_amount} so'm "
            f"depozit to'lovini amalga oshiring."
        )
        payload["admin_telegram"] = f"@{admin_telegram}"
        return Response(payload, status=status.HTTP_201_CREATED)

    def _create_restaurant_reservation(self, user, data):
        room = data["room_obj"]
        business = room.business

        # Kunlik ish oralig'i yozuvi — qulflab olamiz, shunda parallel
        # so'rovlar navbatma-navbat tekshiriladi.
        availability = (
            Availability.objects.select_for_update()
            .filter(business=business, room=room, date=data["date"])
            .first()
        )
        if availability is None:
            raise ValueError("Bu kun uchun ish jadvali ochilmagan.")

        if not (availability.start_time <= data["start_time"] < availability.end_time):
            raise ValueError(
                f"Tanlangan vaqt ish vaqtidan tashqarida "
                f"({availability.start_time}–{availability.end_time})."
            )

        existing = Reservation.objects.select_for_update().filter(
            room=room, availability=availability, status__in=["pending", "confirmed"]
        )
        if _overlaps(existing, data["start_time"], data["end_time"]):
            raise ValueError("Bu vaqt oralig'i allaqachon band qilingan.")

        reservation = Reservation(
            user=user,
            business=business,
            room=room,
            availability=availability,
            start_time=data["start_time"],
            end_time=data["end_time"],
            guests_count=data["guests_count"],
            selected_menu=data.get("menu_snapshot", []),
            special_request=data.get("special_request", ""),
            status="pending",
        )
        reservation.deposit_amount = reservation.resolve_deposit_amount()
        reservation.save()

        logger.info(
            f"Restaurant reservation created: id={reservation.id}, user_id={user.id}, "
            f"room_id={room.id}, date={data['date']}, {data['start_time']}-{data['end_time']}"
        )
        return reservation

    def _create_venue_reservation(self, user, data):
        hall = data["hall_obj"]
        business = hall.business

        availability = (
            Availability.objects.select_for_update()
            .filter(business=business, room__isnull=True, date=data["date"])
            .first()
        )
        if availability is None:
            raise ValueError("Bu kun uchun to'yxona jadvali ochilmagan.")

        # To'yxonada bir kunda faqat bitta to'y bo'ladi.
        taken = Reservation.objects.select_for_update().filter(
            hall=hall, availability=availability, status__in=["pending", "confirmed"]
        ).exists()
        if taken or availability.is_booked:
            raise ValueError("Bu kun uchun zal allaqachon band. Boshqa sanani tanlang.")

        reservation = Reservation(
            user=user,
            business=business,
            hall=hall,
            availability=availability,
            guests_count=data["guests_count"],
            # Taom soni tanlanmasligi ham mumkin (qishloq to'yxonasi —
            # ovqatni to'y egasi o'zi tashkil qiladi), shuning uchun bu
            # yerda 1 ga "to'ldirib" qo'yilmaydi: bo'sh — bo'sh qoladi.
            dish_count=data.get("dish_count"),
            selected_menu=data.get("menu_snapshot", []),
            special_request=data.get("special_request", ""),
            price_per_person=data.get("price_per_person"),
            day_rent_price=data.get("day_rent_price"),
            total_price=data.get("total_price"),
            status="pending",
        )
        reservation.deposit_amount = reservation.resolve_deposit_amount()
        reservation.save()

        logger.info(
            f"Venue reservation created: id={reservation.id}, user_id={user.id}, "
            f"hall_id={hall.id}, date={data['date']}, guests={data['guests_count']}"
        )
        return reservation


class MyReservationListAPIView(APIView):
    """GET /api/reservations/my/ — foydalanuvchining bron tarixi."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReservationFilter
    queryset = Reservation.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=ReservationSerializer(many=True))
    def get(self, request):
        queryset = (
            Reservation.objects.filter(user=request.user)
            .select_related("user", "business", "room", "hall", "availability")
            .order_by("-created_at")
        )
        queryset = ReservationFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            ReservationSerializer(page, many=True, context={"request": request}).data
        )


class PendingReviewAPIView(APIView):
    """
    GET /api/reservations/pending-review/ — sharh kutayotgan bronlar.

    Vaqti tugagan, lekin hali bahoi qo'yilmagan bronlar. Sayt shu
    ro'yxatga qarab sharh oynasini O'ZI ochadi: odam joydan chiqib,
    saytga kirganda darrov "qanday o'tdi?" degan savolni ko'radi.
    Ilgari sharh yozish uchun u "Bronlarim" ni ochib, kerakli bronni
    topib, tugmasini bosishi kerak edi — amalda buni deyarli hech kim
    qilmasdi va joylar sharhsiz qolardi.

    Faqat SO'NGGI bronlar so'raladi: bir oy oldingi tashrif haqida
    so'rash ham bezovta qiladi, ham javobi ishonchsiz bo'ladi.
    """

    permission_classes = [IsAuthenticated]

    # Necha kun ichida tugagan bron uchun sharh so'raladi.
    REVIEW_WINDOW_DAYS = 14
    # Bir vaqtda nechta so'rov qaytadi. Odamga ketma-ket beshta oyna
    # ko'rsatib bo'lmaydi — u birinchisidayoq yopib yuboradi.
    LIMIT = 3

    @extend_schema(responses=ReservationSerializer(many=True))
    def get(self, request):
        since = timezone.localdate() - datetime.timedelta(days=self.REVIEW_WINDOW_DAYS)

        queryset = (
            Reservation.objects.filter(
                user=request.user,
                status="completed",
                availability__date__gte=since,
            )
            # `review` — OneToOne teskari bog'lanishi. Sharh yozilgan
            # bronlar shu bilan chiqarib tashlanadi.
            .filter(review__isnull=True)
            .select_related("user", "business", "room", "hall", "availability")
            .order_by("-availability__date", "-created_at")[: self.LIMIT]
        )

        return Response(
            ReservationSerializer(queryset, many=True, context={"request": request}).data
        )


class ReservationDetailAPIView(APIView):
    """GET /api/reservations/{pk}/ — bitta bron (faqat egasi yoki biznes egasi)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=ReservationSerializer)
    def get(self, request, pk):
        try:
            reservation = Reservation.objects.select_related(
                "user", "business", "room", "hall", "availability"
            ).get(pk=pk)
        except Reservation.DoesNotExist:
            raise NotFound("Bron topilmadi")

        is_customer = reservation.user_id == request.user.id
        is_owner = reservation.business.owner_id == request.user.id
        if not (is_customer or is_owner or request.user.is_staff):
            return Response(
                {"detail": "Bu bronni ko'rish huquqingiz yo'q."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            ReservationSerializer(reservation, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class ReservationCancelAPIView(APIView):
    """PATCH /api/reservations/{pk}/cancel/ — mijoz o'z bronini bekor qiladi."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=ReservationSerializer)
    def patch(self, request, pk):
        try:
            reservation = Reservation.objects.select_related(
                "user", "business", "room", "hall", "availability"
            ).get(pk=pk)
        except Reservation.DoesNotExist:
            raise NotFound("Bron topilmadi")

        is_staff = request.user.is_staff
        if reservation.user_id != request.user.id and not is_staff:
            return Response(
                {"detail": "Bu bronni bekor qila olmaysiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Muddat cheklovi FAQAT mijozga tegishli. Administrator nizoli
        # holatni hal qilishi kerak bo'lsa, muddatdan qat'i nazar bekor
        # qila oladi — aks holda har bir e'tiroz bazaga qo'lda kirishni
        # talab qilardi.
        allowed, reason = reservation.cancel_check()
        if not allowed and not is_staff:
            return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)
        if reservation.status in ("cancelled", "completed"):
            return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Qayta qulflab o'qiymiz: mijoz tugmani ikki marta bossa ham
            # yoki egasi ayni damda tasdiqlayotgan bo'lsa ham holat
            # aralashib ketmasligi kerak. Muddat ham qulf ostida qayta
            # tekshiriladi — ikki so'rov orasida u tugab qolishi mumkin.
            reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
            allowed, reason = reservation.cancel_check()
            if not allowed and not is_staff:
                return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)
            if reservation.status in ("cancelled", "completed"):
                return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)

            reservation.status = "cancelled"
            reservation.save(update_fields=["status"])

            # ISHONCHLILIK BALI — faqat mijoz O'ZI bekor qilganda kamayadi.
            #
            # Administrator nizoni hal qilib bekor qilsa, ayb mijozda
            # ekani noma'lum — uni jazolash noto'g'ri bo'lardi. Joy
            # egasining rad etishi esa umuman boshqa endpoint
            # (`OwnerReservationStatusAPIView`) va u ham balga tegmaydi.
            if reservation.user_id == request.user.id:
                request.user.penalize_trust(reason=f"reservation:{reservation.id}")

        logger.info(
            f"Reservation cancelled by customer: id={reservation.id}, user_id={request.user.id}"
        )
        payload = ReservationSerializer(reservation, context={"request": request}).data
        if reservation.user_id == request.user.id:
            trust = request.user.trust
            payload["trust"] = trust
            payload["message"] = (
                f"Bron bekor qilindi. Ishonchlilik balingizdan "
                f"{TRUST_CANCEL_PENALTY} Bit ayirildi — hozir {trust['bits']} Bit "
                f"({trust['level_display']})."
            )
        return Response(payload, status=status.HTTP_200_OK)


class OwnerReservationListAPIView(APIView):
    """GET /api/owner/reservations/ — biznes egasining "Bronlar" ekrani."""

    permission_classes = [IsBusinessRole]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReservationFilter
    queryset = Reservation.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=ReservationSerializer(many=True))
    def get(self, request):
        business = get_owner_business(request.user)
        queryset = (
            Reservation.objects.filter(business=business)
            .select_related("user", "business", "room", "hall", "availability")
            .order_by("-created_at")
        )
        queryset = ReservationFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            ReservationSerializer(page, many=True, context={"request": request}).data
        )


class OwnerReservationStatusAPIView(APIView):
    """
    PATCH /api/owner/reservations/{pk}/status/ — biznes egasi bronni
    tasdiqlaydi / bekor qiladi / yakunlaydi.
    """

    permission_classes = [IsBusinessRole]

    @extend_schema(request=ReservationStatusSerializer, responses=ReservationSerializer)
    def patch(self, request, pk):
        business = get_owner_business(request.user)
        try:
            reservation = Reservation.objects.select_related(
                "user", "business", "room", "hall", "availability"
            ).get(pk=pk, business=business)
        except Reservation.DoesNotExist:
            raise NotFound("Bron topilmadi yoki sizga tegishli emas")

        serializer = ReservationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        with transaction.atomic():
            # QULFLAB QAYTA O'QIYMIZ — yuqoridagi o'qish qulfsiz edi.
            #
            # Nega kerak: ayni damda mijoz o'z bronini bekor qilayotgan
            # bo'lishi mumkin (`ReservationCancelAPIView` ni qarang — u
            # allaqachon shunday qulf ishlatadi). Qulfsiz ikkala so'rov
            # ham bronni ESKI holatida o'qib olardi va keyin ikkalasi
            # ham yozardi: kim keyin yozsa — o'shaniki. Natijada mijoz
            # "bekor qildim" degan javobni olib, ishonchlilik balidan
            # ham ayrilib, bron esa "tasdiqlangan" bo'lib qolardi —
            # ya'ni joy egasi kelmaydigan mijozni kutib o'tirardi.
            #
            # `select_related` bu yerda ATAYLAB yo'q: `room`/`hall`/
            # `availability` NULL bo'lishi mumkin va ular LEFT JOIN
            # bilan kelardi, PostgreSQL esa outer join'ning nullable
            # tomoniga `FOR UPDATE` qo'yishga ruxsat bermaydi.
            reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)

            reservation.status = new_status
            # save() (update_fields bilan) post_save signalini ishga tushiradi —
            # to'yxona bo'lsa Availability.is_booked avtomatik moslashadi.
            reservation.save(update_fields=["status"])

        logger.info(
            f"Reservation status changed: id={reservation.id}, status={new_status}, "
            f"by={request.user.id}"
        )
        return Response(
            ReservationSerializer(reservation, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class AdminReservationListAPIView(APIView):
    """GET /api/admin/reservations/ — platformadagi barcha bronlar."""

    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReservationFilter
    queryset = Reservation.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=ReservationSerializer(many=True))
    def get(self, request):
        queryset = (
            Reservation.objects.select_related("user", "business", "room", "hall", "availability")
            .order_by("-created_at")
        )
        queryset = ReservationFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            ReservationSerializer(page, many=True, context={"request": request}).data
        )
