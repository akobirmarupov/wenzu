import json

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from unfold.admin import ModelAdmin

from businesses.models import Business

from .forms import MONTH_CHOICES, GenerateAvailabilityForm
from .models import Availability, Reservation


def build_businesses_data():
    """
    {business_id: {"type": ..., "rooms": [...]}} ko'rinishidagi lug'at —
    admin sahifalaridagi JS orqali Business tanlanganda Room maydonini
    ko'rsatish/yashirish va bog'liq autocomplete'larni filtrlash uchun.
    """
    return {
        str(business.id): {
            "type": business.business_type,
            "rooms": [
                {"id": str(room.id), "name": room.name}
                for room in business.rooms.all().order_by("name")
            ],
        }
        for business in Business.objects.all().prefetch_related("rooms")
    }


@admin.register(Availability)
class AvailabilityAdmin(ModelAdmin):
    list_display = ("business", "room", "date", "start_time", "end_time", "is_booked")
    list_filter = ("is_booked", "business", "date")
    list_filter_submit = True
    search_fields = ("business__name", "room__name")
    autocomplete_fields = ("business", "room")
    date_hierarchy = "date"

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(request, queryset, search_term)

        # "Bronlar" formasidagi Availability autocomplete'i shu yerga
        # ?business_id=... qo'shib so'rov yuboradi (dependent_fields.js) —
        # shunda faqat shu businessga tegishli VA hali band bo'lmagan
        # bo'sh vaqtlar ko'rsatiladi.
        business_id = request.GET.get("business_id")
        if business_id:
            queryset = queryset.filter(business_id=business_id, is_booked=False)

        return queryset, may_have_duplicates

    # ------------------------------------------------------------------
    # "Add" sahifasi: bitta kun o'rniga OYLAR bo'yicha ommaviy generatsiya.
    #
    # Restoran: Business + Room tanlanadi.
    # To'yxona: faqat Business tanlanadi, Room maydoni yashirin bo'ladi
    #           (bitta to'yxonada bir kunda faqat bitta to'y bo'lishi
    #           mumkin, shu sabab room tushunchasi yo'q).
    #
    # Tanlangan har bir oyning HAR BIR kuni uchun start_time/end_time
    # bilan Availability yozuvi yaratiladi (Availability.generate_for_months).
    # ------------------------------------------------------------------

    def add_view(self, request, form_url="", extra_context=None):
        if not self.has_add_permission(request):
            raise PermissionDenied

        if request.method == "POST":
            form = GenerateAvailabilityForm(request.POST)
            if form.is_valid():
                business = form.cleaned_data["business"]
                room = form.cleaned_data.get("room")
                start_time = form.cleaned_data["start_time"]
                end_time = form.cleaned_data["end_time"]
                months = form.get_month_dates()

                created, skipped = Availability.generate_for_months(
                    business=business,
                    room=room,
                    start_time=start_time,
                    end_time=end_time,
                    months=months,
                )

                if created:
                    self.message_user(
                        request,
                        f"{created} ta kun uchun bo'sh vaqt yaratildi. "
                        f"{skipped} ta kun allaqachon mavjud bo'lgani uchun o'tkazib yuborildi.",
                        level=messages.SUCCESS,
                    )
                else:
                    self.message_user(
                        request,
                        "Yangi yozuv yaratilmadi — tanlangan oylarning barcha kunlari uchun "
                        "bo'sh vaqt allaqachon mavjud.",
                        level=messages.WARNING,
                    )

                if "_addanother" in request.POST:
                    return HttpResponseRedirect(request.path)
                return HttpResponseRedirect(
                    reverse("admin:reservations_availability_changelist")
                )
        else:
            form = GenerateAvailabilityForm()

        selected_months = [str(m) for m in (form.data.getlist("months") if form.is_bound else [])]

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Bo'sh vaqt qo'shish — oylar bo'yicha",
            "form": form,
            "month_choices": MONTH_CHOICES,
            "selected_months": selected_months,
            "businesses_data_json": json.dumps(build_businesses_data()),
            "type_restaurant": Business.TYPE_RESTAURANT,
            "type_venue": Business.TYPE_VENUE,
        }
        if extra_context:
            context.update(extra_context)

        request.current_app = self.admin_site.name
        return TemplateResponse(
            request,
            "admin/reservations/availability/generate_form.html",
            context,
        )


@admin.register(Reservation)
class ReservationAdmin(ModelAdmin):
    list_display = ("user", "business", "room", "hall", "guests_count", "deposit_amount", "status", "created_at")
    list_filter = ("status", "business")
    list_filter_submit = True
    search_fields = ("user__username", "user__phone_number", "business__name", "room__name")
    autocomplete_fields = ("user", "business", "room", "hall", "availability")
    list_select_related = ("user", "business", "room", "hall")

    class Media:
        js = ("admin/reservations/dependent_fields.js",)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        # Add ham, Change ham shu metodga tushadi — ikkalasida ham
        # dependent_fields.js uchun kerakli JSON'ni beramiz.
        extra_context = extra_context or {}
        extra_context["businesses_data_json"] = json.dumps(build_businesses_data())
        return super().changeform_view(request, object_id, form_url, extra_context)

    actions = ["mark_confirmed", "mark_cancelled", "mark_completed"]

    @admin.action(description="Tanlanganlarni tasdiqlash (confirmed)")
    def mark_confirmed(self, request, queryset):
        # queryset.update() bulk bo'lgani uchun post_save signalini
        # ishga tushirmaydi — shuning uchun har birini alohida saqlaymiz,
        # bog'liq Availability.is_booked ham avtomatik yangilansin.
        count = 0
        for reservation in queryset:
            reservation.status = "confirmed"
            reservation.save(update_fields=["status"])
            count += 1
        self.message_user(request, f"{count} ta bron tasdiqlandi.")

    @admin.action(description="Tanlanganlarni bekor qilish (cancelled)")
    def mark_cancelled(self, request, queryset):
        # `is_booked` ni bu yerda QO'LDA o'zgartirmaymiz: restoranda bitta
        # kunda bir nechta bron bo'lishi mumkin, bittasini bekor qilish
        # butun kunni bo'shatib yubormasligi kerak. Buni post_save signali
        # biznes turiga qarab to'g'ri hal qiladi.
        count = 0
        for reservation in queryset:
            reservation.status = "cancelled"
            reservation.save(update_fields=["status"])
            count += 1
        self.message_user(request, f"{count} ta bron bekor qilindi.")

    @admin.action(description="Tanlanganlarni yakunlash (completed)")
    def mark_completed(self, request, queryset):
        # queryset.update() signalni ishga tushirmaydi — shuning uchun
        # bu yerda ham bittalab saqlaymiz (qolgan action'lar bilan bir xil).
        count = 0
        for reservation in queryset:
            reservation.status = "completed"
            reservation.save(update_fields=["status"])
            count += 1
        self.message_user(request, f"{count} ta bron yakunlandi.")