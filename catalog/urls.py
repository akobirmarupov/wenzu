from django.urls import path

from catalog.routes.restaurant_menu_item import (
    BusinessRestaurantMenuAPIView,
    OwnerRestaurantMenuDetailAPIView,
    OwnerRestaurantMenuListCreateAPIView,
    ShowcaseRestaurantMenuAPIView,
)
from catalog.routes.venue_menu_item import (
    BusinessVenueMenuAPIView,
    OwnerVenueMenuDetailAPIView,
    OwnerVenueMenuListCreateAPIView,
    ShowcaseVenueMenuAPIView,
)

app_name = "catalog"

urlpatterns = [
    # --- ommaviy ---
    path("businesses/<uuid:business_id>/menu/", BusinessRestaurantMenuAPIView.as_view(), name="business-menu"),
    path("businesses/<uuid:business_id>/venue-menu/", BusinessVenueMenuAPIView.as_view(), name="business-venue-menu"),

    # --- bosh sahifa vitrinasi: butun platforma bo'yicha menyu ---
    path("menu/restaurant/", ShowcaseRestaurantMenuAPIView.as_view(), name="showcase-restaurant-menu"),
    path("menu/venue/", ShowcaseVenueMenuAPIView.as_view(), name="showcase-venue-menu"),

    # --- biznes egasi paneli ---
    path("owner/menu/restaurant/", OwnerRestaurantMenuListCreateAPIView.as_view(), name="owner-restaurant-menu-list"),
    path("owner/menu/restaurant/<uuid:pk>/", OwnerRestaurantMenuDetailAPIView.as_view(), name="owner-restaurant-menu-detail"),
    path("owner/menu/venue/", OwnerVenueMenuListCreateAPIView.as_view(), name="owner-venue-menu-list"),
    path("owner/menu/venue/<uuid:pk>/", OwnerVenueMenuDetailAPIView.as_view(), name="owner-venue-menu-detail"),
]
