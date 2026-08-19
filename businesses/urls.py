from django.urls import path

from businesses.routes.business import (
    AdminBusinessListAPIView,
    AdminBusinessToggleBlockAPIView,
    AdminOverviewAPIView,
    BusinessDetailAPIView,
    BusinessListAPIView,
    OwnerBusinessAPIView,
    OwnerOverviewAPIView,
)
from businesses.routes.business_application import (
    AdminApplicationApproveAPIView,
    AdminApplicationListAPIView,
    AdminApplicationRejectAPIView,
    BusinessApplicationCreateAPIView,
    MyBusinessApplicationAPIView,
)
from businesses.routes.business_photo import (
    BusinessPhotoListAPIView,
    OwnerBusinessPhotoDetailAPIView,
    OwnerBusinessPhotoListCreateAPIView,
)
from businesses.routes.hall import (
    BusinessHallListAPIView,
    OwnerHallDetailAPIView,
    OwnerHallListCreateAPIView,
)
from businesses.routes.room import (
    BusinessRoomListAPIView,
    OwnerRoomDetailAPIView,
    OwnerRoomListCreateAPIView,
)
from businesses.routes.venue_pricing import (
    BusinessPricingListAPIView,
    OwnerVenuePricingAPIView,
)

app_name = "businesses"

urlpatterns = [
    # --- ommaviy ---
    path("businesses/", BusinessListAPIView.as_view(), name="business-list"),
    path("businesses/<uuid:pk>/", BusinessDetailAPIView.as_view(), name="business-detail"),
    path("businesses/<uuid:business_id>/rooms/", BusinessRoomListAPIView.as_view(), name="business-rooms"),
    path("businesses/<uuid:business_id>/halls/", BusinessHallListAPIView.as_view(), name="business-halls"),
    path("businesses/<uuid:business_id>/photos/", BusinessPhotoListAPIView.as_view(), name="business-photos"),
    path("businesses/<uuid:business_id>/pricing/", BusinessPricingListAPIView.as_view(), name="business-pricing"),

    # --- ariza oqimi (oddiy foydalanuvchi) ---
    path("business-applications/", BusinessApplicationCreateAPIView.as_view(), name="application-create"),
    path("business-applications/my/", MyBusinessApplicationAPIView.as_view(), name="application-my"),

    # --- biznes egasi paneli ---
    path("owner/overview/", OwnerOverviewAPIView.as_view(), name="owner-overview"),
    path("owner/business/", OwnerBusinessAPIView.as_view(), name="owner-business"),
    path("owner/rooms/", OwnerRoomListCreateAPIView.as_view(), name="owner-room-list"),
    path("owner/rooms/<uuid:pk>/", OwnerRoomDetailAPIView.as_view(), name="owner-room-detail"),
    path("owner/halls/", OwnerHallListCreateAPIView.as_view(), name="owner-hall-list"),
    path("owner/halls/<uuid:pk>/", OwnerHallDetailAPIView.as_view(), name="owner-hall-detail"),
    path("owner/photos/", OwnerBusinessPhotoListCreateAPIView.as_view(), name="owner-photo-list"),
    path("owner/photos/<uuid:pk>/", OwnerBusinessPhotoDetailAPIView.as_view(), name="owner-photo-detail"),
    path("owner/pricing/", OwnerVenuePricingAPIView.as_view(), name="owner-pricing"),

    # --- admin paneli ---
    path("admin/overview/", AdminOverviewAPIView.as_view(), name="admin-overview"),
    path("admin/applications/", AdminApplicationListAPIView.as_view(), name="admin-application-list"),
    path("admin/applications/<uuid:pk>/approve/", AdminApplicationApproveAPIView.as_view(), name="admin-application-approve"),
    path("admin/applications/<uuid:pk>/reject/", AdminApplicationRejectAPIView.as_view(), name="admin-application-reject"),
    path("admin/businesses/", AdminBusinessListAPIView.as_view(), name="admin-business-list"),
    path("admin/businesses/<uuid:pk>/toggle-block/", AdminBusinessToggleBlockAPIView.as_view(), name="admin-business-toggle-block"),
]
