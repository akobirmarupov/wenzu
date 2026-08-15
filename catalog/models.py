from django.db import models

from businesses.models import Business, Hall
from common.models import BaseModel


class RestaurantMenuItem(BaseModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="restaurant_menu_items")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    photo = models.ImageField(upload_to="restaurant_menu/", null=True, blank=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Restaurant Menu Item"

    def __str__(self):
        return self.name


 
class VenueMenuItem(BaseModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="venue_menu_items")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="venue_menu/", null=True, blank=True)
 
    class Meta:
        verbose_name = "Venue Menu Item"
 
    def __str__(self):
        return f"{self.business.name} — {self.name}"
 