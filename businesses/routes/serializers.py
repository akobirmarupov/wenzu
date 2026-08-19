"""businesses ilovasining BARCHA serializerlari shu faylda."""

from rest_framework import serializers

from businesses.models import (
    Business,
    BusinessApplication,
    BusinessPhoto,
    Hall,
    Room,
    VenuePricing,
)


# ===================================================================
# Rasm galereyasi
# ===================================================================
class BusinessPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPhoto
        fields = ["id", "image", "order"]
        read_only_fields = ["id"]


# ===================================================================
# Room
# ===================================================================
class RoomSerializer(serializers.ModelSerializer):
    room_type_display = serializers.CharField(source="get_room_type_display", read_only=True)
    deposit_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Room
        fields = [
            "id", "business", "name", "room_type", "room_type_display",
            "capacity", "photo", "deposit_tier", "deposit_price",
            "deposit_amount", "created_at",
        ]
        read_only_fields = ["id", "business", "created_at"]

    def validate_deposit_tier(self, value):
        if not value:
            raise serializers.ValidationError(
                "Restoran xonasi uchun depozit tarifi (premium/pro) tanlanishi shart."
            )
        return value


# ===================================================================
# Hall
# ===================================================================
class HallSerializer(serializers.ModelSerializer):
    deposit_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Hall
        fields = [
            "id", "business", "name", "people", "photo", "package",
            "all_price", "deposit_price", "deposit_amount", "created_at",
        ]
        read_only_fields = ["id", "business", "created_at"]


# ===================================================================
# VenuePricing
# ===================================================================
class VenuePricingSerializer(serializers.ModelSerializer):
    """To'yxonada 1/2/3 xil taom uchun kishi boshiga narx."""

    class Meta:
        model = VenuePricing
        fields = ["id", "business", "dish_count", "price_per_person"]
        read_only_fields = ["id", "business"]


# ===================================================================
# Business
# ===================================================================
class BusinessListSerializer(serializers.ModelSerializer):
    """
    Ommaviy ro'yxat (kartochka) ko'rinishi.

    `rooms_count` / `halls_count` annotate orqali keladi, `reviews_count`
    esa modelda denormalizatsiya qilingan — ro'yxat so'rovi qo'shimcha
    JOIN qilmasligi uchun.
    """

    business_type_display = serializers.CharField(source="get_business_type_display", read_only=True)
    cuisine_display = serializers.CharField(source="get_cuisine_display", read_only=True)
    rooms_count = serializers.IntegerField(read_only=True, default=0)
    halls_count = serializers.IntegerField(read_only=True, default=0)
    min_capacity = serializers.IntegerField(read_only=True, required=False)
    max_capacity = serializers.IntegerField(read_only=True, required=False)
    distance_km = serializers.FloatField(read_only=True, required=False)

    class Meta:
        model = Business
        fields = [
            "id", "name", "business_type", "business_type_display",
            "address", "district", "latitude", "longitude",
            "description", "cover_photo", "cuisine", "cuisine_display",
            "open_time", "close_time", "rating_avg", "reviews_count",
            "rooms_count", "halls_count", "min_capacity", "max_capacity", "distance_km",
        ]


class BusinessDetailSerializer(serializers.ModelSerializer):
    """
    Bitta biznesning to'liq profili — galereya, xona/zallar, menyu va
    narx paketlari bilan. Mobil ilovadagi detal sahifasi shu bitta
    so'rov bilan to'liq to'ladi (N+1 so'rov bo'lmaydi).
    """

    business_type_display = serializers.CharField(source="get_business_type_display", read_only=True)
    cuisine_display = serializers.CharField(source="get_cuisine_display", read_only=True)
    gallery = BusinessPhotoSerializer(source="photos", many=True, read_only=True)
    rooms = serializers.SerializerMethodField()
    halls = serializers.SerializerMethodField()
    menu = serializers.SerializerMethodField()
    dish_pricing = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Business
        fields = [
            "id", "name", "business_type", "business_type_display",
            "address", "district", "latitude", "longitude",
            "description", "cover_photo", "gallery",
            "cuisine", "cuisine_display", "open_time", "close_time",
            "rating_avg", "reviews_count", "telegram_username",
            "is_visible", "owner_username",
            "rooms", "halls", "menu", "dish_pricing", "created_at",
        ]

    def get_rooms(self, obj) -> list:
        if obj.business_type != Business.TYPE_RESTAURANT:
            return []
        return RoomSerializer(obj.rooms.all(), many=True, context=self.context).data

    def get_halls(self, obj) -> list:
        if obj.business_type != Business.TYPE_VENUE:
            return []
        return HallSerializer(obj.halls.all(), many=True, context=self.context).data

    def get_menu(self, obj) -> list:
        # Aylanma importdan qochish uchun shu yerda import qilinadi.
        from catalog.routes.serializers import (
            RestaurantMenuItemSerializer,
            VenueMenuItemSerializer,
        )
        if obj.business_type == Business.TYPE_RESTAURANT:
            items = [i for i in obj.restaurant_menu_items.all() if i.is_available]
            return RestaurantMenuItemSerializer(items, many=True, context=self.context).data
        return VenueMenuItemSerializer(
            obj.venue_menu_items.all(), many=True, context=self.context
        ).data

    def get_dish_pricing(self, obj) -> list:
        if obj.business_type != Business.TYPE_VENUE:
            return []
        return VenuePricingSerializer(obj.pricings.all(), many=True).data


