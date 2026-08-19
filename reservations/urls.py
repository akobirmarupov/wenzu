from django.urls import path

from reservations.routes.availability import (
    BusinessAvailabilityAPIView,
    HallBusyDatesAPIView,
    OwnerAvailabilityDetailAPIView,
    OwnerAvailabilityGenerateAPIView,
    OwnerAvailabilityListAPIView,
    RoomBusyHoursAPIView,
)
from reservations.routes.reservation import (
    AdminReservationListAPIView,
    MyReservationListAPIView,
    OwnerReservationListAPIView,
    OwnerReservationStatusAPIView,
    ReservationCancelAPIView,
    ReservationCreateAPIView,
    ReservationDetailAPIView,
)

app_name = "reservations"

urlpatterns = [
    # --- ommaviy: bo'sh vaqtlar ---
    path("businesses/<uuid:business_id>/availability/", BusinessAvailabilityAPIView.as_view(), name="business-availability"),
    path("rooms/<uuid:room_id>/busy-hours/", RoomBusyHoursAPIView.as_view(), name="room-busy-hours"),
    path("halls/<uuid:hall_id>/busy-dates/", HallBusyDatesAPIView.as_view(), name="hall-busy-dates"),

    # --- mijoz ---
    path("reservations/", ReservationCreateAPIView.as_view(), name="reservation-create"),
    path("reservations/my/", MyReservationListAPIView.as_view(), name="reservation-my"),
    path("reservations/<uuid:pk>/", ReservationDetailAPIView.as_view(), name="reservation-detail"),
    path("reservations/<uuid:pk>/cancel/", ReservationCancelAPIView.as_view(), name="reservation-cancel"),

    # --- biznes egasi paneli ---
    path("owner/reservations/", OwnerReservationListAPIView.as_view(), name="owner-reservation-list"),
    path("owner/reservations/<uuid:pk>/status/", OwnerReservationStatusAPIView.as_view(), name="owner-reservation-status"),
    path("owner/availability/", OwnerAvailabilityListAPIView.as_view(), name="owner-availability-list"),
    path("owner/availability/generate/", OwnerAvailabilityGenerateAPIView.as_view(), name="owner-availability-generate"),
    path("owner/availability/<uuid:pk>/", OwnerAvailabilityDetailAPIView.as_view(), name="owner-availability-detail"),

    # --- admin paneli ---
    path("admin/reservations/", AdminReservationListAPIView.as_view(), name="admin-reservation-list"),
]
