
# Create your tests here.
"""
O'RINLAR JADVALI testlari.

Kartochkadagi tartib raqami sharhlardan hisoblanadi: yulduzlar
YIG'INDISI bo'yicha. Bitta 5 yulduzli sharh — 5 ball; ustiga 4 yulduzli
qo'shilsa 9 ball va joy yuqoriga ko'tariladi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from businesses.models import Business, BusinessApplication
from reservations.models import Availability, Reservation
from reviews.models import Review

User = get_user_model()


class RankingTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="rank_owner", password="StrongPass123!",
            full_name="Ega", phone_number="+998900008001",
        )
        self.customer = User.objects.create_user(
            username="rank_customer", password="StrongPass123!",
            full_name="Mijoz", phone_number="+998900008002",
        )
        self.a = self._business("Birinchi Restoran")
        self.b = self._business("Ikkinchi Restoran")

    def _business(self, name, business_type="restaurant"):
        application = BusinessApplication.objects.create(
            applicant=self.owner, business_type=business_type, business_name=name,
            status=BusinessApplication.STATUS_APPROVED,
        )
        return Business.objects.create(
            owner=self.owner, application=application, name=name,
            business_type=business_type, is_visible=True,
        )

    #: Har bir sharh uchun ALOHIDA kun.
    #
    # `Availability` da "bitta joy + bitta kun + bitta boshlanish vaqti"
    # yagona bo'lishi shart (`uniq_business_date_start_time_no_room`).
    # Bir xil kun ishlatilsa, ikkinchi sharh yaratilmay xato berardi.
    _day = 0

    def _review(self, business, rating):
        """Sharh bron bilan bog'lanadi — model shuni talab qiladi."""
        RankingTest._day += 1
        availability = Availability.objects.create(
            business=business,
            date=datetime.date.today() + datetime.timedelta(days=RankingTest._day),
            start_time=datetime.time(9, 0), end_time=datetime.time(23, 0),
        )
        reservation = Reservation.objects.create(
            user=self.customer, business=business, availability=availability,
            guests_count=2, status="completed",
        )
        return Review.objects.create(
            user=self.customer, business=business,
            reservation=reservation, rating=rating,
        )

    def test_points_are_the_sum_of_stars(self):
        """5 yulduz + 4 yulduz = 9 ball."""
        self._review(self.a, 5)
        self.a.refresh_from_db()
        self.assertEqual(self.a.rating_points, 5)

        self._review(self.a, 4)
        self.a.refresh_from_db()
        self.assertEqual(self.a.rating_points, 9)
        self.assertEqual(self.a.reviews_count, 2)

    def test_more_points_means_a_higher_place(self):
        self._review(self.b, 5)
        self._review(self.a, 3)

        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual(self.b.rank, 1)
        self.assertEqual(self.a.rank, 2)

        # `a` ikkita sharh yig'ib, `b` dan o'zib ketadi: 3 + 5 = 8 > 5.
        self._review(self.a, 5)
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual(self.a.rank, 1, "Ko'proq ball yig'gan joy birinchi o'ringa chiqadi")
        self.assertEqual(self.b.rank, 2)

    def test_sum_beats_average(self):
        """
        Bitta 5 yulduzli sharh olgan joy, ikkita 4 yulduzli olgan joydan
        PAST turishi kerak: o'rtacha 5.0 > 4.0, lekin yig'indi 5 < 8.

        Aks holda bitta maqtov bilan birinchi o'ringa chiqib olish
        mumkin bo'lardi.
        """
        self._review(self.a, 5)
        self._review(self.b, 4)
        self._review(self.b, 4)

        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual(self.a.rating_avg, 5.0)
        self.assertEqual(self.b.rating_avg, 4.0)
        self.assertEqual(self.b.rank, 1)
        self.assertEqual(self.a.rank, 2)

    def test_restaurants_and_venues_are_ranked_separately(self):
        """Ikki tur bir-biri bilan raqobatlashmaydi — har birida o'z 1-o'rni."""
        venue = self._business("Birinchi To'yxona", business_type="venue")
        self._review(self.a, 5)
        self._review(venue, 3)

        self.a.refresh_from_db()
        venue.refresh_from_db()
        self.assertEqual(self.a.rank, 1)
        self.assertEqual(venue.rank, 1)

    def test_deleting_a_review_moves_the_place_down(self):
        self._review(self.b, 4)
        review = self._review(self.a, 5)

        self.a.refresh_from_db()
        self.assertEqual(self.a.rank, 1)

        review.delete()
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual(self.a.rating_points, 0)
        self.assertEqual(self.b.rank, 1)
        self.assertEqual(self.a.rank, 2)

    def test_list_api_exposes_the_place(self):
        from rest_framework.test import APIClient

        self._review(self.a, 5)
        response = APIClient().get("/api/businesses/?type=restaurant")

        row = next(r for r in response.data["results"] if r["name"] == "Birinchi Restoran")
        self.assertEqual(row["rank"], 1)
        self.assertEqual(row["rating_points"], 5)

    def test_list_api_returns_places_in_rank_order(self):
        """
        Ro'yxat O'RIN bo'yicha keladi: 1-o'rin birinchi, 2-o'rin ikkinchi.

        Ilgari tartib `-rating_avg` bo'yicha edi, o'rin esa yulduzlar
        yig'indisi bo'yicha — mijoz kartochkalarda "1-o'rin, 7-o'rin,
        2-o'rin" deb sochilgan raqamlarni ko'rardi.
        """
        from rest_framework.test import APIClient

        # `a` — ko'p ball (8), lekin past o'rtacha (4.0).
        # `b` — bitta 5 yulduz: o'rtachasi baland, balli kam.
        self._review(self.a, 3)
        self._review(self.a, 5)
        self._review(self.b, 5)

        response = APIClient().get("/api/businesses/?type=restaurant")
        ranks = [row["rank"] for row in response.data["results"]]

        self.assertEqual(ranks, sorted(ranks), "Kartochkalar o'rin bo'yicha ketma-ket kelishi kerak")
        self.assertEqual(response.data["results"][0]["name"], "Birinchi Restoran")

    def test_places_without_a_place_go_last(self):
        """Hali sharh olmagan joy tepaga chiqib ketmasligi kerak."""
        from rest_framework.test import APIClient

        fresh = self._business("Yangi Restoran")
        self._review(self.a, 5)

        response = APIClient().get("/api/businesses/?type=restaurant")
        names = [row["name"] for row in response.data["results"]]

        self.assertEqual(names[0], "Birinchi Restoran")
        self.assertEqual(names[-1], fresh.name)

    def test_ranks_have_no_gaps_when_a_place_is_hidden(self):
        """
        Yashirilgan joy o'rnini band qilib turmaydi.

        Aks holda ro'yxatda raqamlar 1, 2, 4 bo'lib sakrardi — 3-o'rin
        esa hech kimga ko'rinmaydigan joyda qolib ketardi.
        """
        c = self._business("Uchinchi Restoran")
        self._review(self.a, 5)
        self._review(self.b, 4)
        self._review(c, 3)

        self.b.is_visible = False
        self.b.save(update_fields=["is_visible"])

        self.a.refresh_from_db()
        self.b.refresh_from_db()
        c.refresh_from_db()
        self.assertEqual(self.b.rank, 0, "Yashiringan joyning o'rni bo'lmaydi")
        self.assertEqual([self.a.rank, c.rank], [1, 2])

        # Qaytib ochilsa — o'z o'rnini qaytarib oladi.
        self.b.is_visible = True
        self.b.save(update_fields=["is_visible"])

        self.b.refresh_from_db()
        c.refresh_from_db()
        self.assertEqual(self.b.rank, 2)
        self.assertEqual(c.rank, 3)

    def test_a_new_place_gets_a_place_without_waiting_for_a_review(self):
        """Yangi qo'shilgan joy sharh kutmasdan jadvalga tushadi."""
        self._review(self.a, 5)
        fresh = self._business("To'rtinchi Restoran")

        fresh.refresh_from_db()
        self.assertGreater(fresh.rank, 0)
