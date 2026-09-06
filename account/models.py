from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models import Role
from common.validators import validate_image_file

from .trust import TRUST_CANCEL_PENALTY, TRUST_MAX, TRUST_MIN, TRUST_START, clamp_bits, describe
from .validators import validate_phone_number, validate_username


class User(AbstractUser):
    username = models.CharField(max_length=30, unique=True, validators=[validate_username])
    full_name = models.CharField(max_length=150)

    # TELEFON RAQAMI IXTIYORIY.
    #
    # Ro'yxatdan o'tish Google orqali bo'lgani uchun bu maydon kirish
    # paytida bo'sh bo'ladi — Google raqam bermaydi. U BIRINCHI BRON
    # qilinayotganda so'raladi va shundan keyin doim shu yerda turadi.
    #
    # Nega aynan bron paytida: raqam faqat o'sha yerda kerak — joy
    # egasi mehmonga qo'ng'iroq qiladi. Kirish paytida so'rash esa
    # "bir bosishda kirish"ni buzardi va ko'p odam shu yerda to'xtab
    # qolardi.
    #
    # RAQAM YAGONA EMAS — ataylab.
    #
    # Ilgari `unique=True` edi va bir xil raqamni ikkinchi odam
    # kiritganda "Aloqa raqami User allaqachon mavjud" degan xato
    # chiqardi. Bu haqiqiy hayotga to'g'ri kelmaydi:
    #   · oilada bitta telefon bo'ladi — er, xotin, farzand alohida
    #     hisob ochadi, raqam esa bitta
    #   · joy egasi o'z hisobidan tashqari sinov hisobi ham ochadi
    #   · bir odam ish va shaxsiy Google hisobi bilan kiradi
    #
    # Cheklov kerak ham emas: hisobni `username` va `google_sub`
    # aniqlaydi, raqam esa faqat BOG'LANISH uchun — joy egasi
    # mehmonga qo'ng'iroq qiladi, administrator ariza egasiga.
    # Bitta raqamga bir necha marta qo'ng'iroq qilish muammo emas.
    phone_number = models.CharField(
        max_length=13, null=True, blank=True,
        validators=[validate_phone_number],
        verbose_name="Aloqa raqami",
        help_text="Bron yoki ariza berishda so'raladi. Takrorlanishi mumkin.",
    )

    # GOOGLE HISOBI BILAN BOG'LANISH.
    #
    # `sub` — Google beradigan o'zgarmas identifikator. Aynan SHU
    # maydon bo'yicha foydalanuvchi topiladi, email bo'yicha emas:
    # odam Google'dagi pochtasini almashtirsa ham hisobi o'ziniki
    # bo'lib qolishi kerak.
    google_sub = models.CharField(
        max_length=64, unique=True, null=True, blank=True, editable=False,
        verbose_name="Google ID",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER, db_index=True)

    avatar = models.ImageField(
        upload_to="avatars/", null=True, blank=True, validators=[validate_image_file],
        verbose_name="Profil rasmi",
    )
    bio = models.CharField(max_length=200, blank=True, verbose_name="Qisqacha")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Tug'ilgan sana")
    preferred_language = models.CharField(
        max_length=2, choices=(("uz", "O'zbekcha"), ("ru", "Русский"), ("en", "English")),
        default="uz", verbose_name="Interfeys tili",
    )

    # `is_phone_verified` — TARIXIY maydon.
    #
    # Ilgari SMS-kod bilan tasdiqlanardi. SMS oqimi olib tashlangach
    # uning ma'nosi o'zgardi: endi "raqam kiritilganmi" degani, chunki
    # raqam faqat foydalanuvchining o'zi bron paytida yozadi.
    # Maydon o'chirilmadi — eski yozuvlarda ma'lumot bor va admin
    # panelidagi filtrlar unga tayanadi.
    is_phone_verified = models.BooleanField(default=False, verbose_name="Raqam kiritilgan")

    # Hisob tasdiqlanganmi. Google orqali kirganda darhol `True`:
    # pochtani Google o'zi tekshirgan.
    is_confirmed = models.BooleanField(default=False, verbose_name="Tasdiqlangan")

    # 7 kunlik bepul sinov FOYDALANUVCHIGA bir marta beriladi.
    #
    # Biznesga emas, aynan foydalanuvchiga: aks holda odam biznesini
    # o'chirib, yangisini ochib, sinovni cheksiz qayta olardi. Bayroq
    # `start_trial` da qo'yiladi va hech qachon qaytarilmaydi.
    has_used_trial = models.BooleanField(
        default=False, verbose_name="Bepul sinov ishlatilgan",
        help_text="Bir marta berilgach qaytarilmaydi.",
    )

    # ISHONCHLILIK BALI — "Bit".
    #
    # Joy egasi bron so'rovini ko'rganda uni kim yuborganini bilishi
    # kerak: bu odam ilgari o'z bronini bekor qilganmi? Band qilingan,
    # lekin kelinmagan kun egasi uchun to'g'ridan-to'g'ri zarar — u
    # o'sha kunga boshqa mijozlarni rad etgan bo'ladi.
    #
    # Qoida `account.trust` da: 100 dan boshlanadi, har bir bekor
    # qilishda 5 Bit ayiriladi, 1 Bitdan pastga tushmaydi.
    #
    # Nega hisoblab chiqarilmaydi (bekor qilingan bronlarni sanab):
    # jazo qoidasi vaqt o'tib o'zgarishi mumkin, o'zgargan kuni esa
    # BARCHA foydalanuvchining bali orqaga qarab qayta yozilardi. Bal
    # tarixiy fakt bo'lib qolgani to'g'riroq.
    trust_bits = models.PositiveSmallIntegerField(
        default=TRUST_START, db_index=True,
        verbose_name="Ishonchlilik (Bit)",
        help_text=f"{TRUST_MIN}–{TRUST_MAX}. Yangi hisob {TRUST_START} Bit bilan boshlanadi.",
    )
    cancelled_reservations_count = models.PositiveIntegerField(
        default=0, verbose_name="Bekor qilgan bronlari",
        help_text="Faqat foydalanuvchining O'ZI bekor qilganlari. "
                  "Joy egasi rad etgan bronlar bu yerga qo'shilmaydi.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["role", "is_active"], name="idx_user_role_active"),
            models.Index(fields=["phone_number"], name="idx_user_phone"),
            models.Index(fields=["trust_bits"], name="idx_user_trust_bits"),
        ]

    def __str__(self):
        return self.username

    @property
    def avatar_url(self) -> str | None:
        return self.avatar.url if self.avatar else None

    @property
    def initials(self) -> str:
        """Rasm bo'lmaganda ko'rsatiladigan bosh harflar."""
        parts = (self.full_name or self.username or "?").split()
        return "".join(word[0] for word in parts[:2]).upper()

    @property
    def is_platform_admin(self) -> bool:
        """Super-admin — TZ bo\'yicha alohida rol emas, Django huquqi orqali."""
        return self.is_staff or self.is_superuser

    # ---------------- ishonchlilik ----------------
    @property
    def trust(self) -> dict:
        """Bal va daraja bitta lug'atda: `{bits, level, level_display, tone}`."""
        return describe(self.trust_bits)

    def penalize_trust(self, *, points: int = TRUST_CANCEL_PENALTY, reason: str = "") -> int:
        """
        Balni kamaytiradi va bazaga darhol yozadi. Yangi balni qaytaradi.

        Faqat SHU ikki maydon yoziladi (`update_fields`): bekor qilish
        tranzaksiyasi ichida foydalanuvchining boshqa maydonlari —
        masalan ayni damda tahrirlanayotgan profili — tasodifan eski
        qiymatga qaytib qolmasligi kerak.
        """
        self.trust_bits = clamp_bits(self.trust_bits - points)
        self.cancelled_reservations_count += 1
        self.save(update_fields=["trust_bits", "cancelled_reservations_count", "updated_at"])

        if reason:
            import logging
            logging.getLogger("account").info(
                f"Trust penalty: user_id={self.id}, -{points} bit, "
                f"now={self.trust_bits}, reason={reason}"
            )
        return self.trust_bits
