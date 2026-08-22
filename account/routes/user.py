"""User modeli uchun API'lar — ro'yxatdan o'tish, SMS tasdiq, login, profil."""

import logging
import secrets

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from account.filters import UserFilter
from account.models import User
from account.routes.serializers import (
    AvatarSerializer,
    CustomTokenObtainPairSerializer,
    LogoutSerializer,
    RegisterSerializer,
    SendCodeSerializer,
    UserAdminSerializer,
    UserSerializer,
    VerifyPhoneSerializer,
)
from common.pagination import StandardResultsPagination
from common.permissions import IsSuperAdmin
from common.sms import send_verification_code
from common.throttles import (
    LoginThrottle,
    RegisterThrottle,
    SMSSendThrottle,
    SMSVerificationThrottle,
)

logger = logging.getLogger("account")
security_logger = logging.getLogger("django.security")

SMS_CACHE_KEY = "sms_code:%s"
SMS_ATTEMPTS_KEY = "sms_attempts:%s"


class RegisterAPIView(APIView):
    """POST /api/auth/register/ — yangi foydalanuvchi (telefon hali tasdiqlanmagan)."""

    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]

    @extend_schema(request=RegisterSerializer, responses={201: RegisterSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user = serializer.save()

        logger.info(f"User registered: id={user.id}, username={user.username}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SendCodeAPIView(APIView):
    """
    POST /api/auth/send-code/ — telefon raqamiga tasdiqlash kodi yuboradi.

    XAVFSIZLIK: raqam bazada bor-yo'qligidan qat'i nazar BIR XIL javob
    qaytadi. Aks holda bu endpoint "bu raqam ro'yxatdan o'tganmi?" degan
    savolga javob beradigan vositaga aylanib qolardi (user enumeration).
    """

    permission_classes = [AllowAny]
    throttle_classes = [SMSSendThrottle]

    GENERIC_RESPONSE = {
        "detail": "Agar bu raqam ro'yxatdan o'tgan bo'lsa, tasdiqlash kodi yuborildi."
    }

    @extend_schema(request=SendCodeSerializer, responses={200: None})
    def post(self, request):
        serializer = SendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]

        user = User.objects.filter(phone_number=phone_number).only("id").first()
        if user is None:
            security_logger.info(f"send-code: mavjud bo'lmagan raqam so'raldi ({phone_number})")
            return Response(self.GENERIC_RESPONSE, status=status.HTTP_200_OK)

        # `secrets` — `random` emas: tasdiqlash kodi taxmin qilinmaydigan
        # bo'lishi kerak, `random` esa kriptografik jihatdan ishonchsiz.
        code = f"{secrets.randbelow(1_000_000):06d}"
        cache.set(SMS_CACHE_KEY % phone_number, code, timeout=settings.SMS_CODE_TTL_SECONDS)
        cache.delete(SMS_ATTEMPTS_KEY % phone_number)

        send_verification_code(phone_number, code)
        logger.info(f"SMS code issued for user_id={user.id}")

        payload = dict(self.GENERIC_RESPONSE)
        if settings.DEBUG:
            # Faqat ishlab chiqish rejimida — haqiqiy SMS pulini sarflamaslik uchun.
            payload["debug_code"] = code
        return Response(payload, status=status.HTTP_200_OK)


class VerifyPhoneAPIView(APIView):
    """
    POST /api/auth/verify-phone/ — SMS-kodni tekshirib, is_phone_verified=True qiladi.

    Kod cheklangan marta (`SMS_MAX_VERIFY_ATTEMPTS`) tekshiriladi — shundan
    keyin kod bekor qilinadi. 6 xonali kodni 1 000 000 marta sinab
    topib bo'lmasligi uchun.
    """

    permission_classes = [AllowAny]
    throttle_classes = [SMSVerificationThrottle]

    @extend_schema(request=VerifyPhoneSerializer, responses={200: None})
    def post(self, request):
        serializer = VerifyPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        code = serializer.validated_data["code"]

        cache_key = SMS_CACHE_KEY % phone_number
        attempts_key = SMS_ATTEMPTS_KEY % phone_number

        expected = cache.get(cache_key)
        if expected is None:
            return Response(
                {"detail": "Kod muddati tugagan yoki yuborilmagan. Qaytadan so'rang."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attempts = (cache.get(attempts_key) or 0) + 1
        if attempts > settings.SMS_MAX_VERIFY_ATTEMPTS:
            cache.delete(cache_key)
            cache.delete(attempts_key)
            security_logger.warning(f"SMS brute-force to'xtatildi: phone={phone_number}")
            return Response(
                {"detail": "Juda ko'p noto'g'ri urinish. Yangi kod so'rang."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # `compare_digest` — vaqt bo'yicha hujumdan (timing attack) himoya.
        if not secrets.compare_digest(str(expected), str(code)):
            cache.set(attempts_key, attempts, timeout=settings.SMS_CODE_TTL_SECONDS)
            security_logger.warning(
                f"Invalid SMS code attempt {attempts}/{settings.SMS_MAX_VERIFY_ATTEMPTS} "
                f"for phone={phone_number}"
            )
            return Response({"detail": "Kod noto'g'ri."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(phone_number=phone_number).first()
        if user is None:
            return Response(
                {"detail": "Bu raqamda foydalanuvchi topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            user.is_phone_verified = True
            user.save(update_fields=["is_phone_verified"])

        cache.delete(cache_key)
        cache.delete(attempts_key)
        logger.info(f"Phone verified: user_id={user.id}")
        return Response({"detail": "Telefon raqami muvaffaqiyatli tasdiqlandi."})


class LoginAPIView(TokenObtainPairView):
    """
    POST /api/auth/login/ — access/refresh token bilan birga ism-familiya,
    rol va biznes profilini (restoran/to'yxona) qaytaradi. Frontend shu
    javobga qarab qaysi panelni ochishini hal qiladi.
    """

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]

    def get_serializer_context(self):
        # Avatar manzili to'liq (absolute) bo'lishi uchun request kerak.
        return {**super().get_serializer_context(), "request": self.request}

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            logger.info(f"Login OK: username={request.data.get('username')}")
        else:
            security_logger.warning(
                f"Login failed: username={request.data.get('username')} "
                f"ip={request.META.get('REMOTE_ADDR')}"
            )
        return response


class LogoutAPIView(APIView):
    """
    POST /api/auth/logout/ — refresh tokenni qora ro'yxatga qo'shadi.

    Bunisiz "chiqish" faqat mijoz tomonda bo'lardi: o'g'irlangan refresh
    token 30 kun davomida yangi access token olib berishda davom etardi.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutSerializer, responses={205: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Token yaroqsiz yoki allaqachon bekor qilingan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Logout: user_id={request.user.id}")
        return Response({"detail": "Tizimdan chiqdingiz."}, status=status.HTTP_205_RESET_CONTENT)


class MeAPIView(APIView):
    """GET/PATCH/DELETE /api/auth/me/ — joriy foydalanuvchi profili."""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        user = User.objects.prefetch_related("businesses").get(pk=request.user.pk)
        return Response(
            UserSerializer(user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=UserSerializer, responses=UserSerializer)
    def patch(self, request):
        serializer = UserSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(responses={204: None})
    def delete(self, request):
        """
        Hisobni o'chirish (GDPR-ga o'xshash "unut meni" talabi).

        Yozuv jismonan o'chirilmaydi, balki FAOLSIZLANTIRILADI: bronlar va
        to'lov tarixi buxgalteriya uchun saqlanib qolishi kerak. Shaxsiy
        ma'lumotlar esa anonimlashtiriladi.
        """
        user = request.user
        with transaction.atomic():
            user.is_active = False
            user.full_name = "O'chirilgan foydalanuvchi"
            user.phone_number = f"deleted_{user.pk}"
            user.username = f"deleted_{user.pk}"
            user.set_unusable_password()
            user.save()

        logger.info(f"Account deactivated: user_id={user.pk}")
        return Response(status=status.HTTP_204_NO_CONTENT)


class AvatarAPIView(APIView):
    """
    POST/DELETE /api/auth/me/avatar/ — profil rasmini almashtirish yoki olib tashlash.

    Rasm alohida endpointda, chunki u `multipart/form-data` bilan keladi va
    profilning qolgan maydonlari bilan bir so'rovda yuborilsa, mijoz har
    safar butun formani qayta jo'natishga majbur bo'lardi.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=AvatarSerializer, responses=UserSerializer)
    def post(self, request):
        serializer = AvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # Eski faylni diskda qoldirmaymiz — aks holda ular yig'ilib boradi.
            old = request.user.avatar
            serializer.save()
            if old and old.name != request.user.avatar.name:
                old.delete(save=False)

        logger.info(f"Avatar updated: user_id={request.user.id}")
        return Response(
            UserSerializer(request.user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses=UserSerializer)
    def delete(self, request):
        with transaction.atomic():
            if request.user.avatar:
                request.user.avatar.delete(save=False)
                request.user.avatar = None
                request.user.save(update_fields=["avatar"])

        logger.info(f"Avatar removed: user_id={request.user.id}")
        return Response(
            UserSerializer(request.user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class AdminUserListAPIView(APIView):
    """GET /api/admin/users/ — admin panelidagi "Foydalanuvchilar" jadvali."""

    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter
    queryset = User.objects.none()
    pagination_class = StandardResultsPagination

    @extend_schema(
        responses=UserAdminSerializer(many=True),
        parameters=[
            OpenApiParameter("role", str, description="user | business | admin"),
            OpenApiParameter("search", str, description="Ism, username yoki telefon"),
        ],
    )
    def get(self, request):
        # `has_business` — admin panelida "bu odamga biznes ochish mumkinmi"
        # degan savolga javob. `Exists()` bilan bitta so'rovda keladi;
        # har bir qator uchun `businesses.exists()` chaqirish N+1 bo'lardi.
        from django.db.models import Exists, OuterRef

        from businesses.models import Business

        queryset = (
            User.objects.only(
                "id", "username", "full_name", "phone_number", "role",
                "is_phone_verified", "is_confirmed", "is_active", "is_staff", "date_joined",
            )
            .annotate(has_business=Exists(Business.objects.filter(owner=OuterRef("pk"))))
            .order_by("-date_joined")
        )
        queryset = UserFilter(request.GET, queryset=queryset).qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = UserAdminSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminUserDetailAPIView(APIView):
    """GET/PATCH /api/admin/users/{pk}/ — bitta foydalanuvchi (rol/faollik boshqaruvi)."""

    permission_classes = [IsSuperAdmin]

    # Admin API orqali o'zgartira oladigan maydonlar. `is_staff`/`is_superuser`
    # ataylab yo'q — huquq berish faqat Django admin paneli orqali bo'lsin,
    # shunda API kaliti o'g'irlansa ham super-admin yaratib bo'lmaydi.
    EDITABLE_FIELDS = {"is_active", "is_confirmed", "is_phone_verified", "role"}

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise NotFound("Foydalanuvchi topilmadi")

    @extend_schema(responses=UserAdminSerializer)
    def get(self, request, pk):
        return Response(UserAdminSerializer(self.get_object(pk)).data)

    @extend_schema(request=UserAdminSerializer, responses=UserAdminSerializer)
    def patch(self, request, pk):
        user = self.get_object(pk)
        data = {k: v for k, v in request.data.items() if k in self.EDITABLE_FIELDS}
        if not data:
            return Response(
                {"detail": f"Tahrirlash mumkin bo'lgan maydonlar: {sorted(self.EDITABLE_FIELDS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "role" in data and data["role"] not in dict(User._meta.get_field("role").choices):
            return Response({"detail": "Noma'lum rol."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            for field, value in data.items():
                setattr(user, field, value)
            user.save(update_fields=list(data.keys()))

        security_logger.info(
            f"User updated by admin: user_id={user.id}, by={request.user.id}, fields={list(data)}"
        )
        return Response(UserAdminSerializer(user).data, status=status.HTTP_200_OK)
