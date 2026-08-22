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


# ===================================================================
# PWA — ilovani telefonga o'rnatish
#
# Uch fayl ham SHABLON orqali beriladi, oddiy statik fayl sifatida
# emas. Ikki sabab:
#
#   1. `{% static %}` — productionda fayl nomlariga xesh qo'shiladi
#      (`icon-192.a1b2c3.png`). Qo'lda yozilgan manzil o'sha yerda
#      404 bo'lardi va ikonkasiz ilova o'rnatilmaydi.
#   2. Service worker keshining nomiga `asset_version` kiradi — kod
#      yangilanganda eski kesh o'zi o'chadi.
#
# Manzillar ILDIZDA turishi SHART: service worker faqat o'zi turgan
# papka va undan pastini boshqara oladi. `/static/sw.js` bo'lsa,
# u faqat `/static/...` ni ko'rardi — ya'ni sahifalarga ta'sir
# qilolmasdi va oflayn rejim ishlamasdi.
# ===================================================================
class ManifestView(TemplateView):
    """/manifest.webmanifest — ilova nomi, ikonkalari va rangi."""

    template_name = "pwa/manifest.webmanifest"
    content_type = "application/manifest+json"


class ServiceWorkerView(TemplateView):
    """/sw.js — oflayn rejim va o'rnatish uchun."""

    template_name = "pwa/sw.js"
    content_type = "application/javascript"

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        # Worker faylining O'ZI keshlanmasin: aks holda yangi versiya
        # chiqqanda brauzer eskisini ishlatishda davom etardi va
        # foydalanuvchi yangilanishni ko'rmasdi.
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response["Service-Worker-Allowed"] = "/"
        return response


class OfflineView(PageView):
    """Tarmoq uzilganda service worker shu sahifani ko'rsatadi."""

    template_name = "pages/public/offline.html"
    page_title = "Internet yo'q"
    body_class = "page-offline"
