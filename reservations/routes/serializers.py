"""reservations ilovasining BARCHA serializerlari shu faylda."""

import datetime

from django.utils import timezone
from rest_framework import serializers

from businesses.models import Business, Hall, Room
from reservations.models import Availability, Reservation


# ===================================================================
# Availability
# ===================================================================
class AvailabilitySerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source="room.name", read_only=True)

    class Meta:
        model = Availability
        fields = [
            "id", "business", "room", "room_name",
            "date", "start_time", "end_time", "is_booked",
        ]
        read_only_fields = ["id", "business"]


class GenerateAvailabilitySerializer(serializers.Serializer):
    """
    Biznes egasi bir necha OYNI belgilab, shu oylarning barcha kunlari uchun
    bitta shablon (start_time/end_time) bo'yicha bo'sh vaqt yozuvlarini
    generatsiya qiladi — har bir kunni qo'lda kiritmasligi uchun.
    """

    room = serializers.UUIDField(required=False, allow_null=True)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    year = serializers.IntegerField(min_value=2020, max_value=2100)
    months = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=12),
        allow_empty=False,
    )

    def validate(self, attrs):
        business = self.context["business"]
        is_restaurant = business.business_type == Business.TYPE_RESTAURANT
        room_id = attrs.get("room")

        if is_restaurant and not room_id:
            raise serializers.ValidationError({"room": "Restoran uchun xona tanlanishi shart."})
        if not is_restaurant and room_id:
            raise serializers.ValidationError(
                {"room": "To'yxona uchun xona tanlanmaydi — bo'sh qoldiring."}
            )
        if room_id and not Room.objects.filter(pk=room_id, business=business).exists():
            raise serializers.ValidationError({"room": "Bu xona sizning biznesingizga tegishli emas."})

        # To'yxona uchun end_time == 00:00 "yarim tungacha" degani.
        is_midnight_end = (not is_restaurant) and attrs["end_time"] == datetime.time(0, 0)
        if not is_midnight_end and attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError(
                {"end_time": "Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak."}
            )
        return attrs


class BusyRangeSerializer(serializers.Serializer):
    """Bron qilingan soat oralig'i — mijoz ekranidagi soat gridini bo'yash uchun."""

    start_time = serializers.TimeField()
    end_time = serializers.TimeField()


# ===================================================================
# Reservation
# ===================================================================
class ReservationSerializer(serializers.ModelSerializer):
    """Bronni ko'rish — mijoz, biznes egasi va admin uchun bir xil ko'rinish."""

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_phone = serializers.CharField(source="user.phone_number", read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    business_type = serializers.CharField(source="business.business_type", read_only=True)
    business_telegram = serializers.CharField(source="business.telegram_username", read_only=True)
    room_name = serializers.CharField(source="room.name", read_only=True)
    hall_name = serializers.CharField(source="hall.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    date = serializers.DateField(source="availability.date", read_only=True)

    # Bekor qilish oynasi. Frontend tugmani KO'RSATISH-ko'rsatmaslikni
    # shu maydonlarga qarab hal qiladi — qoida ikki joyda takrorlanmasin
    # va mijoz bosib bo'lmaydigan tugmani bosmasin.
    can_cancel = serializers.SerializerMethodField()
    cancel_deadline = serializers.SerializerMethodField()
    cancel_blocked_reason = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "id", "user", "user_name", "user_phone",
            "business", "business_name", "business_type", "business_telegram",
            "room", "room_name", "hall", "hall_name",
            "availability", "date", "start_time", "end_time",
            "guests_count", "special_request", "selected_menu",
            "dish_count", "price_per_person", "total_price", "deposit_amount",
            "status", "status_display", "confirmed_at",
            "can_cancel", "cancel_deadline", "cancel_blocked_reason",
            "created_at",
        ]
        read_only_fields = fields

    def get_can_cancel(self, obj) -> bool:
        return obj.cancel_check()[0]

    def get_cancel_deadline(self, obj) -> str | None:
        deadline = obj.cancel_deadline()
        return deadline.isoformat() if deadline else None

    def get_cancel_blocked_reason(self, obj) -> str:
        allowed, reason = obj.cancel_check()
        return "" if allowed else reason


MAX_BOOKING_DAYS_AHEAD = 365
MAX_MENU_ITEMS = 20


class RestaurantReservationCreateSerializer(serializers.Serializer):
    """
    Restoran broni: mijoz sana + soat oralig'ini (masalan 19:00-21:00) va
    mehmonlar sonini tanlaydi. Menyu tanlash ixtiyoriy — mijoz joyga
    borib ham buyurtma berishi mumkin.
    """

    room = serializers.UUIDField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    guests_count = serializers.IntegerField(min_value=1, max_value=1000)
    menu_items = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list,
        max_length=MAX_MENU_ITEMS,
    )
    special_request = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=1000
    )

    def validate(self, attrs):
        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError(
                {"end_time": "Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak."}
            )
        today = timezone.localdate()
        if attrs["date"] < today:
            raise serializers.ValidationError({"date": "O'tib ketgan sanaga bron qilib bo'lmaydi."})
        if (attrs["date"] - today).days > MAX_BOOKING_DAYS_AHEAD:
            raise serializers.ValidationError(
                {"date": f"Eng ko'pi bilan {MAX_BOOKING_DAYS_AHEAD} kun oldin bron qilish mumkin."}
            )

        try:
            room = Room.objects.select_related("business").get(pk=attrs["room"])
        except Room.DoesNotExist:
            raise serializers.ValidationError({"room": "Xona topilmadi."})

        if room.business.business_type != Business.TYPE_RESTAURANT:
            raise serializers.ValidationError({"room": "Bu xona restoranga tegishli emas."})
        if not room.business.is_visible:
            raise serializers.ValidationError({"room": "Bu restoran hozir bron qabul qilmayapti."})
        if attrs["guests_count"] > room.capacity:
            raise serializers.ValidationError(
                {"guests_count": f"Bu xona eng ko'pi bilan {room.capacity} kishilik."}
            )

        # Tanlangan taomlar — SHU restoranga tegishli ekanini tekshiramiz,
        # aks holda boshqa joyning menyusini bronga tirkab bo'lardi.
        menu_ids = attrs.get("menu_items") or []
        if menu_ids:
            from catalog.models import RestaurantMenuItem

            items = list(
                RestaurantMenuItem.objects.filter(
                    id__in=menu_ids, business=room.business, is_available=True
                ).values("id", "name", "price")
            )
            if len(items) != len(set(menu_ids)):
                raise serializers.ValidationError(
                    {"menu_items": "Ba'zi taomlar topilmadi yoki hozir mavjud emas."}
                )
            attrs["menu_snapshot"] = [
                {"id": str(i["id"]), "name": i["name"], "price": str(i["price"])} for i in items
            ]
        else:
            attrs["menu_snapshot"] = []

        attrs["room_obj"] = room
        return attrs


