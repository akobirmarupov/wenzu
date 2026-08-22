"""catalog ilovasining BARCHA serializerlari shu faylda."""

from rest_framework import serializers

from catalog.models import RestaurantMenuItem, VenueMenuItem


class RestaurantMenuItemSerializer(serializers.ModelSerializer):
    """Restoran menyusidagi taom — narxi bor, mavjudligi o'zgarib turadi."""

    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = RestaurantMenuItem
        fields = [
            "id", "business", "name", "category", "category_display",
            "description", "price", "photo", "is_available", "created_at",
        ]
        read_only_fields = ["id", "business", "created_at"]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Narx manfiy bo'lolmaydi.")
        return value


class VenueMenuItemSerializer(serializers.ModelSerializer):
    """
    To'yxona menyusidagi taom — narxi YO'Q, chunki to'yxonada narx alohida
    taomga emas, taom soniga (VenuePricing) bog'lanadi.
    """

    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = VenueMenuItem
        fields = [
            "id", "business", "name", "category", "category_display",
            "description", "photo", "created_at",
        ]
        read_only_fields = ["id", "business", "created_at"]


# ===================================================================
# Bosh sahifadagi menyu vitrinasi
#
# Bosh sahifa BITTA joyning menyusini emas, PLATFORMADAGI taomlarni
# ko'rsatadi. Shu sababli har bir taom bilan birga qaysi joyga tegishli
# ekani ham keladi — aks holda foydalanuvchi bosganda qayerga o'tishini
# bilmaydi.
# ===================================================================
class ShowcaseRestaurantMenuItemSerializer(serializers.ModelSerializer):
    """Bosh sahifa: restoran taomi + qaysi restoranniki."""

    category_display = serializers.CharField(source="get_category_display", read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    business_district = serializers.CharField(source="business.district", read_only=True)

    class Meta:
        model = RestaurantMenuItem
        fields = [
            "id", "business", "business_name", "business_district",
            "name", "category", "category_display", "price", "photo",
        ]


class ShowcaseVenueMenuItemSerializer(serializers.ModelSerializer):
    """
    Bosh sahifa: to'yxona taomi + qaysi to'yxonaniki.

    To'yxonada taomning o'z narxi yo'q — narx taom soniga bog'lanadi.
    Shuning uchun bu yerda joyning eng arzon "kishi boshiga" narxi
    beriladi: foydalanuvchi taxminiy summani darrov ko'rsin.
    """

    category_display = serializers.CharField(source="get_category_display", read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    business_district = serializers.CharField(source="business.district", read_only=True)
    price_from = serializers.SerializerMethodField()

    class Meta:
        model = VenueMenuItem
        fields = [
            "id", "business", "business_name", "business_district",
            "name", "category", "category_display", "photo", "price_from",
        ]

    def get_price_from(self, obj) -> str | None:
        # `min_price` — queryset'da annotate qilinadi, qo'shimcha so'rov yo'q.
        value = getattr(obj, "min_price", None)
        return str(value) if value is not None else None
