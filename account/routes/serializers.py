"""account ilovasining BARCHA serializerlari shu faylda."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Vazifasi: /api/auth/register/ — yangi foydalanuvchini yaratadi."""

    password = serializers.CharField(
        write_only=True, validators=[validate_password], style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "full_name", "phone_number", "username", "password", "password_confirm"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Parollar mos kelmadi."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        # role alohida yozish shart emas — model maydonida
        # default=Role.USER o'rnatilgan, avtomatik shu bo'ladi.
        user.save()
        return user


class LogoutSerializer(serializers.Serializer):
    """Chiqishda qora ro'yxatga qo'shiladigan refresh token."""

    refresh = serializers.CharField()


class SendCodeSerializer(serializers.Serializer):
    """Vazifasi: /api/auth/send-code/ — shu raqamga SMS-kod yuborish so'rovi."""

    phone_number = serializers.CharField(max_length=13)


class VerifyPhoneSerializer(serializers.Serializer):
    """Vazifasi: /api/auth/verify-phone/ — SMS-kodni tekshirish uchun input."""

    phone_number = serializers.CharField(max_length=13)
    code = serializers.CharField(max_length=6)


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
    # Obuna faqat admin tasdig'idan keyin ochiladi, ya'ni obunaning
    # MAVJUDLIGI — "tasdiqlangan"ning o'zi. Frontend shu bayroqqa qarab
    # boshqaruv paneliga kiritadi yoki "ariza ko'rib chiqilmoqda"
    # sahifasiga qaytaradi.
    is_approved = serializers.SerializerMethodField()
    subscription_status = serializers.SerializerMethodField()

    def get_is_approved(self, obj) -> bool:
        return hasattr(obj, "subscription")

    def get_subscription_status(self, obj) -> str | None:
        subscription = getattr(obj, "subscription", None)
        return subscription.status if subscription else None


def build_user_payload(user, request=None):
    """Login va /me/ javoblarida bir xil ko'rinishdagi user obyektini quradi."""
    business = (
        user.businesses.select_related("subscription").first()
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

    `username`, `phone_number` va `role` ataylab read-only: ular
    identifikator vazifasini bajaradi va o'zgarsa, eski bronlar
    kimga tegishli ekani chalkashib ketardi.
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
            "id", "username", "phone_number", "role", "is_staff",
            "is_phone_verified", "is_confirmed", "has_used_trial", "business", "stats",
            "initials", "date_joined",
        ]

    def get_business(self, obj) -> dict | None:
        # `select_related` — `is_approved` obunaga qaraydi, alohida
        # so'rov bo'lmasin.
        business = obj.businesses.select_related("subscription").first()
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
