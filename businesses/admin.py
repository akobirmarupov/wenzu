from django.contrib import admin

from .models import Business, BusinessApplication, Room


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
    fields = ("name", "room_type", "capacity", "price_per_slot", "deposit_tier")


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        "name", "business_type", "owner", "is_visible",
        "telegram_username", "rating_avg",
    )
    list_filter = ("business_type", "is_visible")
    search_fields = ("name", "address", "owner__username", "owner__full_name")
    inlines = [RoomInline]
    readonly_fields = ("rating_avg",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("business", "name", "room_type", "capacity", "price_per_slot", "deposit_tier")
    list_filter = ("room_type", "deposit_tier", "business__business_type")
    search_fields = ("name", "business__name")


@admin.register(BusinessApplication)
class BusinessApplicationAdmin(admin.ModelAdmin):
    list_display = ("business_name", "business_type", "applicant", "status", "created_at", "approved_at")
    list_filter = ("business_type", "status")
    search_fields = ("business_name", "applicant__username", "applicant__phone_number")
    readonly_fields = ("approved_at", "approved_by")