class VenueReservationCreateSerializer(serializers.Serializer):
    """
    To'yxona broni: butun kunga, bitta zal.

    Narx kishi boshiga hisoblanadi va tanlangan TAOM SONIGA bog'liq
    (VenuePricing): umumiy summa = price_per_person × mehmonlar soni.
    Mijoz nechta xil taom tanlagan bo'lsa, shuncha taom nomini ham
    yuborishi kerak.
    """

    hall = serializers.UUIDField()
    date = serializers.DateField()
    guests_count = serializers.IntegerField(min_value=1, max_value=5000)
    dish_count = serializers.IntegerField(min_value=1, max_value=3, required=False, default=1)
    menu_items = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=MAX_MENU_ITEMS
    )
    special_request = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=1000
    )

    def validate(self, attrs):
        from businesses.models import VenuePricing

        today = timezone.localdate()
        if attrs["date"] < today:
            raise serializers.ValidationError({"date": "O'tib ketgan sanaga bron qilib bo'lmaydi."})
        if (attrs["date"] - today).days > MAX_BOOKING_DAYS_AHEAD:
            raise serializers.ValidationError(
                {"date": f"Eng ko'pi bilan {MAX_BOOKING_DAYS_AHEAD} kun oldin bron qilish mumkin."}
            )

        try:
            hall = Hall.objects.select_related("business").get(pk=attrs["hall"])
        except Hall.DoesNotExist:
            raise serializers.ValidationError({"hall": "Zal topilmadi."})

        if hall.business.business_type != Business.TYPE_VENUE:
            raise serializers.ValidationError({"hall": "Bu zal to'yxonaga tegishli emas."})
        if not hall.business.is_visible:
            raise serializers.ValidationError({"hall": "Bu to'yxona hozir bron qabul qilmayapti."})
        if attrs["guests_count"] > hall.people:
            raise serializers.ValidationError(
                {"guests_count": f"Bu zal eng ko'pi bilan {hall.people} kishilik."}
            )

        # --- narx ---
        dish_count = attrs.get("dish_count", 1)
        pricing = VenuePricing.objects.filter(
            business=hall.business, dish_count=dish_count
        ).first()
        if pricing is not None:
            attrs["price_per_person"] = pricing.price_per_person
            attrs["total_price"] = pricing.price_per_person * attrs["guests_count"]
        elif hall.all_price is not None:
            # Narx paketi sozlanmagan bo'lsa, zalning qat'iy summasiga qaytamiz.
            attrs["price_per_person"] = None
            attrs["total_price"] = hall.all_price
        else:
            raise serializers.ValidationError(
                {"dish_count": "Bu to'yxonada narx hali sozlanmagan. Admin bilan bog'laning."}
            )

        # --- menyu ---
        menu_ids = attrs.get("menu_items") or []
        if menu_ids:
            from catalog.models import VenueMenuItem

            if len(set(menu_ids)) != dish_count:
                raise serializers.ValidationError(
                    {"menu_items": f"{dish_count} xil taom tanlanishi kerak."}
                )
            items = list(
                VenueMenuItem.objects.filter(
                    id__in=menu_ids, business=hall.business
                ).values("id", "name")
            )
            if len(items) != len(set(menu_ids)):
                raise serializers.ValidationError({"menu_items": "Ba'zi taomlar topilmadi."})
            attrs["menu_snapshot"] = [
                {"id": str(i["id"]), "name": i["name"]} for i in items
            ]
        else:
            attrs["menu_snapshot"] = []

        attrs["hall_obj"] = hall
        return attrs


class ReservationStatusSerializer(serializers.Serializer):
    """Biznes egasi bronni tasdiqlaydi / bekor qiladi / yakunlaydi."""

    status = serializers.ChoiceField(choices=["confirmed", "cancelled", "completed"])
