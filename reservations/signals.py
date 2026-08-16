from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Reservation


@receiver(post_save, sender=Reservation)
def sync_availability_booked_status(sender, instance, **kwargs):
    """
    Reservation yaratilganda yoki statusi o'zgarganda, bog'liq Availability
    yozuvining `is_booked` maydonini avtomatik moslashtiradi.

    - status != "cancelled" -> is_booked = True (bron qilingan, boshqa
      hech kim shu vaqtni qayta tanlay olmaydi)
    - status == "cancelled" -> is_booked = False (vaqt yana bo'shaydi)

    Bu admin panel orqali qo'lda Reservation yaratilganda ham, kelajakda
    API orqali yaratilganda ham bir xil ishlaydi.
    """
    availability = instance.availability
    should_be_booked = instance.status != "cancelled"

    if availability.is_booked != should_be_booked:
        availability.is_booked = should_be_booked
        availability.save(update_fields=["is_booked"])