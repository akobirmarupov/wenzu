from django.contrib import admin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from .models import Business, BusinessApplication, BusinessPhoto, Hall, Room, VenuePricing


class RoomInline(TabularInline):
    model = Room
    extra = 1
    fields = ("name", "room_type", "capacity", "deposit_tier")


class BusinessPhotoInline(TabularInline):
    model = BusinessPhoto
    extra = 1
    fields = ("image", "order")


class VenuePricingInline(TabularInline):
    model = VenuePricing
    extra = 0
    fields = ("dish_count", "price_per_person")


class HallInline(TabularInline):
    model = Hall
    extra = 1
    fields = ("name", "people", "all_price", "deposit_price")


@admin.register(Business)
class BusinessAdmin(ModelAdmin):
    list_display = (
        "name", "business_type", "district", "owner", "is_visible",
        "telegram_username", "rating_avg", "reviews_count",
    )
    list_filter = ("business_type", "is_visible", "district", "cuisine")
    search_fields = ("name", "address", "district", "owner__username", "owner__full_name")
    readonly_fields = ("rating_avg", "reviews_count")
    list_select_related = ("owner",)

    def get_inlines(self, request, obj=None):
        if obj is None:
            return []
        if obj.business_type == Business.TYPE_RESTAURANT:
            return [BusinessPhotoInline, RoomInline]
        if obj.business_type == Business.TYPE_VENUE:
            return [BusinessPhotoInline, HallInline, VenuePricingInline]
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

    actions = ["approve_payment", "reject"]

    @admin.action(description=_("To'lovni tasdiqlash (obuna 30 kunga faollashadi)"))
    def approve_payment(self, request, queryset):
        # API va admin panel bir xil servis funksiyasini chaqiradi —
        # shunda oqim ikki joyda ikki xil bo'lib ketmaydi.
        from businesses.services import approve_application

        count = 0
        for application in queryset.exclude(status="approved"):
            approve_application(application=application, approved_by=request.user)
            count += 1
        self.message_user(request, f"{count} ta ariza tasdiqlandi va obuna faollashtirildi.")

    @admin.action(description=_("Arizani rad etish"))
    def reject(self, request, queryset):
        from businesses.services import reject_application

        count = 0
        for application in queryset.exclude(status="rejected"):
            reject_application(application=application, rejected_by=request.user)
            count += 1
        self.message_user(request, f"{count} ta ariza rad etildi.")

@admin.register(VenuePricing)
class VenuePricingAdmin(ModelAdmin):
    list_display = ("business", "dish_count", "price_per_person")
    list_filter = ("dish_count",)
    search_fields = ("business__name",)
    autocomplete_fields = ("business",)


@admin.register(BusinessPhoto)
class BusinessPhotoAdmin(ModelAdmin):
    list_display = ("business", "order", "created_at")
    search_fields = ("business__name",)
    autocomplete_fields = ("business",)
