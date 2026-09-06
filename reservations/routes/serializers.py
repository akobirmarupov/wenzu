"""reservations ilovasining BARCHA serializerlari shu faylda."""

import datetime
from decimal import Decimal

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
class ReservationCustomerSerializer(serializers.Serializer):
    """
    Bron yuborgan MIJOZNING kartochkasi — joy egasi uchun.

    Nima uchun kerak. Joy egasi bron so'rovini ko'rganda bitta savolga
    javob izlaydi: "bu odam kelmaydimi?". Band qilingan, lekin kelinmagan
    kun uning uchun to'g'ridan-to'g'ri zarar — u o'sha kunga boshqa
    mijozlarni rad etgan bo'ladi.

    Shuning uchun bu yerda ism-familiya, telefon va rasmdan tashqari
    ISHONCHLILIK BALI ham bor (`account.trust`): 100 Bitdan boshlanadi
    va har bir bekor qilishda 5 Bit kamayadi.

    Maxfiylik: bu blok faqat BRONNI KO'RA OLADIGANLARGA yetib boradi —
    mijozning o'ziga, joy egasiga va administratorga (view'dagi tekshiruv).
    Ommaviy ro'yxatlarda bu serializer umuman ishlatilmaydi.
    """

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    phone_number = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    avatar = serializers.SerializerMethodField()

    trust_bits = serializers.IntegerField(read_only=True)
    trust_level = serializers.SerializerMethodField()
    trust_level_display = serializers.SerializerMethodField()
    trust_tone = serializers.SerializerMethodField()
    cancelled_reservations_count = serializers.IntegerField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)

    def get_avatar(self, obj) -> str | None:
        if not obj.avatar:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url

    def get_trust_level(self, obj) -> str:
        return obj.trust["level"]

    def get_trust_level_display(self, obj) -> str:
        return obj.trust["level_display"]

    def get_trust_tone(self, obj) -> str:
        return obj.trust["tone"]


