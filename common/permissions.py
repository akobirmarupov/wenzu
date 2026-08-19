from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsSuperAdmin(BasePermission):
    """
    Vazifasi: faqat platforma egasi (Django is_staff/is_superuser) kira oladigan
    amallar uchun — masalan BusinessApplication'ni tasdiqlash,
    umumiy statistikani ko'rish.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )


class HasRole(BasePermission):
    """
    Vazifasi: umumiy rol tekshiruvchi. View'da:
        permission_classes = [HasRole]
        required_role = User.Role.BUSINESS
    kabi ishlatiladi. User.role endi oddiy TextChoices (CharField).
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        required_role = getattr(view, "required_role", None)
        if required_role is None:
            return True
        return request.user.role == required_role


class IsBusinessOwner(BasePermission):
    """
    Vazifasi: business rolidagi foydalanuvchi faqat O'ZIGA tegishli
    Business (va unga bog'liq Room, Hall, RestaurantMenuItem, VenueMenuItem, Subscription)
    obyektlarini tahrirlay olishini ta'minlaydi.
    Object-level permission — get_object() chaqirilganda ishlaydi.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        # obj to'g'ridan-to'g'ri Business bo'lishi ham,
        # yoki unga FK bilan bog'langan model bo'lishi ham mumkin
        business = obj if hasattr(obj, "owner") else getattr(obj, "business", None)
        return bool(business and business.owner_id == request.user.id)


class IsReservationOwner(BasePermission):
    """
    Vazifasi: Reservation'ni faqat uni yaratgan foydalanuvchi
    ko'rishi/bekor qilishi mumkinligini ta'minlaydi (masalan
    /api/reservations/{id}/cancel/ endpointida).
    """

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id


class IsReviewOwnerOrReadOnly(BasePermission):
    """
    Vazifasi: Review'ni hamma ko'ra oladi (GET), lekin faqat sharh
    egasi tahrirlashi/o'chirishi mumkin.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user_id == request.user.id


class IsPhoneVerified(BasePermission):
    """
    Vazifasi: SMS orqali telefon tasdiqlanmagan foydalanuvchiga
    bron qilish/ariza yuborish kabi og'ir amallarni taqiqlaydi.
    """
    message = "Avval telefon raqamingizni SMS-kod orqali tasdiqlang."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_phone_verified
        )

class IsBusinessRole(BasePermission):
    """
    Vazifasi: faqat `role='business'` bo'lgan foydalanuvchi (restoran yoki
    to'yxona egasi) kira oladigan `/api/owner/...` endpointlari uchun.

    Restoran egasi va to'yxona egasi bitta rolda — ular bir-biridan
    `user.businesses.first().business_type` orqali ajraladi. Login javobida
    ham shu `business.type` qaytariladi va frontend shunga qarab
    kerakli boshqaruv panelini (ownerShell) ochadi.
    """
    message = "Bu bo'lim faqat biznes egalari uchun."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "business"
        )


class IsOwnerOfBusinessType(IsBusinessRole):
    """
    Vazifasi: `IsBusinessRole` ustiga biznes TURINI ham tekshiradi — masalan
    "Xonalar" endpointi faqat restoran egasiga, "Zallar" faqat to'yxona
    egasiga ochilishi kerak. View'da:

        permission_classes = [IsOwnerOfBusinessType]
        required_business_type = Business.TYPE_RESTAURANT
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        required = getattr(view, "required_business_type", None)
        if required is None:
            return True
        business = request.user.businesses.first()
        if business is None:
            self.message = "Sizda hali biznes profili yo'q."
            return False
        if business.business_type != required:
            self.message = (
                "Bu bo'lim restoran egalari uchun."
                if required == "restaurant"
                else "Bu bo'lim to'yxona egalari uchun."
            )
            return False
        return True


class HasActiveSubscription(BasePermission):
    """
    Obunasi tugagan biznes egasiga YOZISH amallarini taqiqlaydi.

    O'qish (GET) ochiq qoladi — aks holda egasi o'z paneliga kira olmay,
    "Obunangiz tugadi, davom ettirish uchun @admin bilan bog'laning"
    degan ekranni ham ko'rmasdi. Ya'ni to'lovga undash imkoniyati
    yo'qolardi (TZ 4.1, 6-qadam).
    """

    message = (
        "Obunangiz muddati tugagan. Davom ettirish uchun administrator bilan "
        "Telegram orqali bog'laning."
    )

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_staff:
            return True

        business = request.user.businesses.select_related("subscription").first()
        if business is None:
            return False

        subscription = getattr(business, "subscription", None)
        if subscription is None:
            return True  # obuna hali yaratilmagan — bloklamaymiz
        return subscription.status in ("trial", "active")
