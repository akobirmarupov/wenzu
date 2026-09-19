"""
Foydalanuvchining ISHONCHLILIK bali — "Bit".

Nima uchun kerak. To'yxona yoki restoran egasi uchun eng qimmat narsa —
band qilingan, lekin kelinmagan kun. U o'sha kunni band deb belgilab,
boshqa mijozlarni rad etgan bo'ladi. Shuning uchun egasi bron so'rovini
ko'rganda uning kimdan kelganini bilishi kerak: bu odam ilgari bronini
bekor qilganmi yoki yo'q.

Qanday ishlaydi:

  · Yangi hisob 100 Bit bilan boshlanadi — hech kim gumon ostida emas.
  · Foydalanuvchi O'Z bronini bekor qilsa, 5 Bit ayiriladi.
  · Ball 1 Bitdan pastga tushmaydi: nol "hisob yo'q" degandek ko'rinardi,
    holbuki odam bor va u yana yaxshilanishi mumkin.

Joy egasi bronni rad etsa, mijozning bali TEGILMAYDI — bu uning aybi
emas. Ball faqat foydalanuvchining O'Z qaroridan kamayadi.
"""

TRUST_START = 100
TRUST_MIN = 1
TRUST_MAX = 100

# Bitta bekor qilishning narxi. Ya'ni 100 Bitdan "yomon" darajaga
# (50 Bit) tushish uchun 10 marta bekor qilish kerak — tasodifiy
# bitta holat odamning obro'sini buzmaydi.
TRUST_CANCEL_PENALTY = 5

# Darajalar — PASTDAN yuqoriga. Har bir qator: (eng kam bal, kod, nom, ohang).
#
# `tone` frontend uchun: nishonning rangi shunga qarab tanlanadi va
# rang qoidasi ikki joyda takrorlanmaydi.
TRUST_LEVELS = (
    (80, "excellent", "A'lo", "ok"),
    (65, "good", "Yaxshi", "info"),
    (50, "fair", "Qoniqarli", "warn"),
    (30, "poor", "Yomon", "warn"),
    (TRUST_MIN, "bad", "O'ta yomon", "danger"),
)


def clamp_bits(value) -> int:
    """Balni ruxsat etilgan oraliqqa qisadi."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = TRUST_START
    return max(TRUST_MIN, min(TRUST_MAX, value))


def level_for(bits: int) -> tuple[str, str, str]:
    """Baldan daraja: `(kod, nom, ohang)`."""
    bits = clamp_bits(bits)
    for threshold, code, label, tone in TRUST_LEVELS:
        if bits >= threshold:
            return code, label, tone
    # TRUST_LEVELS oxirgi qatori TRUST_MIN dan boshlanadi, ya'ni bu
    # yerga yetib kelinmaydi. Baribir qoldiramiz — ro'yxat tahrirlansa
    # funksiya `None` qaytarib qo'ymasin.
    return "bad", "O'ta yomon", "danger"


def describe(bits: int) -> dict:
    """Serializer va shablonlar uchun tayyor ko'rinish."""
    bits = clamp_bits(bits)
    code, label, tone = level_for(bits)
    return {"bits": bits, "level": code, "level_display": label, "tone": tone}
