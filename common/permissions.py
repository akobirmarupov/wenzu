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