class BusinessUpdateSerializer(serializers.ModelSerializer):
    """
    Biznes egasining "Sozlamalar" ekrani — faqat o'zi tahrirlay oladigan
    maydonlar. `business_type`, `owner`, `rating_avg`, `is_visible`
    bu yerda read-only: ularni egasi o'zgartira olmasligi kerak.
    """

    class Meta:
        model = Business
        fields = [
            "id", "name", "business_type", "address", "district",
            "latitude", "longitude", "description", "cover_photo",
            "cuisine", "open_time", "close_time", "telegram_username",
            "rating_avg", "reviews_count", "is_visible",
        ]
        read_only_fields = ["id", "business_type", "rating_avg", "reviews_count", "is_visible"]

    def validate(self, attrs):
        business_type = self.instance.business_type if self.instance else None
        if business_type == Business.TYPE_RESTAURANT:
            open_time = attrs.get("open_time", getattr(self.instance, "open_time", None))
            close_time = attrs.get("close_time", getattr(self.instance, "close_time", None))
            if open_time and close_time and open_time == close_time:
                raise serializers.ValidationError(
                    {"close_time": "Ish vaqti boshlanishi va tugashi bir xil bo'lolmaydi."}
                )
        return attrs


class BusinessAdminSerializer(serializers.ModelSerializer):
    """Admin panelidagi "Bizneslar" jadvali uchun."""

    owner_name = serializers.CharField(source="owner.full_name", read_only=True)
    owner_phone = serializers.CharField(source="owner.phone_number", read_only=True)
    subscription_status = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id", "name", "business_type", "address", "district", "owner",
            "owner_name", "owner_phone", "is_visible", "rating_avg",
            "reviews_count", "subscription_status", "created_at",
        ]

    def get_subscription_status(self, obj) -> str | None:
        subscription = getattr(obj, "subscription", None)
        return subscription.status if subscription else None


# ===================================================================
# BusinessApplication
# ===================================================================
class BusinessApplicationCreateSerializer(serializers.ModelSerializer):
    """
    "Restoran/To'yxona ochish" arizasi. TZ bo'yicha foydalanuvchidan faqat
    2 ta maydon so'raladi — biznes turi va nomi. Qolgan ma'lumot (ism,
    telefon, username) tokendagi foydalanuvchidan olinadi.
    """

    class Meta:
        model = BusinessApplication
        fields = ["business_type", "business_name"]

    def validate_business_name(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Biznes nomi kamida 3 ta belgidan iborat bo'lsin.")
        return value


class BusinessApplicationSerializer(serializers.ModelSerializer):
    """Ariza — ko'rish uchun (foydalanuvchi ham, admin ham shu ko'rinishni oladi)."""

    applicant_name = serializers.CharField(source="applicant.full_name", read_only=True)
    applicant_username = serializers.CharField(source="applicant.username", read_only=True)
    applicant_phone = serializers.CharField(source="applicant.phone_number", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    business_type_display = serializers.CharField(source="get_business_type_display", read_only=True)
    business_id = serializers.SerializerMethodField()

    class Meta:
        model = BusinessApplication
        fields = [
            "id", "applicant", "applicant_name", "applicant_username", "applicant_phone",
            "business_type", "business_type_display", "business_name",
            "status", "status_display", "business_id",
            "created_at", "approved_at", "approved_by",
        ]
        read_only_fields = fields

    def get_business_id(self, obj) -> str | None:
        business = getattr(obj, "business", None)
        return str(business.id) if business else None
