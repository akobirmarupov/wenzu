from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import PaymentLog, Subscription, SubscriptionPlan


class PaymentLogInline(TabularInline):
    model = PaymentLog
    extra = 0
    fields = ("amount", "confirmed_by", "note", "created_at")
    readonly_fields = ("created_at",)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(ModelAdmin):
    list_display = ("business_type", "price", "trial_days")
    list_filter = ("business_type",)
    list_filter_submit = True
    search_fields = ("business_type",)


@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = ("business", "plan", "status", "trial_ends_at", "subscription_ends_at", "approved_by")
    list_filter = ("status", "plan")
    list_filter_submit = True
    search_fields = ("business__name",)
    autocomplete_fields = ("business", "plan", "approved_by")
    inlines = [PaymentLogInline]

    actions = ["mark_active", "mark_expired"]

    @admin.action(description="Tanlanganlarni faollashtirish (active)")
    def mark_active(self, request, queryset):
        updated = queryset.update(status="active")
        self.message_user(request, f"{updated} ta obuna faollashtirildi.")

    @admin.action(description="Tanlanganlarni muddati tugagan deb belgilash (expired)")
    def mark_expired(self, request, queryset):
        updated = queryset.update(status="expired")
        self.message_user(request, f"{updated} ta obunaning muddati tugagan deb belgilandi.")


@admin.register(PaymentLog)
class PaymentLogAdmin(ModelAdmin):
    list_display = ("subscription", "amount", "confirmed_by", "created_at")
    search_fields = ("subscription__business__name", "note")
    autocomplete_fields = ("subscription", "confirmed_by")