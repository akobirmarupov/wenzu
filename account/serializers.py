from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Vazifasi: /api/auth/register/ — yangi foydalanuvchini yaratadi."""

    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "full_name", "phone_number", "username", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        # role alohida yozish shart emas — model maydonida
        # default=User.Role.USER o'rnatilgan, avtomatik shu bo'ladi.
        user.save()
        return user


class VerifyPhoneSerializer(serializers.Serializer):
    """Vazifasi: /api/auth/verify-phone/ — SMS-kodni tekshirish uchun input."""

    phone_number = serializers.CharField(max_length=13)
    code = serializers.CharField(max_length=6)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Vazifasi: login qilganda oddiy access/refresh tokendan tashqari,
    javobda foydalanuvchining ism-familiyasi, roli va tasdiqlanganlik
    holatini ham qaytaradi — frontend darhol shu javob bilan ekranga
    "Salom, <full_name>" deb chiqara oladi, alohida /me/ so'rov shart emas.
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": str(self.user.id),
            "username": self.user.username,
            "full_name": self.user.full_name,
            "phone_number": self.user.phone_number,
            "role": self.user.role,
            "is_phone_verified": self.user.is_phone_verified,
            "is_confirmed": self.user.is_confirmed,
        }
        return data

    @classmethod
    def get_token(cls, user):
        # bu qism JWT payload ichiga yoziladi — frontend tokenni decode qilib
        # ham shu ma'lumotlarni serverga so'rovsiz o'qiy oladi
        token = super().get_token(user)
        token["full_name"] = user.full_name
        token["username"] = user.username
        token["is_confirmed"] = user.is_confirmed
        return token


class UserSerializer(serializers.ModelSerializer):
    """Vazifasi: /api/auth/me/ — profilni ko'rsatish (full_name tahrirlanadi)."""

    class Meta:
        model = User
        fields = [
            "id", "username", "full_name", "phone_number",
            "role", "is_phone_verified", "is_confirmed", "date_joined",
        ]
        read_only_fields = [
            "id", "username", "phone_number", "role",
            "is_phone_verified", "is_confirmed", "date_joined",
        ]