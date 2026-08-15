from django.db import models

from businesses.models import Business
from common.models import BaseModel


class MenuItem(BaseModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="menu_items")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    photo = models.ImageField(upload_to="menu_items/", null=True, blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Package(BaseModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="packages")
    name = models.CharField(max_length=150)
    description = models.TextField()
    price_per_person = models.DecimalField(max_digits=12, decimal_places=2)
    min_guests = models.PositiveIntegerField(default=50)

    def __str__(self):
        return self.name