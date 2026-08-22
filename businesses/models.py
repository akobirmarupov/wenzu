from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from account.validators import validate_phone_number
from common.models import BaseModel
from common.validators import validate_image_file, validate_latitude, validate_longitude


class BusinessApplication(BaseModel):
    STATUS_PENDING = "pending_payment"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_PENDING, "To'lov kutilmoqda"),
        (STATUS_APPROVED, "Tasdiqlangan"),
        (STATUS_REJECTED, "Rad etilgan"),
    )
    BUSINESS_TYPE_CHOICES = (
        ("restaurant", "Restoran"),
        ("venue", "To'yxona"),
    )

    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    business_type = models.CharField(max_length=15, choices=BUSINESS_TYPE_CHOICES)
    business_name = models.CharField(max_length=200)

    # Ariza QAYSI tarif bilan berilgani.
    #
    # `None` — bepul sinov: tasdiqlangach 7 kunlik muddat ochiladi.
    # Reja ko'rsatilgan — pullik: tasdiqlangach obuna darhol o'sha
    # muddatga faollashadi, sinov berilmaydi (odam pul to'lagan, unga
    # yana bepul kun qo'shishning ma'nosi yo'q).
    plan = models.ForeignKey(
        "subscriptions.SubscriptionPlan", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="applications",
        verbose_name="Tanlangan tarif",
        help_text="Bo'sh — bepul sinov arizasi.",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_applications")

    class Meta:
        verbose_name = "Business Application"
        verbose_name_plural = "Business Applications"
        ordering = ["-created_at"]
        indexes = [
            # Admin panelidagi "kutilayotgan arizalar" — eng tez-tez so'raladigan filtr.
            models.Index(fields=["status", "-created_at"], name="idx_app_status_created"),
            models.Index(fields=["applicant", "status"], name="idx_app_applicant_status"),
        ]

    def __str__(self):
        return f"{self.business_name} ({self.get_status_display()})"


class Business(BaseModel):
    TYPE_RESTAURANT = "restaurant"
    TYPE_VENUE = "venue"
    TYPE_CHOICES = (
        (TYPE_RESTAURANT, "Restoran"),
        (TYPE_VENUE, "To'yxona"),
    )

    CUISINE_CHOICES = (
        ("milliy", "Milliy taomlar"),
        ("yevropa", "Yevropa oshxonasi"),
        ("fusion", "Fusion"),
        ("sharqona", "Sharqona"),
        ("fastfood", "Fast food"),
        ("boshqa", "Boshqa"),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="businesses")
    application = models.OneToOneField(BusinessApplication, on_delete=models.CASCADE, related_name="business")
    name = models.CharField(max_length=200, db_index=True)
    business_type = models.CharField(max_length=15, choices=TYPE_CHOICES, db_index=True)

    # --- joylashuv ---
    address = models.CharField(max_length=255, blank=True)
    district = models.CharField(
        max_length=100, blank=True, db_index=True,
        help_text="Tuman — qidiruvda nom bilan birga ishlatiladi (masalan: Yunusobod).",
    )
    latitude = models.FloatField(default=0, validators=[validate_latitude])
    longitude = models.FloatField(default=0, validators=[validate_longitude])

    # --- profil ---
    description = models.TextField(blank=True)
    cover_photo = models.ImageField(
        upload_to="business_covers/", null=True, blank=True, validators=[validate_image_file]
    )
    cuisine = models.CharField(
        max_length=20, choices=CUISINE_CHOICES, blank=True, db_index=True,
        help_text="Faqat restoranlar uchun oshxona turi.",
    )
    open_time = models.TimeField(null=True, blank=True, help_text="Ish boshlanish vaqti (restoran).")
    close_time = models.TimeField(null=True, blank=True, help_text="Ish tugash vaqti (restoran).")
    # --- aloqa ---
    #
    # MUHIM: bu ikki maydon faqat RO'YXATDAN O'TGAN foydalanuvchiga
    # ko'rinadi (`BusinessDetailSerializer` ga qarang). Sabab oddiy:
    # ochiq turgan telefon va Telegram bir kunda spam-botlar ro'yxatiga
    # tushadi, joy egasi esa buni bizdan biladi. Bron qilish uchun
    # baribir kirish kerak — ya'ni haqiqiy mijoz hech narsa yo'qotmaydi.
    telegram_username = models.CharField(
        max_length=32, blank=True,
        help_text="@ belgisiz. Mijoz depozit to'lovi uchun shu manzilga yozadi. "
                  "Faqat ro'yxatdan o'tgan foydalanuvchilarga ko'rinadi.",
    )
    phone_number = models.CharField(
        max_length=13, blank=True, validators=[validate_phone_number],
        verbose_name="Aloqa raqami",
        help_text="+998XXXXXXXXX. Faqat ro'yxatdan o'tgan foydalanuvchilarga ko'rinadi.",
    )

    # --- holat va denormalizatsiya ---
    is_visible = models.BooleanField(default=True, db_index=True)
    rating_avg = models.FloatField(default=0, db_index=True)
    reviews_count = models.PositiveIntegerField(
        default=0,
        help_text="Denormalizatsiya: ro'yxat so'rovida COUNT(*) qilmaslik uchun.",
    )

    class Meta:
        verbose_name_plural = "Businesses"
        ordering = ["-rating_avg", "-created_at"]
        indexes = [
            # Bosh sahifadagi asosiy so'rov: ko'rinadigan + turi bo'yicha + reyting tartibida.
            models.Index(fields=["is_visible", "business_type", "-rating_avg"], name="idx_biz_visible_type_rating"),
            models.Index(fields=["is_visible", "district"], name="idx_biz_visible_district"),
            models.Index(fields=["is_visible", "cuisine"], name="idx_biz_visible_cuisine"),
            # Geo-qidiruvdagi bounding box prefiltri shu indeksdan foydalanadi.
            models.Index(fields=["latitude", "longitude"], name="idx_biz_lat_lng"),
            models.Index(fields=["owner"], name="idx_biz_owner"),
        ]

    def __str__(self):
        return self.name


class BusinessPhoto(BaseModel):
    """
    Biznes galereyasi — detal sahifasidagi rasm karuseli.
    `cover_photo` bosh rasm bo'lib qoladi, bular qo'shimcha.
    """

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="business_photos/", validators=[validate_image_file])
    order = models.PositiveSmallIntegerField(default=0, help_text="Karuseldagi tartib.")

    class Meta:
        ordering = ["order", "created_at"]
        indexes = [models.Index(fields=["business", "order"], name="idx_bizphoto_business_order")]

    def __str__(self):
        return f"{self.business.name} — rasm #{self.order}"