class ReservationSerializer(serializers.ModelSerializer):
    """Bronni ko'rish — mijoz, biznes egasi va admin uchun bir xil ko'rinish."""

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_phone = serializers.CharField(source="user.phone_number", read_only=True)
    # Joy egasi ko'radigan to'liq mijoz kartochkasi: rasm, bal, tarix.
    # Yuqoridagi ikki maydon eski mijozlar (mobil ilova) uchun qoladi.
    customer = ReservationCustomerSerializer(source="user", read_only=True)

    business_name = serializers.CharField(source="business.name", read_only=True)
    business_type = serializers.CharField(source="business.business_type", read_only=True)
    business_telegram = serializers.CharField(source="business.telegram_username", read_only=True)
    business_address = serializers.CharField(source="business.address", read_only=True)
    business_district = serializers.CharField(source="business.district", read_only=True)
    business_map_links = serializers.SerializerMethodField()

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
    # Tadbir qachon boshlanishi — bekor qilish muddati aynan shundan
    # hisoblanadi, ya'ni mijoz ikkala sanani yonma-yon ko'rishi kerak.
    event_starts_at = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "id", "user", "user_name", "user_phone", "customer",
            "business", "business_name", "business_type", "business_telegram",
            "business_address", "business_district", "business_map_links",
            "room", "room_name", "hall", "hall_name",
            "availability", "date", "start_time", "end_time", "event_starts_at",
            "guests_count", "special_request", "selected_menu",
            "dish_count", "price_per_person", "day_rent_price",
            "total_price", "deposit_amount",
            "status", "status_display", "confirmed_at",
            "can_cancel", "cancel_deadline", "cancel_blocked_reason",
            "created_at",
        ]
        read_only_fields = fields

    def get_business_map_links(self, obj) -> dict:
        """Bron kartochkasidagi "Xaritada ochish" tugmalari."""
        return obj.business.map_links

    def get_can_cancel(self, obj) -> bool:
        return obj.cancel_check()[0]

    def get_cancel_deadline(self, obj) -> str | None:
        deadline = obj.cancel_deadline()
        return deadline.isoformat() if deadline else None

    def get_cancel_blocked_reason(self, obj) -> str:
        allowed, reason = obj.cancel_check()
        return "" if allowed else reason

    def get_event_starts_at(self, obj) -> str | None:
        event_at = obj.event_starts_at()
        return event_at.isoformat() if event_at else None


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

    ===================================================================
    Summa IKKI QISMDAN yig'iladi
    ===================================================================
    1. BIR KUNLIK IJARA (`Hall.all_price`) — zalning o'zi uchun. Masalan
       15 000 000 so'm. Bu qism mehmonlar soniga BOG'LIQ EMAS: zal
       qancha odam kelishidan qat'i nazar bir kunga band qilinadi.

    2. TAOM (`VenuePricing`) — IXTIYORIY. To'y egasi xohlasa 1, 2 yoki
       3 xil taomni to'yxonadan buyurtma qiladi va bu qism kishi
       boshiga hisoblanadi. Xohlamasa — oshpazni ham, mahsulotni ham
       o'zi olib boradi va bu qism umuman bo'lmaydi.

    Shuning uchun har uch holat ham to'g'ri:

      * faqat ijara      → 15 000 000
      * ijara + 2 xil taom (300 kishi × 120 000)  → 15 000 000 + 36 000 000
      * faqat kishi boshiga (shahar to'yxonasi, ijara kiritilmagan)

    Egasi hech qanday narx kiritmagan bo'lsa, bron NARXSIZ yaratiladi
    va summa keyin kelishiladi. Bu "0 so'm" deb yozib qo'yishdan yaxshi:
    nol summa mijozga ham, egasiga ham noto'g'ri va'da beradi.

    YAGONA QAT'IY QOIDA: taom soni tanlangan bo'lsa, menyudan AYNAN
    shuncha xil taom belgilanishi shart. "2 xil taom" paketini tanlab,
    menyudan bittasini ham ko'rsatmagan bron oshxona uchun bajarib
    bo'lmaydigan buyurtma bo'lardi.
    """

    hall = serializers.UUIDField()
    date = serializers.DateField()
    guests_count = serializers.IntegerField(min_value=1, max_value=5000)
    dish_count = serializers.IntegerField(
        min_value=1, max_value=3, required=False, allow_null=True, default=None,
        help_text="Ixtiyoriy: 1, 2 yoki 3 xil taom. Tanlansa, `menu_items` da "
                  "aynan shuncha taom ko'rsatilishi shart.",
    )
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
        # `dict.fromkeys` — takrorlarni olib tashlaydi, lekin tartibni
        # saqlaydi: mijoz taomlarni qaysi ketma-ketlikda tanlagan bo'lsa,
        # bronda ham shunday ko'rinsin.
        menu_ids = list(dict.fromkeys(attrs.get("menu_items") or []))
        dish_count = attrs.get("dish_count")

        # Taom soni ko'rsatilmagan bo'lsa, tanlangan taomlarning o'zi uni
        # aytib turadi — mijozdan bir xil narsani ikki marta so'ramaymiz.
        if dish_count is None and menu_ids:
            dish_count = len(menu_ids)

        packages = {
            p.dish_count: p
            for p in VenuePricing.objects.filter(business=hall.business)
        }
        pricing = packages.get(dish_count) if dish_count else None

        if dish_count and pricing is None and packages:
            available = ", ".join(str(n) for n in sorted(packages))
            raise serializers.ValidationError(
                {"dish_count": f"Bu to'yxonada {dish_count} xil taom uchun narx "
                               f"belgilanmagan. Mavjud paketlar: {available}."}
            )

        # Ikki qism ALOHIDA hisoblanadi va alohida saqlanadi — mijoz ham,
        # joy egasi ham "15 000 000 ijara + 36 000 000 taom" ni ko'rishi
        # kerak, yagona yig'indini emas.
        day_rent = hall.all_price
        food_total = (
            pricing.price_per_person * attrs["guests_count"] if pricing is not None else None
        )

        if day_rent is None and food_total is None:
            # Egasi hali narx kiritmagan. Bron o'tadi, summa keyin kelishiladi.
            total = None
        else:
            total = (day_rent or Decimal(0)) + (food_total or Decimal(0))

        attrs["price_per_person"] = pricing.price_per_person if pricing is not None else None
        attrs["day_rent_price"] = day_rent
        attrs["total_price"] = total
        attrs["dish_count"] = dish_count

        # --- menyu ---
        # Taom tanlash MAJBURIY emas: to'y egasi o'z oshpazi bilan kelishi
        # mumkin va bunda faqat ijara to'lanadi.
        #
        # Lekin TAOM PAKETI tanlangan bo'lsa (`pricing`), menyudan aynan
        # shuncha xil taom belgilanishi SHART. "2 xil taom" uchun pul
        # to'lab, qaysi ikkitasi ekanini aytmagan bron oshxona uchun
        # bajarib bo'lmaydigan buyurtma bo'lardi — va mijoz to'y kuni
        # buni bilib qolardi.
        if pricing is not None and len(menu_ids) != dish_count:
            raise serializers.ValidationError({
                "menu_items": f"Menyudan aynan {dish_count} xil taom tanlang "
                              f"(hozir {len(menu_ids)} ta belgilangan). Taom "
                              f"kerak bo'lmasa, taom sonini bo'sh qoldiring — "
                              f"u holda faqat zal ijarasi to'lanadi."
            })

        if menu_ids:
            from catalog.models import VenueMenuItem

            items = list(
                VenueMenuItem.objects.filter(
                    id__in=menu_ids, business=hall.business
                ).values("id", "name")
            )
            if len(items) != len(menu_ids):
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
