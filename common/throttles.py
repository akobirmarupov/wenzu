from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


class SMSVerificationThrottle(SimpleRateThrottle):
    scope = "sms_verify"

    def get_cache_key(self, request, view):
        phone = request.data.get("phone_number") or request.query_params.get("phone_number")
        if not phone:
            return None
        return self.cache_format % {"scope": self.scope, "ident": phone}


class ReservationCreateThrottle(ScopedRateThrottle):
    scope = "reservation_create"


class BusinessApplicationThrottle(ScopedRateThrottle):
    scope = "business_application"


class LoginThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        username = request.data.get("username", "anonymous")
        ident = f"{self.get_ident(request)}:{username}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class ReviewCreateThrottle(ScopedRateThrottle):
    scope = "review_create"