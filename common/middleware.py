"""So'rovlarni kuzatish uchun middleware — har bir so'rovga yagona ID beradi."""

import logging
import time
import uuid
from contextvars import ContextVar

logger = logging.getLogger("common")

# ContextVar — thread va async-safe. Log yozuvchi funksiya `request` ni
# argument sifatida olmasa ham, joriy so'rov ID'sini shu yerdan oladi.
_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id.get()


class RequestIDFilter(logging.Filter):
    """Har bir log qatoriga joriy so'rov ID'sini qo'shadi."""

    def filter(self, record):
        record.request_id = get_request_id()
        return True


class RequestIDMiddleware:
    """
    Har bir so'rovga `X-Request-ID` beradi (yoki kelganini ishlatadi) va
    javob sarlavhasiga qaytaradi.

    Nega kerak: 10 000+ foydalanuvchi bo'lganda loglar aralashib ketadi.
    Mijoz "xato chiqdi" desa, u ko'rgan ID bo'yicha o'sha so'rovning
    barcha log qatorlarini bir zumda ajratib olish mumkin.
    """

    SLOW_REQUEST_MS = 1000

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        # Tashqaridan kelgan qiymatga ishonmaymiz — faqat qisqa, xavfsiz qismini olamiz.
        request_id = "".join(c for c in incoming if c.isalnum() or c in "-_")[:64] or uuid.uuid4().hex[:16]

        token = _request_id.set(request_id)
        request.request_id = request_id

        # Har bir so'rov o'z sozlamalar nusxasidan boshlasin — bir so'rovda
        # o'zgartirilgan sozlama keyingisiga "yopishib" qolmasligi uchun.
        from common.models import _solo_memo
        memo_token = _solo_memo.set(None)

        started = time.monotonic()
        try:
            response = self.get_response(request)
        finally:
            elapsed_ms = (time.monotonic() - started) * 1000
            _solo_memo.reset(memo_token)
            _request_id.reset(token)

        response["X-Request-ID"] = request_id

        if elapsed_ms > self.SLOW_REQUEST_MS:
            logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {elapsed_ms:.0f}ms status={response.status_code}"
            )
        return response
