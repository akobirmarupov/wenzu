"""User modeli uchun API'lar — Google orqali kirish, profil, admin ro'yxati."""

import logging
import secrets
from urllib.parse import urlencode

from django.db import transaction
from django.http import HttpResponseRedirect
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
    GoogleAuthSerializer,
    LogoutSerializer,
    UserAdminSerializer,
    UserSerializer,
    build_user_payload,
)
from account.services import (
    GoogleAuthError,
    build_auth_url,
    exchange_code,
    get_or_create_google_user,
    verify_google_token,
)
from common.pagination import StandardResultsPagination
from common.permissions import IsSuperAdmin
from common.throttles import LoginThrottle

logger = logging.getLogger("account")
security_logger = logging.getLogger("django.security")


def google_redirect_uri(request):
    """
    Google qaytadigan manzil.

    So'rovning O'ZIDAN quriladi, sozlamaga yozilmaydi: lokal ishlab
    chiqishda `http://127.0.0.1:8000/...`, productionda
    `https://wenzu.uz/...` bo'ladi va ikkalasini qo'lda boshqarish
    bitta joyni unutish demakdir. Google Console'ga esa ikkalasi ham
    "Authorized redirect URIs" ga qo'shiladi.
    """
    return request.build_absolute_uri("/api/auth/google/callback/")


class GoogleStartAPIView(APIView):
    """
    GET /api/auth/google/start/ — foydalanuvchini Google'ga yuboradi.

    Popup emas, ODDIY O'TISH. Sabab `account/services.py` da batafsil:
    GSI popup oqimi "origin is not allowed" bilan ishlamadi va uni
    tuzatish bizning qo'limizda emas edi. Redirect oqimi esa butunlay
    boshqa ro'yxatga ("Authorized redirect URIs") tayanadi va
    telefonda ham ishonchliroq.

    `state` — CSRF himoyasi: tasodifiy satr sessiyaga yoziladi va
    qaytganda solishtiriladi. Usiz begona odam qurbonni o'z Google
    hisobiga kirgizib qo'yishi mumkin edi.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        state = secrets.token_urlsafe(24)
        request.session["google_state"] = state
        # Kirishdan keyin qayerga qaytish — foydalanuvchi ketayotgan
        # sahifa. Faqat ICHKI manzil: tashqi manzil ochiq
        # yo'naltirish (open redirect) zaifligi bo'lardi.
        next_url = request.GET.get("next") or "/"
        request.session["google_next"] = next_url if next_url.startswith("/") else "/"

        try:
            url = build_auth_url(
                redirect_uri=google_redirect_uri(request), state=state
            )
        except GoogleAuthError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return HttpResponseRedirect(url)


class GoogleCallbackAPIView(APIView):
    """
    GET /api/auth/google/callback/ — Google shu yerga qaytaradi.

    Tokenlar sahifaga URL FRAGMENTI (`#`) bilan uzatiladi. Nega
    aynan fragment: u serverga YUBORILMAYDI va shuning uchun
    kirish jurnallarida, proksi loglarida yoki `Referer` sarlavhasida
    qolib ketmaydi. Frontend uni o'qib, darhol manzildan tozalaydi.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        error = request.GET.get("error")
        if error:
            # Odam "Bekor qilish" bosdi — bu xato emas, tanlov.
            return self._back(request, error="cancelled" if error == "access_denied" else error)

        state = request.GET.get("state")
        expected = request.session.pop("google_state", None)
        if not state or state != expected:
            security_logger.warning("Google callback: state mos kelmadi")
            return self._back(request, error="state")

        code = request.GET.get("code")
        if not code:
            return self._back(request, error="nocode")

        try:
            id_token_value = exchange_code(
                code=code, redirect_uri=google_redirect_uri(request)
            )
            payload = verify_google_token(id_token_value)
            user, created = get_or_create_google_user(payload)
        except GoogleAuthError as exc:
            logger.warning(f"Google callback xatosi: {exc}")
            return self._back(request, error="google")

        if not user.is_active:
            security_logger.warning(f"Bloklangan hisob Google orqali urindi: user_id={user.id}")
            return self._back(request, error="blocked")

        refresh = CustomTokenObtainPairSerializer.get_token(user)
        logger.info(f"Google login OK: user_id={user.id}, yangi={created}")

        # HAR DOIM kirish sahifasiga qaytamiz, `next` esa fragment
        # ichida ketadi.
        #
        # Ilgari to'g'ridan-to'g'ri `next` ga qaytarilardi — masalan
        # joy sahifasiga. U yerda esa tokenni o'qiydigan kod yo'q
        # edi: manzilda `#access=...` osilib qolardi, odam esa
        # kirmagan holda qolaverardi (aynan shunday bo'lgan).
        #
        # Endi tokenni BITTA joy qabul qiladi — kirish sahifasi —
        # va u odamni kerakli joyga o'zi uzatadi. Har bir sahifaga
        # alohida ilgak qo'yish esa bir kun bittasini unutish
        # demakdir.
        fragment = urlencode({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "created": "1" if created else "0",
            "next": self._next(request),
        })
        return HttpResponseRedirect(f"/kirish/#{fragment}")

    def _next(self, request):
        return request.session.pop("google_next", None) or "/"

    def _back(self, request, *, error):
        """Xato bo'lsa kirish sahifasiga sabab bilan qaytaramiz."""
        return HttpResponseRedirect(f"/kirish/?google_error={error}")


class GoogleAuthAPIView(APIView):
    """
    POST /api/auth/google/ — RO'YXATDAN O'TISH VA KIRISH, bitta manzil.

    Brauzer Google'dan `credential` (id_token) oladi va shu yerga
    yuboradi. Biz uni tekshiramiz va o'z tokenlarimizni beramiz.

    Ikkiga bo'lingan "ro'yxat" va "kirish" YO'Q. Foydalanuvchi uchun
    ular bir xil amal: Google tugmasini bosish. Hisob bo'lmasa
    yaratiladi, bo'lsa kiritiladi — buni server o'zi hal qiladi.
    Ilgari odam "men ro'yxatdan o'tganmidim?" deb ikki sahifa orasida
    yurardi.

    SMS-kod oqimi olib tashlandi: pochtani Google tekshirgan.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    @extend_schema(
        request=GoogleAuthSerializer,
        responses={200: None},
        description="Google `id_token` ni tekshirib, access/refresh token qaytaradi.",
    )
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = verify_google_token(serializer.validated_data["credential"])
            user, created = get_or_create_google_user(payload)
        except GoogleAuthError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            security_logger.warning(f"Bloklangan hisob Google orqali urindi: user_id={user.id}")
            return Response(
                {"detail": "Hisobingiz bloklangan. Administrator bilan bog'laning."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = CustomTokenObtainPairSerializer.get_token(user)
        logger.info(f"Google login OK: user_id={user.id}, yangi={created}")

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": build_user_payload(user, request),
                # Frontend shu bayroqqa qarab yangi kelgan odamni
                # profilga, qaytganini esa o'z paneliga yuboradi.
                "created": created,
            },
            status=status.HTTP_200_OK,
        )


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
        response = paginator.get_paginated_response(serializer.data)

        # `count` — FILTRGA tushganlar soni, `total` — platformadagi
        # BARCHA foydalanuvchi. Ikkalasi ham kerak: admin "biznes
        # egalari 20 ta" degan raqamni ko'rib turib, "jami nechta
        # odam bor?" degan savolga javobni ham bir qarashda olishi
        # kerak. Alohida so'rov yubormaslik uchun shu javobga
        # qo'shiladi.
        response.data["total"] = User.objects.count()
        return response


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
