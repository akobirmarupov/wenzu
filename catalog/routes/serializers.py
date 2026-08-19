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
