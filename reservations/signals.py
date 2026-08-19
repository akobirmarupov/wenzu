from django.db.models.signals import post_save
from django.dispatch import receiver

from businesses.models import Business

from .models import Reservation


@receiver(post_save, sender=Reservation)
def sync_availability_booked_status(sender, instance, **kwargs):
    """
    Reservation yaratilganda yoki statusi o'zgarganda, bog'liq Availability
    yozuvining `is_booked` maydonini avtomatik moslashtiradi.

    MUHIM: bu faqat TO'YXONA uchun ishlaydi. To'yxonada bir kunda faqat
    bitta to'y bo'ladi, shuning uchun bron bo'lishi bilan butun kun band
    bo'lib qoladi.

    Restoranda esa bitta xona bir kunda bir nechta bronga ega bo'lishi
    mumkin (masalan 13:00-15:00 va 19:00-21:00), shuning uchun kunni
    butunlay band deb belgilash noto'g'ri bo'lardi — u yerda bandlik
    Reservation.start_time/end_time oralig'i bo'yicha hisoblanadi.

    Bu admin panel orqali qo'lda Reservation yaratilganda ham, API orqali
    yaratilganda ham bir xil ishlaydi.
    """
    availability = instance.availability
    if availability is None:
        return
    if instance.business.business_type != Business.TYPE_VENUE:
        return

    should_be_booked = instance.status != "cancelled"
    if availability.is_booked != should_be_booked:
        availability.is_booked = should_be_booked
        availability.save(update_fields=["is_booked"])
