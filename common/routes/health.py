"""Sog'liq tekshiruvi — load balancer va monitoring uchun."""

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("common")


class HealthCheckAPIView(APIView):
    """
    GET /api/health/ — baza va kesh ishlayaptimi.

    Load balancer shu endpointga qarab serverni navbatga qo'shadi yoki
    chiqarib tashlaydi. Baza yiqilgan serverga trafik yubormaslik uchun
    ulanish HAQIQATAN tekshiriladi (shunchaki "200 OK" qaytarilmaydi).
    """

    permission_classes = [AllowAny]
    throttle_classes = []
    authentication_classes = []

    @extend_schema(responses={200: None, 503: None})
    def get(self, request):
        checks = {}

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = "ok"
        except Exception as exc:
            logger.error(f"Health check — baza xatosi: {exc}")
            checks["database"] = "error"

        try:
            cache.set("healthcheck", "1", 10)
            checks["cache"] = "ok" if cache.get("healthcheck") == "1" else "degraded"
        except Exception as exc:
            logger.error(f"Health check — kesh xatosi: {exc}")
            checks["cache"] = "error"

        healthy = checks["database"] == "ok"
        return Response(
            {
                "status": "healthy" if healthy else "unhealthy",
                "checks": checks,
                "version": settings.SPECTACULAR_SETTINGS["VERSION"],
            },
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
