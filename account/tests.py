"""
Hisob bilan bog'liq testlar: Google orqali kirish va admin ro'yxati.

--- Admin panelidagi "Foydalanuvchilar" jadvali ---

Bu yerda bitta narsa tekshiriladi: javobda IKKI xil raqam bor va ular
chalkashmasligi kerak —
  `count` — hozirgi filtrga tushganlar
  `total` — platformadagi barcha foydalanuvchi

Ilgari faqat `count` qaytardi va admin "biznes egalari" filtrini yoqib
qo'yib, ekrandagi raqamni platformaning umumiy soni deb o'qishi mumkin
edi.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()


class AdminUserCountTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="count_admin", password="StrongPass123!",
            phone_number="+998900007001", full_name="Count Admin", is_staff=True,
        )
        for index in range(4):
            User.objects.create_user(
                username=f"count_user{index}", password="StrongPass123!",
                phone_number=f"+99890000710{index}", full_name=f"User {index}",
                role="business" if index < 2 else "user",
            )
        self.client.force_authenticate(self.admin)

    def test_total_counts_everyone(self):
        response = self.client.get("/api/admin/users/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], User.objects.count())
        self.assertEqual(response.data["count"], response.data["total"])

    def test_filter_narrows_count_but_not_total(self):
        response = self.client.get("/api/admin/users/", {"role": "business"})

        self.assertEqual(response.data["count"], 2, "Filtr faqat biznes egalarini qoldirsin")
        self.assertEqual(
            response.data["total"], User.objects.count(),
            "Jami son filtrga qarab o'zgarmasligi kerak",
        )

    def test_plain_user_cannot_read_the_list(self):
        self.client.force_authenticate(User.objects.get(username="count_user0"))

        response = self.client.get("/api/admin/users/")

        self.assertEqual(response.status_code, 403)


class GoogleUsernameTest(TestCase):
    """
    Pochtadan username yasash.

    Google pochtasi bizning qoidamizga to'g'ri kelmaydi: nuqta, tire,
    bosh harf, hatto lotin bo'lmagan harflar uchraydi. Username esa
    `validate_username` ga bo'ysunishi shart — aks holda hisob
    yaratilmay, odam kirolmay qolardi.
    """

    def test_dots_and_case_are_cleaned(self):
        from account.services import username_from_email

        self.assertEqual(username_from_email("Ali.Valiyev@gmail.com"), "ali_valiyev")

    def test_dashes_become_underscores(self):
        from account.services import username_from_email

        self.assertEqual(username_from_email("nodira-k@mail.ru"), "nodira_k")

    def test_non_latin_does_not_produce_empty_name(self):
        from account.services import username_from_email

        name = username_from_email("тест@mail.ru")

        self.assertGreaterEqual(len(name), 3, "Bo'sh yoki juda kalta nom bo'lmasin")
        self.assertRegex(name, r"^[a-z0-9_]{3,30}$")

    def test_taken_name_gets_a_number(self):
        from account.services import username_from_email

        User.objects.create_user(
            username="sardor", password="x", full_name="Bor", phone_number="+998900001111",
        )

        self.assertEqual(username_from_email("sardor@gmail.com"), "sardor2")

    def test_result_always_passes_the_validator(self):
        from account.services import username_from_email
        from account.validators import validate_username

        for email in ["a@b.uz", "..@gmail.com", "A_B.C-D@x.uz", "x" * 60 + "@y.uz"]:
            validate_username(username_from_email(email))


class GoogleAccountLinkTest(TestCase):
    """
    Mavjud hisob Google'ga BOG'LANADI, ikkinchisi yaratilmaydi.

    Nega muhim: parol bilan ochilgan eski hisobda bronlar, sharhlar,
    hatto biznes bo'lishi mumkin. O'sha odam Google bilan kirganda
    yangi bo'sh hisob berilsa, u o'z ma'lumotini yo'qotgandek his
    qilardi va qo'llab-quvvatlashga yozardi.
    """

    def setUp(self):
        self.client = APIClient()
        self.existing = User.objects.create_user(
            username="eski_hisob", password="StrongPass123!",
            full_name="Eski Foydalanuvchi", phone_number="+998900002222",
        )
        self.existing.email = "eski@gmail.com"
        self.existing.save(update_fields=["email"])

    def _sign_in(self, sub="g-eski", email="eski@gmail.com", name="Eski Foydalanuvchi"):
        with patch("account.routes.user.verify_google_token") as verify:
            verify.return_value = {"sub": sub, "email": email, "name": name, "picture": ""}
            return self.client.post("/api/auth/google/", {"credential": "t"}, format="json")

    def test_same_email_links_instead_of_duplicating(self):
        response = self._sign_in()

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["created"], "Yangi hisob yaratilmasin")
        self.assertEqual(User.objects.count(), 1)

        self.existing.refresh_from_db()
        self.assertEqual(self.existing.google_sub, "g-eski")
        self.assertEqual(response.data["user"]["username"], "eski_hisob")

    def test_phone_and_name_survive_the_link(self):
        self._sign_in(name="Google Nomi")

        self.existing.refresh_from_db()
        self.assertEqual(self.existing.phone_number, "+998900002222", "Raqam saqlansin")
        self.assertEqual(
            self.existing.full_name, "Eski Foydalanuvchi",
            "Profilda yozilgan ism Google'niki bilan almashtirilmasin",
        )

    def test_changed_google_email_still_finds_the_account(self):
        """
        Odam Google'dagi pochtasini almashtirsa ham hisobi o'ziniki
        bo'lib qolsin — qidiruv `sub` bo'yicha boradi.
        """
        self._sign_in()

        response = self._sign_in(email="yangi@gmail.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(response.data["user"]["username"], "eski_hisob")


class GoogleRedirectFlowTest(TestCase):
    """
    Qayta yo'naltirish oqimi — saytdagi ASOSIY kirish yo'li.

    GSI popup oqimi "origin is not allowed" bilan ishlamagach shunga
    o'tilgan. Bu yerda tekshiriladigan narsa xavfsizlik: `state`
    solishtiruvi va ochiq yo'naltirish (open redirect) himoyasi.
    """

    def setUp(self):
        self.client = APIClient()

    def test_start_sends_the_user_to_google(self):
        response = self.client.get("/api/auth/google/start/")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("https://accounts.google.com/"))
        self.assertIn("redirect_uri=", response["Location"])
        self.assertIn("state=", response["Location"])

    def test_state_is_remembered_between_the_two_requests(self):
        self.client.get("/api/auth/google/start/")

        self.assertIn("google_state", self.client.session)

    def test_callback_rejects_a_forged_state(self):
        """
        `state` — CSRF himoyasi. Usiz begona odam qurbonni O'Z Google
        hisobiga kirgizib qo'yishi mumkin edi: keyin qurbon qilgan
        bronlar hujumchining hisobida paydo bo'lardi.
        """
        self.client.get("/api/auth/google/start/")

        response = self.client.get("/api/auth/google/callback/", {
            "code": "x", "state": "boshqa-state",
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn("google_error=state", response["Location"])

    def test_cancelled_sign_in_is_not_an_error_screen(self):
        response = self.client.get("/api/auth/google/callback/", {"error": "access_denied"})

        self.assertIn("google_error=cancelled", response["Location"])

    def test_external_next_is_ignored(self):
        """
        `?next=` faqat ICHKI manzil bo'lishi mumkin. Aks holda havola
        odamni kirgizib, keyin begona saytga tashlab yuborardi —
        klassik "open redirect" zaifligi.
        """
        self.client.get("/api/auth/google/start/", {"next": "https://evil.example/"})

        self.assertEqual(self.client.session["google_next"], "/")

    def test_internal_next_is_kept(self):
        self.client.get("/api/auth/google/start/", {"next": "/bronlarim/"})

        self.assertEqual(self.client.session["google_next"], "/bronlarim/")

    def test_successful_callback_hands_tokens_over_in_the_fragment(self):
        """
        Tokenlar URL FRAGMENTIDA qaytadi — u serverga yuborilmaydi,
        ya'ni kirish jurnallarida va `Referer` sarlavhasida qolmaydi.
        """
        start = self.client.get("/api/auth/google/start/", {"next": "/profil/"})
        self.assertEqual(start.status_code, 302)
        state = self.client.session["google_state"]

        with patch("account.routes.user.exchange_code") as exchange, \
             patch("account.routes.user.verify_google_token") as verify:
            exchange.return_value = "fake-id-token"
            verify.return_value = {
                "sub": "g-redirect-1", "email": "yangi@gmail.com",
                "name": "Yangi Odam", "picture": "",
            }
            response = self.client.get("/api/auth/google/callback/", {
                "code": "good-code", "state": state,
            })

        self.assertEqual(response.status_code, 302)
        location = response["Location"]

        # Har doim kirish sahifasiga qaytadi: tokenni bitta joy
        # qabul qiladi va odamni kerakli sahifaga o'zi uzatadi.
        # `next` esa fragment ichida ketadi.
        self.assertTrue(location.startswith("/kirish/#"), location)
        self.assertIn("access=", location)
        self.assertIn("refresh=", location)
        self.assertIn("created=1", location)
        self.assertIn("next=%2Fprofil%2F", location)
        self.assertTrue(User.objects.filter(email="yangi@gmail.com").exists())


class SharedPhoneNumberTest(TestCase):
    """
    Bitta raqamni bir necha hisob ishlatishi mumkin.

    Ilgari `phone_number` yagona (`unique`) edi va ikkinchi odam o'sha
    raqamni kiritganda "Aloqa raqami User allaqachon mavjud" chiqardi.
    Haqiqiy hayotda esa bitta raqam bir necha hisobga tegishli
    bo'ladi: oiladagi bitta telefon, joy egasining sinov hisobi, bir
    odamning ish va shaxsiy Google hisobi.

    Raqam identifikator EMAS — hisobni `username` va `google_sub`
    aniqlaydi. Raqam faqat bog'lanish uchun.
    """

    def setUp(self):
        self.client = APIClient()
        self.first = User.objects.create_user(username="ortoq_bir", full_name="Bir")
        self.second = User.objects.create_user(username="ortoq_ikki", full_name="Ikki")
        for user in (self.first, self.second):
            user.phone_number = None
            user.save(update_fields=["phone_number"])

    def _save_phone(self, user, phone="+998901112222"):
        self.client.force_authenticate(user)
        return self.client.patch("/api/auth/me/", {"phone_number": phone}, format="json")

    def test_two_accounts_can_share_one_number(self):
        self.assertEqual(self._save_phone(self.first).status_code, 200)

        response = self._save_phone(self.second)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            User.objects.filter(phone_number="+998901112222").count(), 2,
        )

    def test_format_is_still_checked(self):
        """Cheklov olib tashlandi, TEKSHIRUV emas."""
        response = self._save_phone(self.first, "12345")

        self.assertEqual(response.status_code, 400)

    def test_each_account_keeps_its_own_number_locked(self):
        """
        Takrorlanishga ruxsat berilgani bilan, BIR hisobdagi raqam
        baribir bir marta yoziladi.
        """
        self._save_phone(self.first, "+998901112222")

        response = self._save_phone(self.first, "+998903334444")

        self.assertEqual(response.status_code, 400)
        self.first.refresh_from_db()
        self.assertEqual(self.first.phone_number, "+998901112222")
