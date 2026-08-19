"""
Celery vazifasini xavfsiz navbatga qo'yish.

Broker (Redis) o'chib qolgan bo'lsa `.delay()` istisno tashlaydi va agar
u tranzaksiya ichida chaqirilgan bo'lsa — butun bron/ariza bekor bo'lardi.
Xabarnoma yuborilmagani biznes amalini to'xtatmasligi kerak, shuning uchun
xatolik faqat logga yoziladi.
"""

import logging

logger = logging.getLogger("common")


def enqueue(task, *args, **kwargs):
    """Qaytaradi: navbatga qo'yildi (True) / qo'yilmadi (False)."""
    try:
        task.delay(*args, **kwargs)
        return True
    except Exception as exc:  # broker ishlamayapti, timeout va h.k.
        logger.warning(f"Vazifani navbatga qo'yib bo'lmadi ({task.name}): {exc}")
        return False
