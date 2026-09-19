from django.urls import path
from django.views.generic import RedirectView

from web import views

app_name = "web"

urlpatterns = [
    # --- PWA ---
    #
    # ILDIZDA turishi shart: service worker o'zi turgan papkadan
    # pastini boshqaradi, `/static/sw.js` esa sahifalarga yeta olmasdi.
    path("manifest.webmanifest", views.ManifestView.as_view(), name="manifest"),
    path("sw.js", views.ServiceWorkerView.as_view(), name="service-worker"),
    path("oflayn/", views.OfflineView.as_view(), name="offline"),

    # --- ommaviy ---
    path("", views.HomeView.as_view(), name="home"),
    path("restoranlar/", views.RestaurantListView.as_view(), name="restaurants"),
    path("toyxonalar/", views.VenueListView.as_view(), name="venues"),
    path("biznes/<uuid:pk>/", views.BusinessDetailView.as_view(), name="business-detail"),
    path("profil/", views.ProfileView.as_view(), name="profile"),

    # Eski manzil — biznes ochish endi profil ichidagi "Obuna va Premium"
    # bo'limida. Sahifa olib tashlangan, lekin havola foydalanuvchining
    # xatcho'pida yoki tashqi saytda qolgan bo'lishi mumkin: 404 o'rniga
    # to'g'ri joyga olib boramiz.
    path(
        "biznes-ochish/",
        RedirectView.as_view(url="/profil/?tab=premium", permanent=True),
        name="open-business-legacy",
    ),
    path("bronlarim/", views.MyBookingsView.as_view(), name="my-bookings"),

    # --- autentifikatsiya ---
    #
    # BITTA sahifa. Google tugmasi hisob bo'lsa kiritadi, bo'lmasa
    # yaratadi — "ro'yxatdan o'tish" va "kirish" farqi yo'qoldi.
    path("kirish/", views.LoginView.as_view(), name="login"),

    # Eski manzillar. Havolalar xatcho'plarda, qidiruv natijalarida va
    # sayt ichida qolgan bo'lishi mumkin — 404 o'rniga to'g'ri joyga.
    path(
        "royxat/",
        RedirectView.as_view(url="/kirish/", permanent=True),
        name="register",
    ),
    path(
        "tasdiqlash/",
        RedirectView.as_view(url="/kirish/", permanent=True),
        name="verify",
    ),

    # --- biznes egasi paneli ---
    path("panel/", views.OwnerOverviewView.as_view(), name="owner-overview"),
    path("panel/bronlar/", views.OwnerBookingsView.as_view(), name="owner-bookings"),
    path("panel/xonalar/", views.OwnerRoomsView.as_view(), name="owner-rooms"),
    path("panel/zallar/", views.OwnerHallsView.as_view(), name="owner-halls"),
    path("panel/menyu/", views.OwnerMenuView.as_view(), name="owner-menu"),
    path("panel/jadval/", views.OwnerScheduleView.as_view(), name="owner-schedule"),
    path("panel/sharhlar/", views.OwnerReviewsView.as_view(), name="owner-reviews"),
    path("panel/obuna/", views.OwnerSubscriptionView.as_view(), name="owner-subscription"),
    path("panel/sozlamalar/", views.OwnerSettingsView.as_view(), name="owner-settings"),

    # --- super-admin paneli ---
    path("boshqaruv/", views.AdminOverviewView.as_view(), name="admin-overview"),
    path("boshqaruv/arizalar/", views.AdminApplicationsView.as_view(), name="admin-applications"),
    path("boshqaruv/foydalanuvchilar/", views.AdminUsersView.as_view(), name="admin-users"),
    path("boshqaruv/bizneslar/", views.AdminBusinessesView.as_view(), name="admin-businesses"),
    path("boshqaruv/obunalar/", views.AdminSubscriptionsView.as_view(), name="admin-subscriptions"),
    path("boshqaruv/bronlar/", views.AdminReservationsView.as_view(), name="admin-reservations"),
    path("boshqaruv/tolovlar/", views.AdminPaymentsView.as_view(), name="admin-payments"),
    path("boshqaruv/kontent/", views.AdminContentView.as_view(), name="admin-content"),
    path("boshqaruv/sozlamalar/", views.AdminSettingsView.as_view(), name="admin-settings"),
]
