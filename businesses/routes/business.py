"""Business modeli uchun API'lar — ommaviy qidiruv, detal, egasi va admin."""

import logging
from math import asin, cos, radians, sin, sqrt

from django.conf import settings
from django.db import transaction
from django.db.models import Count, IntegerField, Max, Min, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from businesses.filters import BusinessFilter
from businesses.models import Business, Hall, Room
from businesses.routes.serializers import (
    BusinessAdminSerializer,
    BusinessDetailSerializer,
    BusinessListSerializer,
    BusinessUpdateSerializer,
)
from common.cache import build_cache_key, cached_response, invalidate_business_cache
from common.pagination import StandardResultsPagination
from common.permissions import HasActiveSubscription, IsBusinessRole, IsSuperAdmin
from common.services import get_owner_business

logger = logging.getLogger("businesses")

EARTH_RADIUS_KM = 6371.0
KM_PER_DEGREE_LAT = 111.32
MAX_RADIUS_KM = 100


def haversine_km(lat1, lng1, lat2, lng2):
    """Ikki koordinata orasidagi masofa (km)."""
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def bounding_box(lat, lng, radius_km):
    """
    Radiusni to'rtburchakka aylantiradi.

    Nega kerak: Haversine SQL'da hisoblanmaydi, ya'ni har bir biznesni
    Python'ga tortib olish kerak bo'lardi — 10 000 biznesda bu har bir
    qidiruvda 10 000 qator demakdir. Avval indeksdan foydalanadigan
    to'rtburchak bilan kesamiz (bir necha o'nlab qator qoladi), keyin
    aniq masofani faqat o'shalar uchun hisoblaymiz.
    """
    lat_delta = radius_km / KM_PER_DEGREE_LAT
    # Qutbga yaqinlashganda uzunlik darajalari qisqaradi; nolga bo'linishdan saqlanamiz.
    cos_lat = max(cos(radians(lat)), 0.01)
    lng_delta = radius_km / (KM_PER_DEGREE_LAT * cos_lat)
    return lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta


def annotated_business_queryset():
    """
    Ro'yxat uchun asosiy queryset.

    Xona/zal sonini `Count` + `JOIN` bilan emas, `Subquery` bilan olamiz:
    JOIN'da bir nechta bog'liq jadval qo'shilsa qatorlar ko'payib ketadi
    (cartesian) va `DISTINCT` qo'shishga majbur bo'lardik — bu esa katta
    jadvalda sezilarli sekinlashuv.
    """
    rooms = Room.objects.filter(business=OuterRef("pk")).order_by().values("business")
    halls = Hall.objects.filter(business=OuterRef("pk")).order_by().values("business")

    def sub(qs, expression):
        return Subquery(qs.annotate(v=expression).values("v")[:1], output_field=IntegerField())

    return (
        Business.objects.filter(is_visible=True)
        .annotate(
            rooms_count=Coalesce(sub(rooms, Count("id")), 0),
            halls_count=Coalesce(sub(halls, Count("id")), 0),
            # Sig'im: restoranda xonalardan, to'yxonada zallardan olinadi —
            # `guests` filtri ikkalasida ham bir xil maydon bilan ishlashi uchun.
            min_capacity=Coalesce(sub(rooms, Min("capacity")), sub(halls, Min("people"))),
            max_capacity=Coalesce(sub(rooms, Max("capacity")), sub(halls, Max("people"))),
        )
        .only(
            "id", "name", "business_type", "address", "district",
            "latitude", "longitude", "description", "cover_photo",
            "cuisine", "open_time", "close_time", "rating_avg", "reviews_count",
        )
    )


