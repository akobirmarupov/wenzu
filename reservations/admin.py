from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin, StackedInline

from .models import Availability, DepositTransaction, Reservation


class DepositTransactionInline(StackedInline):
    model = DepositTransaction
    extra = 0
    readonly_fields = ("refunded_at",)


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
    inlines = [DepositTransactionInline]

    actions = ["mark_confirmed", "mark_cancelled", "mark_completed"]

    @admin.action(description="Tanlanganlarni tasdiqlash (confirmed)")
    def mark_confirmed(self, request, queryset):
        updated = queryset.update(status="confirmed")
        self.message_user(request, f"{updated} ta bron tasdiqlandi.")

    @admin.action(description="Tanlanganlarni bekor qilish (cancelled)")
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status="cancelled")
        self.message_user(request, f"{updated} ta bron bekor qilindi.")

    @admin.action(description="Tanlanganlarni yakunlash (completed)")
    def mark_completed(self, request, queryset):
        updated = queryset.update(status="completed")
        self.message_user(request, f"{updated} ta bron yakunlandi.")


@admin.register(DepositTransaction)
class DepositTransactionAdmin(ModelAdmin):
    list_display = ("reservation", "amount", "status", "refund_deadline", "refunded_at", "confirmed_by")
    list_filter = ("status",)
    list_filter_submit = True
    search_fields = ("reservation__user__username", "reservation__business__name", "note")
    autocomplete_fields = ("reservation", "confirmed_by")
    readonly_fields = ("refunded_at",)

    actions = ["mark_refunded", "mark_forfeited"]

    @admin.action(description="Tanlanganlarni qaytarilgan deb belgilash (refunded)")
    def mark_refunded(self, request, queryset):
        updated = queryset.update(status=DepositTransaction.STATUS_REFUNDED, refunded_at=timezone.now())
        self.message_user(request, f"{updated} ta depozit qaytarildi.")

    @admin.action(description="Tanlanganlarni qaytarilmaydi deb belgilash (forfeited)")
    def mark_forfeited(self, request, queryset):
        updated = queryset.update(status=DepositTransaction.STATUS_FORFEITED)
        self.message_user(request, f"{updated} ta depozit qaytarilmaydigan deb belgilandi.")