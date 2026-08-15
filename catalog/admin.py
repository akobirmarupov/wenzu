from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import MenuItem, Package


@admin.register(MenuItem)
class MenuItemAdmin(ModelAdmin):
    list_display = ("name", "business", "price", "is_available", "created_at")
    list_filter = ("is_available", "business")
    list_filter_submit = True
    search_fields = ("name", "business__name")
    autocomplete_fields = ("business",)
    list_editable = ("is_available",)  # ro'yxatda to'g'ridan-to'g'ri o'zgartirish uchun


@admin.register(Package)
class PackageAdmin(ModelAdmin):
    list_display = ("name", "business", "price_per_person", "min_guests", "created_at")
    list_filter = ("business",)
    list_filter_submit = True
    search_fields = ("name", "business__name", "description")
    autocomplete_fields = ("business",)