class Room(BaseModel):
    """Restoran xonasi / stoli."""

    ROOM_TYPE_CHOICES = (
        ("vip", "VIP xona"),
        ("standard", "Oddiy zal"),
        ("outdoor", "Tashqi terrasa"),
    )

    DEPOSIT_TIER_PREMIUM = "premium"
    DEPOSIT_TIER_PRO = "pro"
    DEPOSIT_TIER_CHOICES = (
        (DEPOSIT_TIER_PREMIUM, "Premium"),
        (DEPOSIT_TIER_PRO, "Pro"),
    )

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="rooms")
    name = models.CharField(max_length=100)
    room_type = models.CharField(max_length=15, choices=ROOM_TYPE_CHOICES, db_index=True)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    photo = models.ImageField(
        upload_to="rooms/", null=True, blank=True, validators=[validate_image_file]
    )
    deposit_tier = models.CharField(
        max_length=10, choices=DEPOSIT_TIER_CHOICES, null=True, blank=True,
        help_text="Faqat restoranlar uchun. To'yxona zallarida bo'sh qoldiring.",
    )
    deposit_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Bo'sh qoldirilsa, tarifning platformadagi standart narxi olinadi.",
    )

    class Meta:
        ordering = ["capacity", "name"]
        indexes = [
            models.Index(fields=["business", "room_type"], name="idx_room_business_type"),
            models.Index(fields=["business", "capacity"], name="idx_room_business_capacity"),
        ]

    def __str__(self):
        return f"{self.business.name} — {self.name}"

    def clean(self):
        if self.business.business_type == Business.TYPE_RESTAURANT and not self.deposit_tier:
            raise ValidationError(
                {"deposit_tier": "Restoran xonasi uchun deposit tarifi (Premium/Pro) tanlanishi shart."}
            )
        if self.business.business_type == Business.TYPE_VENUE:
            raise ValidationError("Xona faqat restoranga qo'shiladi. To'yxona uchun Zal (Hall) ishlating.")

    @property
    def deposit_amount(self) -> Decimal:
        """
        Xonani bron qilishda oldindan to'lanadigan depozit.

        Egasi o'z narxini kiritsa (`deposit_price`) — o'sha, aks holda
        platformadagi tarif narxi (PlatformSettings) olinadi. Narx bitta
        joyda turgani uchun uni kodga tegmasdan o'zgartirish mumkin.
        """
        if self.deposit_price is not None:
            return self.deposit_price

        from common.models import PlatformSettings
        platform = PlatformSettings.get_solo()
        if self.deposit_tier == self.DEPOSIT_TIER_PREMIUM:
            return platform.room_deposit_premium
        return platform.room_deposit_pro


