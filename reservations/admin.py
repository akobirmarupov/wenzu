from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Availability, Reservation


@admin.register(Availability)
class AvailabilityAdmin(ModelAdmin):
    list_display = ("business", "room", "date", "start_time", "end_time", "is_booked")
    list_filter = ("is_booked", "business", "date")
    list_filter_submit = True
    search_fields = ("business__name", "room__name")
    autocomplete_fields = ("business", "room")
    date_hierarchy = "date"


@admin.register(Reservation)
class ReservationAdmin(ModelAdmin):
    list_display = ("user", "business", "room", "guests_count", "status", "created_at")
    list_filter = ("status", "business")
    list_filter_submit = True
    search_fields = ("user__username", "user__phone_number", "business__name", "room__name")
    autocomplete_fields = ("user", "business", "room", "availability")

    actions = ["mark_confirmed", "mark_cancelled", "mark_completed"]

    @admin.action(description="Tanlanganlarni tasdiqlash (confirmed)")
    def mark_confirmed(self, request, queryset):
        updated = queryset.update(status="confirmed")
        self.message_user(request, f"{updated} ta bron tasdiqlandi.")

    @admin.action(description="Tanlanganlarni bekor qilish (cancelled)")
    def mark_cancelled(self, request, queryset):
        for reservation in queryset:
            reservation.status = "cancelled"
            reservation.save(update_fields=["status"])
            if reservation.availability_id:
                reservation.availability.is_booked = False
                reservation.availability.save(update_fields=["is_booked"])
        self.message_user(request, f"{queryset.count()} ta bron bekor qilindi va bo'sh vaqt qayta ochildi.")

    @admin.action(description="Tanlanganlarni yakunlash (completed)")
    def mark_completed(self, request, queryset):
        updated = queryset.update(status="completed")
        self.message_user(request, f"{updated} ta bron yakunlandi.")