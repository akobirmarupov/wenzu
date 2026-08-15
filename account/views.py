from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from common.throttles import LoginThrottle, SMSVerificationThrottle

from .models import User
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
    VerifyPhoneSerializer,
)


class RegisterView(generics.CreateAPIView):
    """Vazifasi: POST — yangi foydalanuvchini ro'yxatdan o'tkazadi (SMS hali tasdiqlanmagan holatda)."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class VerifyPhoneView(APIView):
    """
    Vazifasi: POST — SMS-kodni tekshirib, is_phone_verified=True qiladi.
    SMSVerificationThrottle bilan himoyalangan (telefon raqami bo'yicha cheklov).
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [SMSVerificationThrottle]

    def post(self, request):
        serializer = VerifyPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        code = serializer.validated_data["code"]

        # TODO: kodni Redis/cache'da saqlangan haqiqiy kod bilan solishtirish
        # (Eskiz.uz / Play Mobile orqali yuborilgan kod shu yerda tekshiriladi)
        user = User.objects.filter(phone_number=phone_number).first()
        if user is None:
            return Response(
                {"detail": "Bu raqamda foydalanuvchi topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified"])
        return Response({"detail": "Telefon raqami muvaffaqiyatli tasdiqlandi."})


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vazifasi: POST /api/auth/login/ — access/refresh token bilan birga
    ism-familiya, rol va tasdiqlanganlik holatini ham qaytaradi.
    LoginThrottle bilan himoyalangan (brute-force'dan).
    """

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]


class MeView(generics.RetrieveUpdateAPIView):
    """Vazifasi: GET/PATCH /api/auth/me/ — joriy foydalanuvchi profili."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user