from django.urls import path

from web import views

app_name = "web"

urlpatterns = [
    # --- ommaviy ---
    path("", views.HomeView.as_view(), name="home"),
    path("restoranlar/", views.RestaurantListView.as_view(), name="restaurants"),
    path("toyxonalar/", views.VenueListView.as_view(), name="venues"),
    path("biznes/<uuid:pk>/", views.BusinessDetailView.as_view(), name="business-detail"),
    path("profil/", views.ProfileView.as_view(), name="profile"),
    path("bronlarim/", views.MyBookingsView.as_view(), name="my-bookings"),
    path("biznes-ochish/", views.OpenBusinessView.as_view(), name="open-business"),

    # --- autentifikatsiya ---
    path("kirish/", views.LoginView.as_view(), name="login"),
    path("royxat/", views.RegisterView.as_view(), name="register"),
    path("tasdiqlash/", views.VerifyPhoneView.as_view(), name="verify"),

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
    path("boshqaruv/kontent/", views.AdminContentView.as_view(), name="admin-content"),
    path("boshqaruv/sozlamalar/", views.AdminSettingsView.as_view(), name="admin-settings"),
]
