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


class HasContactPhone(BasePermission):
    """
    Vazifasi: bron qilish uchun ALOQA RAQAMI bo'lishini talab qiladi.

    Ilgari bu `IsPhoneVerified` edi va SMS-kod bilan tasdiqlangan
    raqamni talab qilardi. Ro'yxatdan o'tish Google'ga o'tgach, SMS
    oqimi butunlay olib tashlandi — Google pochtani o'zi tekshirgan,
    ustiga yana kod yuborishning ma'nosi yo'q edi.

    Lekin raqamning O'ZI baribir kerak: joy egasi mehmonga qo'ng'iroq
    qilib, bronni tasdiqlaydi yoki kechikish haqida ogohlantiradi.
    Raqamsiz bron — egasi uchun boshi berk ko'cha.

    Shuning uchun raqam KIRISH paytida emas, BIRINCHI BRON paytida
    so'raladi: frontend shu xatoni ko'rib, kichik oyna ochadi va
    raqamni profilga saqlaydi. Ikkinchi marta so'ralmaydi.
    """
    # Xabar UMUMIY: bu to'siq bir necha joyda ishlatiladi (bron,
    # biznes arizasi, obuna so'rovi). View o'ziga xos matn bermoqchi
    # bo'lsa `phone_message` orqali beradi — shunda odam nima uchun
    # kerakligini aynan o'sha kontekstda o'qiydi.
    message = "Davom etish uchun aloqa raqamingizni kiriting."
    code = "phone_required"

    def has_permission(self, request, view):
        self.message = getattr(view, "phone_message", self.message)
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.phone_number
        )

