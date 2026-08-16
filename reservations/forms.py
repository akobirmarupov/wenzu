import datetime

from django import forms
from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultipleWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTimeWidget,
)

from businesses.models import Business, Room

MONTH_CHOICES = [
    (1, "Yanvar"), (2, "Fevral"), (3, "Mart"), (4, "Aprel"),
    (5, "May"), (6, "Iyun"), (7, "Iyul"), (8, "Avgust"),
    (9, "Sentyabr"), (10, "Oktyabr"), (11, "Noyabr"), (12, "Dekabr"),
]


class GenerateAvailabilityForm(forms.Form):
    """
    "Bo'sh vaqtlar" bo'limidagi Add sahifasi uchun forma.

    Bitta kunni emas, balki bir nechta OYNI tanlab, shu oylarning
    barcha kunlari uchun bitta shablon (start_time/end_time) bo'yicha
    Availability yozuvlarini avtomatik generatsiya qiladi
    (Availability.generate_for_months orqali).
    """

    business = forms.ModelChoiceField(
        queryset=Business.objects.all().order_by("name"),
        label="Business",
        widget=UnfoldAdminSelectWidget(attrs={"id": "id_business"}),
    )
    room = forms.ModelChoiceField(
        queryset=Room.objects.none(),
        required=False,
        label="Room",
        widget=UnfoldAdminSelectWidget(attrs={"id": "id_room"}),
        help_text=(
            "Faqat restoran uchun. To'yxona uchun bo'sh qoldiriladi — "
            "to'yxonada bo'sh vaqt Room emas, butun business darajasida hisoblanadi."
        ),
    )
    start_time = forms.TimeField(
        label="Start time",
        widget=UnfoldAdminTimeWidget(attrs={"id": "id_start_time"}),
    )
    end_time = forms.TimeField(
        label="End time",
        widget=UnfoldAdminTimeWidget(attrs={"id": "id_end_time"}),
        help_text="To'yxona uchun 00:00 — yarim tungacha (kunning oxirigacha) degani.",
    )
    year = forms.TypedChoiceField(
        label="Yil",
        choices=[],
        coerce=int,
        widget=UnfoldAdminSelectWidget(attrs={"id": "id_year"}),
    )
    months = forms.MultipleChoiceField(
        label="Oylar",
        choices=MONTH_CHOICES,
        widget=UnfoldAdminCheckboxSelectMultipleWidget,
        error_messages={"required": "Kamida bitta oy tanlanishi kerak."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_year = datetime.date.today().year
        year_choices = [(y, str(y)) for y in range(current_year, current_year + 3)]
        self.fields["year"].choices = year_choices
        self.fields["year"].initial = current_year

        # Formaga POST qilingan (yoki initial) business bo'yicha room
        # queryset'ini cheklaymiz — bu faqat server tomonlama validatsiya
        # uchun kerak, UI'da room ro'yxati JS orqali to'ldiriladi.
        business_id = self.data.get("business") or self.initial.get("business")
        if business_id:
            try:
                self.fields["room"].queryset = Room.objects.filter(
                    business_id=business_id
                ).order_by("name")
            except (TypeError, ValueError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        business = cleaned_data.get("business")
        room = cleaned_data.get("room")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if not business:
            return cleaned_data

        is_restaurant = business.business_type == Business.TYPE_RESTAURANT

        if is_restaurant and not room:
            self.add_error("room", "Restoran uchun room tanlanishi shart.")
        elif not is_restaurant and room:
            self.add_error("room", "To'yxona uchun room tanlanmaydi — bo'sh qoldiring.")
        elif room and room.business_id != business.id:
            self.add_error("room", "Bu room ushbu businessga tegishli emas.")

        if start_time and end_time:
            # To'yxona uchun end_time == 00:00 "yarim tungacha" (butun kun)
            # degan maxsus holat sifatida qabul qilinadi.
            is_midnight_end = (not is_restaurant) and end_time == datetime.time(0, 0)
            if not is_midnight_end and end_time <= start_time:
                self.add_error("end_time", "End time start time'dan keyin bo'lishi kerak.")

        return cleaned_data

    def get_month_dates(self):
        year = self.cleaned_data["year"]
        months = sorted(int(m) for m in self.cleaned_data["months"])
        return [datetime.date(year, m, 1) for m in months]