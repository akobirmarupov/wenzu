from django.urls import path

from subscriptions.routes.payment_log import (
    AdminPaymentLogListCreateAPIView,
    OwnerPaymentLogListAPIView,
)
from subscriptions.routes.subscription import (
    AdminSubscriptionActivateAPIView,
    AdminSubscriptionExpireAPIView,
    AdminSubscriptionListAPIView,
    OwnerSubscriptionAPIView,
)
from subscriptions.routes.subscription_plan import (
    AdminSubscriptionPlanDetailAPIView,
    AdminSubscriptionPlanListCreateAPIView,
    SubscriptionPlanListAPIView,
)

app_name = "subscriptions"

urlpatterns = [
    # --- ommaviy ---
    path("subscription-plans/", SubscriptionPlanListAPIView.as_view(), name="plan-list"),

    # --- biznes egasi paneli ---
    path("owner/subscription/", OwnerSubscriptionAPIView.as_view(), name="owner-subscription"),
    path("owner/payments/", OwnerPaymentLogListAPIView.as_view(), name="owner-payments"),

    # --- admin paneli ---
    path("admin/subscriptions/", AdminSubscriptionListAPIView.as_view(), name="admin-subscription-list"),
    path("admin/subscriptions/<uuid:pk>/activate/", AdminSubscriptionActivateAPIView.as_view(), name="admin-subscription-activate"),
    path("admin/subscriptions/<uuid:pk>/expire/", AdminSubscriptionExpireAPIView.as_view(), name="admin-subscription-expire"),
    path("admin/subscription-plans/", AdminSubscriptionPlanListCreateAPIView.as_view(), name="admin-plan-list"),
    path("admin/subscription-plans/<uuid:pk>/", AdminSubscriptionPlanDetailAPIView.as_view(), name="admin-plan-detail"),
    path("admin/payments/", AdminPaymentLogListCreateAPIView.as_view(), name="admin-payment-list"),
]
