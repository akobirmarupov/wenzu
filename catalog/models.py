from django.db import models

from businesses.models import Business
from common.models import BaseModel
from common.validators import validate_image_file


class MenuCategory(models.TextChoices):
    """Menyudagi taomlarni guruhlash uchun — mijoz ekranida bo'limlarga ajraladi."""

    STARTER = "starter", "Boshlang'ich"
    SOUP = "soup", "Sho'rva"
    MAIN = "main", "Asosiy taom"
    SALAD = "salad", "Salat"
    DESSERT = "dessert", "Desert"
    DRINK = "drink", "Ichimlik"
    OTHER = "other", "Boshqa"


class RestaurantMenuItem(BaseModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="restaurant_menu_items")
    name = models.CharField(max_length=150)
    category = models.CharField(
        max_length=15, choices=MenuCategory.choices, default=MenuCategory.MAIN, db_index=True
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    photo = models.ImageField(
        upload_to="restaurant_menu/", null=True, blank=True, validators=[validate_image_file]
    )
    is_available = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Restaurant Menu Item"
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["business", "is_available"], name="idx_rmenu_business_available"),
            models.Index(fields=["business", "category"], name="idx_rmenu_business_category"),
        ]

    def __str__(self):
        return self.name


class VenueMenuItem(BaseModel):
    """
    To'yxona menyusidagi taom — narxi YO'Q, chunki to'yxonada narx alohida
    taomga emas, taom soniga (VenuePricing) bog'lanadi.
    """

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="venue_menu_items")
    name = models.CharField(max_length=150)
    category = models.CharField(
        max_length=15, choices=MenuCategory.choices, default=MenuCategory.MAIN, db_index=True
    )
    description = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to="venue_menu/", null=True, blank=True, validators=[validate_image_file]
    )

    class Meta:
        verbose_name = "Venue Menu Item"
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["business", "category"], name="idx_vmenu_business_category"),
        ]

    def __str__(self):
        return f"{self.business.name} — {self.name}"
