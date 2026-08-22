"""
Sahifa marshrutlari.

Bu ilova HECH QANDAY ma'lumot bermaydi — faqat HTML skeletni qaytaradi.
Barcha ma'lumot brauzerda `/api/...` dan JWT bilan olinadi.

Nega shunday: backend allaqachon sof JSON API. Agar sahifalar server
tomonda ma'lumot bilan to'ldirilsa, bir xil mantiq ikki joyda (Django
view va API) takrorlanardi va mobil ilova bilan veb-sayt bir-biridan
farq qila boshlardi.
"""

from django.views.generic import TemplateView


class PageView(TemplateView):
    """Sahifa sarlavhasi va tanasi klassdan olinadigan umumiy asos."""

    page_title = ""
    body_class = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.page_title
        context["body_class"] = self.body_class
        return context


# ===================================================================
# Ommaviy sahifalar
# ===================================================================
class HomeView(PageView):
    template_name = "pages/public/home.html"
    page_title = "Bosh sahifa"
    body_class = "page-home"


class RestaurantListView(PageView):
    template_name = "pages/public/restaurants.html"
    page_title = "Restoranlar"
    body_class = "page-catalog"


class VenueListView(PageView):
    template_name = "pages/public/venues.html"
    page_title = "To'yxonalar"
    body_class = "page-catalog"


class BusinessDetailView(PageView):
    template_name = "pages/public/detail.html"
    page_title = "Batafsil"
    body_class = "page-detail"


class ProfileView(PageView):
    template_name = "pages/public/profile.html"
    page_title = "Profilim"
    body_class = "page-profile"


class MyBookingsView(PageView):
    """Bronlar — profil ichida emas, ALOHIDA sahifa."""

    template_name = "pages/public/bookings.html"
    page_title = "Bronlarim"
    body_class = "page-bookings"


# ===================================================================
# Autentifikatsiya
# ===================================================================
class LoginView(PageView):
    template_name = "pages/auth/login.html"
    page_title = "Kirish"
    body_class = "page-auth"


class RegisterView(PageView):
    template_name = "pages/auth/register.html"
    page_title = "Ro'yxatdan o'tish"
    body_class = "page-auth"


class VerifyPhoneView(PageView):
    template_name = "pages/auth/verify.html"
    page_title = "Telefonni tasdiqlash"
    body_class = "page-auth"


# ===================================================================
# Biznes egasi paneli
# ===================================================================
class OwnerOverviewView(PageView):
    template_name = "pages/owner/overview.html"
    page_title = "Umumiy ko'rinish"
    body_class = "page-dashboard"


class OwnerBookingsView(PageView):
    template_name = "pages/owner/bookings.html"
    page_title = "Bronlar"
    body_class = "page-dashboard"


class OwnerRoomsView(PageView):
    template_name = "pages/owner/rooms.html"
    page_title = "Xonalar"
    body_class = "page-dashboard"


class OwnerHallsView(PageView):
    template_name = "pages/owner/halls.html"
    page_title = "Zallar"
    body_class = "page-dashboard"


class OwnerMenuView(PageView):
    template_name = "pages/owner/menu.html"
    page_title = "Menyu"
    body_class = "page-dashboard"


class OwnerScheduleView(PageView):
    template_name = "pages/owner/schedule.html"
    page_title = "Bo'sh vaqtlar"
    body_class = "page-dashboard"


class OwnerReviewsView(PageView):
    template_name = "pages/owner/reviews.html"
    page_title = "Sharhlar"
    body_class = "page-dashboard"


class OwnerSubscriptionView(PageView):
    template_name = "pages/owner/subscription.html"
    page_title = "Obuna"
    body_class = "page-dashboard"


class OwnerSettingsView(PageView):
    template_name = "pages/owner/settings.html"
    page_title = "Sozlamalar"
    body_class = "page-dashboard"


# ===================================================================
# Super-admin paneli
# ===================================================================
class AdminOverviewView(PageView):
    template_name = "pages/admin/overview.html"
    page_title = "Umumiy ko'rinish"
    body_class = "page-dashboard"


class AdminApplicationsView(PageView):
    template_name = "pages/admin/applications.html"
    page_title = "Arizalar"
    body_class = "page-dashboard"


class AdminUsersView(PageView):
    template_name = "pages/admin/users.html"
    page_title = "Foydalanuvchilar"
    body_class = "page-dashboard"


class AdminBusinessesView(PageView):
    template_name = "pages/admin/businesses.html"
    page_title = "Bizneslar"
    body_class = "page-dashboard"


class AdminSubscriptionsView(PageView):
    template_name = "pages/admin/subscriptions.html"
    page_title = "Obunalar"
    body_class = "page-dashboard"


class AdminReservationsView(PageView):
    """Platformadagi barcha bronlar — admin faqat kuzatadi, tahrirlamaydi."""

    template_name = "pages/admin/reservations.html"
    page_title = "Barcha bronlar"
    body_class = "page-dashboard"


class AdminPaymentsView(PageView):
    """To'lovlar jurnali — Telegram orqali qabul qilingan to'lovlar."""

    template_name = "pages/admin/payments.html"
    page_title = "To'lovlar"
    body_class = "page-dashboard"


class AdminContentView(PageView):
    template_name = "pages/admin/content.html"
    page_title = "Kontent"
    body_class = "page-dashboard"


class AdminSettingsView(PageView):
    template_name = "pages/admin/settings.html"
    page_title = "Platforma sozlamalari"
    body_class = "page-dashboard"