def unapproved_application_message(application):
    """
    "Nega yozolmayapman?" degan savolga javob — ariza TASDIQLANMAGAN
    hollarda.

    Matn arizaning holatiga qarab boshqacha va bu tafsilot emas:
      · rad etilgan — kutishning ma'nosi yo'q, arizani qayta yuborish kerak
      · tarifsiz (bepul sinov) ariza — tasdiqdan keyin sinov boshlanadi
      · pullik tarif tanlangan — sinov yo'q, obuna to'lov tasdig'idan
        keyin o'sha muddatga faollashadi

    Ilgari uchalasiga bir xil "arizangiz tasdiqlanmagan, 7 kunlik sinov
    boshlanadi" deyilardi: pul to'lagan odam bo'lmagan sinovni kutardi,
    rad etilgani esa umuman kelmaydigan javobni.

    Ikki joyda kerak — `IsBusinessRole` (roli hali yo'q ariza egasi) va
    `HasActiveSubscription` (obunasi ochilmagan biznes).
    """
    if application is not None and application.status == "rejected":
        return (
            "Arizangiz rad etilgan. Sababini administrator bilan "
            "aniqlashtiring va \"Obuna va Premium\" bo'limidan arizani "
            "qayta yuboring."
        )

    applied_plan = application.plan if application else None
    if applied_plan is None:
        from common.models import PlatformSettings
        days = PlatformSettings.get_solo().trial_days
        return (
            "Arizangiz hali tasdiqlanmagan. Administrator tekshirgach, "
            f"{days} kunlik bepul sinov boshlanadi va barcha bo'limlar ochiladi."
        )
    return (
        "Arizangiz hali tasdiqlanmagan. Administrator to'lovingizni "
        f"tasdiqlagach obunangiz {applied_plan.duration_label}ga faollashadi "
        "va barcha bo'limlar ochiladi."
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
        if not (request.user and request.user.is_authenticated):
            return False

        # PLATFORMA EGASI bu bo'limlarga KIRMAYDI.
        #
        # Uning ishi boshqa: barcha ma'lumotni ko'rish, tasdiqlash,
        # o'chirish va platformani boshqarish. Uning o'z restorani yoki
        # to'yxonasi bo'lmaydi, ya'ni "xona qo'shish", "menyu tahrirlash"
        # kabi amallar unga umuman tegishli emas.
        #
        # Ilgari faqat rol tekshirilardi va `is_staff` bo'lgan odam
        # `role='business'` ham bo'lsa, ikkala panelga ham kirardi —
        # ikki xil vazifa bir hisobda aralashib ketardi.
        if request.user.is_staff or request.user.is_superuser:
            self.message = (
                "Platforma egasi biznes panelidan foydalanmaydi — "
                "boshqaruv paneliga o'ting."
            )
            return False

        if request.user.role == "business":
            return True

        # ARIZASI BOR, lekin roli hali yo'q.
        #
        # Rol tasdiqdan keyin beriladi, ya'ni ariza yuborgan odamning
        # roli 'user'. Unga "bu bo'lim faqat biznes egalari uchun" deyish
        # noto'g'ri javob bo'lardi: u aynan biznes ochmoqchi va arizasi
        # ko'rib chiqilyapti. To'g'ri javob — arizasi qanday holatda va
        # keyin nima bo'lishi.
        business = request.user.businesses.select_related(
            "application", "application__plan"
        ).first()
        if business is not None:
            self.message = unapproved_application_message(
                getattr(business, "application", None)
            )
        return False


class IsBusinessOwnerOrApplicant(IsBusinessRole):
    """
    Vazifasi: JOYI BOR odam — roli hali 'business' bo'lmasa ham.

    Rol tasdiqdan keyin beriladi (`approve_application`). Ya'ni arizasi
    ko'rib chiqilayotgan yoki rad etilgan odamning roli 'user' bo'ladi,
    lekin uning joyi va arizasi bor — u o'z holatini KO'RISHI kerak
    ("arizangiz tekshiruvida" / "rad etildi, qayta yuboring").

    Faqat OBUNA ekrani uchun. Panelning qolgan bo'limlari (`xonalar`,
    `bronlar`, `menyu`) `IsBusinessRole` da qoladi: ular tasdiqlangan
    egaga tegishli va tasdiqlanmagan odamga ko'rsatadigan narsasi yo'q.
    """
    message = "Bu bo'lim biznes egalari va ariza yuborganlar uchun."

    def has_permission(self, request, view):
        if super().has_permission(request, view):
            return True
        # Staff bu yerga ham kirmaydi — yuqoridagi tekshiruv uni allaqachon
        # to'xtatgan va `self.message` unga tushuntirilgan.
        user = request.user
        if not (user and user.is_authenticated) or user.is_staff or user.is_superuser:
            return False
        return user.businesses.exists()


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

        business = request.user.businesses.select_related("application", "subscription").first()
        if business is None:
            return False

        subscription = getattr(business, "subscription", None)
        if subscription is None:
            # Obuna yo'q — yozish yopiq. Lekin SABABI uch xil bo'lishi
            # mumkin va odamga to'g'risini aytish kerak:
            #   · ariza hali ko'rib chiqilmagan — kutish kifoya
            #   · ariza tasdiqlangan, ammo obuna ochilmagan (masalan bepul
            #     sinov avval ishlatilgan) — bu yerda kutish yordam
            #     bermaydi, tarif tanlash kerak
            #   · ariza rad etilgan — kutish umuman befoyda, arizani
            #     qayta yuborish kerak
            # Ilgari ikkalasiga bir xil "arizangiz tasdiqlanmagan" deyilardi
            # va tasdiqlangan egasi nima qilishini bilmay qolardi.
            application = getattr(business, "application", None)
            approved = application is not None and application.status == "approved"

            if approved:
                self.message = (
                    "Obunangiz hali ochilmagan. Davom ettirish uchun tarif tanlab, "
                    "administrator bilan Telegram orqali bog'laning."
                )
            else:
                self.message = unapproved_application_message(application)

            return False
        return subscription.status in ("trial", "active")


class IsCustomer(BasePermission):
    """
    Bron qilish va sharh qoldirish uchun — PLATFORMA EGASIDAN tashqari
    hamma kira oladi.

    Nega platforma egasi bron qila olmaydi: u tizimni boshqaradi, undan
    foydalanmaydi. Uning broni statistikani buzardi (o'z platformasida
    o'zi mijoz bo'lib chiqardi) va "bu bronni kim tasdiqlaydi?" degan
    chalkash holat tug'ilardi.
    """

    message = (
        "Platforma egasi bron qila olmaydi — bu bo'lim mijozlar uchun. "
        "Bronlarni boshqarish uchun boshqaruv panelidan foydalaning."
    )

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return not (request.user.is_staff or request.user.is_superuser)