class BusinessListAPIView(APIView):
    """
    GET /api/businesses/ — ommaviy ro'yxat.

    Filtrlar birga ishlatilishi mumkin:
      ?type=restaurant|venue    ?search=<nom/manzil/tuman>
      ?district=Yunusobod       ?cuisine=milliy      ?min_rating=4.5
      ?lat=..&lng=..&radius_km=5      — geolokatsiya (bounding box + Haversine)
      ?date=YYYY-MM-DD                — faqat shu kunga bo'sh joyi borlar
      ?guests=6                       — shuncha kishi sig'adigan xona/zali borlar

    Javob 60 sekundga keshlanadi: bu endpoint eng ko'p so'raladigan joy va
    restoran ro'yxati sekundiga o'zgarmaydi.
    """

    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BusinessFilter
    queryset = Business.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(
        responses=BusinessListSerializer(many=True),
        parameters=[
            OpenApiParameter("type", str, description="restaurant | venue"),
            OpenApiParameter("search", str, description="Nom, manzil yoki tuman"),
            OpenApiParameter("district", str),
            OpenApiParameter("cuisine", str, description="milliy | yevropa | fusion | ..."),
            OpenApiParameter("min_rating", float),
            OpenApiParameter("guests", int, description="Mehmonlar soni — sig'imi yetadiganlar"),
            OpenApiParameter("lat", float),
            OpenApiParameter("lng", float),
            OpenApiParameter("radius_km", float, description=f"1..{MAX_RADIUS_KM}"),
            OpenApiParameter("date", str, description="YYYY-MM-DD"),
        ],
    )
    def get(self, request):
        geo = self._parse_geo(request)
        if isinstance(geo, Response):
            return geo

        cache_key = build_cache_key(
            "biz:list",
            sorted(request.GET.items()),
            request.GET.get("page", 1),
            request.GET.get("page_size", ""),
        )
        data = cached_response(
            cache_key,
            settings.CACHE_TTL_BUSINESS_LIST,
            lambda: self._build(request, geo),
        )
        return Response(data, status=status.HTTP_200_OK)

    def _parse_geo(self, request):
        lat, lng, radius = (
            request.GET.get("lat"),
            request.GET.get("lng"),
            request.GET.get("radius_km"),
        )
        if not (lat and lng):
            return None
        try:
            lat, lng = float(lat), float(lng)
            radius = float(radius) if radius else 5.0
        except ValueError:
            return Response(
                {"detail": "lat, lng va radius_km son bo'lishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return Response(
                {"detail": "Koordinatalar noto'g'ri."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Radius chegarasi — "radius=100000" bilan butun bazani tortib
        # olishning oldini oladi.
        radius = max(0.1, min(radius, MAX_RADIUS_KM))
        return lat, lng, radius

    def _build(self, request, geo):
        queryset = annotated_business_queryset()
        queryset = BusinessFilter(request.GET, queryset=queryset).qs

        date = request.GET.get("date")
        if date:
            queryset = queryset.filter(
                availabilities__date=date, availabilities__is_booked=False
            ).distinct()

        paginator = self.pagination_class()

        if geo is None:
            queryset = queryset.order_by("-rating_avg", "-created_at")
            page = paginator.paginate_queryset(queryset, request, view=self)
            return paginator.get_paginated_response(
                BusinessListSerializer(page, many=True, context={"request": request}).data
            ).data

        lat, lng, radius = geo
        min_lat, max_lat, min_lng, max_lng = bounding_box(lat, lng, radius)
        queryset = queryset.filter(
            latitude__gte=min_lat, latitude__lte=max_lat,
            longitude__gte=min_lng, longitude__lte=max_lng,
        )

        items = []
        for business in queryset:
            distance = haversine_km(lat, lng, business.latitude, business.longitude)
            if distance > radius:
                continue  # to'rtburchak burchaklariga tushib qolganlarni kesamiz
            business.distance_km = round(distance, 2)
            items.append(business)
        items.sort(key=lambda b: b.distance_km)

        page = paginator.paginate_queryset(items, request, view=self)
        return paginator.get_paginated_response(
            BusinessListSerializer(page, many=True, context={"request": request}).data
        ).data


class BusinessDetailAPIView(APIView):
    """
    GET /api/businesses/{pk}/ — bitta biznesning to'liq profili:
    galereya, xona/zallar, menyu va narx paketlari bilan.
    """

    permission_classes = [AllowAny]

    @extend_schema(responses=BusinessDetailSerializer)
    def get(self, request, pk):
        cache_key = build_cache_key("biz:detail", pk)
        data = cached_response(
            cache_key,
            settings.CACHE_TTL_BUSINESS_DETAIL,
            lambda: self._build(request, pk),
        )
        if data is None:
            raise NotFound("Biznes topilmadi yoki ommaviy ko'rinishda emas")
        return Response(data, status=status.HTTP_200_OK)

    def _build(self, request, pk):
        business = (
            Business.objects.select_related("owner")
            .prefetch_related(
                "photos", "rooms", "halls", "pricings",
                "restaurant_menu_items", "venue_menu_items",
            )
            .filter(pk=pk, is_visible=True)
            .first()
        )
        if business is None:
            return None
        return BusinessDetailSerializer(business, context={"request": request}).data


class OwnerBusinessAPIView(APIView):
    """
    GET/PATCH /api/owner/business/ — biznes egasining "Sozlamalar" ekrani.

    Qaysi biznes ekani URL'dan emas, tokendagi foydalanuvchidan aniqlanadi —
    shuning uchun egasi boshqa birovning biznesiga hech qanday yo'l bilan
    tega olmaydi (IDOR imkonsiz).
    """

    permission_classes = [IsBusinessRole, HasActiveSubscription]

    @extend_schema(responses=BusinessUpdateSerializer)
    def get(self, request):
        business = get_owner_business(request.user)
        return Response(
            BusinessUpdateSerializer(business, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=BusinessUpdateSerializer, responses=BusinessUpdateSerializer)
    def patch(self, request):
        business = get_owner_business(request.user)
        serializer = BusinessUpdateSerializer(
            business, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

        invalidate_business_cache()
        logger.info(f"Business updated by owner: business_id={business.id}, user_id={request.user.id}")
        return Response(serializer.data, status=status.HTTP_200_OK)


class OwnerOverviewAPIView(APIView):
    """
    GET /api/owner/overview/ — boshqaruv panelidagi "Umumiy ko'rinish"
    ekranining statistika kartochkalari va so'nggi bronlar.
    """

    permission_classes = [IsBusinessRole]

    @extend_schema(responses=None)
    def get(self, request):
        from django.db.models import Count, Q

        from reservations.models import Reservation
        from reservations.routes.serializers import ReservationSerializer

        business = get_owner_business(request.user)

        # Bitta so'rovda barcha holatlar bo'yicha sanaymiz — beshta alohida
        # COUNT so'rovi yuborish o'rniga.
        counts = Reservation.objects.filter(business=business).aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="pending")),
            confirmed=Count("id", filter=Q(status="confirmed")),
            completed=Count("id", filter=Q(status="completed")),
            cancelled=Count("id", filter=Q(status="cancelled")),
        )

        recent = (
            Reservation.objects.filter(business=business)
            .select_related("user", "business", "room", "hall", "availability")
            .order_by("-created_at")[:5]
        )
        subscription = getattr(business, "subscription", None)

        return Response({
            "business": {
                "id": str(business.id),
                "name": business.name,
                "type": business.business_type,
                "cover_photo": request.build_absolute_uri(business.cover_photo.url)
                if business.cover_photo else None,
                "description": business.description,
                "district": business.district,
            },
            "stats": {
                "total_reservations": counts["total"],
                "pending_reservations": counts["pending"],
                "confirmed_reservations": counts["confirmed"],
                "completed_reservations": counts["completed"],
                "cancelled_reservations": counts["cancelled"],
                "rating_avg": business.rating_avg,
                "reviews_count": business.reviews_count,
            },
            "subscription": {
                "status": subscription.status if subscription else None,
                "trial_ends_at": subscription.trial_ends_at if subscription else None,
                "subscription_ends_at": subscription.subscription_ends_at if subscription else None,
            },
            "recent_reservations": ReservationSerializer(
                recent, many=True, context={"request": request}
            ).data,
        }, status=status.HTTP_200_OK)


class AdminBusinessListAPIView(APIView):
    """GET /api/admin/businesses/ — admin panelidagi "Bizneslar" jadvali."""

    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BusinessFilter
    queryset = Business.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(responses=BusinessAdminSerializer(many=True))
    def get(self, request):
        queryset = Business.objects.select_related("owner", "subscription").order_by("-created_at")
        queryset = BusinessFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = BusinessAdminSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminBusinessToggleBlockAPIView(APIView):
    """
    PATCH /api/admin/businesses/{pk}/toggle-block/ — biznesni bloklash/blokdan
    chiqarish. Bloklangan biznes ommaviy qidiruvda ko'rinmaydi.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(request=None, responses=BusinessAdminSerializer)
    def patch(self, request, pk):
        try:
            business = Business.objects.select_related("owner", "subscription").get(pk=pk)
        except Business.DoesNotExist:
            raise NotFound("Biznes topilmadi")

        with transaction.atomic():
            business.is_visible = not business.is_visible
            business.save(update_fields=["is_visible"])

        logging.getLogger("django.security").info(
            f"Business visibility toggled: business_id={business.id}, "
            f"is_visible={business.is_visible}, by={request.user.id}"
        )
        return Response(BusinessAdminSerializer(business).data, status=status.HTTP_200_OK)


class AdminOverviewAPIView(APIView):
    """GET /api/admin/overview/ — admin panelidagi statistika kartochkalari."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(responses=None)
    def get(self, request):
        from django.contrib.auth import get_user_model
        from django.db.models import Count, Q

        from businesses.models import BusinessApplication
        from businesses.routes.serializers import BusinessApplicationSerializer
        from reservations.models import Reservation
        from subscriptions.models import Subscription

        User = get_user_model()

        business_counts = Business.objects.aggregate(
            total=Count("id"),
            restaurants=Count("id", filter=Q(business_type="restaurant")),
            venues=Count("id", filter=Q(business_type="venue")),
            visible=Count("id", filter=Q(is_visible=True)),
        )
        subscription_counts = Subscription.objects.aggregate(
            trial=Count("id", filter=Q(status="trial")),
            active=Count("id", filter=Q(status="active")),
            expired=Count("id", filter=Q(status="expired")),
        )
        reservation_counts = Reservation.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="pending")),
        )

        recent_apps = (
            BusinessApplication.objects.select_related("applicant")
            .order_by("-created_at")[:5]
        )

        return Response({
            "stats": {
                "users_count": User.objects.filter(is_active=True).count(),
                "businesses_count": business_counts["total"],
                "restaurants_count": business_counts["restaurants"],
                "venues_count": business_counts["venues"],
                "visible_businesses": business_counts["visible"],
                "pending_applications": BusinessApplication.objects.filter(
                    status="pending_payment"
                ).count(),
                "reservations_count": reservation_counts["total"],
                "pending_reservations": reservation_counts["pending"],
            },
            "subscriptions": subscription_counts,
            "recent_applications": BusinessApplicationSerializer(recent_apps, many=True).data,
        }, status=status.HTTP_200_OK)