class Hall(BaseModel):
    """To'yxona zali."""

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="halls")
    name = models.CharField(max_length=100)
    people = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Zaldagi odamlar soni (masalan: 200, 500)",
    )
    photo = models.ImageField(
        upload_to="halls/", null=True, blank=True, validators=[validate_image_file]
    )
    package = models.CharField(max_length=255, null=True, blank=True)
    all_price = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="Qat'iy umumiy summa (ixtiyoriy — odatda narx kishi boshiga hisoblanadi).",
    )
    deposit_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Bron qilishda oldindan to'lov. Bo'sh qoldirilsa platforma standarti olinadi.",
    )

    class Meta:
        ordering = ["-people", "name"]
        indexes = [
            models.Index(fields=["business", "people"], name="idx_hall_business_people"),
        ]

    def __str__(self):
        return f"{self.business.name} — {self.name} ({self.people} kishilik)"

    def clean(self):
        if self.business.business_type == Business.TYPE_RESTAURANT:
            raise ValidationError("Zal faqat to'yxonaga qo'shiladi. Restoran uchun Xona (Room) ishlating.")

    @property
    def deposit_amount(self) -> Decimal:
        if self.deposit_price is not None:
            return self.deposit_price

        from common.models import PlatformSettings
        return PlatformSettings.get_solo().venue_deposit


class VenuePricing(BaseModel):
    """
    To'yxonada narx zalga emas, TAOM SONIGA bog'lanadi: mijoz 1, 2 yoki 3 xil
    taom tanlaydi va kishi boshiga narx shunga qarab o'zgaradi.

    Umumiy summa = price_per_person × mehmonlar soni.
    """

    DISH_COUNT_CHOICES = ((1, "1 xil taom"), (2, "2 xil taom"), (3, "3 xil taom"))

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="pricings")
    dish_count = models.PositiveSmallIntegerField(choices=DISH_COUNT_CHOICES)
    price_per_person = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal(0))]
    )

    class Meta:
        ordering = ["dish_count"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "dish_count"], name="uniq_venue_pricing_business_dish"
            )
        ]

    def __str__(self):
        return f"{self.business.name} — {self.dish_count} xil: {self.price_per_person}"

    def clean(self):
        if self.business.business_type != Business.TYPE_VENUE:
            raise ValidationError("Taom paketi narxi faqat to'yxonalar uchun belgilanadi.")
