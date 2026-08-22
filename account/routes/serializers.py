"""account ilovasining BARCHA serializerlari shu faylda."""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from businesses.models import BusinessApplication

User = get_user_model()


class GoogleAuthSerializer(serializers.Serializer):
    """
    Vazifasi: /api/auth/google/ — brauzer Google'dan olgan `id_token`.

    Bu token IMZOLANGAN: uni server Google kalitlari bilan tekshiradi
    (`account.services.verify_google_token`). Shuning uchun ichidagi
    pochta va ismga ishonish mumkin — brauzer ularni o'zgartira olmaydi.
    """

    credential = serializers.CharField(
        write_only=True,
        help_text="Google Identity Services bergan id_token.",
    )


class LogoutSerializer(serializers.Serializer):
    """Chiqishda qora ro'yxatga qo'shiladigan refresh token."""

    refresh = serializers.CharField()


class BusinessBriefSerializer(serializers.Serializer):
    """
    Login javobiga qo'shiladigan qisqa biznes ma'lumoti.

    MUHIM: frontend aynan shu `type` maydoniga qarab qaysi boshqaruv
    panelini ochishini hal qiladi — `restaurant` bo'lsa "Xonalar" menyusi
    bilan restoran paneli, `venue` bo'lsa "Zallar" menyusi bilan to'yxona
    paneli. `role='admin'`/`is_staff` bo'lsa admin paneli ochiladi.
    """

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    type = serializers.CharField(source="business_type", read_only=True)
    is_visible = serializers.BooleanField(read_only=True)

    # Ariza tasdiqlanganmi.
    #
    # MANBA — ARIZANING O'Z HOLATI, obuna emas.
    #
    # Ilgari bu bayroq "obunasi bormi?" degan savolga qarardi, chunki
    # obuna faqat tasdiqdan keyin ochilardi. Lekin tasdiq bilan obuna
    # bir xil narsa emas va ular ajralib qoladigan haqiqiy holatlar bor:
    #   · admin arizani Django panelidagi shakl orqali "approved" qilsa
    #   · egasi bepul sinovni oldin ishlatgan bo'lsa — `approve_application`
    #     buni ataylab kechiradi: joy ochiladi, obuna esa ochilmaydi
    #   · obuna muddati tugab, `expired` holatida o'chirib tashlansa
    # Har uchalasida ham odam tasdiqlangan biznes egasi bo'lib turib,
    # panelga umuman kira olmasdi — aynan shu xato kuzatilgan.
    #
    # Endi: tasdiq — panelga KIRISH huquqi, obuna esa MA'LUMOT YOZISH
    # huquqi (`HasActiveSubscription`). Frontend ikkinchisini alohida
    # `subscription_status` orqali biladi.
    is_approved = serializers.SerializerMethodField()
    subscription_status = serializers.SerializerMethodField()

    def get_is_approved(self, obj) -> bool:
        application = getattr(obj, "application", None)
        if application is not None:
            return application.status == BusinessApplication.STATUS_APPROVED
        # Ariza yo'q biznes — faqat admin qo'lda ochgan holat. Uni
        # tasdiqlangan deb hisoblaymiz: admin o'zi yaratgan.
        return True

    def get_subscription_status(self, obj) -> str | None:
        subscription = getattr(obj, "subscription", None)
        return subscription.status if subscription else None


