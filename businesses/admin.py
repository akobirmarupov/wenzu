from django.contrib import admin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from .models import Business, BusinessApplication, Hall, Room


class RoomInline(TabularInline):
    model = Room
    extra = 1
    fields = ("name", "room_type", "capacity", "price_per_slot", "deposit_tier")


class HallInline(TabularInline):
    model = Hall
    extra = 1
    fields = ("name", "people", "all_price", "deposit_price")


@admin.register(Business)
class BusinessAdmin(ModelAdmin):
    list_display = (
        "name", "business_type", "owner", "is_visible",
        "telegram_username", "rating_avg",
    )
    list_filter = ("business_type", "is_visible")
    search_fields = ("name", "address", "owner__username", "owner__full_name")
    readonly_fields = ("rating_avg",)

    def get_inlines(self, request, obj=None):
        if obj is None:
            return []
        if obj.business_type == Business.TYPE_RESTAURANT:
            return [RoomInline]
        if obj.business_type == Business.TYPE_VENUE:
            return [HallInline]
        return []


@admin.register(Room)
class RoomAdmin(ModelAdmin):
    list_display = ("business", "name", "room_type", "capacity", "deposit_tier")
    list_filter = ("room_type", "deposit_tier", "business__business_type")
    search_fields = ("name", "business__name")
    actions_detail = ["quick_add_room"]

    @action(description=_("Yangi xona qo'shish"), url_path="quick-add-room")
    def quick_add_room(self, request, object_id):
        from django.shortcuts import redirect
        return redirect(reverse("admin:businesses_room_add"))


@admin.register(Hall)
class HallAdmin(ModelAdmin):
    list_display = ("business", "name", "people", "package", "all_price", "deposit_price")
    list_filter = ("business__business_type",)
    search_fields = ("name", "business__name")
    actions_detail = ["quick_add_hall"]

    @action(description=_("Yangi zal qo'shish"), url_path="quick-add-hall")
    def quick_add_hall(self, request, object_id):
        from django.shortcuts import redirect
        return redirect(reverse("admin:businesses_hall_add"))


@admin.register(BusinessApplication)
class BusinessApplicationAdmin(ModelAdmin):
    list_display = ("business_name", "business_type", "applicant", "status", "created_at", "approved_at")
    list_filter = ("business_type", "status")
    search_fields = ("business_name", "applicant__username", "applicant__phone_number")
    readonly_fields = ("approved_at", "approved_by")