def build_user_payload(user, request=None):
    """Login va /me/ javoblarida bir xil ko'rinishdagi user obyektini quradi."""
    business = (
        user.businesses.select_related("application", "subscription").first()
        if user.role == "business" else None
    )

    avatar = user.avatar.url if user.avatar else None
    if avatar and request is not None:
        avatar = request.build_absolute_uri(avatar)

    return {
        "id": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "role": user.role,
        "is_staff": user.is_staff,
        "is_phone_verified": user.is_phone_verified,
        "is_confirmed": user.is_confirmed,
        # Frontend shu bayroqqa qarab "Bepul sinov" kartochkasining
        # tugmasini ochiq yoki yopiq qiladi.
        "has_used_trial": user.has_used_trial,
        "avatar": avatar,
        "initials": user.initials,
        "preferred_language": user.preferred_language,
        "business": BusinessBriefSerializer(business).data if business else None,
    }


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Vazifasi: login qilganda oddiy access/refresh tokendan tashqari,
    javobda foydalanuvchining ism-familiyasi, roli, tasdiqlanganlik
    holati va (bo'lsa) biznes profilini ham qaytaradi — frontend darhol
    shu javob bilan kerakli panelga yo'naltiradi, alohida /me/ so'rov
    yuborishi shart emas.
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = build_user_payload(self.user, self.context.get("request"))
        return data

    @classmethod
    def get_token(cls, user):
        # bu qism JWT payload ichiga yoziladi — frontend tokenni decode qilib
        # ham shu ma'lumotlarni serverga so'rovsiz o'qiy oladi
        token = super().get_token(user)
        token["full_name"] = user.full_name
        token["username"] = user.username
        token["role"] = user.role
        token["is_confirmed"] = user.is_confirmed
        return token


class UserSerializer(serializers.ModelSerializer):
    """
    /api/auth/me/ — profilni ko'rsatish va tahrirlash.

    `username` va `role` ataylab read-only: ular identifikator
    vazifasini bajaradi va o'zgarsa, eski bronlar kimga tegishli
    ekani chalkashib ketardi.

    `phone_number` — YARIM ochiq: BIR MARTA yoziladi, keyin qulflanadi.

    Sababi ro'yxatdan o'tish oqimida. Google raqam bermaydi, shuning
    uchun yangi hisobda u bo'sh bo'ladi va birinchi bron paytida
    so'raladi (`components/phone-gate.js`). Bir marta yozilgach esa
    o'zgartirib bo'lmaydi: joy egasi o'sha raqamga qo'ng'iroq qiladi
    va mehmon bronni yuborib, keyin raqamni almashtirib qo'ysa,
    egasi bog'lana olmasdi.

    Almashtirish kerak bo'lsa — administrator orqali.
    """

    business = serializers.SerializerMethodField()
    initials = serializers.CharField(read_only=True)
    stats = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "full_name", "phone_number",
            "avatar", "initials", "bio", "birth_date", "preferred_language",
            "role", "is_staff", "is_phone_verified", "is_confirmed",
            "has_used_trial", "business", "stats", "date_joined",
        ]
        read_only_fields = [
            "id", "username", "role", "is_staff",
            "is_phone_verified", "is_confirmed", "has_used_trial", "business", "stats",
            "initials", "date_joined",
        ]

    def validate_phone_number(self, value):
        """Raqam faqat BO'SH bo'lsa yoziladi."""
        if self.instance and self.instance.phone_number:
            raise serializers.ValidationError(
                "Raqam allaqachon kiritilgan. O'zgartirish uchun administrator "
                "bilan bog'laning."
            )
        return value

    def update(self, instance, validated_data):
        # Raqam kiritilgan bo'lsa, eski `is_phone_verified` bayrog'i ham
        # yoqiladi: admin panelidagi filtr va eski kod shunga qaraydi,
        # ma'nosi endi "raqami bor" degani.
        if validated_data.get("phone_number"):
            instance.is_phone_verified = True
        return super().update(instance, validated_data)

    def get_business(self, obj) -> dict | None:
        # `select_related` — `is_approved` arizaga, `subscription_status`
        # obunaga qaraydi; ikkalasi ham alohida so'rov bo'lmasin.
        business = obj.businesses.select_related("application", "subscription").first()
        return BusinessBriefSerializer(business).data if business else None

    def get_stats(self, obj) -> dict:
        """Profil bosh sahifasidagi raqamlar — bitta so'rovda."""
        from django.db.models import Count, Q

        return obj.reservations.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status="completed")),
            upcoming=Count("id", filter=Q(status__in=["pending", "confirmed"])),
        ) | {"reviews": obj.reviews.count()}


class AvatarSerializer(serializers.ModelSerializer):
    """/api/auth/me/avatar/ — faqat profil rasmini almashtirish uchun."""

    class Meta:
        model = User
        fields = ["avatar"]

    def validate_avatar(self, value):
        if value is None:
            raise serializers.ValidationError("Rasm tanlanmadi.")
        return value


class UserAdminSerializer(serializers.ModelSerializer):
    """Vazifasi: admin panelidagi "Foydalanuvchilar" jadvali uchun."""

    role_display = serializers.CharField(source="get_role_display", read_only=True)
    # Queryset'da `Exists()` bilan annotate qilinadi; annotatsiyasiz
    # chaqirilsa (masalan bitta obyekt uchun) False bo'lib qoladi.
    has_business = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = User
        fields = [
            "id", "username", "full_name", "phone_number",
            "role", "role_display", "is_phone_verified", "is_confirmed",
            "is_active", "is_staff", "has_business", "date_joined",
        ]
